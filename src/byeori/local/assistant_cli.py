"""Command line for the local work assistant; all paths are supplied by the user."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .assistant import Assistant, initialize


def build_assistant(workspace=None):
    path = workspace or os.environ.get("BYEORI_ASSISTANT_DATA")
    if not path:
        raise ValueError("Set --workspace or BYEORI_ASSISTANT_DATA")
    return Assistant(path)


def build_parser():
    parser = argparse.ArgumentParser(description="Local work assistant: notes, commits, classification and report drafts")
    parser.add_argument("--workspace", help="Assistant workspace, or BYEORI_ASSISTANT_DATA")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--model", default="qwen3:8b")
    init.add_argument("--read-root", action="append", default=[], help="Explicitly permit reading this directory")
    init.add_argument("--context", type=int, default=8192)
    init.add_argument("--output-tokens", type=int, default=2048)
    init.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    root = sub.add_parser("allow-root")
    root.add_argument("path")
    sub.add_parser("doctor")
    sub.add_parser("mcp-config", help="Print MCP client configuration using this Python environment")
    recover = sub.add_parser("recover-runtime")
    recover.add_argument("--acknowledge-idle", action="store_true")
    for name in ("notes", "report"):
        command = sub.add_parser(name)
        command.add_argument("paths", nargs="*" if name == "report" else "+")
        command.add_argument("--instruction", default="")
        if name == "report":
            command.add_argument("--title", default="작업 보고서")
            command.add_argument("--task", action="append", default=[], help="Include a previous successful assistant task")
    commits = sub.add_parser("commits")
    commits.add_argument("repo")
    commits.add_argument("--since", default="7 days ago")
    commits.add_argument("--until")
    commits.add_argument("--limit", type=int, default=50)
    commits.add_argument("--diff", action="store_true", help="Read committed patches as well as messages and file stats")
    classify = sub.add_parser("classify")
    classify.add_argument("directory")
    classify.add_argument("--category", action="append", help="Custom category; repeat for each permitted value")
    status = sub.add_parser("status")
    status.add_argument("task_id")
    history = sub.add_parser("history")
    history.add_argument("--limit", type=int, default=20)
    read = sub.add_parser("read")
    read.add_argument("task_id")
    read.add_argument("--start", type=int, default=0)
    read.add_argument("--max-chars", type=int, default=8000)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            workspace = args.workspace or os.environ.get("BYEORI_ASSISTANT_DATA")
            if not workspace:
                raise ValueError("Set --workspace or BYEORI_ASSISTANT_DATA")
            result = initialize(workspace, model=args.model, read_roots=args.read_root,
                                context=args.context, output=args.output_tokens, ollama_url=args.ollama_url)
        else:
            assistant = build_assistant(args.workspace)
            match args.command:
                case "allow-root": result = assistant.allow_root(args.path)
                case "mcp-config": result = {"mcpServers": {"byeori-assistant": {
                    "command": sys.executable, "args": ["-m", "byeori.local.assistant_mcp"],
                    "env": {"BYEORI_ASSISTANT_DATA": str(assistant.root)}}}}
                case "doctor":
                    result = assistant.backend.doctor() | {"workspace": str(assistant.root),
                        "context": assistant.backend.context, "output_tokens": assistant.backend.output,
                        "read_roots": [str(p) for p in assistant.read_roots]}
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 0 if (result["model_available"] and result["model_locality"] == "local"
                                 and not result["recovery_pending"]) else 1
                case "recover-runtime": result = assistant.backend.recover_runtime(acknowledge=args.acknowledge_idle)
                case "notes": result = assistant.run("notes", paths=args.paths, instruction=args.instruction)
                case "report": result = assistant.run("report", paths=args.paths, task_ids=args.task,
                                                      title=args.title, instruction=args.instruction)
                case "commits": result = assistant.run("commits", repo=args.repo, since=args.since,
                    until=args.until, limit=args.limit, include_diff=args.diff)
                case "classify": result = assistant.run("classify", directory=args.directory, categories=args.category)
                case "status": result = assistant.get(args.task_id)
                case "history": result = assistant.history(args.limit)
                case "read": result = assistant.read_result(args.task_id, args.start, args.max_chars)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get("status") in {"failed", "interrupted"} else 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(json.dumps({"error": str(exc), "error_code": getattr(exc, "error_code", "invalid_argument"
                         if isinstance(exc, ValueError) else "runtime_error")}, ensure_ascii=False), file=sys.stderr)
        return 2 if isinstance(exc, ValueError) else 1


if __name__ == "__main__":
    raise SystemExit(main())
