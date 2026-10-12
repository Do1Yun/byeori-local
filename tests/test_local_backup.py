"""Backup, restore into a new directory, search rebuild and schema 6 migration."""
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

import pytest

from byeori.local.backup import BackupError, create_backup, restore_backup
from byeori.local.cli import main
from byeori.local.llm import ModelError
from byeori.local.service import LocalService
from byeori.local.store import (SCHEMA_VERSION, LocalStore, SchemaMigrationRequired, _apply,
                                migration_plan)
from test_local_integrity import NO_YEAR_TEI, WORK, Extractor, Model, lookup_for

SCHEMA_6_COLUMNS = ("worker_id", "attempt", "max_attempts", "heartbeat_at", "started_at",
                    "cancel_ack_at", "priority", "executor", "resumed_from", "error_code")


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))


def add_paper(store, path, name):
    pdf = path / f"{name}.pdf"
    pdf.write_bytes(f"%PDF-1.7\n{name}".encode())
    return store.add(pdf)["paper_id"]


class Broken(Model):
    def generate(self, system, prompt, *, think=None):
        raise ModelError("offline")


@pytest.fixture
def rich(tmp_path):
    """Active and past revisions, a retired document id, a failed job and a quarantined file."""
    store = LocalStore(tmp_path / "data")
    pid = add_paper(store, tmp_path, "paper")
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))
    first = service.process(pid)
    service.lookup = lookup_for([WORK])
    moved = service.refresh_metadata(pid)
    assert moved["changed"] and moved["stem"] != first["stem"]
    other = add_paper(store, tmp_path, "other")
    service.backend = Broken()
    with pytest.raises(RuntimeError):
        service.process(other)
    service.backend = Model()
    store.write_new("scratch/left.txt", b"left behind")
    store.quarantine("scratch/left.txt")
    return service, pid, first, moved


def files_of(root):
    root = Path(root)
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file() and "catalog.sqlite3" not in path.name}


def downgrade_to_5(root):
    """The workspace as the release before schema 6 left it."""
    con = sqlite3.connect(Path(root) / "catalog.sqlite3")
    with con:
        con.execute("DROP INDEX jobs_claim")
        for table in ("workers", "checkpoints", "job_events"):
            con.execute(f"DROP TABLE {table}")
        for column in SCHEMA_6_COLUMNS:
            con.execute(f"ALTER TABLE jobs DROP COLUMN {column}")
        con.execute("UPDATE schema_version SET version=5")
    con.close()


def search_rows(store):
    with store.db() as db:
        docs = sorted(tuple(row) for row in db.execute("SELECT * FROM docs"))
        sections = sorted(tuple(row) for row in db.execute(
            "SELECT m.doc_type, m.doc_id, m.section, s.title, s.content FROM sections s "
            "JOIN section_map m ON m.rowid = s.rowid"))
    return docs, sections


def test_backup_writes_a_manifest_and_verifies_every_file(rich, tmp_path):
    service, pid, first, moved = rich
    result = create_backup(service.store.root, tmp_path / "backup")
    manifest = json.loads((tmp_path / "backup" / "manifest.json").read_text())
    assert result["verified"] and manifest["verified"] and manifest["verification_problems"] == []
    assert manifest["referenced_missing"] == [] and manifest["schema_version"] == SCHEMA_VERSION
    paths = {item["path"] for item in manifest["files"]}
    for revision in service.store.revisions(pid):
        assert revision["path"] in paths and revision["extraction_path"] in paths
    assert service.store.paper(pid)["pdf_path"] in paths
    assert any(path.startswith("quarantine/") for path in paths)
    assert not any(path.endswith((".partial", "-wal", "-shm")) for path in paths)
    assert manifest["counts"]["note_versions"] == 2 and manifest["counts"]["document_aliases"] == 1
    snapshot = sqlite3.connect(tmp_path / "backup" / "catalog.sqlite3")
    assert snapshot.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    snapshot.close()
    assert result["same_volume_as_source"] is True and "another device" in result["warning"]


def test_backup_refuses_a_non_empty_destination_or_one_inside_the_workspace(rich, tmp_path):
    service, *_ = rich
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("mine")
    with pytest.raises(BackupError) as raised:
        create_backup(service.store.root, occupied)
    assert raised.value.error_code == "destination_not_empty"
    assert [path.name for path in occupied.iterdir()] == ["keep.txt"]
    with pytest.raises(BackupError) as raised:
        create_backup(service.store.root, service.store.root / "backups")
    assert raised.value.error_code == "destination_inside_workspace"


def test_backups_taken_while_papers_are_published_restore_cleanly(tmp_path):
    store = LocalStore(tmp_path / "data")
    for number in range(12):
        add_paper(store, tmp_path, f"paper-{number}")
    service = LocalService(store, Model(), Extractor())
    finished = threading.Event()

    def publish_all():
        try:
            service.process_all()
        finally:
            finished.set()

    thread = threading.Thread(target=publish_all)
    thread.start()
    backups = []
    while not finished.is_set() or not backups:
        backups.append(create_backup(store.root, tmp_path / f"backup-{len(backups)}"))
    thread.join(30)
    for number, backup in enumerate(backups):
        assert backup["verified"] and backup["referenced_missing"] == [], backup
        report = restore_backup(tmp_path / f"backup-{number}", tmp_path / f"restored-{number}")
        assert report["status"] == "restored", report["checks"]


def test_restore_into_a_new_directory_reproduces_every_citation(rich, tmp_path):
    service, pid, first, moved = rich
    create_backup(service.store.root, tmp_path / "backup")
    before = files_of(service.store.root)
    report = restore_backup(tmp_path / "backup", tmp_path / "restored")
    assert report["status"] == "restored", report["checks"]
    assert files_of(service.store.root) == before, "restoring changes nothing in the source"
    restored = LocalService(LocalStore(tmp_path / "restored", create=False), Model(), Extractor())
    for revision in service.store.revisions(pid):
        number = revision["revision_id"]
        assert restored.read(pid, revision=number)["note_sha256"] == revision["note_sha256"]
        assert restored.context(pid, "P0001", revision=number) == service.context(pid, "P0001", revision=number)
    assert restored.store.paper_for_stem(first["stem"]) == pid, "a retired document id still resolves"
    assert report["checks"]["search_smoke"] == {"checked": 1, "found": 1, "missing": []}
    assert restored.store.integrity_problems(deep=True) == []
    assert json.loads((tmp_path / "restored" / "RESTORED.json").read_text())["status"] == "restored"


def test_restore_refuses_an_existing_destination_and_a_tampered_backup(rich, tmp_path):
    service, *_ = rich
    create_backup(service.store.root, tmp_path / "backup")
    (tmp_path / "exists").mkdir()
    with pytest.raises(BackupError) as raised:
        restore_backup(tmp_path / "backup", tmp_path / "exists")
    assert raised.value.error_code == "destination_exists"
    manifest = json.loads((tmp_path / "backup" / "manifest.json").read_text())
    victim = tmp_path / "backup" / manifest["files"][0]["path"]
    victim.write_bytes(victim.read_bytes() + b"!")
    with pytest.raises(BackupError) as raised:
        restore_backup(tmp_path / "backup", tmp_path / "new")
    assert raised.value.error_code == "restore_verification_failed"
    assert raised.value.details == [{"path": manifest["files"][0]["path"], "problem": "size_mismatch"}]
    assert not (tmp_path / "new").exists()


def test_restore_marks_running_jobs_interrupted_and_keeps_queued(rich, tmp_path):
    service, pid, *_ = rich
    running = service.store.start(pid)
    queued = service.store.enqueue("note", paper_id=pid)
    create_backup(service.store.root, tmp_path / "backup")
    report = restore_backup(tmp_path / "backup", tmp_path / "restored")
    restored = LocalStore(tmp_path / "restored", create=False)
    assert report["interrupted_jobs"] == [running]
    assert restored.job(running)["status"] == "interrupted"
    assert restored.job(running)["error_code"] == "restored_while_running"
    assert restored.job(queued)["status"] == "queued"
    assert service.store.job(running)["status"] == "running", "the source is not touched"


def test_restore_migrates_an_older_backup_and_refuses_a_newer_one(rich, tmp_path):
    service, pid, *_ = rich
    downgrade_to_5(service.store.root)
    create_backup(service.store.root, tmp_path / "old")
    report = restore_backup(tmp_path / "old", tmp_path / "restored")
    assert report["status"] == "restored" and report["migration"] == {"from": 5, "to": SCHEMA_VERSION}
    with pytest.raises(BackupError) as raised:
        restore_backup(tmp_path / "old", tmp_path / "not-migrated", allow_migration=False)
    assert raised.value.error_code == "schema_migration_required"
    con = sqlite3.connect(service.store.root / "catalog.sqlite3")
    with con:
        con.execute("UPDATE schema_version SET version=99")
    con.close()
    create_backup(service.store.root, tmp_path / "newer")
    with pytest.raises(BackupError) as raised:
        restore_backup(tmp_path / "newer", tmp_path / "too-new")
    assert raised.value.error_code == "unsupported_schema" and not (tmp_path / "too-new").exists()


def test_reindex_rebuilds_search_after_index_rows_are_lost(rich):
    service, pid, first, moved = rich
    before = search_rows(service.store)
    with service.store.db() as db:
        db.execute("DELETE FROM sections")
        db.execute("DELETE FROM section_map")
        db.execute("DELETE FROM docs")
    assert any("search cannot reach" in problem for problem in service.store.integrity_problems())
    result = service.store.reindex()
    assert result["problems"] == [] and result["documents"] == [moved["stem"]]
    assert search_rows(service.store) == before, "the rebuilt index is the one publishing wrote"
    assert service.store.integrity_problems() == []
    assert [hit["doc_id"] for hit in service.store.search("BLEU")] == [moved["stem"]]


def test_migration_applies_create_table_statements_idempotently(rich):
    service, *_ = rich
    root = service.store.root
    downgrade_to_5(root)
    store = LocalStore(root)
    assert store.migrated_from == 5 and store.schema_version() == SCHEMA_VERSION
    with store.db() as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
    assert {"workers", "checkpoints", "job_events"} <= tables
    assert set(SCHEMA_6_COLUMNS) <= columns
    assert LocalStore(root).migrated_from is None
    assert all(job["attempt"] == 1 and job["executor"] is None for job in store.iter_jobs()), \
        "earlier jobs keep what they were: inline, first attempt"
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    with pytest.raises(ValueError, match="not idempotent"):
        _apply(con, "CREATE TABLE plain (a)")


def test_auto_migrate_off_refuses_and_plan_reports_without_writing(rich, monkeypatch, capsys):
    service, *_ = rich
    root = service.store.root
    downgrade_to_5(root)
    monkeypatch.setenv("BYEORI_LOCAL_AUTO_MIGRATE", "off")
    catalog = root / "catalog.sqlite3"
    unchanged = hashlib.sha256(catalog.read_bytes()).hexdigest()
    with pytest.raises(SchemaMigrationRequired, match="migrate --plan"):
        LocalStore(root)
    plan = migration_plan(root)
    assert plan["current"] == 5 and plan["target"] == SCHEMA_VERSION and list(plan["steps"]) == [6]
    assert plan["backup_recommended"] and not plan["up_to_date"]
    assert main(["--data-dir", str(root), "migrate", "--plan"]) == 0
    assert hashlib.sha256(catalog.read_bytes()).hexdigest() == unchanged, "a plan writes nothing"
    assert main(["--data-dir", str(root), "migrate", "--apply"]) == 0
    applied = json.loads(capsys.readouterr().out.split("\n}\n")[-2] + "\n}")
    assert applied["from"] == 5 and applied["to"] == SCHEMA_VERSION and applied["migrated"]
    assert LocalStore(root, migrate=False).schema_version() == SCHEMA_VERSION


def test_wal_is_enabled_so_readers_do_not_wait_for_a_writer(rich):
    service, *_ = rich
    assert service.store.journal_mode() == "wal"
    writer = sqlite3.connect(service.store.root / "catalog.sqlite3")
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("UPDATE papers SET title=title")
    try:
        reader = sqlite3.connect(service.store.root / "catalog.sqlite3", timeout=0)
        assert reader.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 2
        reader.close()
    finally:
        writer.rollback()
        writer.close()


def test_metadata_and_revalidate_jobs_leave_receipts(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "data")
    pid = add_paper(store, tmp_path, "paper")
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))
    service.process(pid)
    service.lookup = lookup_for([WORK])

    def refused(*args, **kwargs):
        raise ValueError("injected publication failure")

    with monkeypatch.context() as patch:
        patch.setattr(store, "publish", refused)
        with pytest.raises(RuntimeError, match="injected") as raised:
            service.refresh_metadata(pid)
    failed = store.jobs()[0]
    assert failed["kind"] == "metadata" and failed["status"] == "failed"
    receipt = json.loads(store.path(f"runs/{failed['job_id']}/receipt.json").read_text())
    assert receipt["outcome"] == "failed" and receipt["kind"] == "metadata"
    assert raised.value.error_code == "failed"

    write = store.write_new

    def no_receipt(path, body):
        if path.endswith("/receipt.json"):
            raise OSError("disk full")
        return write(path, body)

    with monkeypatch.context() as patch:
        patch.setattr(store, "write_new", no_receipt)
        moved = service.refresh_metadata(pid)
    assert moved["changed"] and not store.path(f"runs/{moved['job_id']}/receipt.json").exists()
    repaired = store.reconcile_receipts()
    assert moved["job_id"] in repaired["recovered"]
    receipt = json.loads(store.path(f"runs/{moved['job_id']}/receipt.json").read_text())
    assert receipt["outcome"] == "succeeded" and receipt["kind"] == "metadata"
    assert receipt["execution_path"] is None


def test_cli_exit_codes_for_worker_backup_restore_submit_and_status(rich, tmp_path, monkeypatch, capsys):
    import byeori.local.cli as cli
    service, pid, *_ = rich
    root = str(service.store.root)
    assert main(["--data-dir", root, "backup", str(tmp_path / "backup")]) == 0
    capsys.readouterr()
    assert main(["--data-dir", root, "backup", str(tmp_path / "backup")]) == 1
    assert json.loads(capsys.readouterr().err)["error_code"] == "destination_not_empty"
    (tmp_path / "taken").mkdir()
    assert main(["restore", str(tmp_path / "backup"), str(tmp_path / "taken")]) == 1
    assert json.loads(capsys.readouterr().err)["error_code"] == "destination_exists"
    assert main(["restore", str(tmp_path / "backup"), str(tmp_path / "restored")]) == 0
    capsys.readouterr()

    monkeypatch.setattr(cli, "build_service", lambda *a, **k: service)
    assert main(["process", pid, "--submit"]) == 0
    submitted = json.loads(capsys.readouterr().out)
    assert submitted["status"] == "queued" and submitted["executor"] == "worker"
    assert submitted["diagnostic"].startswith("worker_unavailable")
    assert main(["status", submitted["job_id"]]) == 0
    [status] = json.loads(capsys.readouterr().out)
    assert [event["event"] for event in status["events"]] == ["enqueued"]
    assert status["worker"]["alive"] is False
    assert main(["worker", "--once"]) == 0
    ran = json.loads(capsys.readouterr().out)
    assert ran["stopped"] == "queue_empty" and ran["outcomes"] == {"succeeded": 1}
    assert service.store.job(submitted["job_id"])["status"] == "succeeded"
    assert main(["reindex"]) == 0


def test_moved_helpers_are_not_defined_twice():
    import byeori.local.service as module
    source = Path(module.__file__).read_text()
    for name in ("note_summary", "parse_frontmatter", "split_frontmatter"):
        assert f"\ndef {name}(" not in source, name
        assert getattr(module, name).__module__ == "byeori.local.evidence"
