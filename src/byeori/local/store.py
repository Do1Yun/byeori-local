"""A development workspace, independent of the upstream AWS catalog."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from datetime import UTC, datetime
import uuid

from byeori.wiki_search import search_index


def now():
    return datetime.now(UTC).isoformat()


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


class LocalStore:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY, title TEXT NOT NULL, pdf_path TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, paper_id TEXT, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, finished_at TEXT, error TEXT, result TEXT);
                CREATE TABLE IF NOT EXISTS notes (
                    paper_id TEXT PRIMARY KEY, path TEXT NOT NULL, job_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL, model TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS docs (
                    doc_type TEXT, doc_id TEXT, title TEXT, path TEXT, year TEXT,
                    journal TEXT, doi TEXT, category TEXT, s3_key TEXT,
                    PRIMARY KEY(doc_type, doc_id));
                CREATE VIRTUAL TABLE IF NOT EXISTS sections USING fts5(title, section, content,
                    tokenize='porter unicode61');
                CREATE TABLE IF NOT EXISTS section_map (
                    rowid INTEGER PRIMARY KEY, doc_type TEXT, doc_id TEXT, section TEXT);
            """)

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
        path = self.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
        return path

    def add(self, pdf: Path, title: str | None = None):
        if pdf.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("PDF exceeds the 100 MiB intake limit")
        content = pdf.read_bytes()
        if not content.startswith(b"%PDF-"):
            raise ValueError("Input is not a PDF")
        paper_id = digest(content)
        relative = f"papers/{paper_id}/original.pdf"
        # Serialize publication with catalog insertion; a crash orphan is recoverable by hash.
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
            if existing:
                if digest(self.path(existing["pdf_path"]).read_bytes()) != paper_id:
                    raise ValueError("Stored original has changed; restore it before continuing")
                return dict(existing) | {"duplicate": True}
            path = self.path(relative)
            if path.exists():
                if digest(path.read_bytes()) != paper_id:
                    raise ValueError("Stored original hash mismatch")
            else:
                self.write_new(relative, content)
            row = (paper_id, title or pdf.stem, relative, now())
            db.execute("INSERT INTO papers VALUES (?,?,?,?)", row)
        return self.paper(paper_id) | {"duplicate": False}

    def paper(self, paper_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown paper ID")
        return dict(row)

    def papers(self):
        with self.db() as db:
            return [dict(row) for row in db.execute("SELECT p.*, n.path AS note_path FROM papers p "
                "LEFT JOIN notes n USING(paper_id) ORDER BY p.created_at DESC LIMIT 100")]

    def start(self, paper_id):
        job_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute("INSERT INTO jobs(job_id,paper_id,status,created_at) VALUES (?,?,?,?)",
                       (job_id, paper_id, "running", now()))
        return job_id

    def finish(self, job_id, status, result=None, error=None):
        with self.db() as db:
            db.execute("UPDATE jobs SET status=?, finished_at=?, result=?, error=? WHERE job_id=?",
                       (status, now(), json.dumps(result, ensure_ascii=False), error, job_id))

    def jobs(self, job_id=None):
        with self.db() as db:
            rows = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)) if job_id else db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 20")
            return [dict(row) for row in rows]

    def publish(self, paper, job_id, markdown, source_hash, model):
        paper_id = paper["paper_id"]
        relative = f"wiki/sources/{paper_id}/{job_id}.md"
        self.write_new(relative, markdown.encode("utf-8"))
        # Artifact is immutable. Readers see either the old complete index or the new one.
        with self.db() as db:
            db.execute("DELETE FROM sections WHERE rowid IN (SELECT rowid FROM section_map WHERE doc_id=?)", (paper_id,))
            db.execute("DELETE FROM section_map WHERE doc_id=?", (paper_id,))
            db.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?,?)",
                       ("note", paper_id, paper["title"], relative, "", "", "", "other", relative))
            matches = list(re.finditer(r"^## (.+)$", markdown, re.M))
            for i, match in enumerate(matches):
                body = markdown[match.end():matches[i+1].start() if i+1 < len(matches) else len(markdown)]
                cursor = db.execute("INSERT INTO sections(title,section,content) VALUES (?,?,?)",
                                    (paper["title"], match[1], body))
                db.execute("INSERT INTO section_map VALUES (?,?,?,?)", (cursor.lastrowid, "note", paper_id, match[1]))
            db.execute("INSERT OR REPLACE INTO notes VALUES (?,?,?,?,?)", (paper_id, relative, job_id, source_hash, model))
        return relative

    def search(self, query, limit=10):
        with self.db() as db:
            return search_index(db, query, limit, doc_type="note")

    def note(self, paper_id):
        self.paper(paper_id)
        with self.db() as db:
            row = db.execute("SELECT * FROM notes WHERE paper_id=?", (paper_id,)).fetchone()
        if row is None:
            raise ValueError("Paper has no published Evidence Note")
        return dict(row) | {"text": self.path(row["path"]).read_text(encoding="utf-8")}
