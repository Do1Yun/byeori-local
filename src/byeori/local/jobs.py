"""Question jobs: submitted, polled and cancelled, so a slow local model never blocks a client."""
from __future__ import annotations

import threading
import time

WAIT_INTERVAL = 0.1


class QuestionJobs:
    """One question at a time, on a background thread, recorded in the workspace.

    A local model answers in minutes, and an MCP client cannot hold a tool call open that long,
    so a question becomes a job the client polls. Only one runs at a time: a second model call on
    this machine would compete with the first for the same memory.
    """

    def __init__(self, service):
        self.service = service
        self.store = service.store
        self._lock = threading.Lock()
        self._worker = None
        self.recover()

    def recover(self):
        """A question whose process is gone is not still waiting; say so instead of leaving it."""
        self.store.sweep_orphaned_questions()

    def submit(self, question, paper_id=None):
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1 to 4000 characters")
        if paper_id is not None:
            self.store.paper(paper_id)        # fail now, not inside the worker
        job_id = self.store.start_question(question, paper_id)
        self._ensure_worker()
        return {"job_id": job_id, "status": "queued", "poll_with": "get_job"}

    def cancel(self, job_id):
        """Accepting a cancellation and having stopped are different facts, so both are returned."""
        job = self.store.request_cancel(job_id)
        return {"job_id": job_id, "cancel_requested": job["cancel_requested"] is not None,
                "status": job["status"], "stopped": job["status"] in self.store.TERMINAL}

    def wait(self, job_id, timeout=None):
        """Block until the job reaches a terminal state; the CLI answers in the foreground."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            job = self.store.job(job_id)
            if job["status"] in self.store.TERMINAL:
                return job
            if deadline is not None and time.monotonic() > deadline:
                raise TimeoutError(f"Job {job_id} is still {job['status']}")
            time.sleep(WAIT_INTERVAL)

    def _ensure_worker(self):
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, name="byeori-questions",
                                                daemon=True)
                self._worker.start()

    def _run(self):
        while True:
            job = self.store.claim_question()
            if job is None:
                return
            job_id, request = job["job_id"], job["request"]
            if job["cancel_requested"] is not None:
                self.store.finish(job_id, "cancelled", stage="queued",
                                  error="Cancelled before the model was called")
                continue
            try:
                answer = self.service.ask(request["question"], request.get("paper_id"))
            except Exception as exc:                       # a question must not end the worker
                self.store.finish(job_id, "failed", stage="answer", error=str(exc))
                continue
            if self.store.job(job_id)["cancel_requested"] is not None:
                self.store.finish(job_id, "cancelled", stage="answer",
                                  error="Cancelled while the model was answering; the answer "
                                        "it returned was discarded")
            else:
                self.store.finish(job_id, "succeeded", result=answer, stage="answer")
