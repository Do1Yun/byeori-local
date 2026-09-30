from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import sys

from .jobs import QuestionJobs
from .llm import OllamaBackend
from .metadata import OPENALEX_API, OpenAlexLookup
from .service import GrobidExtractor, LocalService
from .store import LocalStore


def build_service(args=None, *, create=False):
    """A service bound to a workspace the caller named. Nothing is created by accident.

    An MCP client starts this server in whatever directory it happens to use, so falling back
    to the working directory would silently open an empty workspace and answer 'no results'.
    """
    def setting(name, env, fallback=None):
        value = getattr(args, name, None)
        return value if value is not None else os.environ.get(env, fallback)

    data_dir = setting("data_dir", "BYEORI_LOCAL_DATA")
    if not data_dir:
        raise ValueError("Set BYEORI_LOCAL_DATA or --data-dir to the workspace directory; "
                         "run 'byeori-local init' to create one")
    backend = OllamaBackend(setting("model", "BYEORI_LOCAL_MODEL", ""),
        setting("ollama_url", "BYEORI_OLLAMA_URL", "http://127.0.0.1:11434"),
        context=int(setting("context", "BYEORI_CONTEXT", "32768")),
        output=int(setting("output_tokens", "BYEORI_OUTPUT_TOKENS", "4096")))
    store = LocalStore(Path(data_dir), create=create)
    # Off by default is the wrong default here: a note with no year cannot be placed in the
    # sequence of work it belongs to, and the lookup never blocks a note when it cannot answer.
    lookup = None if os.environ.get("BYEORI_METADATA_LOOKUP", "on").lower() in {"off", "0", "false"} \
        else OpenAlexLookup(os.environ.get("BYEORI_OPENALEX_URL", OPENALEX_API),
                            mailto=setting("openalex_mailto", "BYEORI_OPENALEX_MAILTO"))
    return LocalService(store, backend, GrobidExtractor(
        os.environ.get("BYEORI_GROBID_URL", "http://127.0.0.1:8070")), lookup=lookup)


VERDICTS = "맞음 / 인용틀림 / 수치틀림 / 근거없음 / 무인용"


def recorded_verdicts(path):
    """Verdicts already written into a sheet, keyed by the claim each was reached on.

    Keyed by the claim's text rather than its number: a rebuilt sheet may number claims
    differently, and a verdict a person reached has to survive the sheet being rebuilt.
    """
    if not path or not Path(path).exists():
        return {}
    kept = {}
    for chunk in re.split(r"(?m)^### ", Path(path).read_text(encoding="utf-8"))[1:]:
        claim = re.sub(r"^\d+\.\s*", "", chunk.splitlines()[0]).strip()
        fields = dict(re.findall(r"(?m)^- (판정|메모|판정자): (\S.*)$", chunk))
        if fields.get("판정"):
            kept[claim] = fields
    return kept


def review_markdown(sheet, kept=None):
    """The sheet as something a person can read and fill in, one claim at a time."""
    fields = sheet["fields"]
    lines = [f"# 검토표: {sheet['stem']}", "",
             f"- 논문: {fields.get('title', '')}",
             f"- 학술지·연도: {fields.get('journal', '-')} {fields.get('year', '-')}"
             f"  (출처 {fields.get('metadata_source', '-')}, DOI {fields.get('doi') or '-'})",
             f"- 노트 revision: `{sheet['revision_id']}`  sha256 `{sheet['note_sha256'][:16]}`",
             f"- 추출: {fields.get('extraction_status', '-')}, 블록 {sheet['blocks_total']}개, "
             f"생성 경로 {fields.get('generation_path', '-')}, 제시 {fields.get('blocks_presented', '-')}",
             f"- 모델: {fields.get('ingest_model_id', '-')}, 검증 수준 {fields.get('evidence_validation', '-')}",
             "",
             "## 채우는 방법", "",
             f"주장마다 판정 한 개를 적습니다: **{VERDICTS}**",
             "",
             "- `맞음` 수치·조건이 논문과 일치하고 인용한 문단이 그 근거를 담고 있음",
             "- `인용틀림` 값은 맞는데 그 값이 없는 문단을 가리킴",
             "- `수치틀림` 값이나 실험 조건이 논문과 다름",
             "- `근거없음` 논문에 없는 내용",
             "",
             "노트의 표현이 논문과 달라도 뜻이 같으면 `맞음`입니다. 인용된 문단이 길어 잘린 경우 "
             "`byeori-local read_paper_context`로 전문을 볼 수 있습니다.",
             "",
             "## 1차 검사", "",
             "`review --audit`을 쓰면 각 주장에 자동 1차 검사 결과가 붙습니다. `flagged`는 "
             "**먼저 보셔야 할 것**이라는 뜻이고, `supported`가 맞다는 보장은 아닙니다. "
             "이 검사는 사람이 논문을 읽고 판정한 5개 주장에서 5/5로 일치했지만, 5개는 "
             "검사기를 검증할 만한 표본이 아닙니다.",
             "",
             "## 핵심 수치", "",
             "이 논문에서 **반드시 맞아야 하는 주장 3~5개**의 번호를 적어주세요. 이후 모델·프롬프트를 "
             "바꿀 때 이 항목들이 기준이 됩니다.", "", "- ", "- ", "- ", ""]
    heading = None
    for number, claim in enumerate(sheet["claims"], 1):
        if claim["heading"] != heading:
            heading = claim["heading"]
            lines += [f"## {heading}", ""]
        lines += [f"### {number}. {claim['claim']}", ""]
        check = claim.get("audit")
        if check:
            flags = "; ".join(check["flags"])
            lines += [f"- 1차 검사: **{check['verdict']}**"
                      + (f" — {flags}" if flags else "")
                      + (f"  (모델: {check['model_verdict']})"
                         if check["model_verdict"] and check["model_verdict"] != check["verdict"] else ""),
                      f"- 근거로 든 문장: {check['quote'] or '-'}", ""]
        previous = (kept or {}).get(claim["claim"].strip(), {})
        lines += [f"- 판정: {previous.get('판정', '')}".rstrip(),
                  f"- 메모: {previous.get('메모', '')}".rstrip()]
        if previous.get("판정자"):
            lines.append(f"- 판정자: {previous['판정자']}")
        lines.append("")
        if not claim["cited"]:
            lines += ["> 인용 없음", ""]
        for source in claim["sources"]:
            lines += [f"**{source['id']}** ({source['kind']}, {source['section']})", "",
                      f"> {source['text'] or '(추출에 없는 문단)'}", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Byeori development runtime with Ollama (no AWS required)")
    parser.add_argument("--data-dir", help="Workspace directory, or BYEORI_LOCAL_DATA")
    parser.add_argument("--model", help="Installed Ollama model, or BYEORI_LOCAL_MODEL")
    parser.add_argument("--ollama-url")
    parser.add_argument("--context", type=int)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--openalex-mailto", help="Identifies you to OpenAlex, or BYEORI_OPENALEX_MAILTO")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create the workspace named by --data-dir or BYEORI_LOCAL_DATA")
    sub.add_parser("doctor")
    sub.add_parser("check", help="Report disagreements between notes, search and job status")
    review = sub.add_parser("review", help="A sheet pairing each claim with the paragraphs it cites")
    review.add_argument("paper_id")
    review.add_argument("--revision")
    review.add_argument("--out", type=Path, help="Write Markdown here instead of printing JSON")
    review.add_argument("--audit", action="store_true",
                        help="Run the first pass so a person starts with the flagged claims")
    review.add_argument("--limit", type=int, help="Audit only the first N claims")
    again = sub.add_parser("revalidate", help="Publish a note a failed job already wrote")
    again.add_argument("job_id", nargs="?")
    again.add_argument("--all", action="store_true")
    meta = sub.add_parser("metadata", help="Settle a published paper's year, journal and work ID")
    meta.add_argument("paper_id", nargs="?")
    meta.add_argument("--all", action="store_true")
    add = sub.add_parser("add", help="Register a PDF, or every PDF in a folder")
    add.add_argument("path", type=Path, help="A PDF file or a folder of them")
    add.add_argument("--title", help="Only when registering a single file")
    intake = sub.add_parser("intake", help="Register everything dropped in the workspace inbox")
    intake.add_argument("--process", action="store_true", help="Then write a note for each")
    process = sub.add_parser("process")
    process.add_argument("paper_id", nargs="?")
    process.add_argument("--all", action="store_true",
                         help="Every registered paper that has no note yet")
    sub.add_parser("list")
    search = sub.add_parser("search")
    search.add_argument("query")
    read = sub.add_parser("read")
    read.add_argument("paper_id")
    read.add_argument("--start", type=int, default=0)
    read.add_argument("--revision", help="Read the exact note revision a citation named")
    revisions = sub.add_parser("revisions")
    revisions.add_argument("paper_id")
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--paper")
    cancel = sub.add_parser("cancel")
    cancel.add_argument("job_id")
    status = sub.add_parser("status")
    status.add_argument("job_id", nargs="?")
    args = parser.parse_args(argv)
    try:
        service = build_service(args, create=args.command == "init")
        match args.command:
            case "init":
                result = {"workspace": str(service.store.root), "created": True}
            case "doctor":
                result = service.backend.doctor()
                result["data_dir"] = str(service.store.root)
                result["integrity_problems"] = service.store.integrity_problems()
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result["model_available"] and not result["integrity_problems"] else 1
            case "check":
                problems = service.store.integrity_problems()
                print(json.dumps({"problems": problems}, ensure_ascii=False, indent=2))
                return 1 if problems else 0
            case "review":
                sheet = (service.audit(args.paper_id, args.revision, args.limit) if args.audit
                         else service.review_sheet(args.paper_id, args.revision))
                if args.out:
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    kept = recorded_verdicts(args.out)
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(review_markdown(sheet, kept), encoding="utf-8")
                    result = {"written": str(args.out), "claims": len(sheet["claims"]),
                              "kept_verdicts": len(kept)}
                    if sheet.get("counts"):
                        result["counts"] = sheet["counts"]
                else:
                    result = sheet
            case "revalidate":
                if args.all == bool(args.job_id):
                    raise ValueError("Give a job ID or --all, not both")
                result = service.revalidate_all() if args.all else service.revalidate(args.job_id)
            case "metadata":
                if args.all == bool(args.paper_id):
                    raise ValueError("Give a paper ID or --all, not both")
                result = service.refresh_all() if args.all else service.refresh_metadata(args.paper_id)
            case "add": result = service.intake(args.path, args.title)
            case "intake":
                folder = service.inbox()
                result = service.intake(folder)
                result["drop_pdfs_here"] = str(folder)
                if args.process:
                    result["processing"] = service.process_all()
            case "process":
                if args.all == bool(args.paper_id):
                    raise ValueError("Give a paper ID or --all, not both")
                result = service.process_all() if args.all else service.process(args.paper_id)
            case "list": result = service.store.papers()
            case "search": result = service.store.search(args.query)
            case "read": result = service.read(args.paper_id, start=args.start, revision=args.revision)
            case "revisions": result = service.store.revisions(args.paper_id)
            case "ask":
                # A question is a recorded job here too, and this foreground process runs it:
                # submitting without waiting belongs to the MCP server, which outlives the call.
                jobs = QuestionJobs(service)
                job = jobs.wait(jobs.submit(args.question, args.paper)["job_id"])
                result = job["result"] if job["status"] == "succeeded" else job
            case "cancel": result = QuestionJobs(service).cancel(args.job_id)
            case "status": result = service.store.jobs(args.job_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
