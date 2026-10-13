from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import sys
import uuid

from .backup import create_backup, restore_backup
from .jobs import QuestionJobs
from .llm import OllamaBackend
from .metadata import OPENALEX_API, OpenAlexLookup
from .service import GrobidExtractor, LocalService
from .store import SCHEMA_VERSION, LocalStore, migration_plan
from .evidence import claim_fingerprint


def build_service(args=None, *, create=False):
    """A service bound to a workspace the caller named. Nothing is created by accident.

    An MCP client starts this server in whatever directory it happens to use, so falling back
    to the working directory would silently open an empty workspace and answer 'no results'.
    """
    def setting(name, env, fallback=None):
        value = getattr(args, name, None)
        return value if value is not None else os.environ.get(env, fallback)

    data_dir = workspace_dir(args)
    backend = OllamaBackend(setting("model", "BYEORI_LOCAL_MODEL", ""),
        setting("ollama_url", "BYEORI_OLLAMA_URL", "http://127.0.0.1:11434"),
        context=int(setting("context", "BYEORI_CONTEXT", "32768")),
        output=int(setting("output_tokens", "BYEORI_OUTPUT_TOKENS", "4096")),
        timeout=float(setting("timeout", "BYEORI_OLLAMA_TIMEOUT", "600")),
        allow_remote=bool(getattr(args, "allow_remote_ollama", False)))
    executor = os.environ.get("BYEORI_LOCAL_EXECUTOR", "inline").strip().lower()
    store = LocalStore(Path(data_dir), create=create)
    # Off by default is the wrong default here: a note with no year cannot be placed in the
    # sequence of work it belongs to, and the lookup never blocks a note when it cannot answer.
    lookup = None if os.environ.get("BYEORI_METADATA_LOOKUP", "on").lower() in {"off", "0", "false"} \
        else OpenAlexLookup(os.environ.get("BYEORI_OPENALEX_URL", OPENALEX_API),
                            mailto=setting("openalex_mailto", "BYEORI_OPENALEX_MAILTO"),
                            api_key=os.environ.get("BYEORI_OPENALEX_API_KEY"))
    return LocalService(store, backend, GrobidExtractor(
        os.environ.get("BYEORI_GROBID_URL", "http://127.0.0.1:8070")), lookup=lookup,
        executor=executor)


def workspace_dir(args=None):
    data_dir = getattr(args, "data_dir", None) or os.environ.get("BYEORI_LOCAL_DATA")
    if not data_dir:
        raise ValueError("Set BYEORI_LOCAL_DATA or --data-dir to the workspace directory; "
                         "run 'byeori-local init' to create one")
    return Path(data_dir)


def storage_command(args):
    """Commands that must not open the workspace the ordinary way, which would migrate it."""
    match args.command:
        case "backup":
            return create_backup(workspace_dir(args), args.destination, include_inbox=args.include_inbox)
        case "restore":
            return restore_backup(args.backup_dir, args.destination,
                                  allow_migration=not args.no_migration)
        case "migrate":
            if args.plan:
                return migration_plan(workspace_dir(args))
            path = workspace_dir(args).expanduser().resolve()
            before = migration_plan(path)
            store = LocalStore(path, create=False, migrate=True)
            return {"workspace": str(path), "from": before["current"], "to": store.schema_version(),
                    "migrated": store.migrated_from is not None,
                    "journal_mode": store.journal_mode()}


VERDICTS = "맞음 / 인용틀림 / 수치틀림 / 근거없음 / 무인용"


def recorded_verdicts(path):
    """Only evidence-bound verdicts can be reused. Legacy sheets are archived, not approved."""
    if not path or not Path(path).exists():
        return {}
    kept = {}
    for chunk in re.split(r"(?m)^### ", Path(path).read_text(encoding="utf-8"))[1:]:
        fingerprint = re.search(r"<!-- evidence-fingerprint: ([a-f0-9]{64}) -->", chunk)
        fields = dict(re.findall(r"(?m)^- (판정|메모|판정자): (\S.*)$", chunk))
        if fields.get("판정") and fingerprint:
            kept[fingerprint[1]] = fields
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
             "MCP `read_paper_context(paper_id, paragraph_id, revision)`로 전문을 볼 수 있습니다.",
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
        fingerprint = claim_fingerprint(sheet["paper_id"], claim)
        lines += [f"### {number}. {claim['claim']}", "",
                  f"<!-- evidence-fingerprint: {fingerprint} -->", ""]
        check = claim.get("audit")
        if check:
            flags = "; ".join(check["flags"])
            lines += [f"- 1차 검사: **{check['verdict']}**"
                      + (f" — {flags}" if flags else "")
                      + (f"  (모델: {check['model_verdict']})"
                         if check["model_verdict"] and check["model_verdict"] != check["verdict"] else ""),
                      f"- 근거로 든 문장: {check['quote'] or '-'}", ""]
        previous = (kept or {}).get(fingerprint, {})
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
    parser.add_argument("--allow-remote-ollama", action="store_true", help="Explicitly permit an external Ollama endpoint; cloud models remain refused")
    parser.add_argument("--context", type=int)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--timeout", type=float,
                        help="Seconds one model call may take, or BYEORI_OLLAMA_TIMEOUT (default 600)")
    parser.add_argument("--openalex-mailto", help="Identifies you to OpenAlex, or BYEORI_OPENALEX_MAILTO")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create the workspace named by --data-dir or BYEORI_LOCAL_DATA")
    sub.add_parser("doctor")
    check = sub.add_parser("check", help="Check stored file hashes, notes, search and job status")
    check.add_argument("--deep", action="store_true", help="Also hash all originals and TEI files")
    recover = sub.add_parser("recover-runtime", help="Release timeout quarantine after checking the server is idle")
    recover.add_argument("--acknowledge-idle", action="store_true")
    sub.add_parser("reconcile-receipts", help="Restore missing terminal receipts from canonical job status")
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
    again.add_argument("--submit", action="store_true", help="Queue it for the worker instead")
    meta = sub.add_parser("metadata", help="Settle a published paper's year, journal and work ID")
    meta.add_argument("paper_id", nargs="?")
    meta.add_argument("--all", action="store_true")
    meta.add_argument("--submit", action="store_true", help="Queue it for the worker instead")
    meta.add_argument("--set", action="append", metavar="KEY=VALUE", dest="assignments",
                      help="Correct year, journal or doi by hand (repeatable); needs --reason")
    meta.add_argument("--reason", help="Why the value is corrected, kept with the correction")
    report = sub.add_parser("report", help="Run a fixed report over every paper: catalog, compare, "
                                           "timeline, gaps, or a templates/<name>.toml")
    report.add_argument("template", nargs="?")
    report.add_argument("--list", action="store_true", help="Templates and their latest reports")
    report.add_argument("--submit", action="store_true", help="Queue it for the worker instead")
    report.add_argument("--refresh", action="store_true",
                        help="Ask the model again even where an answer for that note is cached")
    report.add_argument("--show", action="store_true", help="Print the latest report's Markdown")
    worker = sub.add_parser("worker", help="Run queued jobs until stopped (SIGTERM/Ctrl+C stops "
                                           "at the next safe point)")
    worker.add_argument("--once", action="store_true", help="Exit when nothing can be claimed")
    worker.add_argument("--max-jobs", type=int)
    worker.add_argument("--poll-seconds", type=float, default=2.0)
    worker.add_argument("--no-resume-interrupted", action="store_true",
                        help="Do not queue again the jobs an earlier worker left running")
    worker.add_argument("--log-dir", type=Path)
    worker.add_argument("--allow-sleep", action="store_true",
                        help="Do not hold macOS awake while a job runs (it is by default)")
    marks = sub.add_parser("checkpoints", help="Stored stages a resumed job can read for a paper")
    marks.add_argument("paper_id")
    backup = sub.add_parser("backup", help="Copy the workspace into a new directory and verify it")
    backup.add_argument("destination", type=Path)
    backup.add_argument("--include-inbox", action="store_true")
    restore = sub.add_parser("restore", help="Restore a backup into a directory that does not exist yet")
    restore.add_argument("backup_dir", type=Path)
    restore.add_argument("destination", type=Path)
    restore.add_argument("--no-migration", action="store_true")
    sub.add_parser("reindex", help="Rebuild search from the active notes' files")
    migrate = sub.add_parser("migrate", help=f"Show or apply the move to schema {SCHEMA_VERSION}")
    choice = migrate.add_mutually_exclusive_group(required=True)
    choice.add_argument("--plan", action="store_true", help="Show what would change; change nothing")
    choice.add_argument("--apply", action="store_true")
    add = sub.add_parser("add", help="Register a PDF, or every PDF in a folder")
    add.add_argument("path", type=Path, help="A PDF file or a folder of them")
    add.add_argument("--title", help="Only when registering a single file")
    intake = sub.add_parser("intake", help="Register everything dropped in the workspace inbox")
    intake.add_argument("--process", action="store_true", help="Then write a note for each")
    process = sub.add_parser("process")
    process.add_argument("paper_id", nargs="?")
    process.add_argument("--all", action="store_true",
                         help="Every registered paper that has no note yet")
    process.add_argument("--submit", action="store_true", help="Queue it for the worker instead")
    process.add_argument("--no-resume", action="store_true",
                         help="Ignore stored checkpoints and start the paper over")
    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--cursor")
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
    ask.add_argument("--submit", action="store_true",
                     help="Queue it for the worker and print the job ID instead of waiting")
    cancel = sub.add_parser("cancel")
    cancel.add_argument("job_id")
    status = sub.add_parser("status")
    status.add_argument("job_id", nargs="?")
    status.add_argument("--limit", type=int, default=20)
    status.add_argument("--cursor")
    args = parser.parse_args(argv)
    try:
        if args.command in {"backup", "restore", "migrate"}:
            result = storage_command(args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.command == "backup" and (result["referenced_missing"] or not result["verified"]):
                return 3
            if args.command == "restore" and result["status"] != "restored":
                return 1
            return 0
        service = build_service(args, create=args.command == "init")
        match args.command:
            case "init":
                result = {"workspace": str(service.store.root), "created": True}
            case "doctor":
                result = service.backend.doctor()
                result["data_dir"] = str(service.store.root)
                result["schema"] = {"version": service.store.schema_version(), "code": SCHEMA_VERSION}
                result["journal_mode"] = service.store.journal_mode()
                result["executor"] = service.executor
                result["worker"] = service.store.worker_status()
                probe = getattr(service.extractor, "ready", None)
                result["extractor"] = probe() if callable(probe) else None
                result["integrity_problems"] = service.store.integrity_problems()
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if (result["model_available"] and result["model_locality"] == "local"
                             and not result["recovery_pending"] and not result["integrity_problems"]) else 1
            case "check":
                problems = service.store.integrity_problems(deep=args.deep)
                print(json.dumps({"problems": problems}, ensure_ascii=False, indent=2))
                return 1 if problems else 0
            case "recover-runtime":
                result = service.backend.recover_runtime(acknowledge=args.acknowledge_idle)
            case "reconcile-receipts":
                result = service.store.reconcile_receipts()
            case "review":
                sheet = (service.audit(args.paper_id, args.revision, args.limit) if args.audit
                         else service.review_sheet(args.paper_id, args.revision))
                if args.out:
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    kept = recorded_verdicts(args.out)
                    if args.out.exists():
                        history = args.out.parent / ".review-history"
                        history.mkdir(parents=True, exist_ok=True)
                        (history / f"{args.out.stem}-{uuid.uuid4().hex}.md").write_bytes(args.out.read_bytes())
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
                if args.submit:
                    result = with_worker(service, service.submit_revalidate(args.job_id))
                else:
                    result = service.revalidate_all() if args.all else service.revalidate(args.job_id)
            case "metadata":
                if args.all == bool(args.paper_id):
                    raise ValueError("Give a paper ID or --all, not both")
                if args.assignments:
                    if args.all or args.submit:
                        raise ValueError("--set corrects one paper, in the foreground")
                    values = {}
                    for assignment in args.assignments:
                        key, separator, value = assignment.partition("=")
                        if not separator:
                            raise ValueError(f"Write --set as KEY=VALUE, not {assignment!r}")
                        values[key.strip()] = value
                    result = service.correct_metadata(args.paper_id, values, args.reason)
                elif args.submit:
                    result = with_worker(service, service.submit_metadata(args.paper_id))
                else:
                    result = service.refresh_all() if args.all else service.refresh_metadata(args.paper_id)
            case "worker":
                from .worker import Worker
                result = Worker(service, once=args.once, max_jobs=args.max_jobs,
                                poll_seconds=args.poll_seconds,
                                resume_interrupted=not args.no_resume_interrupted,
                                log_dir=args.log_dir, install_signals=True,
                                prevent_sleep=not args.allow_sleep).run()
            case "report":
                from .report import Reports
                reports = Reports(service)
                if args.list or not args.template:
                    result = reports.list_reports()
                elif args.show:
                    print(reports.read(args.template, max_chars=40000)["text"], end="")
                    return 0
                elif args.submit:
                    result = with_worker(service, service.submit_report(args.template, refresh=args.refresh))
                else:
                    result = service.run_report(args.template, refresh=args.refresh)
            case "checkpoints":
                service.store.paper(args.paper_id)
                result = {"paper_id": args.paper_id, "checkpoints": [
                    {"checkpoint_id": item["checkpoint_id"], "stage": item["stage"],
                     "created_at": item["created_at"], "job_id": item["job_id"],
                     "files": [file["path"] for file in item["files"]], "meta": item["meta"]}
                    for item in service.checkpoints.for_paper(args.paper_id)]}
            case "reindex":
                result = service.store.reindex()
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
                resume = not args.no_resume
                if args.submit:
                    result = with_worker(service, service.submit_all_notes(resume=resume) if args.all
                                         else service.submit_note(args.paper_id, resume=resume))
                else:
                    result = (service.process_all(resume=resume) if args.all
                              else service.process(args.paper_id, resume=resume))
            case "list": result = service.store.paper_page(limit=args.limit, cursor=args.cursor)
            case "search": result = service.store.search(args.query)
            case "read": result = service.read(args.paper_id, start=args.start, revision=args.revision)
            case "revisions": result = service.store.revisions(args.paper_id)
            case "ask":
                if args.submit:
                    result = QuestionJobs(service, executor="worker").submit(args.question, args.paper)
                else:
                    # A question is a recorded job here too, and this foreground process runs it.
                    jobs = QuestionJobs(service, executor="inline")
                    job = jobs.wait(jobs.submit(args.question, args.paper)["job_id"])
                    result = job["result"] if job["status"] == "succeeded" else job
            case "cancel": result = QuestionJobs(service).cancel(args.job_id)
            case "status":
                if args.job_id:
                    result = [service.store.job(args.job_id) | {
                        "events": service.store.events(args.job_id, 20),
                        "worker": service.store.worker_status()}]
                else:
                    result = service.store.job_page(limit=args.limit, cursor=args.cursor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if isinstance(result, dict):
            if result.get("status") in {"failed", "interrupted"}:
                return 1
            if result.get("status") == "partial":
                return 3
            if result.get("failed") or (result.get("processing") or {}).get("failed"):
                return 3
            if result.get("conflicts"):
                return 3
            if any(item.get("error") for item in result.get("jobs", [])):
                return 3
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        code = getattr(exc, "error_code", "invalid_argument" if isinstance(exc, ValueError) else "runtime_error")
        if isinstance(exc, ValueError) and str(exc).startswith("Unknown"):
            code = "not_found"
        failure = {"error": str(exc), "error_code": code, "retryable": getattr(exc, "retryable", False)}
        if getattr(exc, "details", None):
            failure["details"] = exc.details
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        return 2 if code == "invalid_argument" else 1


def with_worker(service, submitted):
    """A submission says whether anything will run it."""
    worker = service.store.worker_status()
    submitted = submitted | {"executor": "worker", "worker_alive": worker["alive"]}
    if not worker["alive"]:
        submitted["diagnostic"] = ("worker_unavailable: start 'byeori-local worker' to run "
                                   "queued jobs")
    return submitted


if __name__ == "__main__":
    raise SystemExit(main())
