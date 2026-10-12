"""A development workspace, independent of the upstream AWS catalog."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import base64
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from datetime import UTC, datetime
import uuid

from byeori.wiki_search import search_index

SCHEMA_VERSION = 5
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "interrupted")
TERMINAL_STATUSES = ("succeeded", "failed", "cancelled", "interrupted")
# Columns added after a workspace may already hold notes, so they are added in place.
MIGRATIONS = {3: ["ALTER TABLE jobs ADD COLUMN kind TEXT",
                  "ALTER TABLE jobs ADD COLUMN request TEXT",
                  "ALTER TABLE jobs ADD COLUMN cancel_requested TEXT"],
              4: ["ALTER TABLE papers ADD COLUMN stem TEXT",
                  "ALTER TABLE docs ADD COLUMN work_ids TEXT",
                  "ALTER TABLE docs ADD COLUMN summary TEXT"],
              5: ["ALTER TABLE note_versions ADD COLUMN document_sha256 TEXT",
                  "ALTER TABLE jobs ADD COLUMN owner_token TEXT"]}
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY, title TEXT NOT NULL, pdf_path TEXT NOT NULL,
    created_at TEXT NOT NULL, stem TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS papers_stem ON papers (stem);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY, paper_id TEXT, status TEXT NOT NULL, stage TEXT,
    created_at TEXT NOT NULL, finished_at TEXT, error TEXT, result TEXT,
    kind TEXT, request TEXT, cancel_requested TEXT, owner_token TEXT);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs (kind, status, created_at);
-- Every note ever published stays addressable: a citation written last month names the
-- revision it read, so it keeps resolving to the paragraph it actually cited.
CREATE TABLE IF NOT EXISTS note_versions (
    revision_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, job_id TEXT NOT NULL,
    path TEXT NOT NULL, note_sha256 TEXT NOT NULL, extraction_id TEXT NOT NULL,
    extraction_path TEXT NOT NULL, extraction_status TEXT NOT NULL, model TEXT NOT NULL,
    validation_level TEXT NOT NULL, created_at TEXT NOT NULL, document_sha256 TEXT);
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
CREATE TABLE IF NOT EXISTS document_aliases (
    alias TEXT PRIMARY KEY, paper_id TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS metadata_checks (
    check_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, state TEXT NOT NULL,
    checked_at TEXT NOT NULL, payload TEXT NOT NULL);
"""


def now():
    return datetime.now(UTC).isoformat()


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


def process_identity(pid):
    """A process's birth time, when the host can report it; unknown is never proof of death."""
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="],
                                capture_output=True, text=True, timeout=2, check=False)
        return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _alive(pid, started=None):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True
    actual = process_identity(pid) if started else None
    return not (started and actual and started != actual)


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
            # A hard link creates the final name exclusively. os.replace after an exists()
            # check can overwrite another writer's immutable artifact in the intervening gap.
            os.link(staged, path)
            staged.unlink()
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

    def papers_with_notes(self):
        with self.db() as db:
            return {row["paper_id"]: row["revision_id"] for row in db.execute("SELECT * FROM notes")}

    def paper_for_stem(self, stem):
        """The stored paper a wiki document id names; search and synthesis speak in stems."""
        with self.db() as db:
            row = db.execute("SELECT paper_id FROM papers WHERE stem=? UNION "
                             "SELECT paper_id FROM document_aliases WHERE alias=?",
                             (stem, stem)).fetchone()
        return row["paper_id"] if row else None

    def papers(self):
        return self.paper_page(limit=100)["papers"]

    @staticmethod
    def _page_bounds(cursor, limit, scope):
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("Page limit must be between 1 and 100")
        if cursor is None:
            return {"scope": scope, "watermark": now(), "last": None}
        try:
            value = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            if (value["scope"] != scope or not isinstance(value["watermark"], str)
                    or not isinstance(value["last"], list) or len(value["last"]) != 2
                    or not all(isinstance(v, str) for v in value["last"])):
                raise ValueError
            return value
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
            raise ValueError("Invalid cursor for this listing") from exc

    @staticmethod
    def _next_cursor(bounds, rows, limit, identity):
        if len(rows) <= limit:
            return None
        last = rows[limit - 1]
        return base64.urlsafe_b64encode(json.dumps(bounds | {
            "last": [last["created_at"], last[identity]]}).encode()).decode()

    def paper_page(self, *, limit=50, cursor=None, pending=False):
        bounds = self._page_bounds(cursor, limit, f"papers:{pending}")
        clauses, params = ["p.created_at <= ?"], [bounds["watermark"]]
        if bounds["last"]:
            clauses.append("(p.created_at,p.paper_id) < (?,?)")
            params.extend(bounds["last"])
        if pending:
            clauses.append("n.revision_id IS NULL")
        with self.db() as db:
            rows = [dict(row) for row in db.execute(
                "SELECT p.*, v.path AS note_path, v.revision_id, v.extraction_status FROM papers p "
                "LEFT JOIN notes n USING(paper_id) "
                "LEFT JOIN note_versions v ON v.revision_id = n.revision_id "
                "WHERE " + " AND ".join(clauses) +
                " ORDER BY p.created_at DESC,p.paper_id DESC LIMIT ?", params + [limit + 1])]
        return {"papers": rows[:limit],
                "next_cursor": self._next_cursor(bounds, rows, limit, "paper_id")}

    def iter_papers(self, *, pending=False):
        cursor = None
        while True:
            page = self.paper_page(limit=100, cursor=cursor, pending=pending)
            yield from page["papers"]
            cursor = page["next_cursor"]
            if cursor is None:
                return

    def record_metadata_check(self, paper_id, resolved):
        with self.db() as db:
            db.execute("INSERT INTO metadata_checks VALUES (?,?,?,?,?)",
                       (uuid.uuid4().hex, paper_id, resolved["state"], now(),
                        json.dumps(resolved, ensure_ascii=False)))

    TERMINAL = TERMINAL_STATUSES

    def start(self, paper_id):
        job_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind) "
                       "VALUES (?,?,?,?,?,?)", (job_id, paper_id, "running", "start", now(), "note"))
        return job_id

    def start_question(self, question, paper_id=None, *, owner_token=None):
        """A question is recorded before the model is called, so it is never an unlogged answer."""
        job_id = uuid.uuid4().hex
        # The process that submits a question is the one that runs it, so its PID makes an
        # orphaned job recognisable after that process is gone.
        request = json.dumps({"question": question, "paper_id": paper_id, "pid": os.getpid(),
                              "process_started": process_identity(os.getpid())},
                             ensure_ascii=False)
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind,request,owner_token) "
                       "VALUES (?,?,?,?,?,?,?,?)",
                       (job_id, paper_id, "queued", "queued", now(), "question", request, owner_token))
        return job_id

    def orphaned_questions(self):
        """Questions left behind by a process that is no longer running."""
        orphans = []
        for job in self.iter_jobs():
            if job["kind"] != "question" or job["status"] not in {"queued", "running"}:
                continue
            request = job["request"] if isinstance(job["request"], dict) else {}
            pid = request.get("pid")
            if not isinstance(pid, int) or pid <= 0 or not _alive(pid, request.get("process_started")):
                orphans.append(job["job_id"])
        return orphans

    def sweep_orphaned_questions(self):
        for job_id in self.orphaned_questions():
            self.finish(job_id, "interrupted", stage="answer",
                        error="The process that submitted this question ended before it was "
                              "answered; ask again")

    def claim_question(self, owner_token=None):
        """Take the oldest queued question, one worker at a time."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE kind='question' AND status='queued' "
                             "AND owner_token IS ? ORDER BY created_at,job_id LIMIT 1",
                             (owner_token,)).fetchone()
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
                if row["status"] == "queued":
                    self._record_terminal(db, job_id, "cancelled", None,
                                          "Cancelled before the model was called", "queued")
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
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown job ID")
            if row["status"] in TERMINAL_STATUSES and row["status"] != status:
                return
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
                "SELECT * FROM jobs ORDER BY created_at DESC,job_id DESC LIMIT ?", (limit,))
            return [self._job(row) for row in rows]

    def job_page(self, *, limit=20, cursor=None):
        bounds = self._page_bounds(cursor, limit, "jobs")
        clause, params = "created_at <= ?", [bounds["watermark"]]
        if bounds["last"]:
            clause += " AND (created_at,job_id) < (?,?)"
            params.extend(bounds["last"])
        with self.db() as db:
            rows = [self._job(row) for row in db.execute(
                "SELECT * FROM jobs WHERE " + clause +
                " ORDER BY created_at DESC,job_id DESC LIMIT ?", params + [limit + 1])]
        return {"jobs": rows[:limit], "next_cursor": self._next_cursor(bounds, rows, limit, "job_id")}

    def iter_jobs(self):
        cursor = None
        while True:
            page = self.job_page(limit=100, cursor=cursor)
            yield from page["jobs"]
            cursor = page["next_cursor"]
            if cursor is None:
                return

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
                previous_stem=None, document_sha256=None):
        """Stage a revision file, then atomically commit its pointer, index and job success.

        Files are immutable but outside SQLite's transaction; failed publication can leave an
        orphan file. It never replaces the previous active revision.
        """
        paper_id = paper["paper_id"]
        revision_id = job_id
        # The note's own folder is the wiki's document id; the SHA-256 stays the storage key.
        relative = f"wiki/sources/{stem}/{revision_id}.md"
        body = markdown.encode("utf-8")
        actual_document_hash = digest(self.path(extraction_path).read_bytes())
        if document_sha256 and actual_document_hash != document_sha256:
            raise ValueError("Extraction JSON hash mismatch before publication")
        self.write_new(relative, body)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            job = db.execute("SELECT status,cancel_requested FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if job is None or job["status"] != "running" or job["cancel_requested"]:
                raise ValueError("Job is no longer allowed to publish")
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
            db.execute("INSERT INTO note_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (revision_id, paper_id, job_id, relative, digest(body), extraction_id,
                        extraction_path, extraction_status, model, validation_level, now(),
                        actual_document_hash))
            if previous_stem and previous_stem != stem:
                db.execute("INSERT OR IGNORE INTO document_aliases VALUES (?,?,?)",
                           (previous_stem, paper_id, now()))
            db.execute("INSERT OR REPLACE INTO notes VALUES (?,?)", (paper_id, revision_id))
            db.execute("UPDATE papers SET stem=? WHERE paper_id=?", (stem, paper_id))
            self._record_success(db, job_id, result | {"revision_id": revision_id})
        return {"path": relative, "revision_id": revision_id, "stem": stem}

    def search(self, query, limit=10):
        with self.db() as db:
            hits = search_index(db, query, limit, doc_type="note")
        valid = []
        for hit in hits:
            paper_id = self.paper_for_stem(hit["doc_id"])
            try:
                note = self.note(paper_id)
                self.document(note)
            except (ValueError, OSError):
                continue
            valid.append(hit)
        return valid

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
        body = self.path(row["path"]).read_bytes()
        if digest(body) != row["note_sha256"]:
            raise ValueError(f"Note hash mismatch: {row['path']}")
        return dict(row) | {"text": body.decode("utf-8"),
                           "integrity_status": "verified" if row["document_sha256"] else "legacy_unverified"}

    def document(self, note):
        body = self.path(note["extraction_path"]).read_bytes()
        expected = note.get("document_sha256")
        if expected and digest(body) != expected:
            raise ValueError(f"Extraction JSON hash mismatch: {note['extraction_path']}")
        document = json.loads(body)
        if not isinstance(document, dict) or not isinstance(document.get("blocks"), list):
            raise ValueError("Invalid extraction JSON structure")
        if document.get("extraction_id") != note["extraction_id"] or document.get("pdf_sha256") != note["paper_id"]:
            raise ValueError("Extraction identity does not match this note revision")
        return document

    def reconcile_receipts(self):
        """Recover missing terminal records from DB truth; never overwrite existing history."""
        recovered, conflicts = [], []
        for job in self.iter_jobs():
            prefix = f"runs/{job['job_id']}"
            execution = self.path(f"{prefix}/execution.json")
            terminal = self.path(f"{prefix}/receipt.json")
            if not execution.exists() or job["status"] not in TERMINAL_STATUSES:
                continue
            if terminal.exists():
                try:
                    if json.loads(terminal.read_text()).get("outcome") != job["status"]:
                        conflicts.append(job["job_id"])
                except (ValueError, OSError):
                    conflicts.append(job["job_id"])
                continue
            record = {"job_id": job["job_id"], "paper_id": job["paper_id"],
                      "outcome": job["status"], "stage": job["stage"],
                      "finished_at": job["finished_at"], "error": job["error"],
                      "reconciled_from_db": True, "execution_path": f"{prefix}/execution.json"}
            try:
                self.write_new(f"{prefix}/receipt.json", json.dumps(record, indent=2).encode())
                recovered.append(job["job_id"])
            except FileExistsError:
                continue
        return {"recovered": recovered, "conflicts": conflicts}

    def integrity_problems(self, *, deep=False):
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
            for row in db.execute("SELECT * FROM note_versions"):
                if not self.path(row["path"]).exists():
                    problems.append(f"revision {row['revision_id']}: note file {row['path']} is missing")
                    continue
                try:
                    note = self.note(row["paper_id"], row["revision_id"])
                    self.document(note)
                    if deep:
                        tei = self.path(str(Path(row["extraction_path"]).parent / "grobid.tei.xml"))
                        if digest(tei.read_bytes()) != row["extraction_id"]:
                            raise ValueError(f"TEI hash mismatch: {tei.relative_to(self.root)}")
                except (ValueError, OSError) as exc:
                    problems.append(f"revision {row['revision_id']}: {exc}")
            if deep:
                for row in db.execute("SELECT paper_id,pdf_path FROM papers"):
                    try:
                        if digest(self.path(row["pdf_path"]).read_bytes()) != row["paper_id"]:
                            problems.append(f"Original PDF hash mismatch: {row['pdf_path']}")
                    except OSError:
                        problems.append(f"Original PDF missing: {row['pdf_path']}")
            indexed = {row[0] for row in db.execute("SELECT DISTINCT doc_id FROM section_map "
                                                    "WHERE doc_type='note'")}
            active = {row[0] for row in db.execute(
                "SELECT p.stem FROM notes n JOIN papers p USING(paper_id) WHERE p.stem IS NOT NULL")}
            for stem in indexed - active:
                problems.append(f"{stem}: indexed for search without an active note")
            for stem in active - indexed:
                problems.append(f"{stem}: has an active note that search cannot reach")
        return problems
