"""The workspace worker: queue, ownership, stopping, waiting and what it writes down.

Temporary data only; no test reaches a real model, extractor or the user's workspace.
"""
import asyncio
import json
import os
import threading
import time

import httpx
import pytest

from byeori.local.jobs import QuestionJobs
from byeori.local.llm import Generation, ModelError, OllamaBackend
from byeori.local.locking import WorkerBusy, runtime_path, worker_lock
from byeori.local.service import LocalService, Run, WorkerRunning
from byeori.local.store import LocalStore, StaleLease, process_identity
from byeori.local.worker import Worker
from local_helpers import ollama_transport
from test_local_integrity import TEI, Extractor, Model, PartsModel, long_tei, note_text


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))


def add_paper(store, path, name):
    pdf = path / f"{name}.pdf"
    pdf.write_bytes(f"%PDF-1.7\n{name}".encode())
    return store.add(pdf)["paper_id"]


@pytest.fixture
def local(tmp_path):
    store = LocalStore(tmp_path / "data")
    return LocalService(store, Model(), Extractor()), add_paper(store, tmp_path, "paper")


def worker(service, **options):
    options.setdefault("prevent_sleep", False)
    return Worker(service, once=True, log_stream=None, poll_seconds=0.01, **options)


def followers(store, job_id):
    return [job for job in store.iter_jobs() if job.get("resumed_from") == job_id]


class NoExtractor(Extractor):
    def ready(self):
        return {"ready": False, "version": None, "error": "ConnectError"}


def test_queued_note_job_is_claimed_and_published_by_worker_once(local):
    service, pid = local
    job_id = service.submit_note(pid)["job_id"]
    assert service.store.job(job_id)["status"] == "queued"
    assert service.submit_note(pid)["status"] == "already_queued", "a paper is not queued twice"
    summary = worker(service).run()
    job = service.store.job(job_id)
    assert job["status"] == "succeeded" and job["worker_id"] == summary["worker_id"]
    assert job["executor"] == "worker" and job["started_at"] and job["heartbeat_at"]
    assert service.store.note(pid)["job_id"] == job_id
    events = [event["event"] for event in service.store.events(job_id)]
    assert events[0] == "enqueued" and "claimed" in events and events[-1] == "finished"
    assert summary["stopped"] == "queue_empty" and summary["outcomes"] == {"succeeded": 1}
    assert service.store.worker_status()["state"] == "stopped"
    assert not service.store.worker_status()["alive"]


def test_second_worker_fails_fast_while_first_holds_lock(local):
    service, _ = local
    with worker_lock(service.store.root):
        with pytest.raises(WorkerBusy) as raised:
            worker(service).run()
    assert raised.value.error_code == "worker_busy"


def test_inline_process_refuses_while_worker_runs(local):
    service, pid = local
    service.store.register_worker("w1", pid=os.getpid(), process_started=process_identity(os.getpid()),
                                  hostname="host", code_version="{}")
    with worker_lock(service.store.root):
        with pytest.raises(WorkerRunning, match="--submit") as raised:
            service.process(pid)
    assert raised.value.error_code == "worker_running"
    service.store.stop_worker("w1")
    with worker_lock(service.store.root):
        with pytest.raises(WorkerBusy, match="Another worker"):
            service.process(pid)


def test_worker_question_is_not_orphaned_when_submitter_pid_is_dead(local):
    service, pid = local
    service.process(pid)
    question = service.store.enqueue("question", paper_id=pid,
                                     request={"question": "What is reported?", "paper_id": pid,
                                              "pid": 2 ** 22})
    service.store.sweep_orphaned_questions()
    QuestionJobs(service)                    # a new process opening the workspace
    assert service.store.job(question)["status"] == "queued"
    worker(service).run()
    assert service.store.job(question)["status"] == "succeeded"


def test_inline_question_left_by_a_dead_process_is_still_interrupted(local):
    service, pid = local
    question = service.store.start_question("Who will run this?", pid)
    with service.store.db() as db:
        db.execute("UPDATE jobs SET request=? WHERE job_id=?",
                   (json.dumps({"question": "Who will run this?", "pid": 2 ** 22}), question))
    QuestionJobs(service)
    assert service.store.job(question)["status"] == "interrupted"


def test_question_is_claimed_before_an_older_note_job(local, tmp_path):
    service, pid = local
    service.process(pid)
    other = add_paper(service.store, tmp_path, "other")
    note_job = service.submit_note(other)["job_id"]
    question = QuestionJobs(service, executor="worker").submit("What is reported?", pid)["job_id"]
    worker(service, max_jobs=1).run()
    assert service.store.job(question)["status"] == "succeeded"
    assert service.store.job(note_job)["status"] == "queued"


def test_cancel_between_parts_stops_before_the_next_model_call(local):
    service, pid = local
    holder = {}

    class CancelAfterFirst(PartsModel):
        def generate(self, system, prompt, *, think=None):
            result = super().generate(system, prompt, think=think)
            if len(self.systems) == 1:
                service.store.request_cancel(holder["job"])
            return result

    service.backend, service.extractor = CancelAfterFirst(), Extractor(long_tei(20))
    holder["job"] = service.submit_note(pid)["job_id"]
    worker(service).run()
    job = service.store.job(holder["job"])
    assert job["status"] == "cancelled" and job["cancel_ack_at"] and job["error_code"] == "cancelled"
    assert len(service.backend.systems) == 1, "no model call after the cancellation"
    assert [c["stage"] for c in service.checkpoints.for_paper(pid)].count("digest") == 1
    assert not service.store.papers_with_notes()
    receipt = json.loads(service.store.path(f"runs/{holder['job']}/receipt.json").read_text())
    assert receipt["outcome"] == "cancelled"


def test_worker_start_requeues_a_job_left_running_with_resumed_from(local):
    service, pid = local
    job_id = service.submit_note(pid)["job_id"]
    with service.store.db() as db:
        db.execute("UPDATE jobs SET status='running', worker_id='dead' WHERE job_id=?", (job_id,))
    summary = worker(service).run()
    old = service.store.job(job_id)
    assert old["status"] == "interrupted" and old["error_code"] == "worker_interrupted"
    follower = summary["requeued_at_start"][job_id]
    new = service.store.job(follower)
    assert new["status"] == "succeeded" and new["attempt"] == 2 and new["resumed_from"] == job_id


def test_requeue_stops_at_max_attempts(local):
    service, pid = local
    job_id = service.submit_note(pid)["job_id"]
    with service.store.db() as db:
        db.execute("UPDATE jobs SET status='running', worker_id='dead', attempt=3, max_attempts=3 "
                   "WHERE job_id=?", (job_id,))
    summary = worker(service).run()
    assert service.store.job(job_id)["error_code"] == "max_attempts_exhausted"
    assert summary["requeued_at_start"] == {} and not followers(service.store, job_id)


def test_timeout_pauses_worker_until_recovery_is_acknowledged(local, tmp_path):
    service, pid = local
    other = add_paper(service.store, tmp_path, "other")
    calls = []

    def chat(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json={"done": True, "done_reason": "stop", "model": "test",
                                         "message": {"content": note_text()}, "eval_count": 10})

    service.backend = OllamaBackend("test", transport=ollama_transport(chat))
    first, second = service.submit_note(pid)["job_id"], service.submit_note(other)["job_id"]
    paused = worker(service).run()
    assert service.store.job(first)["status"] == "failed"
    assert service.store.job(first)["error_code"] == "outcome_unknown"
    assert paused["stopped"] == "recovery_pending"
    assert service.store.job(second)["status"] == "queued", "nothing is sent while recovery is pending"
    assert len(calls) == 1
    service.backend.recover_runtime(acknowledge=True)
    worker(service).run()
    assert service.store.job(second)["status"] == "succeeded"
    assert not followers(service.store, first), "a timed-out request is not sent again on its own"


def test_recovery_pending_tells_an_abandoned_marker_from_a_call_in_flight(tmp_path):
    from byeori.local.locking import inference_lock
    backend = OllamaBackend("test", transport=ollama_transport(lambda r: pytest.fail("no chat")))
    backend.inflight_path.parent.mkdir(parents=True, exist_ok=True)
    backend.inflight_path.write_text("{}")
    held, release = threading.Event(), threading.Event()

    def hold():
        with inference_lock(backend.url):
            held.set()
            release.wait(5)

    thread = threading.Thread(target=hold)
    thread.start()
    try:
        assert held.wait(5)
        assert backend.recovery_pending() is False, "a held lock means the call is still running"
    finally:
        release.set()
        thread.join(5)
    assert backend.recovery_pending() is True, "a free lock beside a marker means it was abandoned"
    assert runtime_path(backend.url).exists()


def test_worker_waits_for_extractor_and_still_answers_questions(local):
    service, pid = local
    service.process(pid)
    service.extractor = NoExtractor()
    note_job = service.store.enqueue("note", paper_id=pid)
    question = QuestionJobs(service, executor="worker").submit("What is reported?", pid)["job_id"]
    summary = worker(service).run()
    assert service.store.job(question)["status"] == "succeeded"
    assert service.store.job(note_job)["status"] == "queued"
    assert summary["stopped"] == "extractor_unavailable"


def test_graceful_stop_interrupts_after_the_current_part_and_requeues(local):
    service, pid = local
    running = worker(service)

    class StopsAfterFirst(PartsModel):
        def generate(self, system, prompt, *, think=None):
            result = super().generate(system, prompt, think=think)
            running.request_stop()
            return result

    service.backend, service.extractor = StopsAfterFirst(), Extractor(long_tei(20))
    job_id = service.submit_note(pid)["job_id"]
    summary = running.run()
    job = service.store.job(job_id)
    assert job["status"] == "interrupted" and job["error_code"] == "worker_interrupted"
    assert summary["stopped"] == "stop_requested"
    [follower] = followers(service.store, job_id)
    assert follower["status"] == "queued" and follower["attempt"] == 2
    assert len(service.backend.systems) == 1
    assert [c["stage"] for c in service.checkpoints.for_paper(pid)].count("digest") == 1
    receipt = json.loads(service.store.path(f"runs/{job_id}/receipt.json").read_text())
    assert receipt["outcome"] == "interrupted" and receipt["requeued_as"] == follower["job_id"]


def test_heartbeat_advances_while_the_model_works(local, monkeypatch):
    service, pid = local
    beats = []
    original = service.store.heartbeat
    monkeypatch.setattr(service.store, "heartbeat",
                        lambda job_id, worker_id: (beats.append(job_id), original(job_id, worker_id)))

    class Slow(Model):
        def generate(self, system, prompt, *, think=None):
            time.sleep(0.3)
            return super().generate(system, prompt, think=think)

    service.backend = Slow()
    job_id = service.submit_note(pid)["job_id"]
    worker(service, heartbeat_seconds=0.05).run()
    assert len(beats) >= 2 and set(beats) == {job_id}


def test_a_stale_lease_cannot_publish(local):
    service, pid = local
    job_id = service.submit_note(pid)["job_id"]
    assert service.store.claim_next("w1")["job_id"] == job_id
    with pytest.raises(StaleLease):
        service.store.set_stage(job_id, "elsewhere", lease="w2")
    with pytest.raises(StaleLease):
        service.store.finish(job_id, "failed", lease="w2")
    with pytest.raises(StaleLease):
        service._process(pid, Run(job_id, lease="w2"))
    job = service.store.job(job_id)
    assert job["status"] == "running" and job["worker_id"] == "w1"
    assert not service.store.papers_with_notes()


def test_worker_log_never_contains_paper_text(local, tmp_path):
    service, pid = local
    service.extractor = Extractor(TEI.replace(b"Attention is sufficient.",
                                              b"Quokka marmalade observatory sentence."))
    other = add_paper(service.store, tmp_path, "other")
    service.submit_note(pid)

    class Broken(Model):
        """Answers the first paper and fails the second, so both endings are logged."""

        def generate(self, system, prompt, *, think=None):
            assert "Quokka" in prompt, "the model does see the paper's text"
            if self.calls:
                raise ModelError("offline")
            return super().generate(system, prompt, think=think)

    service.backend = Broken()
    service.store.enqueue("note", paper_id=other)
    summary = worker(service).run()
    text = open(summary["log"], encoding="utf-8").read()
    assert "Quokka" not in text and "BLEU" not in text and "28.4" not in text
    entries = [json.loads(line) for line in text.splitlines()]
    assert {entry["event"] for entry in entries} >= {"started", "claimed", "finished", "stopped"}
    assert all(set(entry) == {"at", "level", "worker_id", "job_id", "event", "detail"}
               for entry in entries)
    assert summary["outcomes"] == {"succeeded": 1, "failed": 1}


def test_mcp_ask_enqueues_for_worker_when_configured(local):
    from byeori.local.mcp_server import create_server
    service, pid = local
    service.process(pid)
    service.executor = "worker"
    jobs = QuestionJobs(service)
    submitted = jobs.submit("What is reported?", pid)
    assert submitted["executor"] == "worker" and submitted["diagnostic"] == "worker_unavailable"
    assert jobs._worker is None, "no thread in this process answers a worker's question"
    server = create_server(service)

    async def check():
        status = str(await server.call_tool("worker_status", {}))
        assert "queued_kinds" in status and "question" in status and '"alive": false' in status
        job = await server.call_tool("get_job", {"job_id": submitted["job_id"]})
        assert "enqueued" in str(job)
    asyncio.run(check())
    assert service.store.job(submitted["job_id"])["status"] == "queued"


def test_the_mac_is_held_awake_only_while_a_job_runs(local, monkeypatch):
    import byeori.local.worker as module
    service, pid = local
    launched = []

    class Caffeinate:
        def __init__(self, command, **kwargs):
            launched.append(command)
            self.ended = False

        def poll(self):
            return 0 if self.ended else None

        def terminate(self):
            self.ended = True

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(module.sys, "platform", "darwin")
    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/caffeinate")
    monkeypatch.setattr(module.SleepGuard, "spawn", staticmethod(Caffeinate))
    service.submit_note(pid)
    summary = worker(service, prevent_sleep=True).run()
    assert launched == [["/usr/bin/caffeinate", "-i", "-s", "-w", str(os.getpid())]], "one hold per job"
    finished = [json.loads(line) for line in open(summary["log"], encoding="utf-8")
                if '"finished"' in line]
    assert finished[0]["detail"]["sleep_prevented"] is True
    launched.clear()
    worker(service, prevent_sleep=True).run()
    assert launched == [], "an idle worker lets the machine sleep"
