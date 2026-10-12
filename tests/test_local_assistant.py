"""Work-assistant contracts: source coverage, immutable inputs, scope and async tasks."""
import asyncio
import json
from pathlib import Path
import subprocess
import threading
import time

import httpx
import pytest

from byeori.local.assistant import Assistant, initialize, write_json
from byeori.local.assistant_cli import main
from byeori.local.assistant_mcp import AssistantJobs, create_server
from byeori.local.llm import Generation, ModelError, OllamaBackend, estimate_tokens
from local_helpers import ollama_transport


class Backend:
    model = "fixture"
    context = 8192
    output = 2048

    def __init__(self, respond=None, fits=None):
        self.respond = respond
        self.fit_rule = fits
        self.calls = []

    def fits(self, system, prompt):
        return self.fit_rule(system, prompt) if self.fit_rule else len(prompt) < 5000

    def generate(self, system, prompt):
        data = json.loads(prompt)
        self.calls.append(data)
        if self.respond:
            text = self.respond(system, data)
        elif "Exactly one item" in system:
            text = json.dumps({"items": [{"source": s["id"], "category": "notes", "reason": "작업 메모"}
                                         for s in data["source_data"]]})
        elif "commit subject" in system:
            text = json.dumps({"summaries": {s["id"]: "커밋 제목 요약" for s in data["source_data"]}})
        else:
            section = "주요 변경" if "Commit messages" in system or "commit subject" in system else "진행 내용" if "report DRAFT" in system else "요약"
            text = json.dumps({"items": [{"section": section, "text": "입력 내용 정리",
                                         "sources": [data["source_data"][0]["id"]]}]})
        return Generation(text, self.model, 100, 100, "stop")


@pytest.fixture
def assistant(tmp_path):
    inbox = tmp_path / "input"
    inbox.mkdir()
    initialize(tmp_path / "assistant", read_roots=[inbox])
    return Assistant(tmp_path / "assistant", Backend())


def note(assistant, name="work.md", text="테스트를 실행했다.\n배포는 아직 진행하지 않았다.\n"):
    path = Path(assistant.config["read_roots"][-1]) / name
    path.write_text(text, encoding="utf-8")
    return path


def test_notes_keep_original_and_persist_sources_and_receipts(assistant):
    path = note(assistant)
    original = path.read_bytes()
    result = assistant.run("notes", paths=[str(path)])
    assert result["status"] == "succeeded"
    assert path.read_bytes() == original
    assert result["source_count"] == 1 and len(result["calls"]) == 1
    artifact = json.loads(Path(result["result_json_path"]).read_text())
    assert artifact["items"][0]["sources"] == ["S0001"]
    assert "text" not in artifact["sources"][0]
    assert "[S0001]" in assistant.read_result(result["task_id"])["text"]


def test_all_long_note_chunks_reach_model_without_truncation(assistant):
    path = note(assistant, text="line abcdefghijklmnop\n" * 600)
    result = assistant.run("notes", paths=[str(path)])
    assert result["status"] == "succeeded"
    inputs = json.loads((assistant.run_path(result["task_id"]) / "inputs.json").read_text())
    assert "".join(s["text"] for s in inputs["sources"]) == path.read_text()
    sent = [s["id"] for c in assistant.backend.calls for s in c["source_data"]]
    assert sent == [s["id"] for s in inputs["sources"]]
    assert result["batch_count"] > 1


@pytest.mark.parametrize("answer", [
    "not JSON", '{"items":[]}',
    '{"items":[{"section":"요약","text":"claim","sources":["S9999"]}]}',
    '{"items":[{"section":"요약","text":"claim","sources":[]}]}',
    '{"items":[{"section":"unknown","text":"claim","sources":["S0001"]}]}',
])
def test_invalid_outputs_fail_without_publishing_and_retain_candidate(assistant, answer):
    assistant.backend = Backend(lambda *_: answer)
    result = assistant.run("notes", paths=[str(note(assistant))])
    assert result["status"] == "failed"
    run = assistant.run_path(result["task_id"])
    assert (run / "candidate-000.json").exists()
    assert not (run / "result.md").exists()


def test_classification_preserves_files_and_covers_each_once(assistant):
    path = note(assistant)
    before = path.read_bytes()
    result = assistant.run("classify", directory=str(path.parent))
    assert result["status"] == "succeeded"
    assert path.read_bytes() == before
    artifact = json.loads(Path(result["result_json_path"]).read_text())
    assert artifact["items"][0]["category"] == "notes"
    assert artifact["sources"][0]["basis"] == "text_sample"


@pytest.mark.parametrize("items", [
    [{"source": "S0001", "category": "invented", "reason": "x"}],
    [{"source": "S9999", "category": "notes", "reason": "x"}],
    [{"source": "S0001", "category": "notes", "reason": "x"}] * 2,
])
def test_bad_classification_rejected(assistant, items):
    assistant.backend = Backend(lambda *_: json.dumps({"items": items}))
    note(assistant)
    assert assistant.run("classify", directory=assistant.config["read_roots"][-1])["status"] == "failed"


def test_classification_does_not_infer_binary_contents(assistant):
    path = note(assistant, "photo.png", "binary fake")
    sources, _ = assistant.classification_sources(str(path.parent))
    assert sources[0]["text"] == "" and sources[0]["basis"] == "filename_and_metadata"


def test_scope_and_sensitive_paths_are_excluded(assistant, tmp_path):
    normal = note(assistant)
    note(assistant, ".env", "SECRET")
    (normal.parent / "link.md").symlink_to(normal)
    sources, _ = assistant.text_sources([str(normal.parent)])
    assert [s["path"] for s in sources] == [str(normal)]
    outside = tmp_path / "outside.md"
    outside.write_text("private")
    with pytest.raises(ValueError, match="read roots"):
        assistant.text_sources([str(outside)])
    with pytest.raises(ValueError, match="Symlink"):
        assistant.text_sources([str(normal.parent / "link.md")])
    with pytest.raises(ValueError, match="Hidden"):
        assistant.text_sources([str(normal.parent / ".env")])


def test_explicit_allow_root_and_hidden_workspace_inbox(assistant, tmp_path):
    extra = tmp_path / "extra"
    extra.mkdir()
    assistant.allow_root(extra)
    assert extra in Assistant(assistant.root, Backend()).read_roots
    root = tmp_path / ".byeori-assistant"
    initialize(root)
    (root / "inbox" / "work.md").write_text("manually supplied")
    hidden = Assistant(root, Backend())
    assert hidden.run("notes", paths=[str(root / "inbox")])["status"] == "succeeded"


def test_size_and_model_budget_reject_without_call(assistant):
    path = note(assistant, text="x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="size budget"):
        assistant.prepare("notes", paths=[str(path)])
    path.write_text("small")
    assistant.backend = Backend(fits=lambda *_: False)
    result = assistant.run("notes", paths=[str(path)])
    assert result["status"] == "failed" and not assistant.backend.calls


def test_reports_can_chain_successful_drafts_and_detect_tampering(assistant):
    first = assistant.run("notes", paths=[str(note(assistant))])
    result = assistant.run("report", task_ids=[first["task_id"]], title="주간 보고서")
    assert result["status"] == "succeeded"
    assert "# 주간 보고서" in assistant.read_result(result["task_id"])["text"]
    artifact = json.loads(Path(result["result_json_path"]).read_text())
    assert artifact["sources"][0]["source_task"] == first["task_id"]
    Path(first["result_path"]).write_text("altered")
    with pytest.raises(RuntimeError, match="hash"):
        assistant.run("report", task_ids=[first["task_id"]])
    with pytest.raises(RuntimeError, match="hash"):
        assistant.read_result(first["task_id"])


def test_input_snapshot_hash_is_checked_before_inference(assistant):
    receipt = assistant.prepare("notes", paths=[str(note(assistant))])
    (assistant.run_path(receipt["task_id"]) / "inputs.json").write_text("{}")
    result = assistant.execute(receipt["task_id"])
    assert result["status"] == "failed" and "hash" in result["error"]
    assert not assistant.backend.calls


def test_dead_process_task_is_interrupted(assistant):
    receipt = assistant.prepare("notes", paths=[str(note(assistant))])
    receipt["pid"] = 2_000_000_000
    write_json(assistant.run_path(receipt["task_id"]) / "receipt.json", receipt)
    assert assistant.get(receipt["task_id"])["status"] == "interrupted"


def test_background_jobs_return_immediately_and_keep_queue_alive(assistant):
    started, finish = threading.Event(), threading.Event()
    def respond(system, data):
        started.set()
        assert finish.wait(3)
        return json.dumps({"items": [{"section": "요약", "text": "done", "sources": [data["source_data"][0]["id"]]}]})
    assistant.backend = Backend(respond)
    jobs = AssistantJobs(assistant)
    first = jobs.submit("notes", paths=[str(note(assistant))])
    assert started.wait(3)
    assert assistant.get(first["task_id"])["status"] == "running"
    second = jobs.submit("notes", paths=[str(note(assistant))])
    assert second["status"] == "queued"
    finish.set()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and assistant.get(second["task_id"])["status"] != "succeeded":
        time.sleep(0.01)
    assert assistant.get(first["task_id"])["status"] == "succeeded"
    assert assistant.get(second["task_id"])["status"] == "succeeded"


def test_git_summary_is_local_bounded_and_ignores_dirty_files(assistant):
    repo = Path(assistant.config["read_roots"][-1]) / "repo"
    repo.mkdir()
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    git("init")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.test")
    file = repo / "work.txt"
    file.write_text("first")
    git("add", "work.txt")
    git("commit", "-m", "Add work")
    file.write_text("second")
    git("commit", "-am", "Update work")
    file.write_text("UNCOMMITTED_SECRET")
    result = assistant.run("commits", repo=str(repo), since="2000-01-01", limit=1)
    assert result["status"] == "succeeded"
    assert result["request"]["scope"]["limit_reached"]
    assert len(result["request"]["scope"]["commit_ids"]) == 1
    assert "UNCOMMITTED_SECRET" not in json.dumps(assistant.backend.calls)
    assert "Update work" in json.dumps(assistant.backend.calls)
    sources, scope = assistant.git_sources(repo, since="2000-01-01", limit=1, include_diff=True)
    assert "+second" in "".join(s["text"] for s in sources)
    assert scope["basis"] == "commit_messages_and_diff"


def test_cli_exit_codes_and_workspace_preservation(tmp_path, capsys, monkeypatch):
    workspace = str(tmp_path / "workspace")
    assert main(["--workspace", workspace, "init"]) == 0
    before = (Path(workspace) / "config.json").read_bytes()
    assert main(["--workspace", workspace, "init", "--model", "other"]) == 2
    assert before == (Path(workspace) / "config.json").read_bytes()
    assistant = Assistant(workspace, Backend(lambda *_: "bad JSON"))
    input_file = Path(workspace) / "inbox" / "work.md"
    input_file.write_text("hello")
    monkeypatch.setattr("byeori.local.assistant_cli.build_assistant", lambda _: assistant)
    assert main(["--workspace", workspace, "notes", str(input_file)]) == 1
    assert "failed" in capsys.readouterr().out


def test_mcp_tools_registered(assistant):
    tools = asyncio.run(create_server(assistant).list_tools())
    assert {t.name for t in tools} == {"organize_notes", "summarize_commits", "classify_files",
        "draft_report", "get_task", "list_tasks", "read_task_result"}


def test_native_ollama_gets_task_specific_schema_and_receipt(assistant, monkeypatch, tmp_path):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    bodies = []
    def chat(request):
        body = json.loads(request.content)
        bodies.append(body)
        schema = body["format"]["properties"]["items"]["items"]["properties"]
        assert schema["section"]["enum"] == ["요약", "결정 사항", "할 일", "미확정 사항"]
        assert schema["sources"]["items"]["enum"] == ["S0001"]
        return httpx.Response(200, json={"done": True, "done_reason": "stop", "model": "test",
            "message": {"content": json.dumps({"items": [{"section": "요약", "text": "draft", "sources": ["S0001"]}]})}})
    assistant.backend = OllamaBackend("test", context=8192, output=2048, transport=ollama_transport(chat))
    result = assistant.run("notes", paths=[str(note(assistant))])
    assert result["status"] == "succeeded" and bodies[0]["think"] is False
    assert result["calls"][0]["metadata"]["payload_sha256"]


def test_mcp_submission_and_polling_return_readable_result(assistant):
    path = note(assistant)
    server = create_server(assistant)
    async def submit():
        content = await server.call_tool("organize_notes", {"paths": [str(path)]})
        return json.loads(content[0].text)
    submitted = asyncio.run(submit())
    assert submitted["status"] == "queued"
    task_id = submitted["task_id"]
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and assistant.get(task_id)["status"] != "succeeded":
        time.sleep(0.01)
    async def read():
        content = await server.call_tool("read_task_result", {"task_id": task_id})
        return json.loads(content[0].text)
    result = asyncio.run(read())
    assert result["status"] == "succeeded" and "[S0001]" in result["text"]


def test_oversized_file_list_is_not_silently_cut_off(assistant):
    root = Path(assistant.config["read_roots"][-1])
    for index in range(201):
        (root / f"file-{index}.txt").write_text("x")
    with pytest.raises(ValueError, match="200 files"):
        assistant.prepare("classify", directory=str(root))
    assert not assistant.backend.calls


def test_classification_required_map_covers_all_files(assistant):
    first = note(assistant)
    note(assistant, "data.csv", "x,y\n1,2\n")
    assistant.backend = Backend(lambda _, data: json.dumps({"classifications": {
        s["id"]: {"category": "data" if s["file"].endswith(".csv") else "notes", "reason": "파일 형식 확인"}
        for s in data["source_data"]}}))
    result = assistant.run("classify", directory=str(first.parent))
    assert result["status"] == "succeeded"
    artifact = json.loads(Path(result["result_json_path"]).read_text())
    assert {i["source"] for i in artifact["items"]} == {"S0001", "S0002"}


@pytest.mark.parametrize("response", [
    '{"classifications":{"S0001":{"category":"notes","reason":"짧은 이유"}}}',
    '{"classifications":{"S0001":{"category":"notes","reason":"a"},"S0001":{"category":"notes","reason":"b"}}}',
])
def test_classification_placeholders_and_duplicate_json_keys_are_rejected(assistant, response):
    file = note(assistant)
    assistant.backend = Backend(lambda *_: response)
    assert assistant.run("classify", directory=str(file.parent))["status"] == "failed"


def test_work_token_calibration_preserves_original_paper_guard(monkeypatch, tmp_path):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    system, prompt = "Summarize Git file statistics", '{"source":"' + "file.py | 42 ++++----\n" * 20 + '"}'
    reported = int(estimate_tokens(system + prompt) * 0.479)
    def chat(request):
        return httpx.Response(200, json={"done": True, "done_reason": "stop", "model": "test",
            "prompt_eval_count": reported, "message": {"content": "short summary"}})
    kwargs = {"context": 8192, "output": 2048, "transport": ollama_transport(chat)}
    with pytest.raises(ModelError, match="truncated"):
        OllamaBackend("test", **kwargs).generate(system, prompt)
    result = OllamaBackend("test", truncation_ratio=0.35, **kwargs).generate(system, prompt)
    assert result.input_tokens == reported
    assert result.metadata["truncation_ratio"] == 0.35


@pytest.mark.parametrize("response", [
    '{"summaries":{"S0002":"Unknown source"}}',
    '{"items":[{"section":"주요 변경","text":"No per-commit binding","sources":["S0001"]}]}',
])
def test_default_commit_summary_cannot_omit_source_bindings(response):
    with pytest.raises(ModelError):
        Assistant.parse(response, "commits", {"scope": {"commit_body_included": False}},
                        [{"id": "S0001", "subject": "Update docs"}])


def test_report_draft_citations_cannot_collide_with_outer_source_ids():
    prompt = Assistant.prompt({"instruction": ""}, [{"id": "S0002", "path": "/draft/result.md",
        "basis": "generated_draft", "text": "A claim from another task [S0001]."}])
    record = json.loads(prompt)["source_data"][0]
    assert record["id"] == "S0002" and "[S0001]" not in record["text"]
    assert "A claim from another task" in record["text"]
