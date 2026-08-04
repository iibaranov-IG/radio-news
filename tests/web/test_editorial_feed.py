from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from radio_news.errors import RadioNewsError
from radio_news.web.server import create_editorial_feed_server
from radio_news.workflow import run_fixture_pipeline


def _request_once(server, path: str) -> tuple[int, str, str]:
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    with urllib.request.urlopen(f"http://{host}:{port}{path}", timeout=5) as response:
        body = response.read().decode("utf-8")
        result = response.status, response.headers.get_content_type(), body
    thread.join(timeout=5)
    return result


def test_browser_page_shows_persisted_news(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    server = create_editorial_feed_server(database, port=0)
    try:
        status, content_type, body = _request_once(server, "/")
    finally:
        server.server_close()

    assert status == 200
    assert content_type == "text/html"
    assert "КПNEWS" in body
    assert "Fixture KP" in body
    assert "READY" in body
    assert "Новостей: 1" in body


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
    assert status == 200
    assert content_type == "application/json"
    assert payload["count"] == 1
    assert payload["items"][0]["source_id"] == "fixture-kp"
    assert database.read_bytes() == before


def test_non_loopback_bind_is_rejected(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    with pytest.raises(RadioNewsError, match="only on localhost"):
        create_editorial_feed_server(database, host="0.0.0.0", port=0)
