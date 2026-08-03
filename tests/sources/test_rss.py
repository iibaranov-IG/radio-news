from __future__ import annotations

from radio_news.config import AppConfig
from radio_news.sources import RSSFixtureParser, load_fixture_bytes


def test_fixture_parser_preserves_raw_payload(app_config: AppConfig, now) -> None:
    item = RSSFixtureParser(app_config.source, fetched_at=now).read()[0]
    assert item.raw_payload.startswith("<?xml")
    assert item.source_external_id == "fixture-001"
    assert len(item.content_hash) == 64


def test_fixture_parser_is_deterministic(app_config: AppConfig, now) -> None:
    parser = RSSFixtureParser(app_config.source, fetched_at=now)
    first = parser.read()[0]
    second = parser.read(payload_override=load_fixture_bytes("sample.xml"))[0]
    assert first.id == second.id
    assert first.content_hash == second.content_hash
