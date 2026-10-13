"""Resuming a paper from what an earlier attempt already computed, and only from that."""
import json

import httpx
import pytest

import byeori.local.service as service_module
from byeori.local.cli import main
from byeori.local.llm import AbnormalStop, Generation, ModelError, OllamaBackend, OutputTruncated, estimate_tokens
from byeori.local.service import LocalService
from byeori.local.store import LocalStore
from local_helpers import ollama_transport
from test_local_integrity import Extractor, Model, PartsModel, long_tei


# Five parts at PartsModel's window, so a crash in the fourth leaves three finished.
PARAGRAPHS = 40


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))


@pytest.fixture
def paper(tmp_path):
    store = LocalStore(tmp_path / "data")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\nfixture")
    return store, store.add(pdf)["paper_id"]


class Crashes(PartsModel):
    """Digests until the fourth part, where the server goes away, until told otherwise."""

    crash_at = 4
    digest = "a" * 64

    def __init__(self):
        super().__init__()
        self.crash = True

    def fingerprint(self):
        return {"model": self.model, "model_digest": self.digest, "template_sha256": "t",
                "context": self.context, "output": self.output}

    def generate(self, system, prompt, *, think=None):
        if (self.crash and system.startswith("Digest one part")
                and sum(s.startswith("Digest one part") for s in self.systems) == self.crash_at - 1):
            self.systems.append(system)
            raise ModelError("server went away")
        return super().generate(system, prompt, think=think)

    def digests_asked(self):
        return sum(s.startswith("Digest one part") for s in self.systems)


class Versioned(Extractor):
    def __init__(self, xml, version):
        super().__init__(xml)
        self.version = version

    def ready(self):
        return {"ready": True, "version": self.version}


def crashed(store, paper_id, model=None, extractor=None):
    """A service whose first attempt at the paper died in its fourth part."""
    model = model or Crashes()
    service = LocalService(store, model, extractor or Extractor(long_tei(PARAGRAPHS)))
    with pytest.raises(RuntimeError, match="server went away"):
        service.process(paper_id)
    failed = store.jobs()[0]
    model.crash = False
    model.systems.clear()
    return service, model, failed


def test_resume_after_a_crash_in_the_fourth_part_reuses_three_digests(paper):
    store, pid = paper
    service, model, failed = crashed(store, pid)
    result = service.process(pid)
    planned = result["coverage"]["parts_planned"]
    assert planned >= 4
    assert model.digests_asked() == planned - 3, "the three finished parts are not asked again"
    assert result["coverage"]["parts_reused"] == 3 and result["checkpoints_reused"] == 4
    receipt = json.loads(store.path(f"runs/{result['job_id']}/receipt.json").read_text())
    reused = receipt["checkpoints"]["reused"]
    assert [item["stage"] for item in reused] == ["extraction", "digest", "digest", "digest"]
    assert {item["job_id"] for item in reused} == {failed["job_id"]}
    events = [event["event"] for event in store.events(result["job_id"])]
    assert events.count("checkpoint_reused") == 4


def test_checkpoint_is_not_reused_when_the_model_digest_changes(paper):
    store, pid = paper
    service, model, _ = crashed(store, pid)
    model.digest = "b" * 64
    result = service.process(pid)
    assert model.digests_asked() == result["coverage"]["parts_planned"]
    assert result["checkpoints_reused"] == 1, "only the extraction, which no model wrote"


def test_checkpoint_is_not_reused_when_the_prompt_version_changes(paper, monkeypatch):
    store, pid = paper
    service, model, _ = crashed(store, pid)
    monkeypatch.setattr(service_module, "PROMPT_VERSION", "local-note-test")
    result = service.process(pid)
    assert model.digests_asked() == result["coverage"]["parts_planned"]


def test_checkpoint_is_not_reused_when_the_extraction_changes(paper):
    store, pid = paper
    service, model, failed = crashed(store, pid, extractor=Versioned(long_tei(PARAGRAPHS), "0.9.1"))
    service.extractor = Versioned(long_tei(PARAGRAPHS).replace(b"number 3.", b"number three."), "0.9.2")
    result = service.process(pid)
    assert result["checkpoints_reused"] == 0
    assert model.digests_asked() == result["coverage"]["parts_planned"]
    assert store.note(pid)["extraction_path"] == f"runs/{result['job_id']}/document.json"


def test_a_corrupt_checkpoint_file_is_ignored_and_recorded_not_deleted(paper):
    store, pid = paper
    service, model, failed = crashed(store, pid)
    first = store.path(f"runs/{failed['job_id']}/digest-01.md")
    first.write_bytes(b"- tampered [P0001]")
    result = service.process(pid)
    assert model.digests_asked() == result["coverage"]["parts_planned"] - 2
    assert first.read_bytes() == b"- tampered [P0001]", "evidence of tampering is kept"
    corrupt = [event for event in store.events(failed["job_id"]) if event["event"] == "checkpoint_corrupt"]
    assert corrupt and corrupt[0]["detail"]["problem"] == "hash_mismatch"


def test_no_resume_ignores_every_checkpoint(paper):
    store, pid = paper
    service, model, _ = crashed(store, pid)
    result = service.process(pid, resume=False)
    assert result["checkpoints_reused"] == 0
    assert model.digests_asked() == result["coverage"]["parts_planned"]


def test_a_published_note_ends_its_checkpoints(paper):
    """Processing a paper again after its note was published is a request to start over."""
    store, pid = paper
    service, model, _ = crashed(store, pid)
    service.process(pid)
    model.systems.clear()
    again = service.process(pid)
    assert again["checkpoints_reused"] == 0
    assert model.digests_asked() == again["coverage"]["parts_planned"]


def test_a_part_that_ran_out_of_output_before_is_split_without_asking_again(paper):
    store, pid = paper

    class RefusesLargeParts(Crashes):
        crash_at = 99

        def generate(self, system, prompt, *, think=None):
            if system.startswith("Digest one part") and prompt.count("[P") > 3:
                self.systems.append(system)
                raise OutputTruncated("Model did not finish normally: output limit")
            if self.crash and "faithful digests" in system:
                self.systems.append(system)
                raise ModelError("server went away")
            return super().generate(system, prompt, think=think)

    model = RefusesLargeParts()
    service = LocalService(store, model, Extractor(long_tei(20)))
    with pytest.raises(RuntimeError, match="server went away"):
        service.process(pid)
    truncated_first = sum(1 for s in model.systems if s.startswith("Digest one part"))
    model.crash = False
    model.systems.clear()
    result = service.process(pid)
    assert model.digests_asked() == 0, "every digest and every split is read back"
    assert result["coverage"]["parts_split"] > 0 and truncated_first > model.digests_asked()


@pytest.mark.parametrize("response,error", [
    ({"done": True, "done_reason": "length", "message": {"content": "partial"}}, OutputTruncated),
    ({"done": False, "done_reason": "stop", "message": {"content": "partial"}}, AbnormalStop),
    ({"done": True, "done_reason": "unload", "message": {"content": "partial"}}, AbnormalStop)])
def test_output_truncation_is_its_own_error(response, error):
    backend = OllamaBackend("test", transport=ollama_transport(lambda r: httpx.Response(200, json=response)))
    with pytest.raises(error, match="did not finish"):
        backend.generate("system", "paper")


def test_a_larger_output_budget_is_sent_and_checked_against_the_context():
    bodies = []

    def chat(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"done": True, "done_reason": "stop", "message": {"content": "ok"}})

    backend = OllamaBackend("test", context=4096, output=1024, transport=ollama_transport(chat))
    result = backend.generate("system", "paper", num_predict=2048)
    assert bodies[0]["options"]["num_predict"] == 2048 and result.metadata["num_predict"] == 2048
    with pytest.raises(ModelError, match="Nothing was truncated"):
        backend.generate("system", "x" * 6000, num_predict=3000)


class TruncatesNote(Model):
    def __init__(self, times=1):
        super().__init__()
        self.times, self.requests = times, []

    def generate(self, system, prompt, *, think=None, num_predict=None):
        self.requests.append(num_predict)
        if len(self.requests) <= self.times:
            raise OutputTruncated("Model did not finish normally: output limit")
        return Generation(self.answer, self.model, 100, 200, "stop")


def test_a_truncated_final_note_is_retried_once_with_a_larger_output_within_context(paper):
    store, pid = paper
    model = TruncatesNote()
    result = LocalService(store, model, Extractor()).process(pid)
    assert result["status"] == "succeeded"
    assert model.requests[0] is None and model.requests[1] == 2 * model.output
    assert len(model.requests) == 2
    receipt = json.loads(store.path(f"runs/{result['job_id']}/receipt.json").read_text())
    assert receipt["note_retry"] == {"retry_cause": "output_truncated", "num_predict_override": 8192}


def test_the_retry_never_asks_for_more_than_the_context_leaves(paper):
    store, pid = paper
    model = TruncatesNote()
    model.context, model.output = 12000, 4096
    service = LocalService(store, model, Extractor(long_tei(14)))
    result = service.process(pid)
    assert result["coverage"]["path"] == "single"
    from byeori.local.service import NOTE_SYSTEM, WRITE_NOW, format_blocks
    blocks = service.store.document(service.store.note(pid))["blocks"]
    room = 12000 - estimate_tokens(NOTE_SYSTEM + format_blocks(blocks) + WRITE_NOW) - 512
    assert model.requests[1] == min(2 * 4096, room) and model.requests[1] > 4096


def test_a_twice_truncated_note_is_not_published(paper):
    store, pid = paper
    model = TruncatesNote(times=2)
    with pytest.raises(RuntimeError, match="output limit") as raised:
        LocalService(store, model, Extractor()).process(pid)
    assert raised.value.error_code == "output_truncated"
    assert len(model.requests) == 2
    assert store.jobs()[0]["error_code"] == "output_truncated"
    assert not store.papers_with_notes()


def test_a_reused_extraction_keeps_the_note_pointing_at_the_existing_document_json(paper):
    store, pid = paper
    service, _, failed = crashed(store, pid)
    result = service.process(pid)
    note = store.note(pid)
    assert note["extraction_path"] == f"runs/{failed['job_id']}/document.json"
    assert not store.path(f"runs/{result['job_id']}/document.json").exists(), "a pointer, not a copy"
    assert service.context(pid, "P0001")["text"]
    assert store.integrity_problems(deep=True) == []
    assert f'extraction_path: "runs/{failed["job_id"]}/document.json"' in note["text"]


def test_revalidate_reads_the_extraction_path_from_the_receipt(paper, monkeypatch):
    store, pid = paper
    service, _, failed = crashed(store, pid)

    def stricter(*args, **kwargs):
        raise ValueError("Uncited statement in a check that has since been relaxed")

    with monkeypatch.context() as patch:
        patch.setattr(service_module, "validate_note", stricter)
        with pytest.raises(RuntimeError, match="since been relaxed"):
            service.process(pid)
    candidate_job = store.jobs()[0]["job_id"]
    assert not store.path(f"runs/{candidate_job}/document.json").exists()
    published = service.revalidate(candidate_job)
    assert published["published"] is True
    assert store.note(pid)["extraction_path"] == f"runs/{failed['job_id']}/document.json"
    receipt = json.loads(store.path(f"runs/{published['job_id']}/receipt.json").read_text())
    assert receipt["outcome"] == "succeeded" and receipt["kind"] == "revalidate"


def test_checkpoints_listing_names_stage_job_and_files(paper, monkeypatch, capsys):
    import byeori.local.cli as cli
    store, pid = paper
    service, _, failed = crashed(store, pid)
    monkeypatch.setattr(cli, "build_service", lambda *a, **k: service)
    assert main(["checkpoints", pid]) == 0
    listed = json.loads(capsys.readouterr().out)["checkpoints"]
    assert sorted(item["stage"] for item in listed) == ["digest"] * 3 + ["extraction"]
    assert all(item["job_id"] == failed["job_id"] and item["files"] for item in listed)


def test_a_caller_can_hold_a_json_prompt_to_its_own_truncation_ratio():
    """A JSON prompt read at 0.548 of its estimate is not a truncated one at 0.35."""
    def chat(request):
        body = json.loads(request.content)
        estimated = estimate_tokens(body["messages"][0]["content"] + body["messages"][1]["content"])
        return httpx.Response(200, json={"done": True, "done_reason": "stop", "message": {"content": "{}"},
                                         "prompt_eval_count": int(estimated * 0.5)})

    backend = OllamaBackend("test", transport=ollama_transport(chat))
    with pytest.raises(ModelError, match="truncated"):
        backend.generate("system", '{"a": [1, 2, 3]}' * 40)
    result = backend.generate("system", '{"a": [1, 2, 3]}' * 40, truncation_ratio=0.35)
    assert result.metadata["truncation_ratio"] == 0.35
