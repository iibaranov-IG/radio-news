from __future__ import annotations

import json
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from radio_news.web.server import create_editorial_feed_server
from radio_news.workflow import run_fixture_pipeline


def _request_once(server, path: str) -> tuple[int, str, str]:
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as response:
            result = response.status, response.headers.get_content_type(), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        result = exc.code, exc.headers.get_content_type(), exc.read().decode("utf-8")
    thread.join(timeout=5)
    return result


def _story_id(database: Path, raw_item_id: str) -> str:
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT story_id FROM claims WHERE raw_item_id=?", (raw_item_id,)).fetchone()
    assert row is not None
    return row[0]


def test_feed_card_opens_story_evidence_view(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    result = run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    story_id = _story_id(database, result.items[0].raw_item_id)
    server = create_editorial_feed_server(database, port=0)
    try:
        status, content_type, body = _request_once(server, "/")
    finally:
        server.server_close()
    assert status == 200 and content_type == "text/html"
    assert f'/stories/{urllib.parse.quote(story_id, safe="")}' in body
    assert f"Story: {story_id}" in body


def test_story_page_exposes_complete_evidence_chain_read_only(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    result = run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    story_id = _story_id(database, result.items[0].raw_item_id)
    before = database.read_bytes()
    server = create_editorial_feed_server(database, port=0)
    try:
        status, content_type, body = _request_once(server, f"/stories/{urllib.parse.quote(story_id, safe='')}")
    finally:
        server.server_close()
    assert status == 200 and content_type == "text/html"
    for marker in ("Story", "Source", "RawItem", "NormalizedItem", "Claim", "Fact", "VerificationResult", "Provenance"):
        assert marker in body
    assert "Fixture KP" in body and "READY" in body and "SQLite открыта read-only" in body
    assert database.read_bytes() == before


def test_story_api_exposes_linked_records_and_provenance_read_only(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    result = run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    raw_id = result.items[0].raw_item_id
    story_id = _story_id(database, raw_id)
    before = database.read_bytes()
    server = create_editorial_feed_server(database, port=0)
    try:
        status, content_type, body = _request_once(server, f"/api/stories/{urllib.parse.quote(story_id, safe='')}")
    finally:
        server.server_close()
    payload = json.loads(body)
    assert status == 200 and content_type == "application/json"
    assert payload["story"]["id"] == story_id
    assert payload["raw_items"][0]["id"] == raw_id
    assert payload["sources"][0]["source_id"] == "fixture-kp"
    assert payload["claims"] and payload["facts"] and payload["verification_results"]
    assert {edge["relation"] for edge in payload["provenance"]} >= {"supported_by", "evaluated_by"}
    assert database.read_bytes() == before


def test_unknown_story_returns_404_in_browser_and_api(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    server = create_editorial_feed_server(database, port=0)
    try:
        html_status, html_type, html_body = _request_once(server, "/stories/missing-story")
        api_status, api_type, api_body = _request_once(server, "/api/stories/missing-story")
    finally:
        server.server_close()
    assert html_status == 404 and html_type == "text/html" and "Сюжет не найден" in html_body
    assert api_status == 404 and api_type == "application/json"
    assert "story not found" in json.loads(api_body)["error"]
