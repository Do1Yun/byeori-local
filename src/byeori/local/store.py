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

SCHEMA_VERSION = 6
JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled", "interrupted")
TERMINAL_STATUSES = ("succeeded", "failed", "cancelled", "interrupted")
JOB_KINDS = ("note", "question", "metadata", "revalidate")
# inline: run by the process that submitted it (the CLI in the foreground, or the MCP server's
# question thread). worker: left in the queue for `byeori-local worker`, which may be another
# process entirely. A row written before this column existed is inline.
EXECUTORS = ("inline", "worker")
QUESTION_PRIORITY = 10
# The worker writes a heartbeat every 15 seconds while it runs a job and while it waits.
WORKER_STALE_SECONDS = 60
INLINE_INTERRUPTED = "Worker stopped before completion; rerun process to retry"
ALTER_COLUMN = re.compile(r"ALTER TABLE (\w+) ADD COLUMN (\w+)\b", re.I)
# Columns added after a workspace may already hold notes, so they are added in place.
MIGRATIONS = {3: ["ALTER TABLE jobs ADD COLUMN kind TEXT",
                  "ALTER TABLE jobs ADD COLUMN request TEXT",
                  "ALTER TABLE jobs ADD COLUMN cancel_requested TEXT"],
              4: ["ALTER TABLE papers ADD COLUMN stem TEXT",
                  "ALTER TABLE docs ADD COLUMN work_ids TEXT",
                  "ALTER TABLE docs ADD COLUMN summary TEXT"],
              5: ["ALTER TABLE note_versions ADD COLUMN document_sha256 TEXT",
                  "ALTER TABLE jobs ADD COLUMN owner_token TEXT"],
              6: ["ALTER TABLE jobs ADD COLUMN worker_id TEXT",
                  "ALTER TABLE jobs ADD COLUMN attempt INTEGER NOT NULL DEFAULT 1",
                  "ALTER TABLE jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3",
                  "ALTER TABLE jobs ADD COLUMN heartbeat_at TEXT",
                  "ALTER TABLE jobs ADD COLUMN started_at TEXT",
                  "ALTER TABLE jobs ADD COLUMN cancel_ack_at TEXT",
                  "ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 0",
                  "ALTER TABLE jobs ADD COLUMN executor TEXT",
                  "ALTER TABLE jobs ADD COLUMN resumed_from TEXT",
                  "ALTER TABLE jobs ADD COLUMN error_code TEXT",
                  "CREATE INDEX IF NOT EXISTS jobs_claim ON jobs (status, executor, priority, created_at)",
                  "CREATE TABLE IF NOT EXISTS workers ("
                  " worker_id TEXT PRIMARY KEY, pid INTEGER NOT NULL, process_started TEXT,"
                  " hostname TEXT, code_version TEXT, started_at TEXT NOT NULL,"
                  " heartbeat_at TEXT NOT NULL, state TEXT NOT NULL, current_job_id TEXT,"
                  " stopped_at TEXT)",
                  "CREATE TABLE IF NOT EXISTS checkpoints ("
                  " checkpoint_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, stage TEXT NOT NULL,"
                  " key_sha256 TEXT NOT NULL, job_id TEXT NOT NULL, created_at TEXT NOT NULL,"
                  " files TEXT NOT NULL, meta TEXT NOT NULL)",
                  "CREATE INDEX IF NOT EXISTS checkpoints_key ON checkpoints (paper_id, stage, key_sha256)",
                  "CREATE TABLE IF NOT EXISTS job_events ("
                  " event_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,"
                  " at TEXT NOT NULL, event TEXT NOT NULL, worker_id TEXT, detail TEXT)",
                  "CREATE INDEX IF NOT EXISTS job_events_job ON job_events (job_id, event_id)"]}
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY, title TEXT NOT NULL, pdf_path TEXT NOT NULL,
    created_at TEXT NOT NULL, stem TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS papers_stem ON papers (stem);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY, paper_id TEXT, status TEXT NOT NULL, stage TEXT,
    created_at TEXT NOT NULL, finished_at TEXT, error TEXT, result TEXT,
    kind TEXT, request TEXT, cancel_requested TEXT, owner_token TEXT,
    worker_id TEXT, attempt INTEGER NOT NULL DEFAULT 1, max_attempts INTEGER NOT NULL DEFAULT 3,
    heartbeat_at TEXT, started_at TEXT, cancel_ack_at TEXT, priority INTEGER NOT NULL DEFAULT 0,
    executor TEXT, resumed_from TEXT, error_code TEXT);
CREATE INDEX IF NOT EXISTS jobs_queue ON jobs (kind, status, created_at);
CREATE INDEX IF NOT EXISTS jobs_claim ON jobs (status, executor, priority, created_at);
-- The worker that holds .worker.lock, and when it last said it was alive.
CREATE TABLE IF NOT EXISTS workers (
    worker_id TEXT PRIMARY KEY, pid INTEGER NOT NULL, process_started TEXT, hostname TEXT,
    code_version TEXT, started_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL,
    state TEXT NOT NULL, current_job_id TEXT, stopped_at TEXT);
-- A stage of a paper's processing that a later job may read instead of computing again. The
-- files stay in the run that wrote them; a checkpoint only points at them, with their hashes.
CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL, stage TEXT NOT NULL,
    key_sha256 TEXT NOT NULL, job_id TEXT NOT NULL, created_at TEXT NOT NULL,
    files TEXT NOT NULL, meta TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS checkpoints_key ON checkpoints (paper_id, stage, key_sha256);
CREATE TABLE IF NOT EXISTS job_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, at TEXT NOT NULL,
    event TEXT NOT NULL, worker_id TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS job_events_job ON job_events (job_id, event_id);
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


class SchemaMigrationRequired(ValueError):
    error_code = "schema_migration_required"


class StaleLease(RuntimeError):
    """A worker tried to change a job it no longer owns."""
    error_code = "stale_lease"


def now():
    return datetime.now(UTC).isoformat()


def _event(db, job_id, event, worker_id=None, detail=None):
    db.execute("INSERT INTO job_events(job_id,at,event,worker_id,detail) VALUES (?,?,?,?,?)",
               (job_id, now(), event, worker_id,
                json.dumps(detail, ensure_ascii=False) if detail is not None else None))


def _apply(db, statement):
    """One migration statement, safe to apply to a workspace that already has its effect."""
    column = ALTER_COLUMN.match(statement)
    if column:
        table, name = column.groups()
        if name not in {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}:
            db.execute(statement)
    elif "IF NOT EXISTS" in statement.upper():
        db.execute(statement)
    else:
        raise ValueError(f"Migration statement is not idempotent: {statement[:60]}")


def migration_plan(root):
    """What opening this workspace would change, read without changing anything."""
    path = Path(root).expanduser().resolve() / "catalog.sqlite3"
    if not path.exists():
        raise ValueError(f"No catalog at {path}")
    try:
        con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        con.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        # A WAL database whose shared-memory file is gone cannot be opened read-only; a normal
        # connection that only reads changes nothing either.
        con = sqlite3.connect(path)
    try:
        has_version = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND "
                                  "name='schema_version'").fetchone()
        row = con.execute("SELECT version FROM schema_version").fetchone() if has_version else None
        journal = con.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        con.close()
    current = row[0] if row else None
    steps = ({step: MIGRATIONS[step] for step in range(current + 1, SCHEMA_VERSION + 1)
              if step in MIGRATIONS} if current is not None and current < SCHEMA_VERSION else {})
    return {"workspace": str(path.parent), "current": current, "target": SCHEMA_VERSION,
            "up_to_date": current == SCHEMA_VERSION,
            "unsupported": current is not None and current > SCHEMA_VERSION,
            "steps": steps, "journal_mode": journal, "backup_recommended": bool(steps)}


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


def code_version():
    """The release and, when this runs from a checkout, the commit that is doing the work."""
    try:
        from importlib.metadata import version
        package = version("byeori")
    except Exception:                                   # noqa: BLE001 - informational only
        package = None
    commit = None
    try:
        result = subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[3]), "rev-parse",
                                 "--short", "HEAD"], capture_output=True, text=True, timeout=2,
                                check=False)
        commit = result.stdout.strip() or None if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"package": package, "git": commit}


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
    def __init__(self, root: Path, *, create=True, migrate=None, sweep_orphans=True):
        self.root = root.expanduser().resolve()
        if not self.root.is_dir():
            if not create:
                raise ValueError(f"Workspace does not exist: {self.root}")
            self.root.mkdir(parents=True, exist_ok=True)
        if migrate is None:
            migrate = os.environ.get("BYEORI_LOCAL_AUTO_MIGRATE", "on").lower() not in {"off", "0", "false"}
        self.migrated_from = None
        with self.db() as db:
            self._upgrade(db)
            # Migrate before the schema script runs: its indexes name columns a migration adds.
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND "
                          "name='schema_version'").fetchone():
                row = db.execute("SELECT version FROM schema_version").fetchone()
                if row and row["version"] != SCHEMA_VERSION:
                    if row["version"] < SCHEMA_VERSION and not migrate:
                        raise SchemaMigrationRequired(
                            f"Workspace schema is {row['version']} and this release reads "
                            f"{SCHEMA_VERSION}; run 'byeori-local migrate --plan', back the "
                            "workspace up, then 'byeori-local migrate --apply'")
                    self.migrated_from = self._migrate(db, row["version"])
            db.executescript(SCHEMA)
            if db.execute("SELECT version FROM schema_version").fetchone() is None:
                db.execute("INSERT INTO schema_version VALUES (?)", (SCHEMA_VERSION,))
        self._enable_wal()
        # Opening the workspace is when an orphan becomes visible, so it is also when it is
        # recorded as one: a reader must never be told a question is still waiting for an answer
        # that no process is going to write.
        if sweep_orphans:
            self.sweep_orphaned_questions()

    def _enable_wal(self):
        """Readers no longer wait for a writer: a worker, the MCP server and the CLI share it."""
        con = sqlite3.connect(self.root / "catalog.sqlite3", timeout=5)
        try:
            if con.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass                                   # another connection is busy; the next open retries
        finally:
            con.close()

    def journal_mode(self):
        with self.db() as db:
            return db.execute("PRAGMA journal_mode").fetchone()[0]

    def schema_version(self):
        with self.db() as db:
            return db.execute("SELECT version FROM schema_version").fetchone()["version"]

    @staticmethod
    def _migrate(db, version):  # noqa: C901
        """Carry a workspace forward in place, all steps or none. Notes, runs and originals are
        never rewritten. Returns the version it started from, or None if another process did it."""
        if version > SCHEMA_VERSION:
            raise ValueError(f"Workspace schema is version {version} and this release reads "
                             f"{SCHEMA_VERSION}; use the release that wrote it.")
        db.execute("BEGIN IMMEDIATE")
        try:
            # Another process may have migrated while this one waited for the write lock.
            version = db.execute("SELECT version FROM schema_version").fetchone()["version"]
            if version >= SCHEMA_VERSION:
                db.commit()
                return None
            for step in range(version + 1, SCHEMA_VERSION + 1):
                if step not in MIGRATIONS:
                    raise ValueError(f"No migration to schema version {step}; every file is "
                                     "preserved, so a workspace created by this release can "
                                     "republish from them.")
                for statement in MIGRATIONS[step]:
                    _apply(db, statement)
            db.execute("UPDATE schema_version SET version=?", (SCHEMA_VERSION,))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        return version

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

    def last_note_published(self, paper_id):
        """When a model-written note for this paper was last published; checkpoints older than
        that belong to finished work, and a paper processed again starts over."""
        with self.db() as db:
            row = db.execute("SELECT MAX(finished_at) AS at FROM jobs WHERE paper_id=? AND "
                             "status='succeeded' AND (kind IS NULL OR kind IN ('note','revalidate'))",
                             (paper_id,)).fetchone()
        return row["at"]

    def record_metadata_check(self, paper_id, resolved):
        with self.db() as db:
            db.execute("INSERT INTO metadata_checks VALUES (?,?,?,?,?)",
                       (uuid.uuid4().hex, paper_id, resolved["state"], now(),
                        json.dumps(resolved, ensure_ascii=False)))

    TERMINAL = TERMINAL_STATUSES

    def start(self, paper_id, kind="note"):
        """A job this process runs at once, in the foreground."""
        if kind not in JOB_KINDS:
            raise ValueError(f"Job kind must be one of {', '.join(JOB_KINDS)}")
        job_id, started = uuid.uuid4().hex, now()
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind,executor,"
                       "started_at,heartbeat_at) VALUES (?,?,?,?,?,?,?,?,?)",
                       (job_id, paper_id, "running", "start", started, kind, "inline", started, started))
            _event(db, job_id, "started", detail={"kind": kind, "executor": "inline"})
        return job_id

    # --- the worker queue ----------------------------------------------------------------

    def enqueue(self, kind, *, paper_id=None, request=None, priority=None, executor="worker",
                resumed_from=None, attempt=1, max_attempts=3):
        """A queued job for `byeori-local worker`; nothing runs until a worker claims it."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._enqueue(db, kind, paper_id=paper_id, request=request, priority=priority,
                                 executor=executor, resumed_from=resumed_from, attempt=attempt,
                                 max_attempts=max_attempts)

    @staticmethod
    def _enqueue(db, kind, *, paper_id=None, request=None, priority=None, executor="worker",
                 resumed_from=None, attempt=1, max_attempts=3):
        if kind not in JOB_KINDS:
            raise ValueError(f"Job kind must be one of {', '.join(JOB_KINDS)}")
        if executor not in EXECUTORS:
            raise ValueError(f"Executor must be one of {', '.join(EXECUTORS)}")
        if priority is None:
            priority = QUESTION_PRIORITY if kind == "question" else 0
        job_id = uuid.uuid4().hex
        db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind,request,priority,"
                   "executor,resumed_from,attempt,max_attempts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (job_id, paper_id, "queued", "queued", now(), kind,
                    json.dumps(request, ensure_ascii=False) if request is not None else None,
                    priority, executor, resumed_from, attempt, max_attempts))
        _event(db, job_id, "enqueued", detail={"kind": kind, "executor": executor,
                                               "resumed_from": resumed_from, "attempt": attempt})
        return job_id

    def active_job(self, paper_id, kind):
        """A queued or running job of this kind for this paper, so it is not submitted twice."""
        with self.db() as db:
            row = db.execute("SELECT job_id FROM jobs WHERE paper_id=? AND kind=? AND status IN "
                             "('queued','running') ORDER BY created_at LIMIT 1",
                             (paper_id, kind)).fetchone()
        return row["job_id"] if row else None

    def queued_kinds(self):
        with self.db() as db:
            return {row["kind"] for row in db.execute(
                "SELECT DISTINCT kind FROM jobs WHERE status='queued' AND executor='worker'")}

    def claim_next(self, worker_id, kinds=None):
        """The worker's next job: questions before papers, then oldest first."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            query, params = "SELECT job_id FROM jobs WHERE status='queued' AND executor='worker'", []
            if kinds:
                query += f" AND kind IN ({','.join('?' * len(kinds))})"
                params.extend(kinds)
            row = db.execute(query + " ORDER BY priority DESC, created_at, job_id LIMIT 1",
                             params).fetchone()
            if row is None:
                return None
            started = now()
            claimed = db.execute("UPDATE jobs SET status='running', stage='claimed', worker_id=?, "
                                 "started_at=?, heartbeat_at=? WHERE job_id=? AND status='queued'",
                                 (worker_id, started, started, row["job_id"])).rowcount
            if claimed != 1:
                return None
            _event(db, row["job_id"], "claimed", worker_id=worker_id)
        return self.job(row["job_id"])

    def heartbeat(self, job_id, worker_id):
        beat = now()
        with self.db() as db:
            db.execute("UPDATE jobs SET heartbeat_at=? WHERE job_id=? AND worker_id=? "
                       "AND status='running'", (beat, job_id, worker_id))
            db.execute("UPDATE workers SET heartbeat_at=? WHERE worker_id=?", (beat, worker_id))

    def register_worker(self, worker_id, *, pid, process_started, hostname, code_version):
        started = now()
        with self.db() as db:
            db.execute("INSERT INTO workers(worker_id,pid,process_started,hostname,code_version,"
                       "started_at,heartbeat_at,state) VALUES (?,?,?,?,?,?,?,?)",
                       (worker_id, pid, process_started, hostname, code_version, started, started,
                        "starting"))

    def update_worker(self, worker_id, state, current_job_id=None):
        with self.db() as db:
            db.execute("UPDATE workers SET state=?, current_job_id=?, heartbeat_at=? WHERE worker_id=?",
                       (state, current_job_id, now(), worker_id))

    def stop_worker(self, worker_id, state="stopped"):
        stopped = now()
        with self.db() as db:
            db.execute("UPDATE workers SET state=?, current_job_id=NULL, stopped_at=?, heartbeat_at=? "
                       "WHERE worker_id=?", (state, stopped, stopped, worker_id))

    def worker_status(self):
        """The newest worker and whether it is alive: its process exists and it beat recently."""
        with self.db() as db:
            row = db.execute("SELECT * FROM workers ORDER BY started_at DESC, worker_id DESC "
                             "LIMIT 1").fetchone()
        if row is None:
            return {"worker_id": None, "alive": False, "state": None}
        age = (datetime.now(UTC) - datetime.fromisoformat(row["heartbeat_at"])).total_seconds()
        alive = (row["state"] != "stopped" and age < WORKER_STALE_SECONDS
                 and _alive(row["pid"], row["process_started"]))
        return dict(row) | {"alive": alive, "heartbeat_age_seconds": round(age, 1)}

    def event(self, job_id, event, *, worker_id=None, detail=None):
        with self.db() as db:
            _event(db, job_id, event, worker_id, detail)

    def events(self, job_id, limit=50):
        with self.db() as db:
            rows = db.execute("SELECT * FROM job_events WHERE job_id=? ORDER BY event_id DESC LIMIT ?",
                              (job_id, limit)).fetchall()
        return [dict(row) | {"detail": json.loads(row["detail"]) if row["detail"] else None}
                for row in reversed(rows)]

    def sweep_running_jobs(self, *, requeue=True):
        """Every job left running by a process that held .worker.lock, now that this one holds it.

        Holding the lock proves no other worker or foreground processing is alive. A worker's job
        is queued again as a new job that names it, up to its attempt limit; checkpoints make the
        retry cheap. A foreground job is not: the person who ran it reruns it. Questions the MCP
        server's own thread runs are not this lock's to judge.
        """
        interrupted, requeued = [], {}
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT * FROM jobs WHERE status='running' AND (executor='worker' OR "
                "((executor IS NULL OR executor='inline') AND (kind IS NULL OR kind != 'question')))"
            ).fetchall()
            for row in rows:
                interrupted.append(row["job_id"])
                again = self._interrupt(db, row, requeue=requeue)
                if again:
                    requeued[row["job_id"]] = again
        return {"interrupted": interrupted, "requeued": requeued}

    def mark_restored(self, backup_created_at):
        """A restored workspace runs nothing: what was running when the backup was taken is
        recorded as interrupted, and every worker it remembers as stopped."""
        ended = now()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            running = [row["job_id"] for row in db.execute("SELECT job_id FROM jobs WHERE status='running'")]
            for job_id in running:
                db.execute("UPDATE jobs SET status='interrupted', finished_at=?, error=?, "
                           "error_code='restored_while_running' WHERE job_id=?",
                           (ended, f"Running when the backup of {backup_created_at} was taken; "
                                   "restored, not resumed", job_id))
                _event(db, job_id, "interrupted", detail={"error_code": "restored_while_running"})
            db.execute("UPDATE workers SET state='stopped', current_job_id=NULL, "
                       "stopped_at=COALESCE(stopped_at, ?) WHERE state != 'stopped'", (ended,))
        return running

    def interrupt(self, job_id, *, lease=None, requeue=True, error=None):
        """A job its worker stopped at a safe point; returns the job that continues it, if any."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown job ID")
            if lease is not None and row["worker_id"] != lease:
                raise StaleLease(f"Job {job_id} is not owned by worker {lease}")
            if row["status"] != "running":
                return None
            return self._interrupt(db, row, requeue=requeue, error=error)

    def _interrupt(self, db, row, *, requeue, error=None):
        worker = row["executor"] == "worker"
        eligible = worker and requeue and row["cancel_requested"] is None
        again = eligible and (row["attempt"] or 1) < (row["max_attempts"] or 3)
        code = "max_attempts_exhausted" if eligible and not again else "worker_interrupted"
        if error is None:
            error = (INLINE_INTERRUPTED if not worker else
                     "The worker stopped before this job finished; "
                     + ("it was queued again" if again else "it was not queued again"))
        stopped = now()
        db.execute("UPDATE jobs SET status='interrupted', finished_at=?, error=?, error_code=?, "
                   "cancel_ack_at=CASE WHEN cancel_requested IS NOT NULL "
                   "THEN COALESCE(cancel_ack_at, ?) ELSE cancel_ack_at END WHERE job_id=?",
                   (stopped, error, code, stopped, row["job_id"]))
        _event(db, row["job_id"], "interrupted", row["worker_id"], {"error_code": code})
        if not again:
            return None
        follower = self._requeue_row(db, row)
        _event(db, row["job_id"], "requeued", detail={"as": follower})
        return follower

    def _requeue_row(self, db, row):
        request = row["request"]
        return self._enqueue(db, row["kind"] or "note", paper_id=row["paper_id"],
                             request=json.loads(request) if request else None,
                             priority=row["priority"], executor="worker",
                             resumed_from=row["job_id"], attempt=(row["attempt"] or 1) + 1,
                             max_attempts=row["max_attempts"] or 3)

    def requeue(self, job_id, *, reason):
        """A failed worker job whose cause was outside it, queued again within its attempt limit."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if (row is None or row["status"] != "failed" or row["executor"] != "worker"
                    or row["cancel_requested"] is not None
                    or (row["attempt"] or 1) >= (row["max_attempts"] or 3)):
                return None
            follower = self._requeue_row(db, row)
            _event(db, job_id, "requeued", detail={"as": follower, "reason": reason})
            return follower

    def start_question(self, question, paper_id=None, *, owner_token=None):
        """A question is recorded before the model is called, so it is never an unlogged answer."""
        job_id = uuid.uuid4().hex
        # The process that submits a question is the one that runs it, so its PID makes an
        # orphaned job recognisable after that process is gone.
        request = json.dumps({"question": question, "paper_id": paper_id, "pid": os.getpid(),
                              "process_started": process_identity(os.getpid())},
                             ensure_ascii=False)
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,stage,created_at,kind,request,"
                       "owner_token,executor,priority) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (job_id, paper_id, "queued", "queued", now(), "question", request, owner_token,
                        "inline", QUESTION_PRIORITY))
            _event(db, job_id, "enqueued", detail={"kind": "question", "executor": "inline"})
        return job_id

    def orphaned_questions(self):
        """Questions left behind by a process that is no longer running."""
        orphans = []
        for job in self.iter_jobs():
            if job["kind"] != "question" or job["status"] not in {"queued", "running"}:
                continue
            if job.get("executor") == "worker":
                # A worker's question outlives whoever submitted it; the worker judges its own.
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
                             "AND (executor IS NULL OR executor='inline') "
                             "AND owner_token IS ? ORDER BY created_at,job_id LIMIT 1",
                             (owner_token,)).fetchone()
            if row is None:
                return None
            started = now()
            db.execute("UPDATE jobs SET status='running', stage='answer', started_at=?, "
                       "heartbeat_at=? WHERE job_id=?", (started, started, row["job_id"]))
            _event(db, row["job_id"], "claimed", detail={"executor": "inline"})
        return self.job(row["job_id"])

    def request_cancel(self, job_id):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown job ID")
            if row["status"] not in TERMINAL_STATUSES and row["cancel_requested"] is None:
                db.execute("UPDATE jobs SET cancel_requested=? WHERE job_id=?", (now(), job_id))
                _event(db, job_id, "cancel_requested", detail={"status": row["status"]})
                if row["status"] == "queued":
                    self._record_terminal(db, job_id, "cancelled", None,
                                          "Cancelled before the model was called", "queued",
                                          error_code="cancelled")
        return self.job(job_id)

    def job(self, job_id):
        rows = self.jobs(job_id)
        if not rows:
            raise ValueError("Unknown job ID")
        return rows[0]

    def set_stage(self, job_id, stage, *, lease=None):
        """Where a running job has got to. A paper can take half an hour; a reader should see it.

        Returns when cancellation was requested, so the caller can stop before its next model call.
        """
        with self.db() as db:
            query, params = ("UPDATE jobs SET stage=?, heartbeat_at=? WHERE job_id=? AND "
                             "status='running'", [stage, now(), job_id])
            if lease is not None:
                query += " AND worker_id=?"
                params.append(lease)
            changed = db.execute(query, params).rowcount
            if lease is not None and changed != 1:
                raise StaleLease(f"Job {job_id} is not running under worker {lease}")
            if changed:
                _event(db, job_id, "stage", lease, {"stage": stage})
            row = db.execute("SELECT cancel_requested FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return row["cancel_requested"] if row else None

    def finish(self, job_id, status, result=None, error=None, stage=None, *, error_code=None,
               lease=None):
        if status not in JOB_STATUSES:
            raise ValueError(f"Job status must be one of {', '.join(JOB_STATUSES)}")
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status, worker_id FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown job ID")
            if lease is not None and row["worker_id"] != lease:
                raise StaleLease(f"Job {job_id} is not owned by worker {lease}")
            if row["status"] in TERMINAL_STATUSES and row["status"] != status:
                return
            self._record_terminal(db, job_id, status, result, error, stage, error_code=error_code)

    @staticmethod
    def _record_terminal(db, job_id, status, result, error, stage, *, error_code=None):
        finished = now()
        db.execute("UPDATE jobs SET status=?, stage=?, finished_at=?, result=?, error=?, error_code=?, "
                   "cancel_ack_at=CASE WHEN ?='cancelled' THEN COALESCE(cancel_ack_at, ?) "
                   "ELSE cancel_ack_at END WHERE job_id=?",
                   (status, stage, finished, json.dumps(result, ensure_ascii=False) if result else None,
                    error, error_code, status, finished, job_id))
        _event(db, job_id, "finished", detail={"status": status, "stage": stage, "error_code": error_code})

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
                previous_stem=None, document_sha256=None, lease=None):
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
            job = db.execute("SELECT status,cancel_requested,worker_id FROM jobs WHERE job_id=?",
                             (job_id,)).fetchone()
            if job is not None and lease is not None and job["worker_id"] != lease:
                raise StaleLease(f"Job {job_id} is not owned by worker {lease}")
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
            self._index_note(db, stem=stem, title=metadata.get("title") or paper["title"],
                             relative=relative, markdown=markdown, year=metadata.get("year", ""),
                             journal=metadata.get("journal", ""), doi=metadata.get("doi", ""),
                             work_id=metadata.get("work_id") or "", summary=summary)
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

    @staticmethod
    def _index_note(db, *, stem, title, relative, markdown, year, journal, doi, work_id, summary):
        """The catalogue row and one search section per level-2 heading of an active note."""
        db.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   ("note", stem, title, relative, year, journal, doi, work_id, "other",
                    relative, summary))
        matches = list(re.finditer(r"^## (.+)$", markdown, re.M))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            cursor = db.execute("INSERT INTO sections(title,section,content) VALUES (?,?,?)",
                                (title, match[1], markdown[match.end():end]))
            db.execute("INSERT INTO section_map VALUES (?,?,?,?)",
                       (cursor.lastrowid, "note", stem, match[1]))

    def reindex(self):
        """Rebuild search from the active revisions' own files, in one transaction.

        Only active notes are indexed: a retired revision must stay readable by the citations that
        name it, but it must not answer searches. A note whose file no longer matches its recorded
        hash is left out and reported, as search already refuses to return it.
        """
        from .evidence import note_summary, parse_frontmatter
        indexed, problems = [], []
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT n.paper_id, v.revision_id, v.path, v.note_sha256, p.stem, p.title "
                "FROM notes n JOIN note_versions v ON v.revision_id = n.revision_id "
                "JOIN papers p ON p.paper_id = n.paper_id ORDER BY n.paper_id").fetchall()
            db.execute("DELETE FROM sections WHERE rowid IN (SELECT rowid FROM section_map "
                       "WHERE doc_type='note')")
            db.execute("DELETE FROM section_map WHERE doc_type='note'")
            db.execute("DELETE FROM docs WHERE doc_type='note'")
            for row in rows:
                try:
                    body = self.path(row["path"]).read_bytes()
                except OSError as exc:
                    problems.append(f"{row['paper_id']}: {row['path']} unreadable ({type(exc).__name__})")
                    continue
                if digest(body) != row["note_sha256"]:
                    problems.append(f"{row['paper_id']}: note hash mismatch {row['path']}")
                    continue
                if not row["stem"]:
                    problems.append(f"{row['paper_id']}: active note has no document id")
                    continue
                markdown = body.decode("utf-8")
                fields, _ = parse_frontmatter(markdown)

                def text(key):
                    value = fields.get(key, "")
                    return "" if value is None else str(value)

                self._index_note(db, stem=row["stem"], title=fields.get("title") or row["title"],
                                 relative=row["path"], markdown=markdown, year=text("year"),
                                 journal=text("journal"), doi=text("doi"),
                                 work_id=text("work_ids"), summary=note_summary(markdown))
                indexed.append(row["stem"])
        return {"reindexed": len(indexed), "documents": indexed, "problems": problems}

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
            # Metadata and revalidation jobs call no model and leave no execution record; their
            # terminal receipt is still owed.
            if job["status"] not in TERMINAL_STATUSES or not (
                    execution.exists() or job["kind"] in ("metadata", "revalidate")):
                continue
            if terminal.exists():
                try:
                    if json.loads(terminal.read_text()).get("outcome") != job["status"]:
                        conflicts.append(job["job_id"])
                except (ValueError, OSError):
                    conflicts.append(job["job_id"])
                continue
            record = {"job_id": job["job_id"], "kind": job["kind"], "paper_id": job["paper_id"],
                      "outcome": job["status"], "stage": job["stage"],
                      "finished_at": job["finished_at"], "error": job["error"],
                      "error_code": job.get("error_code"), "reconciled_from_db": True,
                      "execution_path": f"{prefix}/execution.json" if execution.exists() else None}
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
