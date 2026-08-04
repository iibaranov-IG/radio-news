from __future__ import annotations

from pathlib import Path

import pytest

from radio_news.application import EditorialFeedService
from radio_news.errors import RadioNewsError
from radio_news.workflow import run_fixture_pipeline


def test_feed_reads_persisted_news_without_modifying_database(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    before = database.read_bytes()

    snapshot = EditorialFeedService(database).snapshot()

    assert len(snapshot.items) == 1
    item = snapshot.items[0]
    assert item.title
    assert item.source_id == "fixture-kp"
    assert item.source_name == "Fixture KP"
    assert item.processing_state == "READY"
    assert database.read_bytes() == before


def test_feed_missing_database_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(RadioNewsError, match="database not found"):
        EditorialFeedService(tmp_path / "missing.sqlite").snapshot()
