from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from .config import load_config
from .workflow import run_fixture_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="radio-news")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-fixture", help="Run the authorized fixture-only vertical slice")
    run.add_argument("--config", required=True)
    run.add_argument("--editor", required=True)
    run.add_argument("--now", help="ISO-8601 time; defaults to current UTC")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-fixture":
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(UTC)
        result = run_fixture_pipeline(load_config(args.config), editor_id=args.editor, now=now)
        print(json.dumps({"raw_item_ids": result.raw_item_ids, "counts": result.counts}, sort_keys=True))
        return 0
    raise AssertionError("unreachable")
