from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from radio_news.config import AppConfig


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 3, 10, 0, tzinfo=UTC)


@pytest.fixture
def config_dict() -> dict[str, object]:
    return {
        "source": {
            "source_id": "fixture-kp",
            "display_name": "Fixture KP",
            "source_type": "rss_fixture",
            "enabled": True,
            "trust_class": "TEST",
            "fixture_resource": "sample.xml",
        }
    }


@pytest.fixture
def app_config(config_dict: dict[str, object]) -> AppConfig:
    return AppConfig.from_dict(config_dict)


@pytest.fixture
def config_file(tmp_path: Path, config_dict: dict[str, object]) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config_dict, ensure_ascii=False), encoding="utf-8")
    return path
