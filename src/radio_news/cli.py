from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .errors import RadioNewsError
from .storage import SQLiteStore
from .workflow import run_fixture_pipeline


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if is_dataclass(value):
        return _json_value(asdict(value))
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="radio-news")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-fixture", help="Run the authorized fixture-only vertical slice")
    run.add_argument("--config", required=True)
    run.add_argument("--database", required=True)
    run.add_argument("--editor", required=True)
    run.add_argument("--now", help="ISO-8601 time; defaults to current UTC")

    read = sub.add_parser("read-graph", help="Read the persisted first-slice graph")
    read.add_argument("--database", required=True)
    read.add_argument("--raw-item-id", required=True)

    status = sub.add_parser("migration-status", help="Show applied SQLite migration versions")
    status.add_argument("--database", required=True)
    return parser


def _parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RadioNewsError("--now must include a timezone")
    return parsed


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "run-fixture":
            result = run_fixture_pipeline(
                load_config(args.config),
                database_path=Path(args.database),
                editor_id=args.editor,
                now=_parse_now(args.now),
            )
            print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "read-graph":
            graph = SQLiteStore(args.database).read_graph(args.raw_item_id)
            print(json.dumps(_json_value(graph), ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "migration-status":
            versions = SQLiteStore(args.database).migration_versions()
            print(json.dumps({"migration_versions": list(versions)}, sort_keys=True))
            return 0
        raise AssertionError("unreachable")
    except (RadioNewsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
