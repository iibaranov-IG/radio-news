from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from radio_news.storage import SQLiteStore
from radio_news.web.server import create_editorial_feed_server


def _seed(database: Path) -> None:
    store = SQLiteStore(database)
    assert store.migrate() == (1, 2)
    with store.connect() as connection:
        connection.executemany(
            "INSERT INTO stories(id,canonical_key,title,created_at) VALUES (?,?,?,?)",
            [
                ("story-a", "key-a", "Первая новость", "2026-08-05T09:00:00+00:00"),
                ("story-b", "key-b", "Вторая новость", "2026-08-05T08:00:00+00:00"),
                ("story-c", "key-c", "Третья новость", "2026-08-05T07:00:00+00:00"),
            ],
        )


def _request(url: str, *, payload: dict[str, object] | None = None) -> tuple[int, str]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _run_server(database: Path):
    server = create_editorial_feed_server(database, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def test_manual_selection_survives_server_restart_and_preserves_evidence(tmp_path: Path) -> None:
    database = tmp_path / "radio-news.sqlite"
    _seed(database)
    store = SQLiteStore(database)
    before = store.counts()

    server, thread, base = _run_server(database)
    try:
        status, workspace = _request(f"{base}/selections/current")
        assert status == 200
        for marker in ("Ручная редакционная подборка", "Добавить", "lead", "body", "reserve", "Сохранить"):
            assert marker in workspace

        status, body = _request(
            f"{base}/api/selections/current",
            payload={
                "title": "Выпуск 12:00",
                "items": [
                    {"story_id": "story-b", "role": "lead"},
                    {"story_id": "story-a", "role": "body"},
                    {"story_id": "story-c", "role": "reserve"},
                ],
            },
        )
        assert status == 200
        saved = json.loads(body)["selection"]
        assert [(item["story_id"], item["role"], item["position"]) for item in saved["items"]] == [
            ("story-b", "lead", 0),
            ("story-a", "body", 1),
            ("story-c", "reserve", 2),
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    server, thread, base = _run_server(database)
    try:
        status, body = _request(f"{base}/api/selections/current")
        assert status == 200
        restored = json.loads(body)["selection"]
        assert restored["title"] == "Выпуск 12:00"
        assert [item["story_id"] for item in restored["items"]] == ["story-b", "story-a", "story-c"]

        status, body = _request(
            f"{base}/api/selections/current",
            payload={
                "title": "Выпуск 12:00",
                "items": [
                    {"story_id": "story-a", "role": "lead"},
                    {"story_id": "story-b", "role": "body"},
                ],
            },
        )
        assert status == 200
        assert [item["story_id"] for item in json.loads(body)["selection"]["items"]] == ["story-a", "story-b"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert store.counts() == before
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM editorial_selections").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM editorial_selection_items").fetchone()[0] == 2


def test_selection_api_rejects_invalid_role_and_unknown_story(tmp_path: Path) -> None:
    database = tmp_path / "radio-news.sqlite"
    _seed(database)
    server, thread, base = _run_server(database)
    try:
        status, body = _request(
            f"{base}/api/selections/current",
            payload={"title": "x", "items": [{"story_id": "story-a", "role": "automatic"}]},
        )
        assert status == 400
        assert "lead, body, or reserve" in json.loads(body)["error"]

        status, body = _request(
            f"{base}/api/selections/current",
            payload={"title": "x", "items": [{"story_id": "missing", "role": "lead"}]},
        )
        assert status == 400
        assert "unknown Story" in json.loads(body)["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
