"""Regression contracts from the 2026-10-01 review, using temporary data only."""
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

import httpx
import pytest

from byeori.local.cli import main, recorded_verdicts, review_markdown
from byeori.local.evidence import claim_fingerprint
from byeori.local.jobs import QuestionJobs
from byeori.local.llm import Generation, ModelError, ModelTimeout, OllamaBackend
from byeori.local.locking import runtime_path
from byeori.local.metadata import OpenAlexLookup
from byeori.local.service import LocalService
from byeori.local.store import LocalStore
from local_helpers import ollama_transport
from test_local_integrity import Extractor, Model, PartsModel, NO_YEAR_TEI, WORK, lookup_for, long_tei, note_text


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))


@pytest.fixture
def local(tmp_path):
    store = LocalStore(tmp_path / "data")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\nfixture")
    pid = store.add(pdf)["paper_id"]
    return LocalService(store, Model(), Extractor()), pid


def add_papers(store, path, count):
    for number in range(count):
        pdf = path / f"paper-{number}.pdf"
        pdf.write_bytes(f"%PDF-1.7\nfixture {number}".encode())
        store.add(pdf)


def test_batch_processes_101_papers_and_reports_all_pending(local, tmp_path):
    service, pid = local
    add_papers(service.store, tmp_path, 100)
    assert len(service.pending()) == 101
    result = service.process_all()
    assert result["processed"] == result["total"] == 101
    assert result["remaining"] == result["failed"] == 0
    assert len(service.store.papers_with_notes()) == 101
    assert service.process_all()["processed"] == 0


def test_pagination_tied_timestamps_and_new_arrivals(local, tmp_path):
    service, pid = local
    add_papers(service.store, tmp_path, 100)
    with service.store.db() as db:
        db.execute("UPDATE papers SET created_at='2026-01-01T00:00:00+00:00'")
    page = service.store.paper_page(limit=17)
    seen = [p["paper_id"] for p in page["papers"]]
    newcomer = tmp_path / "new.pdf"
    newcomer.write_bytes(b"%PDF-1.7\nnew arrival")
    new_id = service.store.add(newcomer)["paper_id"]
    while page["next_cursor"]:
        page = service.store.paper_page(limit=17, cursor=page["next_cursor"])
        seen.extend(p["paper_id"] for p in page["papers"])
    assert len(seen) == len(set(seen)) == 101
    assert new_id not in seen
    with pytest.raises(ValueError, match="cursor"):
        service.store.paper_page(cursor="not-json")


def test_orphan_scan_reaches_beyond_1000_recent_jobs(local):
    service, pid = local
    orphan = service.store.start_question("old")
    with service.store.db() as db:
        db.execute("UPDATE jobs SET created_at='2000', request=? WHERE job_id=?",
                   (json.dumps({"pid": 2 ** 22}), orphan))
        db.executemany("INSERT INTO jobs(job_id,status,created_at,kind) VALUES (?,?,?,?)",
                       [(f"recent-{i}", "succeeded", "2026", "note") for i in range(1001)])
    service.store.sweep_orphaned_questions()
    assert service.store.job(orphan)["status"] == "interrupted"
    assert len(list(service.store.iter_jobs())) == 1002


@pytest.mark.parametrize("failure", ["disabled", 429, 503, "empty"])
def test_refresh_preserves_confirmed_metadata_and_search(local, failure):
    service, pid = local
    service.extractor = Extractor(NO_YEAR_TEI)
    service.lookup = lookup_for([WORK])
    first = service.process(pid)
    if failure == "disabled":
        service.lookup = None
    else:
        def serve(request):
            return httpx.Response(200, json={"results": []}) if failure == "empty" else httpx.Response(failure)
        service.lookup = OpenAlexLookup(transport=httpx.MockTransport(serve))
    refreshed = service.refresh_metadata(pid)
    assert refreshed["changed"] is False
    assert service.store.note(pid)["revision_id"] == first["revision_id"]
    hit = service.store.search("BLEU")[0]
    assert str(hit["year"]) == "2021"
    assert "W4409484936" in service.store.note(pid)["text"]
    with service.store.db() as db:
        status = db.execute("SELECT state FROM metadata_checks ORDER BY checked_at DESC LIMIT 1").fetchone()[0]
    assert status == {"disabled": "disabled", 429: "rate_limited", 503: "unavailable", "empty": "not_found"}[failure]


def test_retired_stem_resolves_to_same_paper(local):
    service, pid = local
    service.extractor = Extractor(NO_YEAR_TEI)
    before = service.process(pid)
    service.lookup = lookup_for([WORK])
    after = service.refresh_metadata(pid)
    assert after["stem"] != before["stem"]
    assert service.store.paper_for_stem(before["stem"]) == pid
    assert service.read(pid, revision=before["revision_id"])["revision_id"] == before["revision_id"]


@pytest.mark.parametrize("answer,reason", [
    ("It reports a result. [E1-P0002]", "model_citation_unresolvable"),
    ("An uncited assertion. Another result. [E1]", "model_answer_uncited_statement")])
def test_answer_rejects_unshown_paragraph_or_uncited_sentence(local, answer, reason):
    service, pid = local
    service.process(pid)
    service.backend.answer = answer
    result = service.ask("What happened?", pid)
    assert result["answer_status"] == "insufficient_evidence"
    assert result["reason"] == reason
    assert answer not in result["answer"]


def test_final_note_cannot_cite_a_paragraph_removed_from_digests(local):
    service, pid = local
    class DropsEvidence(PartsModel):
        def generate(self, system, prompt, *, think=None):
            if system.startswith("Digest one part"):
                shown = [p for p in re.findall(r"\[(P\d+)\]", prompt) if p != "P0007"]
                return Generation("fact " + "".join(f"[{p}]" for p in shown), self.model, 100, 50, "stop")
            return Generation(note_text("P0007"), self.model, 100, 200, "stop")
    service.backend, service.extractor = DropsEvidence(), Extractor(long_tei(20))
    with pytest.raises(RuntimeError, match="unknown paragraph"):
        service.process(pid)
    assert not service.store.papers_with_notes()


@pytest.mark.parametrize("artifact", ["note", "document"])
def test_file_tamper_blocks_read_answer_and_search(local, artifact):
    service, pid = local
    service.process(pid)
    note = service.store.note(pid)
    path = service.store.path(note["path"] if artifact == "note" else note["extraction_path"])
    path.write_bytes(path.read_bytes().replace(b"28.4", b"99.9"))
    assert any("hash mismatch" in p for p in service.store.integrity_problems())
    with pytest.raises(ValueError, match="hash mismatch"):
        service.context(pid, "P0001")
    service.backend.answer = "The result is 99.9. [E1]"
    with pytest.raises(ValueError, match="hash mismatch"):
        service.ask("What was measured?", pid)
    assert service.store.search("BLEU") == []


def test_deep_check_catches_original_tamper(local):
    service, pid = local
    service.process(pid)
    service.store.path(service.store.paper(pid)["pdf_path"]).write_bytes(b"changed")
    assert any("Original PDF hash mismatch" in p for p in service.store.integrity_problems(deep=True))


def test_publish_failure_never_writes_success_receipt(local, monkeypatch):
    service, pid = local
    monkeypatch.setattr(service.store, "_record_success", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(RuntimeError):
        service.process(pid)
    job = service.store.jobs()[0]
    receipt = json.loads(service.store.path(f"runs/{job['job_id']}/receipt.json").read_text())
    assert job["status"] == receipt["outcome"] == "failed"
    assert not service.store.papers_with_notes()


def test_receipt_failure_after_commit_does_not_downgrade_job(local, monkeypatch):
    service, pid = local
    write = service.store.write_new
    def failed_receipt(path, body):
        if path.endswith("/receipt.json"):
            raise OSError("disk error")
        return write(path, body)
    monkeypatch.setattr(service.store, "write_new", failed_receipt)
    result = service.process(pid)
    assert result["receipt_incomplete"]
    assert service.store.job(result["job_id"])["status"] == "succeeded"
    assert service.store.note(pid)["revision_id"] == result["revision_id"]
    monkeypatch.setattr(service.store, "write_new", write)
    repaired = service.store.reconcile_receipts()
    assert repaired["recovered"] == [result["job_id"]]
    receipt = json.loads(service.store.path(f"runs/{result['job_id']}/receipt.json").read_text())
    assert receipt["outcome"] == "succeeded" and receipt["reconciled_from_db"]
    assert service.store.reconcile_receipts()["recovered"] == []
    service.store.finish(result["job_id"], "failed")
    assert service.store.job(result["job_id"])["status"] == "succeeded"


def test_publish_checks_extraction_hash_after_generation(local):
    service, pid = local
    generate = service.backend.generate
    def tamper_after_call(*args, **kwargs):
        result = generate(*args, **kwargs)
        job = service.store.jobs()[0]["job_id"]
        file = service.store.path(f"runs/{job}/document.json")
        file.write_bytes(file.read_bytes().replace(b"28.4", b"99.9"))
        return result
    service.backend.generate = tamper_after_call
    with pytest.raises(RuntimeError, match="hash mismatch before publication"):
        service.process(pid)
    assert not service.store.papers_with_notes()


def test_two_artifact_writers_cannot_overwrite_each_other(local):
    service, pid = local
    start = threading.Barrier(2)
    def write(value):
        start.wait(5)
        try:
            service.store.write_new("immutable.txt", value)
            return True
        except FileExistsError:
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(write, [b"first", b"second"]))
    assert sorted(results) == [False, True]
    assert service.store.path("immutable.txt").read_bytes() in {b"first", b"second"}


@pytest.mark.parametrize("change", ["citation", "source"])
def test_verdict_is_not_reused_after_evidence_changes(local, tmp_path, change):
    service, pid = local
    service.process(pid)
    sheet = service.review_sheet(pid)
    path = tmp_path / "review.md"
    path.write_text(review_markdown(sheet).replace("- 판정:", "- 판정: 맞음"))
    kept = recorded_verdicts(path)
    assert "- 판정: 맞음" in review_markdown(sheet, kept)
    for claim in sheet["claims"]:
        if change == "citation":
            claim["cited"] = ["P0002"]
        else:
            for source in claim["sources"]:
                source["text"] += " changed evidence"
    assert "- 판정: 맞음" not in review_markdown(sheet, kept)


def test_review_includes_tables_quotes_summary_and_glossary(local):
    service, pid = local
    service.backend.answer = note_text().replace("## 4. Key Results and Benchmarks\n\n",
        "## 4. Key Results and Benchmarks\n\n| Metric | Value |\n| --- | --- |\n| AUC | 999% [P0001] |\n\n> Quoted result is 28.4. [P0001]\n\n")
    service.process(pid)
    sheet = service.review_sheet(pid)
    table = next(c for c in sheet["claims"] if "999%" in c["claim"])
    assert "Metric" in table["claim"] and table["location"]["kind"] == "table_row"
    assert any("Quoted result" in c["claim"] for c in sheet["claims"])
    assert any(c["heading"] == "One-line Summary" for c in sheet["claims"])
    assert any(c["heading"] == "7. Glossary" for c in sheet["claims"])
    assert sheet["evaluation_schema"] == 2


def test_duplicate_top_level_functions_and_classes_are_absent():
    import byeori.local.service as module
    tree = ast.parse(Path(module.__file__).read_text())
    names = Counter(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
    assert not [name for name, count in names.items() if count > 1]


def test_failed_question_has_failure_exit_code(local, monkeypatch, capsys):
    import byeori.local.cli as cli
    service, pid = local
    service.process(pid)
    monkeypatch.setattr(cli, "build_service", lambda *a, **k: service)
    def broken(*a, **k):
        raise ModelError("offline")
    service.backend.generate = broken
    assert main(["ask", "question", "--paper", pid]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"


def test_two_question_managers_do_not_run_together(local):
    service, pid = local
    entered, release = threading.Event(), threading.Event()
    class BlockingService:
        store = service.store
        def ask(self, question, paper_id=None):
            if question == "first":
                entered.set()
                assert release.wait(5)
            return {"answer_status": "answered", "answer": question}
    first, second = QuestionJobs(BlockingService()), QuestionJobs(BlockingService())
    one = first.submit("first")["job_id"]
    assert entered.wait(5)
    two = second.submit("second")["job_id"]
    try:
        assert service.store.job(two)["status"] == "queued"
    finally:
        release.set()
    assert first.wait(one, 5)["status"] == second.wait(two, 5)["status"] == "succeeded"


def test_submit_during_worker_exit_is_not_stranded(local, monkeypatch):
    service, pid = local
    class ImmediateService:
        store = service.store
        def ask(self, *args):
            return {"answer_status": "answered"}
    jobs = QuestionJobs(ImmediateService())
    empty_seen, exit_allowed, submit_started = threading.Event(), threading.Event(), threading.Event()
    claim = service.store.claim_question
    def slow_empty(owner_token=None):
        result = claim(owner_token)
        if result is None and not empty_seen.is_set():
            empty_seen.set()
            assert exit_allowed.wait(5)
        return result
    monkeypatch.setattr(service.store, "claim_question", slow_empty)
    jobs._ensure_worker()
    assert empty_seen.wait(5)
    def submit():
        submit_started.set()
        return jobs.submit("arrives on exit")["job_id"]
    with ThreadPoolExecutor() as executor:
        incoming = executor.submit(submit)
        assert submit_started.wait(5)
        exit_allowed.set()
        job_id = incoming.result(5)
    assert jobs.wait(job_id, 5)["status"] == "succeeded"


def test_endpoint_lock_is_shared_across_processes(tmp_path):
    source = """
import sys, time
from pathlib import Path
from byeori.local.locking import inference_lock
root, role = Path(sys.argv[1]), sys.argv[2]
(root / (role + '-ready')).touch()
with inference_lock():
    (root / (role + '-entered')).touch()
    if role == 'one':
        while not (root / 'release').exists(): time.sleep(.01)
"""
    def wait_file(name):
        deadline = time.monotonic() + 5
        while not (tmp_path / name).exists():
            assert time.monotonic() < deadline
            time.sleep(.01)
    one = subprocess.Popen([sys.executable, "-c", source, str(tmp_path), "one"])
    two = None
    try:
        wait_file("one-entered")
        two = subprocess.Popen([sys.executable, "-c", source, str(tmp_path), "two"])
        wait_file("two-ready")
        assert not (tmp_path / "two-entered").exists()
        (tmp_path / "release").touch()
        assert one.wait(5) == two.wait(5) == 0
        assert (tmp_path / "two-entered").exists()
    finally:
        (tmp_path / "release").touch()
        for process in (one, two):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
    assert runtime_path("http://localhost:11434") == runtime_path("http://127.0.0.1:11434")


@pytest.mark.parametrize("remote", [{"remote_host": "https://ollama.com"}, {"remote_model": "alias"}])
def test_cloud_alias_is_rejected_before_chat(remote):
    backend = OllamaBackend("test", transport=ollama_transport(lambda r: pytest.fail("cloud inference attempted"), remote=remote))
    assert backend.doctor()["model_locality"] == "remote"
    with pytest.raises(ModelError, match="Remote/cloud"):
        backend.generate("system", "input")


def test_external_endpoint_requires_explicit_opt_in():
    with pytest.raises(ValueError, match="Non-loopback"):
        OllamaBackend("test", "https://remote.example")
    assert OllamaBackend("test", "http://192.168.1.2:11434", allow_remote=True).endpoint_policy == "explicit_remote_endpoint"


def test_timeout_is_not_retried_without_think_and_quarantines_endpoint():
    calls = []
    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("slow", request=request)
    backend = OllamaBackend("test", transport=ollama_transport(timeout))
    with pytest.raises(ModelTimeout):
        backend.generate("system", "paper", think=False)
    assert len(calls) == 1
    assert backend.doctor()["recovery_pending"]
    with pytest.raises(ModelError, match="recovery_pending"):
        backend.generate("system", "paper")
    assert len(calls) == 1
    with pytest.raises(ValueError, match="Confirm"):
        backend.recover_runtime()
    backend.recover_runtime(acknowledge=True)
    assert not backend.blocked_path.exists()


def test_only_explicit_unsupported_thinking_error_is_retried():
    bodies = []
    def serve(request):
        body = json.loads(request.content)
        bodies.append(body)
        if "think" in body:
            return httpx.Response(400, json={"error": "model does not support thinking"})
        return httpx.Response(200, json={"done": True, "done_reason": "stop", "message": {"content": "result"}})
    result = OllamaBackend("test", transport=ollama_transport(serve)).generate("system", "paper", think=False)
    assert len(bodies) == 2 and "think" not in bodies[1]
    assert result.metadata["think"] is None
    assert result.metadata["model_digest"] == "a" * 64
    assert result.metadata["token_accounting"] == "unverified"


def test_abandoned_server_request_blocks_a_successor_until_explicit_recovery():
    backend = OllamaBackend("test", transport=ollama_transport(lambda r: pytest.fail("another inference started")))
    backend.inflight_path.parent.mkdir(parents=True)
    backend.inflight_path.write_text('{"model":"test"}')
    assert backend.doctor()["recovery_pending"]
    with pytest.raises(ModelError, match="recovery_pending"):
        backend.generate("system", "paper")
    backend.recover_runtime(acknowledge=True)
    assert not backend.doctor()["recovery_pending"]
