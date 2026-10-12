"""Submit bounded tasks and poll results without holding an MCP call open for inference."""
from __future__ import annotations

from collections import deque
import threading

from mcp.server.fastmcp import FastMCP

from .assistant_cli import build_assistant


class AssistantJobs:
    def __init__(self, assistant):
        self.assistant = assistant
        self._lock = threading.Lock()
        self._queue = deque()
        self._worker = None

    def submit(self, task, **kwargs):
        with self._lock:
            if len(self._queue) >= 8:
                raise ValueError("Eight tasks already queued; wait for results before submitting more")
            receipt = self.assistant.prepare(task, **kwargs)
            self._queue.append(receipt["task_id"])
            if self._worker is None:
                self._worker = threading.Thread(target=self._run, name="byeori-assistant", daemon=True)
                self._worker.start()
        return {"task_id": receipt["task_id"], "status": "queued", "poll_with": "get_task"}

    def _run(self):
        while True:
            with self._lock:
                if not self._queue:
                    self._worker = None
                    return
                task_id = self._queue.popleft()
            try:
                self.assistant.execute(task_id)
            except Exception:
                # A changed/deleted state file must not strand unrelated queued tasks.
                continue


def create_server(assistant=None):
    server = FastMCP("byeori-assistant")
    state = {"assistant": assistant, "jobs": None}
    state_lock = threading.RLock()

    def current():
        with state_lock:
            if state["assistant"] is None:
                state["assistant"] = build_assistant()
            return state["assistant"]

    def jobs():
        with state_lock:
            if state["jobs"] is None:
                state["jobs"] = AssistantJobs(current())
            return state["jobs"]

    @server.tool()
    def organize_notes(paths: list[str], instruction: str = "") -> dict:
        """Submit note organization (summary, decisions, TODOs, uncertainties). Inputs must be in configured read roots."""
        return jobs().submit("notes", paths=paths, instruction=instruction)

    @server.tool()
    def summarize_commits(repo: str, since: str = "7 days ago", until: str | None = None,
                          limit: int = 50, include_diff: bool = False) -> dict:
        """Submit a local Git history summary. Never runs network operations; excludes uncommitted changes."""
        return jobs().submit("commits", repo=repo, since=since, until=until, limit=limit, include_diff=include_diff)

    @server.tool()
    def classify_files(directory: str, categories: list[str] | None = None) -> dict:
        """Submit file classification suggestions. Originals are preserved; nothing is moved or renamed."""
        return jobs().submit("classify", directory=directory, categories=categories)

    @server.tool()
    def draft_report(paths: list[str] | None = None, task_ids: list[str] | None = None,
                     title: str = "작업 보고서", instruction: str = "") -> dict:
        """Draft a report from explicit text files and/or completed assistant tasks. Poll get_task afterward."""
        return jobs().submit("report", paths=paths, task_ids=task_ids, title=title, instruction=instruction)

    @server.tool()
    def get_task(task_id: str) -> dict:
        """Read queued/running/succeeded/failed/interrupted status and result paths; source IDs do not certify truth."""
        return current().get(task_id)

    @server.tool()
    def list_tasks(limit: int = 20) -> list[dict]:
        """Read recent persisted task receipts."""
        return current().history(limit)

    @server.tool()
    def read_task_result(task_id: str, start: int = 0, max_chars: int = 8000) -> dict:
        """Read a hash-checked draft window; pass next_start to continue."""
        return current().read_result(task_id, start, max_chars)

    return server


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
