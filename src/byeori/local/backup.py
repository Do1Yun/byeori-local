"""A verified copy of a workspace, and restoring one into a new directory.

The catalog is copied first, through SQLite's backup API, so it is one consistent snapshot even
while a worker writes. Files are copied after it. That order is what makes the pair consistent
without stopping anything: every file the snapshot names was written before the transaction that
named it, and stored files are never changed or deleted, so each one is still there to copy. A
file written after the snapshot is copied too and listed as unreferenced.

A restore never writes over a workspace. It goes into a directory that does not exist yet, checks
every file against the manifest before creating it, and is complete only when the restored
workspace passes its own deep check and every active note answers a search for its title.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import time

from .store import SCHEMA_VERSION, LocalStore, code_version, now

BACKUP_FORMAT = 1
INCLUDED_DIRS = ("papers", "wiki", "runs", "quarantine", "logs", "reports", "templates")
SKIPPED_NAMES = {".DS_Store"}


class BackupError(ValueError):
    def __init__(self, message, error_code, details=None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or []


def _sha256(path):
    hashed = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def _copy(source, target):
    """Copy a file to a name that must not exist yet, hashing what was read."""
    hashed, size = hashlib.sha256(), 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, target.open("xb") as writer:
        for chunk in iter(lambda: reader.read(1 << 20), b""):
            hashed.update(chunk)
            writer.write(chunk)
            size += len(chunk)
        writer.flush()
        os.fsync(writer.fileno())
    shutil.copystat(source, target)
    return hashed.hexdigest(), size


def _staging(name):
    # write_new's half-written file, which becomes a real file only under its final name.
    return name in SKIPPED_NAMES or (name.startswith(".") and name.endswith(".partial"))


def _walk(root, top):
    """Files under one top-level folder, without following links out of the workspace."""
    files, links = [], []
    for directory, folders, names in os.walk(root / top, followlinks=False):
        folders.sort()
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                links.append(relative)
            elif not _staging(name):
                files.append(relative)
        links.extend((Path(directory) / folder).relative_to(root).as_posix()
                     for folder in folders if (Path(directory) / folder).is_symlink())
    return files, links


def _tables(con):
    return {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _referenced(con):
    """Every file the catalog names: originals, revisions, extractions, checkpoints."""
    tables, names = _tables(con), set()
    if "papers" in tables:
        names |= {row[0] for row in con.execute("SELECT pdf_path FROM papers")}
    if "note_versions" in tables:
        for path, extraction in con.execute("SELECT path, extraction_path FROM note_versions"):
            names |= {path, extraction, str(PurePosixPath(extraction).parent / "grobid.tei.xml")}
    if "checkpoints" in tables:
        for (files,) in con.execute("SELECT files FROM checkpoints"):
            names |= {item["path"] for item in json.loads(files)}
    return names


def _counts(con):
    tables = _tables(con)
    return {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("papers", "notes", "note_versions", "jobs", "checkpoints", "document_aliases")
            if table in tables}


def _schema(con):
    if "schema_version" not in _tables(con):
        return None
    row = con.execute("SELECT version FROM schema_version").fetchone()
    return row[0] if row else None


def _write_manifest(directory, manifest):
    temporary = directory / f".manifest.{os.getpid()}.tmp"
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, directory / "manifest.json")


def create_backup(root, destination, *, include_inbox=False):
    root = Path(root).expanduser().resolve()
    catalog = root / "catalog.sqlite3"
    if not catalog.is_file():
        raise BackupError(f"No workspace catalog at {catalog}", "not_a_workspace")
    destination = Path(destination).expanduser().resolve()
    if destination == root or destination.is_relative_to(root):
        raise BackupError("A backup cannot be written inside the workspace it copies",
                          "destination_inside_workspace")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise BackupError(f"Backup destination is not empty: {destination}", "destination_not_empty")
    started = time.monotonic()
    destination.mkdir(parents=True, exist_ok=True)

    # The catalog first: see the module docstring for why that order needs no lock.
    snapshot = destination / "catalog.sqlite3"
    source = sqlite3.connect(catalog, timeout=30)
    try:
        copy = sqlite3.connect(snapshot)
        try:
            source.backup(copy)
            copy.execute("PRAGMA journal_mode=DELETE")       # one self-contained file
            integrity = copy.execute("PRAGMA integrity_check").fetchone()[0]
            referenced, counts, schema = _referenced(copy), _counts(copy), _schema(copy)
            journal = source.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            copy.close()
    finally:
        source.close()
    if integrity != "ok":
        raise BackupError(f"The catalog snapshot failed its integrity check: {integrity}",
                          "backup_db_corrupt")

    files, links = [], []
    for top in INCLUDED_DIRS + (("inbox",) if include_inbox else ()):
        if not (root / top).is_dir():
            continue
        found, linked = _walk(root, top)
        links.extend(linked)
        for relative in found:
            sha256, size = _copy(root / relative, destination / relative)
            files.append({"path": relative, "sha256": sha256, "bytes": size})
    copied = {item["path"] for item in files}
    manifest = {"format": BACKUP_FORMAT, "created_at": now(), "source_root": str(root),
                "schema_version": schema, "code_version": code_version(), "journal_mode": journal,
                "db": {"file": "catalog.sqlite3", "sha256": _sha256(snapshot),
                       "bytes": snapshot.stat().st_size, "integrity_check": integrity},
                "files": files, "counts": counts,
                "referenced_missing": sorted(referenced - copied),
                "unreferenced": sorted(copied - referenced),
                "skipped_symlinks": links,
                "included_dirs": list(INCLUDED_DIRS) + (["inbox"] if include_inbox else []),
                "verified": False}
    _write_manifest(destination, manifest)

    # Read every copy back: a backup that was never read is a hope, not a backup.
    mismatched = [item["path"] for item in files
                  if _sha256(destination / item["path"]) != item["sha256"]]
    if _sha256(snapshot) != manifest["db"]["sha256"]:
        mismatched.append("catalog.sqlite3")
    manifest["verified"] = not mismatched
    manifest["verification_problems"] = mismatched
    _write_manifest(destination, manifest)

    same_volume = os.stat(destination).st_dev == os.stat(root).st_dev
    result = {"destination": str(destination), "schema_version": schema, "files": len(files),
              "bytes": sum(item["bytes"] for item in files) + manifest["db"]["bytes"],
              "counts": counts, "referenced_missing": manifest["referenced_missing"],
              "unreferenced": len(manifest["unreferenced"]), "skipped_symlinks": links,
              "verified": manifest["verified"], "verification_problems": mismatched,
              "same_volume_as_source": same_volume,
              "seconds": round(time.monotonic() - started, 2)}
    if same_volume:
        result["warning"] = ("This backup is on the same disk as the workspace; copy it to another "
                             "device to survive a disk failure")
    return result


def _verify_backup(backup_dir, manifest):
    problems = []
    entries = [{"path": manifest["db"]["file"], "sha256": manifest["db"]["sha256"],
                "bytes": manifest["db"]["bytes"]}] + manifest["files"]
    for item in entries:
        path = backup_dir / item["path"]
        if not path.is_file():
            problems.append({"path": item["path"], "problem": "missing"})
        elif path.stat().st_size != item["bytes"]:
            problems.append({"path": item["path"], "problem": "size_mismatch"})
        elif _sha256(path) != item["sha256"]:
            problems.append({"path": item["path"], "problem": "hash_mismatch"})
    return problems


def search_smoke(store):
    """Every active note must answer a search for its own title."""
    with store.db() as db:
        rows = db.execute("SELECT doc_id, title FROM docs WHERE doc_type='note' ORDER BY doc_id").fetchall()
    missing = []
    for row in rows:
        try:
            hits = store.search(row["title"] or row["doc_id"], 5)
        except ValueError:
            hits = []
        if row["doc_id"] not in {hit["doc_id"] for hit in hits}:
            missing.append(row["doc_id"])
    return {"checked": len(rows), "found": len(rows) - len(missing), "missing": missing}


def restore_backup(backup_dir, destination, *, allow_migration=True):
    backup_dir = Path(backup_dir).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.is_file():
        raise BackupError(f"No manifest.json in {backup_dir}", "not_a_backup")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != BACKUP_FORMAT:
        raise BackupError(f"Backup format {manifest.get('format')} is not {BACKUP_FORMAT}",
                          "unsupported_backup_format")
    if destination.exists():
        raise BackupError(f"Restore only into a new directory; {destination} exists",
                          "destination_exists")
    if destination.is_relative_to(backup_dir):
        raise BackupError("Restore destination cannot be inside the backup", "destination_inside_backup")
    if manifest.get("verified") is not True:
        raise BackupError("This backup failed its own verification when it was written",
                          "restore_verification_failed", manifest.get("verification_problems"))
    problems = _verify_backup(backup_dir, manifest)
    if problems:
        raise BackupError(f"{len(problems)} file(s) in the backup do not match its manifest; "
                          "nothing was restored", "restore_verification_failed", problems)
    schema = manifest.get("schema_version")
    if schema is not None and schema > SCHEMA_VERSION:
        raise BackupError(f"Backup schema {schema} is newer than this release's {SCHEMA_VERSION}",
                          "unsupported_schema")
    if schema is not None and schema < SCHEMA_VERSION and not allow_migration:
        raise BackupError(f"Backup schema {schema} needs migration to {SCHEMA_VERSION}",
                          "schema_migration_required")

    started = time.monotonic()
    destination.mkdir(parents=True)
    copy_problems = []
    for item in [{"path": manifest["db"]["file"], "sha256": manifest["db"]["sha256"]}] + manifest["files"]:
        sha256, _ = _copy(backup_dir / item["path"], destination / item["path"])
        if sha256 != item["sha256"]:
            copy_problems.append({"path": item["path"], "problem": "changed_while_copying"})

    store = LocalStore(destination, create=False, migrate=True, sweep_orphans=False)
    interrupted = store.mark_restored(manifest["created_at"])
    reindexed = store.reindex()
    integrity = store.integrity_problems(deep=True)
    smoke = search_smoke(store)
    complete = not (copy_problems or reindexed["problems"] or integrity or smoke["missing"])
    report = {"status": "restored" if complete else "restored_with_problems",
              "destination": str(destination), "backup_dir": str(backup_dir),
              "backup_created_at": manifest["created_at"], "restored_at": now(),
              "migration": ({"from": store.migrated_from, "to": SCHEMA_VERSION}
                            if store.migrated_from is not None else None),
              "files": len(manifest["files"]), "interrupted_jobs": interrupted,
              "checks": {"copy": copy_problems, "reindex": reindexed["problems"],
                         "integrity": integrity, "search_smoke": smoke},
              "seconds": round(time.monotonic() - started, 2)}
    store.write_new("RESTORED.json", json.dumps(report, ensure_ascii=False, indent=2).encode())
    return report
