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


def note_text(citation="P0001", trailing="", level="## "):
    """A note in the shape the contract asks for, Glossary lines byeori can read included."""
    sections = []
    for heading in HEADINGS:
        body = f"The model reports 28.4 BLEU. [{citation}]"
        if heading.endswith("Glossary"):
            body = "\n".join(f"- **Attention head {index}**: one of the parallel attention "
                             f"functions. [{citation}]" for index in range(1, 4))
        prefix = "## " if heading == HEADINGS[0] else level
        sections.append(f"{prefix}{heading}{trailing}\n\n{body}")
    return "\n\n".join(sections)


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
        self.answer = note_text(cite, trailing)
        self.calls = 0

    def generate(self, system, prompt, *, think=None):
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
    service.backend.answer = note_text(trailing="  ", level="### ")
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

    def generate(self, system, prompt, *, think=None):
        self.systems.append(system)
        shown = re.findall(r"\[(P\d+)\]", prompt)
        if system.startswith("Digest one part") or system.startswith("Merge these digests"):
            return Generation("- a reported value " + " ".join(f"[{i}]" for i in shown),
                              self.model, 100, 50, "stop")
        return Generation(note_text(shown[0]), self.model, 100, 200, "stop")


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

    def generate(self, system, prompt, *, think=None):
        from byeori.local.llm import estimate_tokens
        self.systems.append(system)
        shown = list(dict.fromkeys(re.findall(r"\[(P\d+)\]", prompt)))
        if system.startswith("Digest one part"):
            labels = " ".join(f"[{block_id}]" for block_id in shown)
            target = int(estimate_tokens(prompt) * self.FIRST)
            filler = "value " * max(1, (target - estimate_tokens(labels)) // 2)
            return Generation(f"- {labels} {filler}", self.model, 100, 50, "stop")
        return Generation(note_text(shown[0]), self.model, 100, 200, "stop")


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

    def generate(self, system, prompt, *, think=None):
        if "Evidence Note" in system or system.startswith("Digest"):
            return Generation(note_text(), self.model, 100, 200, "stop")
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


# --- R10: a note byeori's own wiki recognises ---------------------------------------------

HEADED_TEI = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader><fileDesc>
<titleStmt><title level="a" type="main">De novo variants in autism cohorts</title></titleStmt>
<publicationStmt><date type="published" when="2021-04-16">16 April 2021</date></publicationStmt>
<sourceDesc><biblStruct>
<analytic>
<author><persName><forename type="first">Mei</forename><surname>Zhou</surname></persName></author>
<author><persName><forename type="first">Ada</forename><surname>Okafor</surname></persName></author>
<idno type="DOI">10.1000/example.2021.4567</idno>
</analytic>
<monogr><title level="j">Nature Genetics</title></monogr>
</biblStruct></sourceDesc>
</fileDesc>
<encodingDesc><appInfo><application version="0.9.1" ident="GROBID"/></appInfo></encodingDesc>
<profileDesc><abstract><div><p>We sequenced 1,204 probands.</p></div></abstract></profileDesc>
</teiHeader>
<text><body><div><head>Results</head><p>We found 42 de novo variants in SCN2A.</p></div></body></text></TEI>"""


@pytest.fixture
def headed(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(HEADED_TEI))
    return service, paper_id, service.process(paper_id)


def test_a_published_note_passes_byeoris_own_page_validation(headed):
    from byeori.validation import page_errors
    service, paper_id, result = headed
    note = service.store.note(paper_id)["text"]
    assert page_errors(f"wiki/sources/{result['stem']}.md", note) == []


def test_a_published_note_yields_concept_candidates(headed):
    """A note whose Glossary byeori cannot parse contributes nothing to a concept page."""
    from byeori.synthesis_terms import glossary_entries
    service, paper_id, _ = headed
    entries = glossary_entries(service.store.note(paper_id)["text"])
    assert len(entries) >= 3 and all(term and definition for term, definition in entries)


def test_a_note_without_a_readable_glossary_is_not_published(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(HEADED_TEI))
    service.backend.answer = "\n\n".join(f"## {heading}\n\nA value. [P0001]" for heading in HEADINGS)
    with pytest.raises(RuntimeError, match="Glossary has 0 entries"):
        service.process(paper_id)


def test_the_document_id_is_the_identity_byeori_reads_elsewhere(headed):
    from byeori.identity import split_stem
    service, paper_id, result = headed
    assert result["stem"] == "zhou-2021-de-novo-variants-in-autism-cohorts"
    assert split_stem(result["stem"]) == ("zhou", "2021", "de-novo-variants-in-autism-cohorts")
    assert service.store.paper_for_stem(result["stem"]) == paper_id
    assert service.store.search("de novo variants")[0]["doc_id"] == result["stem"]


def test_the_note_carries_the_metadata_the_extraction_read(headed):
    service, paper_id, _ = headed
    note = service.store.note(paper_id)["text"]
    for line in ('title: "De novo variants in autism cohorts"', 'year: "2021"',
                 'doi: "10.1000/example.2021.4567"', 'journal: "Nature Genetics"',
                 'authors: "Mei Zhou, Ada Okafor"', 'text_extractor: "GROBID"',
                 'text_extractor_version: "0.9.1"'):
        assert line in note, line


def test_the_index_holds_what_a_synthesis_reads(headed):
    from byeori.wiki_search import RESULT_FIELDS
    service, paper_id, result = headed
    with service.store.db() as db:
        columns = [row["name"] for row in db.execute("PRAGMA table_info(docs)")]
        row = dict(db.execute("SELECT * FROM docs WHERE doc_id=?", (result["stem"],)).fetchone())
    assert columns == ["doc_type", "doc_id", "title", "path", "year", "journal", "doi",
                       "work_ids", "category", "s3_key", "summary"]
    assert set(RESULT_FIELDS) - {"score", "section"} <= set(columns)
    assert row["summary"].startswith("The model reports 28.4 BLEU")
    assert row["year"] == "2021" and row["journal"] == "Nature Genetics"


def test_a_paper_keeps_its_identity_when_its_note_is_rewritten(headed):
    service, paper_id, result = headed
    service.extractor = Extractor(HEADED_TEI.replace(b"De novo variants in autism cohorts",
                                                     b"A completely different title"))
    again = service.process(paper_id)
    assert again["stem"] == result["stem"], "a rewritten note must not move the document"
    assert again["revision_id"] != result["revision_id"]
    hits = service.store.search("BLEU")
    assert [hit["doc_id"] for hit in hits] == [result["stem"]], "one document, not two"


def test_two_papers_that_read_as_the_same_document_get_separate_ids(workspace, tmp_path):
    store, first_id, _ = workspace
    LocalService(store, Model(), Extractor(HEADED_TEI)).process(first_id)
    other = tmp_path / "other.pdf"
    other.write_bytes(b"%PDF-1.7\na different file with the same title page")
    second_id = store.add(other, "Cohort study")["paper_id"]
    second = LocalService(store, Model(), Extractor(HEADED_TEI)).process(second_id)
    assert second["stem"] == "zhou-2021-de-novo-variants-in-autism-cohorts-2"
    assert store.paper_for_stem(second["stem"]) == second_id
    assert store.integrity_problems() == []


def test_a_citation_written_in_parentheses_still_names_its_paragraph(workspace):
    """qwen3:8b cited (P0042) on a paper whose own text is full of [MASK] and [CLS]."""
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(HEADED_TEI))
    service.backend.answer = note_text().replace("[P0001]", "(P0001)")
    assert service.process(paper_id)["status"] == "succeeded"
    note = store.note(paper_id)["text"]
    assert "(P0001)" not in note and "[P0001]" in note


def test_several_paragraphs_cited_in_one_parenthesis_become_separate_citations():
    from byeori.local.service import normalize_note
    assert normalize_note("A value (P0042, P0043).") == "A value [P0042][P0043]."
    assert normalize_note("Written in 2018 (Peters et al., 2018a).") == \
        "Written in 2018 (Peters et al., 2018a)."


def test_a_note_indexed_under_an_earlier_identity_stops_answering_searches(headed):
    service, paper_id, result = headed
    with service.store.db() as db:      # what a pre-identity workspace left behind
        db.execute("INSERT INTO section_map VALUES (?,?,?,?)", (9001, "note", paper_id, "Results"))
        db.execute("INSERT INTO docs VALUES ('note',?,?,?,?,?,?,?,?,?,?)",
                   (paper_id, "Retired", "wiki/sources/old.md", "", "", "", "", "other",
                    "wiki/sources/old.md", ""))
    assert service.store.integrity_problems(), "the stale row is a problem worth reporting"
    service.process(paper_id)
    assert service.store.integrity_problems() == []
    assert [hit["doc_id"] for hit in service.store.search("BLEU")] == [result["stem"]]


def test_an_answer_that_names_paragraphs_keeps_every_note_it_read(local):
    """qwen3:8b answered from three notes as [E1-P0040], [E2-P0056], [E3]; only E3 was recorded."""
    service, paper_id, _ = local
    service.process(paper_id)
    service.backend.answer = ("Bahdanau reports 34.16 [E1-P0001]. The Transformer reports 28.4 "
                              "[E1-P0001, P0002]. BERT is not a translation model [E1].")
    answer = service.ask("Compare the BLEU scores", paper_id)
    assert answer["answer_status"] == "answered"
    assert [citation["label"] for citation in answer["citations"]] == ["E1"]
    assert answer["citations"][0]["block_ids"] == ["P0001", "P0002"]


def test_an_answer_citing_a_paragraph_the_note_does_not_have_is_withheld(local):
    service, paper_id, _ = local
    service.process(paper_id)
    service.backend.answer = "It reports 99 BLEU [E1-P9999]."
    answer = service.ask("How good is it?", paper_id)
    assert answer["answer_status"] == "insufficient_evidence"
    assert answer["reason"] == "model_citation_unresolvable"
    assert "P9999" in answer["answer"] and "99 BLEU" not in answer["answer"]


def test_every_note_an_answer_cites_is_returned_as_a_citation(workspace, tmp_path):
    store, first_id, _ = workspace
    service = LocalService(store, Model(), Extractor())
    service.process(first_id)
    second = tmp_path / "second.pdf"
    second.write_bytes(b"%PDF-1.7\nanother paper about the same cohort")
    second_id = store.add(second, "Another cohort study")["paper_id"]
    service.process(second_id)

    service.backend.answer = "One says 28.4 [E1-P0001] and the other says 28.4 [E2]."
    answer = service.ask("What do they report?")
    assert [citation["label"] for citation in answer["citations"]] == ["E1", "E2"]
    assert {citation["paper_id"] for citation in answer["citations"]} == {first_id, second_id}


# --- a folder of PDFs, registered and processed in one go ---------------------------------

def test_a_folder_of_pdfs_is_registered_in_one_go(local, tmp_path):
    service, _, _ = local
    folder = tmp_path / "drop"
    (folder / "nested").mkdir(parents=True)
    (folder / "one.pdf").write_bytes(b"%PDF-1.7\nfirst paper")
    (folder / "nested" / "two.pdf").write_bytes(b"%PDF-1.7\nsecond paper")
    (folder / "notes.txt").write_text("not a paper")

    result = service.intake(folder)
    assert result["files"] == 2 and result["registered"] == 2 and result["failed"] == 0
    assert {paper["file"] for paper in result["papers"]} == {"one.pdf", "two.pdf"}


def test_dropping_the_same_folder_again_registers_nothing_twice(local, tmp_path):
    service, _, _ = local
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "one.pdf").write_bytes(b"%PDF-1.7\nfirst paper")
    service.intake(folder)
    again = service.intake(folder)
    assert again["registered"] == 0 and again["duplicate"] == 1


def test_one_unreadable_file_does_not_stop_the_others(local, tmp_path):
    service, _, _ = local
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "broken.pdf").write_bytes(b"not a PDF at all")
    (folder / "good.pdf").write_bytes(b"%PDF-1.7\na real one")
    result = service.intake(folder)
    assert result["registered"] == 1 and result["failed"] == 1
    assert result["errors"][0]["file"] == "broken.pdf" and "not a PDF" in result["errors"][0]["error"]


def test_the_inbox_is_a_folder_inside_the_workspace(local):
    service, _, _ = local
    inbox = service.inbox()
    assert inbox.is_dir() and inbox.parent == service.store.root


def test_processing_every_pending_paper_leaves_none_without_a_note(local, tmp_path):
    service, first_id, _ = local
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "one.pdf").write_bytes(b"%PDF-1.7\nfirst paper")
    (folder / "two.pdf").write_bytes(b"%PDF-1.7\nsecond paper")
    service.intake(folder)

    assert len(service.pending()) == 3
    result = service.process_all()
    assert result["processed"] == 3 and result["failed"] == 0
    assert service.pending() == []
    assert len(service.store.search("BLEU")) == 3


def test_a_paper_that_fails_does_not_stop_the_batch(local, tmp_path):
    service, first_id, _ = local
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "one.pdf").write_bytes(b"%PDF-1.7\nfirst paper")
    service.intake(folder)

    failing = {service.store.papers()[0]["paper_id"]}
    original = service.extractor.extract

    def extract(pdf):
        if b"first paper" in pdf:
            raise ValueError("Extraction contains no body text")
        return original(pdf)

    service.extractor.extract = extract
    result = service.process_all()
    assert result["processed"] == 1 and result["failed"] == 1
    assert len(service.pending()) == 1, "the paper that failed is still pending, the other is not"
    assert service.store.integrity_problems() == []


def test_a_running_job_says_which_stage_it_is_in(workspace):
    """A domain paper took 20 minutes here, and its job still reported the stage it started in."""
    store, paper_id, _ = workspace
    seen = []

    class Watching(PartsModel):
        def generate(self, system, prompt, *, think=None):
            seen.append(store.jobs()[0]["stage"])
            return super().generate(system, prompt, think=think)

    service = LocalService(store, Watching(), Extractor(long_tei(20)))
    result = service.process(paper_id)
    assert any(stage.startswith("generate part 1/") for stage in seen), seen
    assert any(stage.startswith("generate part 2/") for stage in seen), seen
    assert seen[-1].startswith("generate note from")
    assert store.jobs(result["job_id"])[0]["stage"] == "publish"


# --- metadata settled against OpenAlex ------------------------------------------------------

WORK = {"id": "https://openalex.org/W4409484936", "doi": "https://doi.org/10.1000/example.2021.4567",
        "display_name": "De novo variants in autism cohorts", "publication_year": 2021,
        "publication_date": "2021-04-16", "type": "article",
        "authorships": [{"author": {"display_name": "Mei Zhou"}},
                        {"author": {"display_name": "Ada Okafor"}}],
        "primary_location": {"source": {"display_name": "Nature Genetics", "id": "S1", "issn": ["1"]}},
        "cited_by_count": 7}
NO_YEAR_TEI = HEADED_TEI.replace(b'<date type="published" when="2021-04-16">16 April 2021</date>', b"")


def lookup_for(works, calls=None):
    """An OpenAlex that answers from a fixture; no test reaches the network."""
    import httpx
    from byeori.local.metadata import OpenAlexLookup

    def handler(request):
        if calls is not None:
            calls.append(str(request.url))
        return httpx.Response(200, json={"results": works})

    return OpenAlexLookup(transport=httpx.MockTransport(handler), mailto="lab@example.org")


def test_a_paper_whose_pdf_prints_no_year_still_gets_one(workspace):
    """GROBID left the date empty on a real Nature Communications PDF; the DOI was there."""
    store, paper_id, _ = workspace
    calls = []
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI), lookup=lookup_for([WORK], calls))
    result = service.process(paper_id)
    assert result["stem"] == "zhou-2021-de-novo-variants-in-autism-cohorts"
    note = store.note(paper_id)["text"]
    assert 'year: "2021"' in note and 'journal: "Nature Genetics"' in note
    assert 'work_ids: "W4409484936"' in note and 'metadata_source: "openalex"' in note
    assert any("doi" in call for call in calls), "the DOI printed on the page is asked about first"


def test_a_record_that_is_not_this_paper_is_refused(workspace):
    store, paper_id, _ = workspace
    other = dict(WORK, display_name="An entirely different paper about hepatocytes",
                 authorships=[{"author": {"display_name": "Someone Else"}}])
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI), lookup=lookup_for([other]))
    result = service.process(paper_id)
    assert result["stem"] == "zhou-0000-de-novo-variants-in-autism-cohorts"
    note = store.note(paper_id)["text"]
    assert 'metadata_source: "extraction"' in note
    assert "hepatocytes" not in note


def test_a_lookup_that_cannot_answer_never_blocks_a_note(workspace):
    import httpx
    from byeori.local.metadata import OpenAlexLookup
    store, paper_id, _ = workspace

    def refuse(request):
        raise httpx.ConnectError("no network")

    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI),
                           lookup=OpenAlexLookup(transport=httpx.MockTransport(refuse)))
    assert service.process(paper_id)["status"] == "succeeded"
    assert 'metadata_source: "extraction"' in store.note(paper_id)["text"]


def test_a_year_the_page_printed_is_not_overruled_but_the_disagreement_is_recorded(workspace):
    """OpenAlex answered 2025 for a 2017 paper and 2014 for a paper published in 2015."""
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(HEADED_TEI),
                           lookup=lookup_for([dict(WORK, publication_year=2019)]))
    service.process(paper_id)
    note = store.note(paper_id)["text"]
    assert 'year: "2021"' in note, "the page printed 2021 and keeps it"
    assert 'openalex_year: "2019"' in note and 'metadata_disagreement: "year"' in note


def test_a_year_learned_later_moves_the_paper_and_leaves_no_stale_entry(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))      # no lookup at first
    first = service.process(paper_id)
    assert first["stem"] == "zhou-0000-de-novo-variants-in-autism-cohorts"

    service.lookup = lookup_for([WORK])
    refreshed = service.refresh_metadata(paper_id)
    assert refreshed["changed"] and refreshed["stem"] == "zhou-2021-de-novo-variants-in-autism-cohorts"
    assert refreshed["previous_stem"] == first["stem"]
    assert [hit["doc_id"] for hit in store.search("BLEU")] == [refreshed["stem"]]
    assert store.integrity_problems() == []


def test_settling_metadata_does_not_call_the_model(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))
    service.process(paper_id)
    before = service.backend.calls
    service.lookup = lookup_for([WORK])
    service.refresh_metadata(paper_id)
    assert service.backend.calls == before, "the body is the model's work and is copied, not rewritten"


def test_the_note_body_survives_a_metadata_revision_word_for_word(workspace):
    from byeori.local.service import split_frontmatter
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))
    service.process(paper_id)
    before = split_frontmatter(store.note(paper_id)["text"])[1]
    service.lookup = lookup_for([WORK])
    service.refresh_metadata(paper_id)
    after = store.note(paper_id)["text"]
    assert split_frontmatter(after)[1] == before
    assert 'revision_reason: "metadata-resolved"' in after


def test_settling_metadata_twice_changes_nothing_the_second_time(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI), lookup=lookup_for([WORK]))
    service.process(paper_id)
    assert service.refresh_metadata(paper_id)["changed"] is False


def test_metadata_can_be_settled_again_after_it_has_already_moved_a_paper(workspace):
    """A metadata revision has a job of its own and no extraction beside it."""
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))
    service.process(paper_id)
    service.lookup = lookup_for([WORK])
    assert service.refresh_metadata(paper_id)["changed"] is True
    assert service.refresh_metadata(paper_id)["changed"] is False
    assert store.integrity_problems() == []


def test_an_earlier_revision_still_reads_after_the_paper_moves(workspace):
    store, paper_id, _ = workspace
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI))
    first = service.process(paper_id)
    service.lookup = lookup_for([WORK])
    service.refresh_metadata(paper_id)
    kept = service.read(paper_id, revision=first["revision_id"])
    assert kept["revision_id"] == first["revision_id"]
    assert service.context(paper_id, "P0001", revision=first["revision_id"])["text"]


def test_a_part_whose_digest_is_cut_off_is_halved_and_retried(workspace):
    """scGPT lost a ten-part run to one digest the model could not finish inside the budget."""
    store, paper_id, _ = workspace

    class RefusesLargeParts(PartsModel):
        """Finishes a digest only when its part holds few enough blocks."""

        limit = 3

        def generate(self, system, prompt, *, think=None):
            self.systems.append(system)
            shown = re.findall(r"\[(P\d+)\]", prompt)
            if system.startswith("Digest one part"):
                if len(shown) > self.limit:
                    raise ModelError("Model did not finish normally; incomplete output "
                                     "was not published")
                return Generation("- a reported value " + " ".join(f"[{i}]" for i in shown),
                                  self.model, 100, 50, "stop")
            return Generation(note_text(shown[0]), self.model, 100, 200, "stop")

    service = LocalService(store, RefusesLargeParts(), Extractor(long_tei(20)))
    coverage = service.process(paper_id)["coverage"]
    assert coverage["parts_split"] > 0
    assert coverage["parts"] > coverage["parts_planned"]
    assert coverage["blocks_presented"] == coverage["blocks_total"] == 20, \
        "every block still reaches the model exactly once"
    assert len(list(store.path(f"runs/{store.note(paper_id)['job_id']}").glob("digest-*.md"))) \
        == coverage["parts"]


def test_splitting_stops_rather_than_going_on_for_ever(workspace):
    store, paper_id, _ = workspace

    class NeverFinishes(PartsModel):
        def generate(self, system, prompt, *, think=None):
            self.systems.append(system)
            if system.startswith("Digest one part"):
                raise ModelError("Model did not finish normally; incomplete output was not published")
            return Generation(note_text(), self.model, 100, 200, "stop")

    service = LocalService(store, NeverFinishes(), Extractor(long_tei(20)))
    with pytest.raises(RuntimeError, match="missing to note it|did not finish"):
        service.process(paper_id)
    from byeori.local.service import MAX_PART_SPLITS
    attempts = sum(s.startswith("Digest one part") for s in service.backend.systems)
    assert attempts <= 2 * MAX_PART_SPLITS + 4, f"{attempts} attempts is not a bounded retry"


def test_one_block_the_model_cannot_digest_does_not_cost_the_paper(workspace):
    """On scGPT this block was a figure's axis labels flattened into a paragraph."""
    store, paper_id, _ = workspace

    class ChokesOnOneBlock(PartsModel):
        def generate(self, system, prompt, *, think=None):
            self.systems.append(system)
            shown = re.findall(r"\[(P\d+)\]", prompt)
            if system.startswith("Digest one part"):
                if "P0007" in shown:
                    raise ModelError("Model did not finish normally; incomplete output "
                                     "was not published")
                return Generation("- a reported value " + " ".join(f"[{i}]" for i in shown),
                                  self.model, 100, 50, "stop")
            return Generation(note_text(shown[0]), self.model, 100, 200, "stop")

    service = LocalService(store, ChokesOnOneBlock(), Extractor(long_tei(20)))
    coverage = service.process(paper_id)["coverage"]
    assert coverage["blocks_skipped"] == ["P0007"]
    assert coverage["blocks_presented"] == 19 and coverage["blocks_total"] == 20
    assert 'blocks_presented: "19/20"' in store.note(paper_id)["text"], \
        "the note says how much of the paper it was written from"


def test_a_paper_too_much_of_which_cannot_be_digested_is_not_published(workspace):
    store, paper_id, _ = workspace

    class ChokesOnMany(PartsModel):
        def generate(self, system, prompt, *, think=None):
            self.systems.append(system)
            shown = re.findall(r"\[(P\d+)\]", prompt)
            if system.startswith("Digest one part"):
                raise ModelError("Model did not finish normally; incomplete output was not published")
            return Generation(note_text(shown[0] if shown else "P0001"), self.model, 100, 200, "stop")

    service = LocalService(store, ChokesOnMany(), Extractor(long_tei(20)))
    with pytest.raises(RuntimeError, match="too much of this paper is missing"):
        service.process(paper_id)
    with pytest.raises(ValueError, match="no published"):
        store.note(paper_id)
