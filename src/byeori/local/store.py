"""A development workspace, independent of the upstream AWS catalog."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from datetime import UTC, datetime
import uuid

from byeori.wiki_search import search_index

SCHEMA_VERSION = 2
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "interrupted")
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY, title TEXT NOT NULL, pdf_path TEXT NOT NULL,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY, paper_id TEXT, status TEXT NOT NULL, stage TEXT,
    created_at TEXT NOT NULL, finished_at TEXT, error TEXT, result TEXT);
-- Every note ever published stays addressable: a citation written last month names the
-- revision it read, so it keeps resolving to the paragraph it actually cited.
CREATE TABLE IF NOT EXISTS note_versions (
    revision_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, job_id TEXT NOT NULL,
    path TEXT NOT NULL, note_sha256 TEXT NOT NULL, extraction_id TEXT NOT NULL,
    extraction_path TEXT NOT NULL, extraction_status TEXT NOT NULL, model TEXT NOT NULL,
    validation_level TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS note_versions_paper ON note_versions (paper_id, created_at);
CREATE TABLE IF NOT EXISTS notes (paper_id TEXT PRIMARY KEY, revision_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS docs (
    doc_type TEXT, doc_id TEXT, title TEXT, path TEXT, year TEXT,
    journal TEXT, doi TEXT, category TEXT, s3_key TEXT,
    PRIMARY KEY(doc_type, doc_id));
CREATE VIRTUAL TABLE IF NOT EXISTS sections USING fts5(title, section, content,
    tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS section_map (
    rowid INTEGER PRIMARY KEY, doc_type TEXT, doc_id TEXT, section TEXT);
CREATE INDEX IF NOT EXISTS section_map_doc ON section_map (doc_type, doc_id);
"""


def now():
    return datetime.now(UTC).isoformat()


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


class LocalStore:
    def __init__(self, root: Path, *, create=True):
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            if not create:
                raise ValueError(f"Workspace does not exist: {self.root}")
            self.root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            self._upgrade(db)
            db.executescript(SCHEMA)
            row = db.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                db.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise ValueError(f"Workspace schema is version {row['version']}, this release needs "
                                 f"{SCHEMA_VERSION}. Papers, notes and runs are untouched on disk; "
                                 "rerun process in a workspace created by this release.")

    @staticmethod
    def _upgrade(db):
        """Take a workspace from the release before revisions existed, or refuse to guess.

        An earlier workspace recorded only each paper's active note, so a published note cannot
        be given the revision and extraction identity a citation now needs. Its files stay where
        they are; only an empty catalog is carried forward.
        """
        tables = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables or "schema_version" in tables:
            return
        if "notes" in tables:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(notes)")}
            if "revision_id" not in columns:
                if db.execute("SELECT 1 FROM notes LIMIT 1").fetchone():
                    raise ValueError(
                        "This workspace was written before notes carried revisions, and it already "
                        "holds published notes. Every file is preserved; rerun process in a workspace "
                        "created by this release so each note gets a revision a citation can name.")
                db.execute("DROP TABLE notes")
        if "jobs" in tables and "stage" not in {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}:
            db.execute("ALTER TABLE jobs ADD COLUMN stage TEXT")

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.root / "catalog.sqlite3", timeout=30)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def path(self, relative: str):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("Path must stay inside the workspace")
        return path

    def write_new(self, relative, content: bytes):
        """Create a file that is either absent or complete: no reader sees a half-written artifact."""
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {relative}")
        staged = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
        try:
            with staged.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(staged, path)
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
        handle = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(handle)
        finally:
            os.close(handle)
        return path

    def quarantine(self, relative):
        """Move a file aside instead of deleting it; originals are never destroyed here."""
        source = self.path(relative)
        target = self.path(f"quarantine/{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-"
                           f"{uuid.uuid4().hex[:8]}-{source.name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return target.relative_to(self.root).as_posix()

    def add(self, pdf: Path, title: str | None = None):
        if pdf.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("PDF exceeds the 100 MiB intake limit")
        content = pdf.read_bytes()
        if not content.startswith(b"%PDF-"):
            raise ValueError("Input is not a PDF")
        paper_id = digest(content)
        relative = f"papers/{paper_id}/original.pdf"
        quarantined = None
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
            if existing:
                if digest(self.path(existing["pdf_path"]).read_bytes()) != paper_id:
                    raise ValueError("Stored original has changed; restore it before continuing")
                return dict(existing) | {"duplicate": True}
            path = self.path(relative)
            if path.exists() and digest(path.read_bytes()) != paper_id:
                # No catalog row names this file, so it is an interrupted intake, not an original.
                quarantined = self.quarantine(relative)
            if not path.exists():
                self.write_new(relative, content)
            row = (paper_id, title or pdf.stem, relative, now())
            db.execute("INSERT INTO papers VALUES (?,?,?,?)", row)
        result = self.paper(paper_id) | {"duplicate": False}
        return result | {"recovered_from": quarantined} if quarantined else result

    def paper(self, paper_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown paper ID")
        return dict(row)

    def papers(self):
        with self.db() as db:
            return [dict(row) for row in db.execute(
                "SELECT p.*, v.path AS note_path, v.revision_id, v.extraction_status FROM papers p "
                "LEFT JOIN notes n USING(paper_id) "
                "LEFT JOIN note_versions v ON v.revision_id = n.revision_id "
                "ORDER BY p.created_at DESC LIMIT 100")]

    def start(self, paper_id):
        job_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at) VALUES (?,?,?,?,?)",
                       (job_id, paper_id, "running", "start", now()))
        return job_id

    def finish(self, job_id, status, result=None, error=None, stage=None):
        if status not in JOB_STATUSES:
            raise ValueError(f"Job status must be one of {', '.join(JOB_STATUSES)}")
        with self.db() as db:
            self._record_terminal(db, job_id, status, result, error, stage)

    @staticmethod
    def _record_terminal(db, job_id, status, result, error, stage):
        db.execute("UPDATE jobs SET status=?, stage=?, finished_at=?, result=?, error=? WHERE job_id=?",
                   (status, stage, now(), json.dumps(result, ensure_ascii=False) if result else None,
                    error, job_id))

    def _record_success(self, db, job_id, result, stage="publish"):
        """The last write of a successful job; publish() calls it inside its own transaction."""
        self._record_terminal(db, job_id, "succeeded", result, None, stage)

    def jobs(self, job_id=None):
        with self.db() as db:
            rows = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)) if job_id else db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 20")
            return [dict(row) for row in rows]

    def publish(self, paper, job_id, markdown, *, extraction_id, extraction_path,
                extraction_status, model, validation_level, result):
        """Write the note, swap the index, move the active pointer and record the job's success.

        All four happen in one transaction, so a reader never finds a live note whose job is
        not recorded as succeeded, and a failure leaves the previous note serving searches.
        """
        paper_id = paper["paper_id"]
        revision_id = job_id
        relative = f"wiki/sources/{paper_id}/{revision_id}.md"
        body = markdown.encode("utf-8")
        self.write_new(relative, body)
        with self.db() as db:
            db.execute("DELETE FROM sections WHERE rowid IN "
                       "(SELECT rowid FROM section_map WHERE doc_type='note' AND doc_id=?)", (paper_id,))
            db.execute("DELETE FROM section_map WHERE doc_type='note' AND doc_id=?", (paper_id,))
            db.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?,?)",
                       ("note", paper_id, paper["title"], relative, "", "", "", "other", relative))
            matches = list(re.finditer(r"^## (.+)$", markdown, re.M))
            for i, match in enumerate(matches):
                end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
                cursor = db.execute("INSERT INTO sections(title,section,content) VALUES (?,?,?)",
                                    (paper["title"], match[1], markdown[match.end():end]))
                db.execute("INSERT INTO section_map VALUES (?,?,?,?)",
                           (cursor.lastrowid, "note", paper_id, match[1]))
            db.execute("INSERT INTO note_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (revision_id, paper_id, job_id, relative, digest(body), extraction_id,
                        extraction_path, extraction_status, model, validation_level, now()))
            db.execute("INSERT OR REPLACE INTO notes VALUES (?,?)", (paper_id, revision_id))
            self._record_success(db, job_id, result | {"revision_id": revision_id})
        return {"path": relative, "revision_id": revision_id}

    def search(self, query, limit=10):
        with self.db() as db:
            return search_index(db, query, limit, doc_type="note")

    def revisions(self, paper_id):
        self.paper(paper_id)
        with self.db() as db:
            active = db.execute("SELECT revision_id FROM notes WHERE paper_id=?", (paper_id,)).fetchone()
            rows = db.execute("SELECT * FROM note_versions WHERE paper_id=? ORDER BY created_at DESC",
                              (paper_id,))
            return [dict(row) | {"active": active is not None and row["revision_id"] == active[0]}
                    for row in rows]

    def note(self, paper_id, revision=None):
        """The paper's active note, or the exact revision a citation was written against."""
        self.paper(paper_id)
        with self.db() as db:
            if revision is None:
                row = db.execute(
                    "SELECT v.* FROM notes n JOIN note_versions v ON v.revision_id = n.revision_id "
                    "WHERE n.paper_id=?", (paper_id,)).fetchone()
                if row is None:
                    raise ValueError("Paper has no published Evidence Note")
            else:
                row = db.execute("SELECT * FROM note_versions WHERE revision_id=? AND paper_id=?",
                                 (revision, paper_id)).fetchone()
                if row is None:
                    raise ValueError("Unknown note revision for this paper")
        return dict(row) | {"text": self.path(row["path"]).read_text(encoding="utf-8")}

    def integrity_problems(self):
        """What a person should be told before trusting this workspace; cheap checks only."""
        problems = []
        with self.db() as db:
            for row in db.execute(
                    "SELECT n.paper_id, n.revision_id, v.path, j.status FROM notes n "
                    "LEFT JOIN note_versions v ON v.revision_id = n.revision_id "
                    "LEFT JOIN jobs j ON j.job_id = v.job_id"):
                if row["path"] is None:
                    problems.append(f"{row['paper_id']}: active revision {row['revision_id']} has no record")
                    continue
                if row["status"] != "succeeded":
                    problems.append(f"{row['paper_id']}: active note's job is {row['status']}, not succeeded")
                if not self.path(row["path"]).exists():
                    problems.append(f"{row['paper_id']}: active note file {row['path']} is missing")
            for row in db.execute("SELECT revision_id, path FROM note_versions"):
                if not self.path(row["path"]).exists():
                    problems.append(f"revision {row['revision_id']}: note file {row['path']} is missing")
            indexed = {row[0] for row in db.execute("SELECT DISTINCT doc_id FROM section_map "
                                                    "WHERE doc_type='note'")}
            active = {row[0] for row in db.execute("SELECT paper_id FROM notes")}
            for paper_id in indexed - active:
                problems.append(f"{paper_id}: indexed for search without an active note")
            for paper_id in active - indexed:
                problems.append(f"{paper_id}: has an active note that search cannot reach")
        return problems
