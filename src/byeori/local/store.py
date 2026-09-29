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

SCHEMA_VERSION = 4
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "interrupted")
TERMINAL_STATUSES = ("succeeded", "failed", "cancelled", "interrupted")
# Columns added after a workspace may already hold notes, so they are added in place.
MIGRATIONS = {3: ["ALTER TABLE jobs ADD COLUMN kind TEXT",
                  "ALTER TABLE jobs ADD COLUMN request TEXT",
                  "ALTER TABLE jobs ADD COLUMN cancel_requested TEXT"],
              4: ["ALTER TABLE papers ADD COLUMN stem TEXT",
                  "ALTER TABLE docs ADD COLUMN work_ids TEXT",
                  "ALTER TABLE docs ADD COLUMN summary TEXT"]}
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY, title TEXT NOT NULL, pdf_path TEXT NOT NULL,
    created_at TEXT NOT NULL, stem TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS papers_stem ON papers (stem);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY, paper_id TEXT, status TEXT NOT NULL, stage TEXT,
    created_at TEXT NOT NULL, finished_at TEXT, error TEXT, result TEXT,
    kind TEXT, request TEXT, cancel_requested TEXT);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs (kind, status, created_at);
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
    journal TEXT, doi TEXT, work_ids TEXT, category TEXT, s3_key TEXT, summary TEXT,
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


def _alive(pid):
    """Whether that process still exists. A recycled PID would read as alive; on one machine
    running one workspace that is rarer than a crashed worker, and only delays a sweep."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    return True


class LocalStore:
    def __init__(self, root: Path, *, create=True):
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            if not create:
                raise ValueError(f"Workspace does not exist: {self.root}")
            self.root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            self._upgrade(db)
            # Migrate before the schema script runs: its indexes name columns a migration adds.
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND "
                          "name='schema_version'").fetchone():
                row = db.execute("SELECT version FROM schema_version").fetchone()
                if row and row["version"] != SCHEMA_VERSION:
                    self._migrate(db, row["version"])
            db.executescript(SCHEMA)
            if db.execute("SELECT version FROM schema_version").fetchone() is None:
                db.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
        # Opening the workspace is when an orphan becomes visible, so it is also when it is
        # recorded as one: a reader must never be told a question is still waiting for an answer
        # that no process is going to write.
        self.sweep_orphaned_questions()

    @staticmethod
    def _migrate(db, version):  # noqa: C901
        """Carry a workspace forward in place. Notes, runs and originals are never rewritten."""
        if version > SCHEMA_VERSION:
            raise ValueError(f"Workspace schema is version {version} and this release reads "
                             f"{SCHEMA_VERSION}; use the release that wrote it.")
        for step in range(version + 1, SCHEMA_VERSION + 1):
            if step not in MIGRATIONS:
                raise ValueError(f"No migration to schema version {step}; every file is preserved, "
                                 "so a workspace created by this release can republish from them.")
            for statement in MIGRATIONS[step]:
                table, column = statement.split()[2], statement.split()[-2]
                if column not in {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}:
                    db.execute(statement)
        db.execute("UPDATE schema_version SET version=?", (SCHEMA_VERSION,))

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
            # The stem is the extraction's to give, so it stays empty until the first note.
            db.execute("INSERT INTO papers(paper_id,title,pdf_path,created_at) VALUES (?,?,?,?)",
                       (paper_id, title or pdf.stem, relative, now()))
        result = self.paper(paper_id) | {"duplicate": False}
        return result | {"recovered_from": quarantined} if quarantined else result

    def paper(self, paper_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown paper ID")
        return dict(row)

    def paper_for_stem(self, stem):
        """The stored paper a wiki document id names; search and synthesis speak in stems."""
        with self.db() as db:
            row = db.execute("SELECT paper_id FROM papers WHERE stem=?", (stem,)).fetchone()
        return row["paper_id"] if row else None

    def papers(self):
        with self.db() as db:
            return [dict(row) for row in db.execute(
                "SELECT p.*, v.path AS note_path, v.revision_id, v.extraction_status FROM papers p "
                "LEFT JOIN notes n USING(paper_id) "
                "LEFT JOIN note_versions v ON v.revision_id = n.revision_id "
                "ORDER BY p.created_at DESC LIMIT 100")]

    TERMINAL = TERMINAL_STATUSES

    def start(self, paper_id):
        job_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind) "
                       "VALUES (?,?,?,?,?,?)", (job_id, paper_id, "running", "start", now(), "note"))
        return job_id

    def start_question(self, question, paper_id=None):
        """A question is recorded before the model is called, so it is never an unlogged answer."""
        job_id = uuid.uuid4().hex
        # The process that submits a question is the one that runs it, so its PID makes an
        # orphaned job recognisable after that process is gone.
        request = json.dumps({"question": question, "paper_id": paper_id, "pid": os.getpid()},
                             ensure_ascii=False)
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind,request) "
                       "VALUES (?,?,?,?,?,?,?)",
                       (job_id, paper_id, "queued", "queued", now(), "question", request))
        return job_id

    def orphaned_questions(self):
        """Questions left behind by a process that is no longer running."""
        orphans = []
        for job in self.jobs(limit=1000):
            if job["kind"] != "question" or job["status"] not in {"queued", "running"}:
                continue
            pid = (job["request"] or {}).get("pid") if isinstance(job["request"], dict) else None
            if pid is None or not _alive(pid):
                orphans.append(job["job_id"])
        return orphans

    def sweep_orphaned_questions(self):
        for job_id in self.orphaned_questions():
            self.finish(job_id, "interrupted", stage="answer",
                        error="The process that submitted this question ended before it was "
                              "answered; ask again")

    def claim_question(self):
        """Take the oldest queued question, one worker at a time."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE kind='question' AND status='queued' "
                             "ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE jobs SET status='running', stage='answer' WHERE job_id=?",
                       (row["job_id"],))
        return self.job(row["job_id"])

    def request_cancel(self, job_id):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown job ID")
            if row["status"] not in TERMINAL_STATUSES and row["cancel_requested"] is None:
                db.execute("UPDATE jobs SET cancel_requested=? WHERE job_id=?", (now(), job_id))
        return self.job(job_id)

    def job(self, job_id):
        rows = self.jobs(job_id)
        if not rows:
            raise ValueError("Unknown job ID")
        return rows[0]

    def set_stage(self, job_id, stage):
        """Where a running job has got to. A paper can take half an hour; a reader should see it."""
        with self.db() as db:
            db.execute("UPDATE jobs SET stage=? WHERE job_id=? AND status='running'",
                       (stage, job_id))

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

    def jobs(self, job_id=None, limit=20):
        with self.db() as db:
            rows = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)) if job_id else db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [self._job(row) for row in rows]

    @staticmethod
    def _job(row):
        """A job as a reader needs it: its request and its result read back as objects."""
        job = dict(row)
        job["kind"] = job.get("kind") or "note"
        for field in ("request", "result"):
            if job.get(field):
                try:
                    job[field] = json.loads(job[field])
                except json.JSONDecodeError:
                    pass
        return job

    def publish(self, paper, job_id, markdown, *, extraction_id, extraction_path,
                extraction_status, model, validation_level, result, stem, metadata, summary,
                previous_stem=None):
        """Write the note, swap the index, move the active pointer and record the job's success.

        All four happen in one transaction, so a reader never finds a live note whose job is
        not recorded as succeeded, and a failure leaves the previous note serving searches.
        """
        paper_id = paper["paper_id"]
        revision_id = job_id
        # The note's own folder is the wiki's document id; the SHA-256 stays the storage key.
        relative = f"wiki/sources/{stem}/{revision_id}.md"
        body = markdown.encode("utf-8")
        self.write_new(relative, body)
        with self.db() as db:
            # Both this document id and the paper's storage key: a workspace written before notes
            # had a document id indexed them under the SHA-256, and leaving those rows would keep
            # a retired note answering searches.
            for identity in dict.fromkeys(i for i in (stem, previous_stem, paper_id) if i):
                db.execute("DELETE FROM sections WHERE rowid IN (SELECT rowid FROM section_map "
                           "WHERE doc_type='note' AND doc_id=?)", (identity,))
                db.execute("DELETE FROM section_map WHERE doc_type='note' AND doc_id=?", (identity,))
                db.execute("DELETE FROM docs WHERE doc_type='note' AND doc_id=?", (identity,))
            db.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       ("note", stem, metadata.get("title") or paper["title"], relative,
                        metadata.get("year", ""), metadata.get("journal", ""),
                        metadata.get("doi", ""), metadata.get("work_id") or "", "other",
                        relative, summary))
            matches = list(re.finditer(r"^## (.+)$", markdown, re.M))
            for i, match in enumerate(matches):
                end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
                cursor = db.execute("INSERT INTO sections(title,section,content) VALUES (?,?,?)",
                                    (metadata.get("title") or paper["title"], match[1],
                                     markdown[match.end():end]))
                db.execute("INSERT INTO section_map VALUES (?,?,?,?)",
                           (cursor.lastrowid, "note", stem, match[1]))
            db.execute("INSERT INTO note_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (revision_id, paper_id, job_id, relative, digest(body), extraction_id,
                        extraction_path, extraction_status, model, validation_level, now()))
            db.execute("INSERT OR REPLACE INTO notes VALUES (?,?)", (paper_id, revision_id))
            db.execute("UPDATE papers SET stem=? WHERE paper_id=?", (stem, paper_id))
            self._record_success(db, job_id, result | {"revision_id": revision_id})
        return {"path": relative, "revision_id": revision_id, "stem": stem}

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
            active = {row[0] for row in db.execute(
                "SELECT p.stem FROM notes n JOIN papers p USING(paper_id) WHERE p.stem IS NOT NULL")}
            for stem in indexed - active:
                problems.append(f"{stem}: indexed for search without an active note")
            for stem in active - indexed:
                problems.append(f"{stem}: has an active note that search cannot reach")
        return problems
