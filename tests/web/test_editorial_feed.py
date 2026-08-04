from __future__ import annotations

import json
import sqlite3
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from radio_news.errors import RadioNewsError
from radio_news.storage import SQLiteStore
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


def test_browser_page_shows_persisted_news(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    before = database.read_bytes()
    server = create_editorial_feed_server(database, port=0)
    try:
        status, content_type, body = _request_once(server, "/")
    finally:
        server.server_close()
    assert status == 200
    assert content_type == "text/html"
    assert "КПNEWS" in body and "Fixture KP" in body and "READY" in body and "Новостей: 1" in body
    assert database.read_bytes() == before


def test_feed_api_is_read_only_and_machine_readable(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    before = database.read_bytes()
    server = create_editorial_feed_server(database, port=0)
    try:
        status, content_type, body = _request_once(server, "/api/feed")
    finally:
        server.server_close()
    payload = json.loads(body)
    assert status == 200 and content_type == "application/json"
    assert payload["count"] == 1 and payload["items"][0]["source_id"] == "fixture-kp"
    assert database.read_bytes() == before


def test_empty_compatible_database_shows_empty_state(tmp_path: Path) -> None:
    database = tmp_path / "empty.sqlite"
    SQLiteStore(database).migrate()
    server = create_editorial_feed_server(database, port=0)
    try:
        status, _, body = _request_once(server, "/")
    finally:
        server.server_close()
    assert status == 200
    assert "Лента пока пуста" in body and "Новостей: 0" in body


def test_missing_database_is_reported_in_browser_and_api(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite"
    server = create_editorial_feed_server(database, port=0)
    try:
        html_status, _, html_body = _request_once(server, "/")
        api_status, api_type, api_body = _request_once(server, "/api/feed")
    finally:
        server.server_close()
    assert html_status == 503 and "Не удалось открыть ленту" in html_body
    assert api_status == 503 and api_type == "application/json"
    assert "database not found" in json.loads(api_body)["error"]
    assert not database.exists()


def test_incompatible_database_is_reported_in_browser(tmp_path: Path) -> None:
    database = tmp_path / "wrong.sqlite"
    sqlite3.connect(database).close()
    server = create_editorial_feed_server(database, port=0)
    try:
        status, _, body = _request_once(server, "/")
    finally:
        server.server_close()
    assert status == 503 and "Не удалось открыть ленту" in body


def test_one_raw_item_remains_one_card_with_multiple_facts_and_policies(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    result = run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    raw_id = result.items[0].raw_item_id
    with sqlite3.connect(database) as connection:
        claim_id, story_id = connection.execute("SELECT id,story_id FROM claims WHERE raw_item_id=?", (raw_id,)).fetchone()
        connection.execute("INSERT INTO facts VALUES (?,?,?,?,?,?)", ("fact-extra", story_id, "Extra fact", "editor", now.isoformat(), "APPROVED"))
        connection.execute("INSERT INTO fact_claims VALUES (?,?)", ("fact-extra", claim_id))
        connection.execute("INSERT INTO verification_results VALUES (?,?,?,?,?,?,?)", ("verification-extra", "fact-extra", "NEEDS_REVIEW", '[\"EXTRA\"]', "extra", "manual-fact-v2", now.isoformat()))
    server = create_editorial_feed_server(database, port=0)
    try:
        status, _, body = _request_once(server, "/api/feed")
    finally:
        server.server_close()
    payload = json.loads(body)
    assert status == 200
    assert payload["count"] == 1
    assert payload["items"][0]["processing_state"] == "READY"


def test_non_loopback_bind_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RadioNewsError, match="only on localhost"):
        create_editorial_feed_server(tmp_path / "missing.sqlite", host="0.0.0.0", port=0)
