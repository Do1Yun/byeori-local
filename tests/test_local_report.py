"""Reports across papers: fixed templates, cached answers, checked citations, and year fixes."""
import asyncio
import json

import pytest

from byeori.local.backup import create_backup
from byeori.local.cli import main
from byeori.local.llm import Generation
from byeori.local.report import FIELDS_PATH, ReportError, Reports
from byeori.local.service import LocalService
from byeori.local.store import LocalStore
from byeori.local.worker import Worker
from test_local_integrity import NO_YEAR_TEI, WORK, Extractor, Model, lookup_for

TITLES = {"lang-a": ("Language model A", "2019"), "lang-b": ("Language model B", "2017"),
          "cell-c": ("Cell model C", "2021")}


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("BYEORI_LOCAL_RUNTIME_DIR", str(tmp_path / "runtime"))


class ReportModel(Model):
    """Writes notes like Model, and answers the report prompts from what they were given."""

    def __init__(self):
        super().__init__()
        self.report_calls = []

    def generate(self, system, prompt, *, think=None, response_format=None, num_predict=None,
                 truncation_ratio=None):
        assert response_format is None or truncation_ratio == 0.35, "report calls use the JSON ratio"
        if response_format is None:
            return super().generate(system, prompt, think=think)
        kind = system.split()[1:3]
        self.report_calls.append(" ".join(kind))
        data = json.loads(prompt)
        if system.startswith("You read one Evidence Note"):
            value = self.card(data, response_format)
        elif system.startswith("You group papers"):
            value = self.fields(data)
        elif system.startswith("You write the chronological"):
            value = self.timeline(data)
        else:
            value = self.gaps(data)
        return Generation(json.dumps(value, ensure_ascii=False), self.model, 100, 50, "stop")

    def card(self, data, schema):
        first = next(iter(schema["properties"]["answers"]["properties"].values()))
        cited = first["properties"]["citations"]["items"]["enum"]
        return {"answers": {q["id"]: {"found": True, "short": f"{q['id']} 요약",
                                      "detail": f"{q['id']} 자세한 답", "citations": [cited[0]]}
                            for q in data["questions"]}}

    def fields(self, data):
        names = {"Language": "언어 모델 (language models)", "Cell": "세포 모델 (cell models)"}
        existing = {field["name"] for field in data["existing_fields"]}
        assignments = {paper["id"]: names[paper["title"].split()[0]] for paper in data["papers"]}
        return {"new_fields": [{"name": name, "description": f"{name} 설명"}
                               for name in sorted(set(assignments.values())) if name not in existing],
                "assignments": assignments}

    def timeline(self, data):
        labels = [paper["label"] for paper in data["papers"]]
        years = [paper["year"] for paper in data["papers"]]
        return {"overview": "흐름 개요", "overview_citations": labels[:1],
                "periods": [{"from_year": min(years), "to_year": max(years), "text": "기간 서술",
                             "citations": labels}],
                "shifts": [{"aspect": "방법", "text": "방법이 바뀜", "citations": labels[-1:]}]}

    def gaps(self, data):
        labels = [paper["label"] for paper in data["papers"]]
        return {"items": [{"limitation": "데이터가 적다", "source": labels[0], "status": "addressed",
                           "addressed_by": labels[1:], "how": "더 큰 데이터로 학습"}],
                "open_problems": [{"text": "평가 기준이 없다", "citations": labels[-1:]}]}


def add_paper(store, path, key):
    pdf = path / f"{key}.pdf"
    pdf.write_bytes(f"%PDF-1.7\n{key}".encode())
    return store.add(pdf, TITLES[key][0])["paper_id"]


@pytest.fixture
def corpus(tmp_path):
    """Three published papers: two language models, one cell model, with years set by hand."""
    store = LocalStore(tmp_path / "data")
    model = ReportModel()
    service = LocalService(store, model, Extractor())
    ids = {key: add_paper(store, tmp_path, key) for key in TITLES}
    service.process_all()
    for key, pid in ids.items():
        service.correct_metadata(pid, {"year": TITLES[key][1]}, "fixture year")
    return service, model, ids


def report_json(service, result):
    return json.loads(service.store.path(result["json"]).read_text())


def test_catalog_lists_every_paper_by_year_without_the_model(corpus):
    service, model, ids = corpus
    result = service.run_report("catalog")
    assert result["status"] == "complete" and model.report_calls == []
    text = service.store.path(result["report"]).read_text()
    rows = [line for line in text.splitlines() if line.startswith("| 20")]
    assert [row.split("|")[1].strip() for row in rows] == ["2017", "2019", "2021"]
    assert "Language model B" in rows[0] and "The model reports 28.4 BLEU" in rows[0]
    assert "**핵심 기여**" in text and "로컬 모델이" not in text, "a catalog is the notes, not a draft"
    assert set(report_json(service, result)["inputs"]) == {service.store.paper(p)["stem"] for p in ids.values()}


def test_a_year_corrected_by_hand_survives_a_refresh_and_keeps_the_document_id(tmp_path):
    store = LocalStore(tmp_path / "data")
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.7\nyear")
    pid = store.add(pdf)["paper_id"]
    service = LocalService(store, Model(), Extractor(NO_YEAR_TEI), lookup=lookup_for([WORK]))
    first = service.process(pid)
    corrected = service.correct_metadata(first["stem"], {"year": "2020", "journal": "Venue X"},
                                         "published version is 2020")
    assert corrected["changed"] and corrected["set"] == {"year": "2020", "journal": "Venue X"}
    note = store.note(pid)["text"]
    assert 'year: "2020"' in note and 'journal: "Venue X"' in note
    assert '"year": "manual"' in note and 'revision_reason: "metadata-corrected"' in note
    assert store.paper(pid)["stem"] == first["stem"], "the identity does not move"
    assert store.search("BLEU")[0]["year"] == "2020"
    refreshed = service.refresh_metadata(pid)
    after = store.note(pid)["text"]
    assert 'year: "2020"' in after, "OpenAlex does not overwrite a person's correction"
    assert refreshed["changed"] is False or 'openalex_year: "2021"' in after
    assert service.correct_metadata(pid, {"year": "2020"}, "again")["changed"] is False
    with store.db() as db:
        states = [row[0] for row in db.execute("SELECT state FROM metadata_checks ORDER BY checked_at")]
    assert "manual" in states
    for values, reason in (({"year": "20x0"}, "bad"), ({"title": "New"}, "bad"), ({"year": "2020"}, "")):
        with pytest.raises(ValueError):
            service.correct_metadata(pid, values, reason)


def test_compare_asks_each_note_once_and_reuses_answers(corpus):
    service, model, ids = corpus
    first = service.run_report("compare")
    assert first["status"] == "complete" and model.report_calls.count("read one") == 3
    assert first["cards_created"] == 3 and first["cards_reused"] == 0
    text = service.store.path(first["report"]).read_text()
    assert "| 논문 | 다루는 문제 | 핵심 방법 |" in text and "problem 자세한 답 [P0001]" in text
    model.report_calls.clear()
    service.correct_metadata(ids["cell-c"], {"journal": "Cell Journal"}, "venue known")
    again = service.run_report("compare")
    assert model.report_calls == [] and again["cards_reused"] == 3, "a frontmatter fix costs nothing"
    model.answer = model.answer.replace("28.4 BLEU", "28.5 BLEU")
    service.process(ids["lang-a"])
    model.report_calls.clear()
    third = service.run_report("compare")
    assert model.report_calls == ["read one"] and third["cards_reused"] == 2
    assert service.run_report("compare", refresh=True)["cards_created"] == 3


def test_an_answer_without_a_cited_paragraph_is_withheld(corpus):
    service, model, _ = corpus

    def card(data, schema):
        value = ReportModel.card(model, data, schema)
        value["answers"]["data_scale"]["citations"] = []
        return value

    model.card = card
    result = service.run_report("compare")
    row = next(iter(report_json(service, result)["data"]["cards"].values()))
    assert row["answers"]["data_scale"]["withheld"]
    assert "(근거 없어 제외)" in service.store.path(result["report"]).read_text()


def test_chinese_characters_are_asked_again_then_flagged(corpus):
    service, model, _ = corpus
    attempts = []

    def card(data, schema):
        attempts.append(1)
        value = ReportModel.card(model, data, schema)
        value["answers"]["problem"]["short"] = "問題 정의"
        return value

    model.card = card
    result = service.run_report("compare")
    assert len(attempts) == 6, "each paper asked twice"
    text = service.store.path(result["report"]).read_text()
    assert "한자가 섞인 답" in text


def test_fields_are_classified_once_and_edits_are_respected(corpus):
    service, model, ids = corpus
    result = service.run_report("timeline")
    assert model.report_calls.count("group papers") == 1
    saved = json.loads(service.store.path(FIELDS_PATH).read_text())
    assert set(saved["fields"]) == {"언어 모델 (language models)", "세포 모델 (cell models)"}
    assert "_how_to_edit" in saved
    text = service.store.path(result["report"]).read_text()
    assert "## 언어 모델 (language models) — 논문 2편 (2017–2019)" in text
    assert "[Language 2017][Language 2019]" in text.replace("] [", "][")
    assert "흐름을 서술하지 않았습니다" in text, "a one-paper field gets no synthesis"
    assert model.report_calls.count("write the") == 1
    stem = service.store.paper(ids["cell-c"])["stem"]
    saved["papers"][stem] = "언어 모델 (language models)"
    service.store.path(FIELDS_PATH).write_text(json.dumps(saved, ensure_ascii=False))
    model.report_calls.clear()
    again = service.run_report("timeline")
    assert "group papers" not in model.report_calls
    assert "논문 3편 (2017–2021)" in service.store.path(again["report"]).read_text()


def test_timeline_flags_a_period_that_cites_a_paper_outside_it(corpus):
    service, model, _ = corpus

    def timeline(data):
        value = ReportModel.timeline(model, data)
        first = data["papers"][0]["year"]
        value["periods"] = [{"from_year": first, "to_year": first, "text": "첫 해", "citations":
                             [paper["label"] for paper in data["papers"]]}]
        return value

    model.timeline = timeline
    result = service.run_report("timeline")
    assert "이 기간 밖의 논문을 인용함 (Language 2019)" in service.store.path(result["report"]).read_text()


def test_gaps_drop_a_solution_published_before_the_problem(corpus):
    service, model, _ = corpus

    def gaps(data):
        labels = [paper["label"] for paper in data["papers"]]
        return {"items": [{"limitation": "느리다", "source": labels[-1], "status": "addressed",
                           "addressed_by": labels[:1], "how": "빠르게 함"}], "open_problems": []}

    model.gaps = gaps
    result = service.run_report("gaps")
    section = next(s for s in report_json(service, result)["data"]["sections"] if len(s["papers"]) == 2)
    assert section["items"][0]["status"] == "unclear" and section["items"][0]["addressed_by"] == []
    text = service.store.path(result["report"]).read_text()
    assert "먼저 나온 논문이라 해결 논문에서 뺐습니다" in text and "판단 어려움" in text


def test_gaps_render_who_took_up_which_limitation(corpus):
    service, _, _ = corpus
    text = service.store.path(service.run_report("gaps")["report"]).read_text()
    assert "| 데이터가 적다 | [Language 2017] | [Language 2019] | 해결 | 더 큰 데이터로 학습 |" in text
    assert "### 남은 문제" in text and "평가 기준이 없다 [Language 2019]" in text


def test_a_user_template_asks_its_own_questions_and_a_broken_one_is_named(corpus):
    service, model, _ = corpus
    folder = service.store.path("templates")
    folder.mkdir(exist_ok=True)
    (folder / "setup.toml").write_text('title = "실험 설정"\n[[questions]]\nid = "optimizer"\n'
                                       'label = "옵티마이저"\nask = "Which optimizer?"\n', encoding="utf-8")
    (folder / "broken.toml").write_text('kind = "timeline"\n', encoding="utf-8")
    listing = Reports(service).list_reports()
    assert "setup" in {entry["template"] for entry in listing["templates"]}
    assert "broken.toml" in listing["template_problems"]
    result = service.run_report("setup")
    text = service.store.path(result["report"]).read_text()
    assert "# 실험 설정" in text and "| 논문 | 옵티마이저 |" in text
    with pytest.raises(ReportError, match="kind"):
        service.run_report("broken")
    with pytest.raises(ReportError, match="Unknown report template"):
        service.run_report("nothing")


def test_a_report_job_runs_on_the_worker_and_resumes_from_cached_answers(corpus):
    service, model, _ = corpus
    running = Worker(service, once=True, log_stream=None, prevent_sleep=False)

    def card(data, schema):
        running.request_stop()
        return ReportModel.card(model, data, schema)

    model.card = card
    submitted = service.submit_report("compare")
    assert service.submit_report("compare")["status"] == "already_queued"
    running.run()
    job = service.store.job(submitted["job_id"])
    assert job["status"] == "interrupted" and model.report_calls.count("read one") == 1
    model.card = lambda data, schema: ReportModel.card(model, data, schema)
    summary = Worker(service, once=True, log_stream=None, prevent_sleep=False).run()
    assert summary["outcomes"] == {"succeeded": 1}
    follower = [j for j in service.store.iter_jobs() if j.get("resumed_from") == submitted["job_id"]][0]
    assert follower["result"]["cards_reused"] == 1 and follower["result"]["cards_created"] == 2


def test_a_report_is_marked_stale_after_a_note_changes(corpus):
    service, model, ids = corpus
    service.run_report("catalog")
    entry = {e["template"]: e for e in Reports(service).list_reports()["templates"]}["catalog"]
    assert entry["latest"]["stale"] is False
    model.answer = model.answer.replace("28.4 BLEU", "28.6 BLEU")
    service.process(ids["cell-c"])
    entry = {e["template"]: e for e in Reports(service).list_reports()["templates"]}["catalog"]
    assert entry["latest"]["stale"] is True
    assert entry["latest"]["changed_papers"] == [service.store.paper(ids["cell-c"])["stem"]]


def test_cli_lists_runs_shows_and_submits_reports(corpus, monkeypatch, capsys):
    import byeori.local.cli as cli
    service, model, ids = corpus
    monkeypatch.setattr(cli, "build_service", lambda *a, **k: service)
    assert main(["report", "--list"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert {e["template"] for e in listed["templates"]} >= {"catalog", "compare", "timeline", "gaps"}
    assert main(["report", "catalog"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"
    assert main(["report", "catalog", "--show"]) == 0
    assert capsys.readouterr().out.startswith("# 논문 목록")
    assert main(["report", "gaps", "--submit"]) == 0
    assert json.loads(capsys.readouterr().out)["diagnostic"].startswith("worker_unavailable")
    assert main(["metadata", ids["lang-a"], "--set", "journal=ACL", "--reason", "known venue"]) == 0
    assert json.loads(capsys.readouterr().out)["set"] == {"journal": "ACL"}
    assert main(["metadata", ids["lang-a"], "--set", "journal"]) == 2


def test_a_partial_report_exits_three(corpus, monkeypatch, capsys):
    import byeori.local.cli as cli
    service, model, _ = corpus
    calls = []

    def card(data, schema):
        calls.append(1)
        if len(calls) <= 2:
            return {"answers": {}}
        return ReportModel.card(model, data, schema)

    model.card = card
    monkeypatch.setattr(cli, "build_service", lambda *a, **k: service)
    assert main(["report", "compare"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "partial" and len(result["problems"]) == 1
    assert "failed its check twice" in result["problems"][0]


def test_mcp_reads_the_latest_report(corpus):
    from byeori.local.mcp_server import create_server
    service, _, _ = corpus
    service.run_report("catalog")
    server = create_server(service)

    async def check():
        listed = str(await server.call_tool("list_reports", {}))
        assert "catalog" in listed and "stale" in listed
        read = str(await server.call_tool("read_report", {"template": "catalog", "max_chars": 200}))
        assert "논문 목록" in read and "next_start" in read
    asyncio.run(check())


def test_backups_carry_reports_and_field_assignments(corpus, tmp_path):
    service, _, _ = corpus
    service.run_report("timeline")
    result = create_backup(service.store.root, tmp_path / "backup")
    manifest = json.loads((tmp_path / "backup" / "manifest.json").read_text())
    paths = {item["path"] for item in manifest["files"]}
    assert FIELDS_PATH in paths and any(p.startswith("reports/timeline/") for p in paths)
    assert result["verified"]
