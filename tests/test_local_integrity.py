"""Integrity invariants for the local runtime, taken from real GROBID output and real notes.

Every assertion here is something a person using byeori-local can see: what a citation
resolves to, what a published note contains, what a failed job leaves behind. The TEI
fixture copies the shape GROBID 0.9.1 actually emits for a paper with a numeric table,
including the abstract nested in a <div> and a figure caption between two body paragraphs.
"""
import json

import pytest

from byeori.local.llm import Generation
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
