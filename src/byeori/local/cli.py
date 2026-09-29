from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .llm import OllamaBackend
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
    return LocalService(store, backend, GrobidExtractor(
        os.environ.get("BYEORI_GROBID_URL", "http://127.0.0.1:8070")))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Byeori development runtime with Ollama (no AWS required)")
    parser.add_argument("--data-dir", help="Workspace directory, or BYEORI_LOCAL_DATA")
    parser.add_argument("--model", help="Installed Ollama model, or BYEORI_LOCAL_MODEL")
    parser.add_argument("--ollama-url")
    parser.add_argument("--context", type=int)
    parser.add_argument("--output-tokens", type=int)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create the workspace named by --data-dir or BYEORI_LOCAL_DATA")
    sub.add_parser("doctor")
    sub.add_parser("check", help="Report disagreements between notes, search and job status")
    add = sub.add_parser("add")
    add.add_argument("pdf", type=Path)
    add.add_argument("--title")
    process = sub.add_parser("process")
    process.add_argument("paper_id")
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
            case "add": result = service.store.add(args.pdf, args.title)
            case "process": result = service.process(args.paper_id)
            case "list": result = service.store.papers()
            case "search": result = service.store.search(args.query)
            case "read": result = service.read(args.paper_id, start=args.start, revision=args.revision)
            case "revisions": result = service.store.revisions(args.paper_id)
            case "ask": result = service.ask(args.question, args.paper)
            case "status": result = service.store.jobs(args.job_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
