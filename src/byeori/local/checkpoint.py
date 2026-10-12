"""Stages of a paper's processing that a later job reads instead of computing again.

A checkpoint is a pointer, not a copy: the files stay in the run that wrote them, immutable, and
the checkpoint records their paths and hashes. It is keyed by everything the stage's output
depends on (the original, the extraction, the exact model and template, the prompts, the budget),
so a key that matches is the same computation, and anything that changed is a different key.
A file that no longer matches its hash is never reused, never deleted, and is reported.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from .store import digest, now

# Raise when parse_tei or the document.json shape changes: earlier extractions then stop matching.
EXTRACTION_SCHEMA = 1
STAGES = ("extraction", "digest", "digest-truncated")


def key(stage, **inputs):
    """The identity of one stage's computation."""
    if stage not in STAGES:
        raise ValueError(f"Checkpoint stage must be one of {', '.join(STAGES)}")
    packet = json.dumps({"stage": stage, **inputs}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(packet.encode()).hexdigest()


class Checkpoints:
    def __init__(self, store):
        self.store = store

    def lookup(self, paper_id, stage, key_sha256, *, after=None):
        """The newest checkpoint for this key whose files are all intact, with their bytes.

        after excludes checkpoints written before that time: a note published since then used
        them, and processing the paper again is a request to start over, not to resume.
        """
        query = "SELECT * FROM checkpoints WHERE paper_id=? AND stage=? AND key_sha256=?"
        params = [paper_id, stage, key_sha256]
        if after:
            query += " AND created_at > ?"
            params.append(after)
        with self.store.db() as db:
            rows = db.execute(query + " ORDER BY created_at DESC, checkpoint_id DESC", params).fetchall()
        for row in rows:
            files, contents, broken = json.loads(row["files"]), {}, None
            for item in files:
                try:
                    data = self.store.path(item["path"]).read_bytes()
                except (OSError, ValueError):
                    broken = {"path": item["path"], "problem": "missing"}
                    break
                if digest(data) != item["sha256"]:
                    broken = {"path": item["path"], "problem": "hash_mismatch"}
                    break
                contents[item["path"]] = data
            if broken:
                self.store.event(row["job_id"], "checkpoint_corrupt",
                                 detail={"checkpoint_id": row["checkpoint_id"], "stage": stage} | broken)
                continue
            return dict(row) | {"files": files, "meta": json.loads(row["meta"]), "contents": contents}
        return None

    def record(self, paper_id, stage, key_sha256, job_id, files=(), meta=None):
        """Point at files this job already wrote with write_new; returns the checkpoint ID."""
        checkpoint_id = uuid.uuid4().hex
        listed = [{"path": path, "sha256": digest(data), "bytes": len(data)} for path, data in files]
        with self.store.db() as db:
            db.execute("INSERT INTO checkpoints VALUES (?,?,?,?,?,?,?,?)",
                       (checkpoint_id, paper_id, stage, key_sha256, job_id, now(),
                        json.dumps(listed), json.dumps(meta or {}, ensure_ascii=False)))
        return checkpoint_id

    def for_paper(self, paper_id):
        with self.store.db() as db:
            rows = db.execute("SELECT * FROM checkpoints WHERE paper_id=? ORDER BY created_at DESC, "
                              "checkpoint_id DESC", (paper_id,)).fetchall()
        return [dict(row) | {"files": json.loads(row["files"]), "meta": json.loads(row["meta"])}
                for row in rows]
