from __future__ import annotations

import html
import ipaddress
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import type

from ..application import EditorialFeedService, FeedSnapshot
from ..errors import RadioNewsError

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _validate_loopback_host(host: str) -> None:
    if host in _LOOPBACK_HOSTS:
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise RadioNewsError("P1 server may listen only on localhost/loopback")


def _render_feed(snapshot: FeedSnapshot) -> str:
    if snapshot.items:
        cards = "".join(
            f"""
            <article class="card">
              <div class="meta">
                <span class="source">{html.escape(item.source_name)}</span>
                <span>{html.escape(item.published_at)}</span>
              </div>
              <h2>{html.escape(item.title)}</h2>
              <div class="footer">
                <code>{html.escape(item.source_id)}</code>
                <span class="state">{html.escape(item.processing_state)}</span>
              </div>
            </article>
            """
            for item in snapshot.items
        )
        content = f'<section class="feed">{cards}</section>'
    else:
        content = """
        <section class="empty">
          <h2>Лента пока пуста</h2>
          <p>В выбранной базе нет сохранённых новостей. Сначала выполните fixture pipeline, затем обновите страницу.</p>
        </section>
        """

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>КПNEWS — редакционная лента</title>
  <style>
    :root {{ color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f4f5f7; color: #17191d; }}
    header {{ padding: 28px max(24px, calc((100vw - 980px)/2)); background: #17191d; color: white; }}
    header h1 {{ margin: 0 0 6px; font-size: 28px; }}
    header p {{ margin: 0; opacity: .72; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px 24px 48px; }}
    .summary {{ display: flex; gap: 12px; align-items: center; margin-bottom: 18px; color: #5a606b; }}
    .count {{ background: #fff; border: 1px solid #dfe2e7; border-radius: 999px; padding: 6px 10px; font-weight: 650; }}
    .feed {{ display: grid; gap: 14px; }}
    .card {{ background: white; border: 1px solid #dfe2e7; border-radius: 14px; padding: 20px; box-shadow: 0 4px 16px rgba(20,25,35,.04); }}
    .card h2 {{ font-size: 20px; line-height: 1.3; margin: 13px 0 18px; }}
    .meta, .footer {{ display: flex; justify-content: space-between; gap: 14px; align-items: center; color: #68707d; font-size: 13px; }}
    .source {{ color: #22262d; font-weight: 700; }}
    .state {{ background: #e8f5ec; color: #176335; border-radius: 999px; padding: 5px 9px; font-weight: 700; }}
    code {{ overflow-wrap: anywhere; }}
    .empty, .error {{ background: white; border: 1px solid #dfe2e7; border-radius: 14px; padding: 34px; text-align: center; }}
  </style>
</head>
<body>
  <header>
    <h1>КПNEWS</h1>
    <p>Редакционная лента · только чтение</p>
  </header>
  <main>
    <div class="summary"><span class="count">Новостей: {len(snapshot.items)}</span><span>SQLite открыта read-only</span></div>
    {content}
  </main>
</body>
</html>"""


def _render_error(message: str) -> str:
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>КПNEWS — ошибка</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f5f7;margin:0;padding:48px;color:#20242a}}.error{{max-width:760px;margin:auto;background:white;border:1px solid #ddd;border-radius:14px;padding:30px}}code{{overflow-wrap:anywhere}}</style>
</head><body><section class="error"><h1>Не удалось открыть ленту</h1><p>{html.escape(message)}</p><p>Проверьте путь к базе и запустите приложение снова.</p></section></body></html>"""


def _handler(service: EditorialFeedService) -> type[BaseHTTPRequestHandler]:
    class EditorialFeedHandler(BaseHTTPRequestHandler):
        server_version = "radio-news-p1"

        def _send(self, status: HTTPStatus, content_type: str, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/healthz":
                self._send(HTTPStatus.OK, "application/json; charset=utf-8", b'{"status":"ok"}')
                return
            if self.path not in {"/", "/api/feed"}:
                self._send(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", "not found".encode())
                return
            try:
                snapshot = service.snapshot()
            except RadioNewsError as exc:
                if self.path == "/api/feed":
                    payload = json.dumps({"error": str(exc)}, ensure_ascii=False).encode()
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE, "application/json; charset=utf-8", payload)
                else:
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE, "text/html; charset=utf-8", _render_error(str(exc)).encode())
                return
            if self.path == "/api/feed":
                payload = json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True).encode()
                self._send(HTTPStatus.OK, "application/json; charset=utf-8", payload)
            else:
                self._send(HTTPStatus.OK, "text/html; charset=utf-8", _render_feed(snapshot).encode())

        def log_message(self, format: str, *args: object) -> None:
            return

    return EditorialFeedHandler


def create_editorial_feed_server(
    database_path: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    _validate_loopback_host(host)
    if not 0 <= port <= 65535:
        raise RadioNewsError("port must be between 0 and 65535")
    service = EditorialFeedService(database_path)
    service.snapshot()  # fail before binding when the database is missing or incompatible
    return ThreadingHTTPServer((host, port), _handler(service))


def serve_editorial_feed(database_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    if port == 0:
        raise RadioNewsError("CLI port must be between 1 and 65535")
    server = create_editorial_feed_server(database_path, host=host, port=port)
    print(f"КПNEWS: http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
