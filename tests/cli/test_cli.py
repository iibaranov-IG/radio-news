from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "radio_news.cli", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_run_fixture_and_readback(config_file: Path, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    first = run_cli(
        "run-fixture",
        "--config",
        str(config_file),
        "--database",
        str(database),
        "--editor",
        "editor-1",
        "--now",
        "2026-08-03T10:00:00Z",
    )
    assert first.returncode == 0, first.stderr
    payload = json.loads(first.stdout)
    assert payload["verification_status"] == "READY"
    raw_id = payload["raw_item_ids"][0]
    second = run_cli(
        "run-fixture",
        "--config",
        str(config_file),
        "--database",
        str(database),
        "--editor",
        "editor-1",
        "--now",
        "2026-08-03T11:00:00Z",
    )
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["item_statuses"] == ["existing"]
    readback = run_cli(
        "read-graph", "--database", str(database), "--raw-item-id", raw_id
    )
    assert readback.returncode == 0, readback.stderr
    graph = json.loads(readback.stdout)
    assert graph["source"]["source_id"] == "fixture-kp"
    assert graph["verification"]["status"] == "READY"


def test_expected_cli_error_has_no_traceback(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"source": []}', encoding="utf-8")
    result = run_cli(
        "run-fixture",
        "--config",
        str(bad),
        "--database",
        str(tmp_path / "news.db"),
        "--editor",
        "editor-1",
    )
    assert result.returncode == 2
    assert result.stderr.startswith("error:")
    assert "Traceback" not in result.stderr
