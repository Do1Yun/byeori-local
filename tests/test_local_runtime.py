import asyncio
import json
import os
from pathlib import Path
import sys

import httpx
import pytest

from byeori.local.llm import Generation, ModelError, OllamaBackend
from byeori.local.service import HEADINGS, LocalService, parse_tei
from byeori.local.store import LocalStore

XML = b'<TEI><text><body><div><head>Results</head><p>The cohort included 42 samples.</p></div></body></text></TEI>'


class Extractor:
    def extract(self, pdf):
        return XML, parse_tei(XML)


class Model:
    model = "test-model"
    context = 32768
    output = 4096

    @property
    def input_budget(self):
        return self.context - self.output - 512

    def fits(self, system, prompt):
        from byeori.local.llm import estimate_tokens
        return estimate_tokens(system + prompt) <= self.input_budget

    def __init__(self):
        self.answer = "\n\n".join(f"## {heading}\n\nThe cohort included 42 samples. [P0001]" for heading in HEADINGS)
        self.calls = 0

    def generate(self, system, prompt):
        self.calls += 1
        return Generation(self.answer, self.model, 100, 200, "stop")


@pytest.fixture
def local(tmp_path):
    store = LocalStore(tmp_path / "data")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\nfixture")
    paper = store.add(pdf, "Cohort study")
    model = Model()
    return LocalService(store, model, Extractor()), paper["paper_id"], pdf


def test_pipeline_search_context_and_cited_answer(local):
    service, pid, _ = local
    result = service.process(pid)
    assert result["status"] == "succeeded"
    assert service.store.search("cohort samples")[0]["doc_id"] == pid
    note = service.read(pid, max_chars=40)
    assert note["next_start"] == 40
    assert service.context(pid, "P0001")["text"] == "The cohort included 42 samples."
    assert "## 1. Document Information" in service.store.note(pid)["text"]
    service.backend.answer = "The cohort has 42 samples. [E1]"
    answer = service.ask("How many samples?", pid)
    assert answer["citations"][0]["paper_id"] == pid
    assert service.store.jobs(result["job_id"])[0]["status"] == "succeeded"


def test_duplicate_and_failed_regeneration_preserve_good_note(local):
    service, pid, pdf = local
    service.process(pid)
    before = service.store.note(pid)
    assert service.store.add(pdf)["duplicate"]
    service.backend.answer = "Bad output [P9999]"
    with pytest.raises(RuntimeError, match="failed"):
        service.process(pid)
    assert service.store.note(pid) == before
    assert len(service.store.search("cohort")) == 1
    assert service.store.jobs()[0]["status"] == "failed"


def test_original_tamper_is_detected_before_model(local):
    service, pid, _ = local
    service.store.path(f"papers/{pid}/original.pdf").write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="hash changed"):
        service.process(pid)
    assert service.backend.calls == 0


def test_no_search_evidence_does_not_call_model(local):
    service, _, _ = local
    assert service.ask("cohort")["answer_status"] == "insufficient_evidence"
    assert service.backend.calls == 0


def test_unknown_answer_citation_is_rejected(local):
    service, pid, _ = local
    service.process(pid)
    service.backend.answer = "Made up. [E9]"
    answer = service.ask("cohort", pid)
    assert answer["answer_status"] == "insufficient_evidence"
    assert "Made up" not in answer["answer"]


def test_paths_cannot_escape_workspace(local):
    service, _, _ = local
    with pytest.raises(ValueError, match="inside"):
        service.store.path("../secret")
    with pytest.raises(ValueError, match="Unknown paper"):
        service.read("../../secret")


@pytest.mark.parametrize("xml", [b'<TEI><text><body/></text></TEI>',
    b'<TEI><abstract><p>Abstract only.</p></abstract></TEI>', b'<!DOCTYPE TEI><TEI/>'])
def test_extraction_refuses_missing_body_or_entities(xml):
    with pytest.raises(ValueError):
        parse_tei(xml)


def test_ollama_request_and_stop_reason():
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"done": True, "done_reason": "stop",
            "message": {"content": "result", "thinking": "not published"}, "model": "test"})
    backend = OllamaBackend("test", transport=httpx.MockTransport(handler))
    assert backend.generate("system", "paper").text == "result"
    assert requests[0]["stream"] is False
    assert requests[0]["options"]["num_ctx"] == 32768


@pytest.mark.parametrize("response", [
    {"done": True, "done_reason": "length", "message": {"content": "partial"}},
    {"done": False, "done_reason": "stop", "message": {"content": "partial"}},
    {"done": True, "done_reason": "stop", "message": {"content": ""}},
])
def test_ollama_does_not_publish_truncated_or_empty_response(response):
    backend = OllamaBackend("test", transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response)))
    with pytest.raises(ModelError):
        backend.generate("system", "paper")


def test_context_overflow_rejected_before_network():
    def handler(request):
        pytest.fail("oversized input must not reach the server")
    backend = OllamaBackend("test", context=2048, output=128, transport=httpx.MockTransport(handler))
    with pytest.raises(ModelError, match="Nothing was truncated"):
        backend.generate("system", "x" * 20000)


def test_mcp_tools_use_local_service(local):
    from byeori.local.mcp_server import create_server
    service, pid, _ = local
    service.process(pid)
    server = create_server(service)
    async def check():
        tools = await server.list_tools()
        assert {t.name for t in tools} == {"list_papers", "search_wiki", "read_evidence_note",
            "list_note_revisions", "read_paper_context", "ask_byeori", "get_job"}
        result = await server.call_tool("search_wiki", {"query": "cohort"})
        assert pid in str(result)
    asyncio.run(check())


def test_worker_lock_and_crash_recovery(local):
    from byeori.local.locking import worker_lock
    service, pid, _ = local
    interrupted = service.store.start(pid)
    with worker_lock(service.store.root):
        with pytest.raises(RuntimeError, match="Another worker"):
            service.process(pid)
    service.process(pid)
    assert service.store.jobs(interrupted)[0]["status"] == "interrupted"


def test_grobid_http_request():
    from byeori.local.service import GrobidExtractor
    def handler(request):
        assert request.url.path == "/api/processFulltextDocument"
        assert b'filename="paper.pdf"' in request.content
        return httpx.Response(200, content=XML)
    xml, blocks = GrobidExtractor(transport=httpx.MockTransport(handler)).extract(b"%PDF-1.7")
    assert xml == XML and blocks[0]["id"] == "P0001"


def test_real_stdio_mcp_handshake_and_search(local):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    service, pid, _ = local
    service.process(pid)

    async def run():
        parameters = StdioServerParameters(command=sys.executable,
            args=["-m", "byeori.local.mcp_server"],
            env={**os.environ, "BYEORI_LOCAL_DATA": str(service.store.root)})
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("search_wiki", {"query": "cohort"})
                assert not result.isError
                assert pid in str(result.content)
    asyncio.run(run())
