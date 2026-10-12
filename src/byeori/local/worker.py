"""The workspace's long-running worker: it claims queued jobs one at a time and outlives the
processes that submitted them.

A question asked through MCP, a paper submitted with --submit, a metadata or revalidation request:
each waits in the workspace's own queue until this process claims it. It holds .worker.lock for
its whole life, so foreground processing in the same workspace refuses while it runs and says
why. It never starts GROBID or restarts Ollama: when either is unavailable it waits and says so.
"""
from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

from .jobs import answer_question
from .locking import worker_lock
from .service import Run
from .store import StaleLease, code_version, now, process_identity

NON_NOTE_KINDS = ("question", "metadata", "revalidate")
# A job that failed for a reason outside it is queued again within its attempt limit. A timeout is
# not among them: the server may still be computing, and the same request is not sent twice.
REQUEUE_ON_FAILURE = {"recovery_pending", "extractor_unavailable"}


class WorkerLog:
    """One JSON line per event, and a readable line on stderr. Never paper text or prompts."""

    def __init__(self, directory, worker_id, stream=sys.stderr):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.path = directory / f"worker-{stamp}-{worker_id[:8]}.jsonl"
        self.worker_id, self.stream = worker_id, stream

    def write(self, event, *, level="info", job_id=None, detail=None):
        entry = {"at": now(), "level": level, "worker_id": self.worker_id, "job_id": job_id,
                 "event": event, "detail": detail}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if self.stream is not None:
            line = f"{entry['at'][11:19]} {level:<5} {event}"
            if job_id:
                line += f" job={job_id[:8]}"
            if detail:
                line += " " + json.dumps(detail, ensure_ascii=False)
            print(line, file=self.stream, flush=True)


class Heartbeat:
    """Says the job is alive while the model works on it, which may be many minutes."""

    def __init__(self, store, job_id, worker_id, interval):
        self.store, self.job_id, self.worker_id, self.interval = store, job_id, worker_id, interval
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._run, name="byeori-heartbeat", daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        while not self._done.wait(self.interval):
            try:
                self.store.heartbeat(self.job_id, self.worker_id)
            except Exception:                             # noqa: BLE001 - a missed beat is not fatal
                pass

    def stop(self):
        self._done.set()
        self._thread.join(timeout=5)


class SleepGuard:
    """Keeps an unattended Mac from idle-sleeping while a job runs.

    Measured on this machine: macOS entered maintenance sleep for 99 seconds in the middle of a
    digest, and the model's work paused with it. caffeinate -i holds the same assertion a person
    holding the machine awake would, and -w ends it if this process dies without cleaning up.
    """

    spawn = staticmethod(subprocess.Popen)

    def __init__(self, enabled=True):
        self.command = (shutil.which("caffeinate")
                        if enabled and sys.platform == "darwin" else None)
        self.process = None

    def __enter__(self):
        if self.command:
            try:
                self.process = self.spawn([self.command, "-i", "-w", str(os.getpid())],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                self.process = None
        return self

    @property
    def active(self):
        return self.process is not None and self.process.poll() is None

    def __exit__(self, *exc):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


class Worker:
    def __init__(self, service, *, once=False, max_jobs=None, resume_interrupted=True,
                 poll_seconds=2.0, heartbeat_seconds=15.0, extractor_wait=30.0,
                 recovery_wait=30.0, log_dir=None, log_stream=sys.stderr, install_signals=False,
                 prevent_sleep=True):
        self.service, self.store = service, service.store
        self.worker_id = uuid.uuid4().hex
        self.once, self.max_jobs, self.resume_interrupted = once, max_jobs, resume_interrupted
        self.poll_seconds, self.heartbeat_seconds = poll_seconds, heartbeat_seconds
        self.extractor_wait, self.recovery_wait = extractor_wait, recovery_wait
        self.install_signals, self.prevent_sleep = install_signals, prevent_sleep
        self.stop_event = threading.Event()
        self.log = WorkerLog(log_dir or self.store.root / "logs", self.worker_id, log_stream)
        self.state, self._last_beat = None, 0.0
        self.jobs_run, self.counts = 0, {}

    def request_stop(self):
        """Stop at the next safe point: before the next model call, never inside a publication."""
        self.stop_event.set()

    def run(self):
        with worker_lock(self.store.root):        # WorkerBusy if another worker holds it
            return self._run()

    def _run(self):
        previous = self._install_signals() if self.install_signals else {}
        self.store.register_worker(self.worker_id, pid=os.getpid(),
                                   process_started=process_identity(os.getpid()),
                                   hostname=socket.gethostname(),
                                   code_version=json.dumps(code_version()))
        self.log.write("started", detail={"pid": os.getpid(), "once": self.once,
                                          "max_jobs": self.max_jobs,
                                          "workspace": str(self.store.root)})
        stopped, swept = "stop_requested", {"interrupted": [], "requeued": {}}
        try:
            swept = self.store.sweep_running_jobs(requeue=self.resume_interrupted)
            if swept["interrupted"]:
                self.log.write("swept", level="warn", detail=swept)
            while not self.stop_event.is_set():
                if self._recovery_pending():
                    self._set_state("paused_recovery_pending")
                    if self.once:
                        stopped = "recovery_pending"
                        break
                    self.stop_event.wait(self.recovery_wait)
                    continue
                pending = self.store.queued_kinds()
                if not pending:
                    self._set_state("idle")
                    if self.once:
                        stopped = "queue_empty"
                        break
                    self.stop_event.wait(self.poll_seconds)
                    continue
                ready = "note" not in pending or self._extractor_ready()
                job = self.store.claim_next(self.worker_id, kinds=None if ready else NON_NOTE_KINDS)
                if job is None:
                    if not ready:
                        # Questions and metadata still run; papers wait for the extractor.
                        self._set_state("waiting_extractor")
                        if self.once:
                            stopped = "extractor_unavailable"
                            break
                        self.stop_event.wait(self.extractor_wait)
                    continue
                self._run_job(job)
                if self.max_jobs and self.jobs_run >= self.max_jobs:
                    stopped = "max_jobs"
                    break
        finally:
            self.store.stop_worker(self.worker_id)
            self.log.write("stopped", detail={"reason": stopped, "jobs_run": self.jobs_run,
                                              **self.counts})
            for number, handler in previous.items():
                signal.signal(number, handler)
        return {"worker_id": self.worker_id, "stopped": stopped, "jobs_run": self.jobs_run,
                "outcomes": self.counts, "interrupted_at_start": swept["interrupted"],
                "requeued_at_start": swept["requeued"], "log": str(self.log.path)}

    def _install_signals(self):
        """First SIGTERM/SIGINT: stop at the next safe point. Second: leave at once."""
        def handle(number, frame):
            if self.stop_event.is_set():
                os._exit(130)
            self.stop_event.set()
        previous = {}
        for number in (signal.SIGTERM, signal.SIGINT):
            previous[number] = signal.signal(number, handle)
        return previous

    def _set_state(self, state, job_id=None):
        clock = time.monotonic()
        if state != self.state or clock - self._last_beat >= self.heartbeat_seconds:
            self.store.update_worker(self.worker_id, state, job_id)
            self._last_beat = clock
        if state != self.state:
            self.log.write("state", job_id=job_id, detail={"state": state})
            self.state = state

    def _recovery_pending(self):
        method = getattr(self.service.backend, "recovery_pending", None)
        return bool(method()) if callable(method) else False

    def _extractor_ready(self):
        probe = getattr(self.service.extractor, "ready", None)
        return bool(probe()["ready"]) if callable(probe) else True

    def _run_job(self, job):
        job_id = job["job_id"]
        self._set_state("running", job_id)
        self.log.write("claimed", job_id=job_id,
                       detail={"kind": job["kind"], "paper_id": job["paper_id"],
                               "attempt": job.get("attempt"), "resumed_from": job.get("resumed_from")})
        run = Run(job_id, lease=self.worker_id, stop=self.stop_event)
        beat = Heartbeat(self.store, job_id, self.worker_id, self.heartbeat_seconds)
        beat.start()
        # Wall-clock time: macOS's monotonic clock stops while the machine sleeps, which made a
        # 248-second job read as 151 seconds.
        started, outcome, awake = time.time(), None, False
        try:
            with SleepGuard(self.prevent_sleep) as guard:
                awake = guard.active
                outcome = self._dispatch(job, run)
        except StaleLease as exc:
            self.log.write("stale_lease", level="error", job_id=job_id, detail={"error": str(exc)[:200]})
        except Exception as exc:                          # noqa: BLE001 - one job never ends the worker
            self._ensure_ended(job_id, exc)
        finally:
            beat.stop()
        final = self.store.job(job_id)
        if final["status"] == "running":
            self._ensure_ended(job_id, RuntimeError("The job returned without recording how it ended"))
            final = self.store.job(job_id)
        follower = (outcome or {}).get("requeued_as") if isinstance(outcome, dict) else None
        if final["status"] == "failed" and final.get("error_code") in REQUEUE_ON_FAILURE:
            follower = self.store.requeue(job_id, reason=final["error_code"])
        self.jobs_run += 1
        self.counts[final["status"]] = self.counts.get(final["status"], 0) + 1
        detail = {"status": final["status"], "stage": final.get("stage"),
                  "error_code": final.get("error_code"), "seconds": round(time.time() - started, 1),
                  "sleep_prevented": awake}
        if follower:
            detail["requeued_as"] = follower
        if isinstance(outcome, dict) and outcome.get("checkpoints_reused") is not None:
            detail["checkpoints_reused"] = outcome["checkpoints_reused"]
        self.log.write("finished", level="info" if final["status"] == "succeeded" else "warn",
                       job_id=job_id, detail=detail)

    def _dispatch(self, job, run):
        request = job["request"] if isinstance(job["request"], dict) else {}
        match job["kind"]:
            case "note":
                return self.service._process(job["paper_id"], run, resume=not request.get("no_resume"))
            case "question":
                return answer_question(self.service, job, lease=self.worker_id)
            case "metadata":
                return self.service._refresh(job["paper_id"], run)
            case "revalidate":
                return self.service._revalidate(request["written_by"], run)
        raise ValueError(f"Unknown job kind {job['kind']!r}")

    def _ensure_ended(self, job_id, exc):
        """A job the dispatch could not end is recorded as failed, with a receipt saying so."""
        code = getattr(exc, "error_code", None) or "failed"
        self.log.write("error", level="error", job_id=job_id,
                       detail={"error_code": code, "error": str(exc)[:200]})
        try:
            job = self.store.job(job_id)
            if job["status"] != "running":
                return
            self.store.finish(job_id, "failed", error=str(exc)[:2000], stage=job["stage"],
                              error_code=code, lease=self.worker_id)
            receipt = f"runs/{job_id}/receipt.json"
            if not self.store.path(receipt).exists():
                self.store.write_new(receipt, json.dumps({
                    "job_id": job_id, "kind": job["kind"], "paper_id": job["paper_id"],
                    "outcome": "failed", "stage": job["stage"], "error": str(exc)[:2000],
                    "error_code": code, "finished_at": now(), "written_by": "worker"},
                    ensure_ascii=False, indent=2).encode())
        except Exception as inner:                        # noqa: BLE001
            self.log.write("error", level="error", job_id=job_id,
                           detail={"error": f"could not record the failure: {type(inner).__name__}"})
