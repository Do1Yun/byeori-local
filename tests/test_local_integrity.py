"""Integrity invariants for the local runtime, taken from real GROBID output and real notes.

Every assertion here is something a person using byeori-local can see: what a citation
resolves to, what a published note contains, what a failed job leaves behind. The TEI
fixture copies the shape GROBID 0.9.1 actually emits for a paper with a numeric table,
including the abstract nested in a <div> and a figure caption between two body paragraphs.
"""
import json
import re

import pytest

from byeori.local.llm import Generation, ModelError
from byeori.local.service import HEADINGS, LocalService, extraction_status, parse_tei
from byeori.local.store import LocalStore

TEI = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader><encodingDesc><appInfo><application version="0.9.1" ident="GROBID"/></appInfo></encodingDesc>
<profileDesc><abstract>
<div xmlns="http://www.tei-c.org/ns/1.0"><p>We propose the Transformer, based solely on attention.</p></div>
</abstract></profileDesc></teiHeader>
<text xml:lang="en"><body>
<div><head n="6.1">Machine Translation</head>
<p>Our model achieves 28.4 BLEU on the WMT 2014 English-to-German task.</p>
<figure xml:id="fig_0"><head>Figure 1</head><label>1</label><figDesc>The Transformer architecture.</figDesc></figure>
<p>Training took 3.5 days on 8 P100 GPUs.</p>
</div>
<figure type="table" xml:id="tab_1"><head>Table 2</head><label>2</label>
<figDesc>BLEU scores and training cost.</figDesc>
<table><row><cell>Model</cell><cell>EN-DE</cell><cell>Cost</cell></row>
<row><cell>Deep-Att</cell><cell>39.2</cell><cell>1.0 10 20</cell></row>
<row><cell>GNMT</cell><cell>24.6</cell><cell>2.3 10 19</cell></row></table></figure>
<div><head>Conclusion</head><p>Attention is sufficient.</p></div>
</body></text></TEI>"""

NO_ABSTRACT = b'<TEI><text><body><div><head>Results</head><p>The cohort included 42 samples.</p></div></body></text></TEI>'


class Extractor:
    """Stands in for GROBID; the bytes and the parse are the real ones."""

    def __init__(self, xml=TEI):
        self.xml = xml

    def extract(self, pdf):
        return self.xml, parse_tei(self.xml)


class Model:
    model, context, output = "test-model", 32768, 4096

    @property
    def input_budget(self):
        return self.context - self.output - 512

    def fits(self, system, prompt):
        from byeori.local.llm import estimate_tokens
        return estimate_tokens(system + prompt) <= self.input_budget

    def __init__(self, cite="P0001", trailing="  "):
        # Real models end a heading line with a markdown hard break; qwen3:8b did on the first paper.
        self.answer = "\n\n".join(f"## {heading}{trailing}\n\nThe model reports 28.4 BLEU. [{cite}]"
                                 for heading in HEADINGS)
        self.calls = 0

    def generate(self, system, prompt):
        self.calls += 1
        return Generation(self.answer, self.model, 100, 200, "stop")


@pytest.fixture
def workspace(tmp_path):
    store = LocalStore(tmp_path / "data")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\nfixture")
    paper = store.add(pdf, "Attention Is All You Need")
    return store, paper["paper_id"], pdf


@pytest.fixture
def local(workspace):
    store, paper_id, pdf = workspace
    return LocalService(store, Model(), Extractor()), paper_id, pdf


# --- R02: what the extraction must carry ------------------------------------------------

def test_abstract_reaches_the_note_input():
    blocks = parse_tei(TEI)
    assert any("based solely on attention" in block["text"] for block in blocks), \
        "GROBID nests the abstract in a <div>; dropping it silently loses the paper's own summary"


def test_table_cells_stay_separate_values():
    table = next(block for block in parse_tei(TEI) if block["kind"] == "table")
    assert "39.21.0" not in table["text"], "gluing 39.2 to 1.0 invents a value no table contains"
    assert "24.62.3" not in table["text"]
    for value in ("39.2", "24.6", "1.0", "2.3"):
        assert value in table["text"]


def test_figure_caption_does_not_relabel_the_next_paragraph():
    blocks = parse_tei(TEI)
    paragraph = next(b for b in blocks if "3.5 days" in b["text"])
    assert paragraph["section"] == "Machine Translation", \
        "a figure caption must not become the section of the body text that follows it"


def test_extraction_status_names_a_missing_abstract():
    assert extraction_status(parse_tei(TEI)) == "complete"
    assert extraction_status(parse_tei(NO_ABSTRACT)) == "partial"


# --- the note a real model writes -------------------------------------------------------

def test_headings_with_a_trailing_hard_break_still_publish(local):
    service, paper_id, _ = local
    result = service.process(paper_id)
    assert result["status"] == "succeeded", "a correct note must not be discarded over trailing spaces"
    assert "## One-line Summary\n" in service.store.note(paper_id)["text"]


# --- R01: a citation keeps meaning what it meant -----------------------------------------

def test_an_old_citation_still_resolves_to_the_paragraph_it_cited(local):
    service, paper_id, _ = local
    service.process(paper_id)
    first = service.read(paper_id)
    cited = service.context(paper_id, "P0001", revision=first["revision_id"])["text"]

    moved = TEI.replace(b"<p>Our model achieves 28.4 BLEU on the WMT 2014 English-to-German task.</p>",
                        b"<p>An inserted paragraph that was not there before.</p>"
                        b"<p>Our model achieves 28.4 BLEU on the WMT 2014 English-to-German task.</p>")
    service.extractor = Extractor(moved)
    service.process(paper_id)

    assert service.read(paper_id)["revision_id"] != first["revision_id"]
    assert service.context(paper_id, "P0001", revision=first["revision_id"])["text"] == cited
    assert service.read(paper_id, revision=first["revision_id"])["note_sha256"] == first["note_sha256"]


def test_reading_a_revision_that_is_not_this_paper_is_refused(local):
    service, paper_id, _ = local
    service.process(paper_id)
    with pytest.raises(ValueError, match="revision"):
        service.read(paper_id, revision="no-such-revision")


# --- R04: the note, the index and the job status agree ----------------------------------

def test_the_active_note_always_belongs_to_a_succeeded_job(local, monkeypatch):
    service, paper_id, _ = local
    service.process(paper_id)
    published = service.store.note(paper_id)

    monkeypatch.setattr(service.store, "_record_success",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sqlite is locked")))
    service.backend = Model("P0001")
    with pytest.raises(RuntimeError):
        service.process(paper_id)

    assert service.store.note(paper_id) == published, "a job that failed must not leave its note live"
    assert service.store.integrity_problems() == []
    assert len(service.store.search("BLEU")) == 1


# --- R03: a crash during registration is recoverable -------------------------------------

def test_a_partly_written_original_can_be_registered_again(tmp_path):
    store = LocalStore(tmp_path / "data")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\nthe whole paper")
    paper_id = __import__("hashlib").sha256(pdf.read_bytes()).hexdigest()
    partial = store.path(f"papers/{paper_id}/original.pdf")
    partial.parent.mkdir(parents=True)
    partial.write_bytes(b"%PDF-1.7\nthe wh")          # the crash left half a file and no catalog row

    result = store.add(pdf, "Recovered")
    assert result["paper_id"] == paper_id
    assert store.path(result["pdf_path"]).read_bytes() == pdf.read_bytes()
    assert list(store.root.glob("quarantine/**/*.pdf")), "the partial file is kept, not deleted"


def test_a_registered_original_is_never_replaced(workspace):
    store, paper_id, pdf = workspace
    store.path(f"papers/{paper_id}/original.pdf").write_bytes(b"%PDF-1.7\ntampered")
    with pytest.raises(ValueError, match="changed"):
        store.add(pdf)


# --- R05: an honest refusal is an answer, not a crash ------------------------------------

def test_an_uncited_model_answer_is_reported_as_insufficient_evidence(local):
    service, paper_id, _ = local
    service.process(paper_id)
    service.backend.answer = "The model is better than the baseline."      # no [E1]
    answer = service.ask("How good is it?", paper_id)
    assert answer["answer_status"] == "insufficient_evidence"
    assert answer["reason"] == "model_answer_uncited"
    assert answer["citations"] == []
    assert "better than the baseline" not in json.dumps(answer, ensure_ascii=False)


def test_a_cited_answer_names_the_revision_it_read(local):
    service, paper_id, _ = local
    service.process(paper_id)
    service.backend.answer = "It reaches 28.4 BLEU. [E1]"
    answer = service.ask("How good is it?", paper_id)
    citation = answer["citations"][0]
    assert answer["answer_status"] == "answered"
    assert citation["note_revision_id"] == service.read(paper_id)["revision_id"]
    assert citation["extraction_id"] and citation["note_sha256"]
    assert answer["validation_level"] == "structure_checked"


# --- R08: the workspace is never invented ------------------------------------------------

def test_the_workspace_must_be_named_explicitly(tmp_path, monkeypatch):
    from byeori.local.cli import build_service
    monkeypatch.delenv("BYEORI_LOCAL_DATA", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="BYEORI_LOCAL_DATA"):
        build_service()
    assert list(tmp_path.iterdir()) == [], "no workspace may appear in whatever directory we started in"


def test_an_unknown_workspace_is_not_created_on_read(tmp_path, monkeypatch):
    from byeori.local.cli import build_service
    monkeypatch.setenv("BYEORI_LOCAL_DATA", str(tmp_path / "absent"))
    with pytest.raises(ValueError, match="does not exist"):
        build_service()
    assert not (tmp_path / "absent").exists()


# --- R09: a failure leaves a record you can read -----------------------------------------

def test_a_failed_job_leaves_a_receipt_naming_the_stage(local):
    service, paper_id, _ = local
    service.backend.answer = "Not a note at all."
    with pytest.raises(RuntimeError):
        service.process(paper_id)
    job = service.store.jobs()[0]
    assert job["status"] == "failed" and job["stage"] == "validate"
    receipt = json.loads(service.store.path(f"runs/{job['job_id']}/receipt.json").read_text())
    assert receipt["stage"] == "validate"
    assert receipt["error_type"] == "ValueError"
    assert receipt["extraction"]["status"] == "complete"
    assert receipt["extractor"]["version"] == "0.9.1"
    assert receipt["prompt_sha256"] and receipt["settings"]["context"] == 32768


def test_a_level_three_heading_is_still_the_same_section(workspace):
    """qwen3:8b wrote '### 2. Key Contributions' on the second real run; the names were right."""
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor())
    service.backend.answer = "## One-line Summary  \n\nIt reports 28.4 BLEU. [P0001]\n\n" + "\n\n".join(
        f"### {heading}\n\nIt reports 28.4 BLEU. [P0001]" for heading in HEADINGS[1:])
    assert service.process(paper_id)["status"] == "succeeded"
    note = service.store.note(paper_id)["text"]
    assert "### 2. Key Contributions" not in note
    # The headings a published note carries are the ones byeori's own validator expects of an
    # evidence note, section 1 included, so the AWS wiki would accept this page unchanged.
    from byeori.validation import LLM_WIKI_SOURCE_SECTIONS
    assert re.findall(r"^## (.+)$", note, re.M) == [h[3:] for h in LLM_WIKI_SOURCE_SECTIONS]


def test_a_subheading_the_note_invents_is_left_alone(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor())
    service.backend.answer = service.backend.answer.replace(
        "## 6. Related Work", "## 6. Related Work\n\n### Prior attention mechanisms")
    service.process(paper_id)
    assert "### Prior attention mechanisms" in service.store.note(paper_id)["text"]


# --- R06: the input budget, and a paper that does not fit one pass ------------------------

def long_tei(paragraphs, chars=400):
    body = "".join(f"<div><head>Section {i}</head><p>{'word ' * (chars // 5)}number {i}.</p></div>"
                   for i in range(1, paragraphs + 1))
    return f'<TEI><text><body>{body}</body></text></TEI>'.encode()


class PartsModel:
    """A window too small for the paper: digests come back carrying the IDs they were shown."""

    model = "test-model"

    def __init__(self, context=4096, output=1024):
        self.context, self.output = context, output
        self.systems = []

    @property
    def input_budget(self):
        return self.context - self.output - 512

    def fits(self, system, prompt):
        from byeori.local.llm import estimate_tokens
        return estimate_tokens(system + prompt) <= self.input_budget

    def generate(self, system, prompt):
        self.systems.append(system)
        shown = re.findall(r"\[(P\d+)\]", prompt)
        if system.startswith("Digest one part") or system.startswith("Merge these digests"):
            return Generation("- a reported value " + " ".join(f"[{i}]" for i in shown),
                              self.model, 100, 50, "stop")
        return Generation("\n\n".join(f"## {heading}\n\nA reported value. [{shown[0]}]"
                                      for heading in HEADINGS), self.model, 100, 200, "stop")


def test_a_paper_the_old_byte_rule_refused_now_fits_the_default_context():
    """The real paper measured 33,403 characters of extracted text and 8,567 prompt tokens."""
    from byeori.local.llm import OllamaBackend, estimate_tokens
    from byeori.local.service import NOTE_SYSTEM
    backend = OllamaBackend("test-model")
    assert backend.fits(NOTE_SYSTEM, "word " * 6680)
    assert estimate_tokens("word " * 6680) < 12000


def test_a_long_paper_is_written_part_by_part_with_every_block_presented(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, PartsModel(), Extractor(long_tei(20)))
    result = service.process(paper_id)
    coverage = result["coverage"]
    assert coverage["path"] == "chunked" and coverage["parts"] > 1
    assert coverage["blocks_presented"] == coverage["blocks_total"] == 20, \
        "every extracted block must reach the model in exactly one part"
    assert coverage["blocks_cited_in_digests"] == 20
    assert sum(s.startswith("Digest one part") for s in service.backend.systems) == coverage["parts"]
    note = store.note(paper_id)["text"]
    assert 'generation_path: "chunked"' in note and 'blocks_presented: "20/20"' in note


def test_each_part_of_a_long_paper_leaves_its_own_digest(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, PartsModel(), Extractor(long_tei(20)))
    result = service.process(paper_id)
    digests = sorted(store.path(f"runs/{result['job_id']}").glob("digest-*.md"))
    assert len(digests) == result["coverage"]["parts"]
    assert all(digest.read_text().startswith("- a reported value") for digest in digests)
    receipt = json.loads(store.path(f"runs/{result['job_id']}/receipt.json").read_text())
    assert len(receipt["generations"]) == result["coverage"]["parts"] + 1


def test_no_part_is_larger_than_the_model_can_answer(workspace):
    """The first real chunked run cut a digest off: a part must fit the reply, not just the window."""
    store, paper_id, _ = workspace
    service = LocalService(store, PartsModel(), Extractor(long_tei(20)))
    coverage = service.process(paper_id)["coverage"]
    from byeori.local.service import DIGEST_FIXED_OUTPUT, PROSE_OUTPUT_PER_TOKEN
    writable = (service.backend.output - DIGEST_FIXED_OUTPUT) / PROSE_OUTPUT_PER_TOKEN
    assert coverage["largest_part_tokens"] <= writable
    assert coverage["blocks_presented"] == coverage["blocks_total"]


def test_a_single_block_too_large_for_the_window_is_named(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, PartsModel(), Extractor(long_tei(3, chars=6000)))
    with pytest.raises(RuntimeError, match="Block P0001 needs about"):
        service.process(paper_id)
    assert store.jobs()[0]["stage"] == "generate"


def test_a_prompt_the_server_may_have_truncated_is_not_published():
    """Ollama answers a prompt longer than num_ctx by cutting it and reporting no error."""
    import httpx
    from byeori.local.llm import ModelError, OllamaBackend
    served = httpx.Response(200, json={"done": True, "done_reason": "stop", "model": "test-model",
                                       "message": {"content": "## One-line Summary"},
                                       "prompt_eval_count": 500, "eval_count": 20})
    backend = OllamaBackend("test-model", transport=httpx.MockTransport(lambda request: served))
    with pytest.raises(ModelError, match="may have been truncated"):
        backend.generate("system", "word " * 4000)


class LongDigestModel(PartsModel):
    """Digests nearly as long as their parts, which is what no window can then hold at once.

    Measured here, digesting a paper's parts compresses to about 0.54 of it, but merging those
    digests into fewer expands them: 1.76 output tokens per input token for two, 1.22 for four.
    So a paper whose digests do not fit one pass has no round that would make them fit.
    """

    FIRST = 0.95

    def generate(self, system, prompt):
        from byeori.local.llm import estimate_tokens
        self.systems.append(system)
        shown = list(dict.fromkeys(re.findall(r"\[(P\d+)\]", prompt)))
        if system.startswith("Digest one part"):
            labels = " ".join(f"[{block_id}]" for block_id in shown)
            target = int(estimate_tokens(prompt) * self.FIRST)
            filler = "value " * max(1, (target - estimate_tokens(labels)) // 2)
            return Generation(f"- {labels} {filler}", self.model, 100, 50, "stop")
        return Generation("\n\n".join(f"## {heading}\n\nA reported value. [{shown[0]}]"
                                      for heading in HEADINGS), self.model, 100, 200, "stop")


def test_digests_too_large_for_one_note_pass_name_the_window_they_need(workspace):
    """Nothing is written from part of the evidence: the paper is refused with what it needs."""
    store, paper_id, _ = workspace
    service = LocalService(store, LongDigestModel(16384, 4096), Extractor(long_tei(300)))
    with pytest.raises(RuntimeError, match=r"needs a context of about \d+ tokens"):
        service.process(paper_id)
    assert "nothing was truncated" in service.store.jobs()[0]["error"]
    assert service.store.integrity_problems() == []
    with pytest.raises(ValueError, match="no published"):
        store.note(paper_id)


# Character-class counts of two prompts this workspace sent to qwen3:8b, with the prompt token
# count the server reported for each: the whole paper in one pass, and the part holding Tables
# 2 to 4. An estimate below the real count is what lets a paper be silently truncated.
MEASURED_PROMPTS = [(25922, 1245, 5764, 1663, 8567), (2049, 579, 1008, 527, 1948)]


@pytest.mark.parametrize("letters,digits,spaces,punctuation,reported", MEASURED_PROMPTS)
def test_the_token_estimate_stays_above_what_the_model_reported(letters, digits, spaces,
                                                                punctuation, reported):
    from byeori.local.llm import estimate_tokens
    text = "a" * letters + "1" * digits + " " * spaces + "|" * punctuation
    assert estimate_tokens(text) >= reported
    assert estimate_tokens(text) <= reported * 2, "this much headroom would split papers that fit"


# --- R07: a question is a job, so a slow model never blocks the client --------------------

class SlowModel(PartsModel):
    """Answers only when released, so a test can look at the client while the model is busy."""

    def __init__(self):
        super().__init__()
        self.release = __import__("threading").Event()
        self.started = __import__("threading").Event()
        self.answer = "It reaches 28.4 BLEU. [E1]"

    def generate(self, system, prompt):
        if "Evidence Note" in system or system.startswith("Digest"):
            return Generation("\n\n".join(f"## {heading}\n\nA value. [P0001]" for heading in HEADINGS),
                              self.model, 100, 200, "stop")
        self.started.set()
        assert self.release.wait(5), "the model was never released"
        return Generation(self.answer, self.model, 100, 200, "stop")


@pytest.fixture
def answered(workspace):
    from byeori.local.jobs import QuestionJobs
    store, paper_id, _ = workspace
    service = LocalService(store, SlowModel(), Extractor())
    service.process(paper_id)
    return service, QuestionJobs(service), paper_id


def test_a_question_returns_a_job_id_before_the_model_has_answered(answered):
    service, jobs, paper_id = answered
    submitted = jobs.submit("How good is it?", paper_id)
    assert submitted["status"] == "queued" and submitted["job_id"]
    assert service.backend.started.wait(5), "the question never reached the model"
    assert jobs.store.job(submitted["job_id"])["status"] == "running"
    service.backend.release.set()
    job = jobs.wait(submitted["job_id"], timeout=5)
    assert job["status"] == "succeeded"
    assert job["result"]["answer_status"] == "answered"
    assert job["result"]["citations"][0]["paper_id"] == paper_id


def test_the_question_asked_is_recorded_with_its_scope(answered):
    service, jobs, paper_id = answered
    job_id = jobs.submit("무슨 방법을 썼나?", paper_id)["job_id"]
    service.backend.release.set()
    jobs.wait(job_id, timeout=5)
    job = jobs.store.job(job_id)
    assert job["kind"] == "question"
    assert job["request"]["question"] == "무슨 방법을 썼나?"
    assert job["request"]["paper_id"] == paper_id
    assert job["stage"] == "answer"


def test_one_question_runs_at_a_time(answered):
    service, jobs, paper_id = answered
    first = jobs.submit("First?", paper_id)["job_id"]
    second = jobs.submit("Second?", paper_id)["job_id"]
    assert service.backend.started.wait(5)
    assert jobs.store.job(second)["status"] == "queued", "a second model call would share the memory"
    service.backend.release.set()
    assert jobs.wait(first, timeout=5)["status"] == "succeeded"
    assert jobs.wait(second, timeout=5)["status"] == "succeeded"


def test_cancelling_separates_the_request_from_having_stopped(answered):
    service, jobs, paper_id = answered
    job_id = jobs.submit("How good is it?", paper_id)["job_id"]
    assert service.backend.started.wait(5)
    accepted = jobs.cancel(job_id)
    assert accepted["cancel_requested"] and not accepted["stopped"], \
        "a job inside the model call has accepted the request but has not stopped"
    service.backend.release.set()
    job = jobs.wait(job_id, timeout=5)
    assert job["status"] == "cancelled" and job["result"] is None
    assert "discarded" in job["error"]


def test_a_question_whose_model_call_fails_does_not_end_the_worker(answered):
    service, jobs, paper_id = answered
    service.backend.release.set()
    original = service.backend.generate

    def broken(system, prompt):
        if "Evidence Note" not in system:
            raise ModelError("the server went away")
        return original(system, prompt)

    service.backend.generate = broken
    failed = jobs.submit("Broken?", paper_id)["job_id"]
    job = jobs.wait(failed, timeout=5)
    assert job["status"] == "failed" and "went away" in job["error"] and job["stage"] == "answer"

    service.backend.generate = original
    good = jobs.submit("Still working?", paper_id)["job_id"]
    assert jobs.wait(good, timeout=5)["status"] == "succeeded", \
        "one failed question must not stop the ones queued behind it"


def test_a_question_for_an_unknown_paper_is_refused_at_submission(answered):
    _, jobs, _ = answered
    with pytest.raises(ValueError, match="Unknown paper"):
        jobs.submit("Broken?", "not-a-paper-id")


# --- R12: a workspace created by an earlier schema keeps its notes -------------------------

def test_a_workspace_from_an_earlier_schema_keeps_its_notes(local):
    import sqlite3
    service, paper_id, _ = local
    service.process(paper_id)
    published = service.store.note(paper_id)
    root = service.store.root

    connection = sqlite3.connect(root / "catalog.sqlite3")
    with connection:
        connection.execute("DROP INDEX jobs_queue")
        for column in ("kind", "request", "cancel_requested"):
            connection.execute(f"ALTER TABLE jobs DROP COLUMN {column}")
        connection.execute("UPDATE schema_version SET version=2")
    connection.close()

    reopened = LocalStore(root)
    assert reopened.note(paper_id) == published, "a migration must not cost a published note"
    assert reopened.integrity_problems() == []
    assert reopened.jobs()[0]["kind"] == "note", "jobs written before the column default to notes"


def test_processing_a_paper_does_not_interrupt_a_running_question(answered):
    service, jobs, paper_id = answered
    job_id = jobs.submit("How good is it?", paper_id)["job_id"]
    assert service.backend.started.wait(5)
    service.process(paper_id)
    assert jobs.store.job(job_id)["status"] == "running", \
        "the note worker must not mark another kind of job interrupted"
    service.backend.release.set()
    assert jobs.wait(job_id, timeout=5)["status"] == "succeeded"


def test_a_question_left_by_a_dead_process_is_not_left_queued(answered):
    from byeori.local.jobs import QuestionJobs
    service, jobs, paper_id = answered
    job_id = service.store.start_question("Who will run this?", paper_id)
    with service.store.db() as db:      # a PID that is not running any more
        db.execute("UPDATE jobs SET request=? WHERE job_id=?",
                   (json.dumps({"question": "Who will run this?", "paper_id": paper_id,
                                "pid": 2 ** 22}), job_id))

    QuestionJobs(service)               # a new process opening the workspace
    job = service.store.job(job_id)
    assert job["status"] == "interrupted"
    assert "ended before it was answered" in job["error"]


def test_a_question_this_process_still_owns_is_left_alone(answered):
    from byeori.local.jobs import QuestionJobs
    service, jobs, paper_id = answered
    job_id = jobs.submit("How good is it?", paper_id)["job_id"]
    assert service.backend.started.wait(5)
    QuestionJobs(service)               # another reader must not declare a live job orphaned
    assert service.store.job(job_id)["status"] == "running"
    service.backend.release.set()
    assert jobs.wait(job_id, timeout=5)["status"] == "succeeded"
