from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from radio_news.config import load_config
from radio_news.storage import SQLiteStore
from radio_news.workflow import run_fixture_pipeline


def make_config(tmp_path: Path) -> Path:
    fixture = Path(__file__).parent / "fixtures" / "sample.xml"
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "database_path": "state/news.db",
                "source": {
                    "source_id": "fixture-kp",
                    "display_name": "Fixture KP",
                    "source_type": "rss_fixture",
                    "enabled": True,
                    "trust_class": "TEST",
                    "fixture_path": str(fixture),
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_full_fixture_pipeline_is_idempotent_and_restart_safe(tmp_path: Path) -> None:
    config = load_config(make_config(tmp_path))
    now = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
    first = run_fixture_pipeline(config, editor_id="editor-1", now=now)
    second = run_fixture_pipeline(config, editor_id="editor-1", now=now)
    expected = {
        "raw_items": 1,
        "normalized_items": 1,
        "stories": 1,
        "claims": 1,
        "facts": 1,
        "verification_results": 1,
    }
    assert first.counts == expected
    assert second.counts == expected

    store = SQLiteStore(config.database_path)
    graph = store.read_graph(first.raw_item_ids[0])
    assert graph["raw"]["raw_payload"].startswith("<?xml")
    assert graph["normalized"]["raw_item_id"] == graph["raw"]["id"]
    assert graph["claim"]["raw_item_id"] == graph["raw"]["id"]
    assert graph["fact"]["editor_id"] == "editor-1"
    assert graph["verification"]["status"] == "READY"
    assert graph["verification"]["policy_version"] == "manual-fact-v1"


def test_config_rejects_unknown_fields(tmp_path: Path) -> None:
    path = make_config(tmp_path)
    data = json.loads(path.read_text())
    data["unexpected"] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unknown app config fields"):
        load_config(path)


def test_first_slice_rejects_network_source_type(tmp_path: Path) -> None:
    path = make_config(tmp_path)
    data = json.loads(path.read_text())
    data["source"]["source_type"] = "rss"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="rss_fixture"):
        load_config(path)
