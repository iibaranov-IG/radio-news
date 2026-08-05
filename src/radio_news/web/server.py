from __future__ import annotations

import html
import ipaddress
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from ..application import EditorialFeedService, FeedSnapshot, StoryEvidenceService, StoryEvidenceSnapshot
from ..errors import RadioNewsError, StoryNotFound

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _validate_loopback_host(host: str) -> None:
    if host in _LOOPBACK_HOSTS:
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise RadioNewsError("KPNEWS server may listen only on localhost/loopback")


def _render_feed(snapshot: FeedSnapshot) -> str:
    if snapshot.items:
        rendered_cards: list[str] = []
        for item in snapshot.items:
            title = html.escape(item.title)
            if item.story_id:
                story_url = f"/stories/{quote(item.story_id, safe='')}"
                title_markup = f'<h2><a href="{html.escape(story_url, quote=True)}">{title}</a></h2>'
                story_markup = f'<code>Story: {html.escape(item.story_id)}</code>'
            else:
                title_markup = f"<h2>{title}</h2>"
                story_markup = "<code>Story: недоступен</code>"
            rendered_cards.append(
                f'<article class="card"><div class="meta"><strong>{html.escape(item.source_name)}</strong><span>{html.escape(item.published_at)}</span></div>{title_markup}<div class="meta"><span><code>{html.escape(item.source_id)}</code> · {story_markup}</span><span class="state">{html.escape(item.processing_state)}</span></div></article>'
            )
        content = f'<section class="feed">{"".join(rendered_cards)}</section>'
    else:
        content = '<section class="panel"><h2>Лента пока пуста</h2><p>В выбранной базе нет сохранённых новостей.</p></section>'
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>КПNEWS — редакционная лента</title><style>
body{{margin:0;background:#f4f5f7;color:#17191d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}header{{padding:28px max(24px,calc((100vw - 980px)/2));background:#17191d;color:white}}header h1{{margin:0 0 6px}}main{{max-width:980px;margin:auto;padding:28px 24px}}.feed{{display:grid;gap:14px}}.card,.panel{{background:white;border:1px solid #dfe2e7;border-radius:14px;padding:20px}}.meta{{display:flex;justify-content:space-between;gap:14px;color:#68707d;font-size:13px}}.state{{background:#e8f5ec;color:#176335;border-radius:999px;padding:5px 9px;font-weight:700}}h2{{line-height:1.3}}a{{color:#174d9b;text-decoration:none}}a:hover{{text-decoration:underline}}
</style></head><body><header><h1>КПNEWS</h1><p>Редакционная лента · только чтение</p></header><main><p>Новостей: {len(snapshot.items)} · SQLite открыта read-only</p>{content}</main></body></html>'''


def _render_story_evidence(snapshot: StoryEvidenceSnapshot) -> str:
    source_by_id = {item.source_id: item for item in snapshot.sources}
    normalized_by_raw = {item.raw_item_id: item for item in snapshot.normalized_items}
    claims_by_raw: dict[str, list[object]] = {}
    for claim in snapshot.claims:
        claims_by_raw.setdefault(claim.raw_item_id, []).append(claim)
    links_by_fact: dict[str, list[str]] = {}
    for link in snapshot.fact_claims:
        links_by_fact.setdefault(link.fact_id, []).append(link.claim_id)
    verifications_by_fact: dict[str, list[object]] = {}
    for verification in snapshot.verification_results:
        verifications_by_fact.setdefault(verification.fact_id, []).append(verification)

    item_sections: list[str] = []
    for raw_item in snapshot.raw_items:
        source = source_by_id.get(raw_item.source_id)
        normalized = normalized_by_raw.get(raw_item.id)
        claim_markup = "".join(
            f'<div class="record"><div class="record-title">Claim <code>{html.escape(claim.id)}</code></div><p>{html.escape(claim.text)}</p><div class="small">asserted_at: {html.escape(claim.asserted_at)}</div></div>'
            for claim in claims_by_raw.get(raw_item.id, [])
        ) or '<p class="muted">Claim отсутствует.</p>'
        normalized_markup = (
            f'<div class="record"><div class="record-title">NormalizedItem <code>{html.escape(normalized.id)}</code></div><h3>{html.escape(normalized.title)}</h3><p>{html.escape(normalized.content)}</p><div class="small">canonical_url: {html.escape(normalized.canonical_url)}</div></div>'
            if normalized
            else '<p class="muted">NormalizedItem отсутствует.</p>'
        )
        source_markup = (
            f'<div class="record"><div class="record-title">Source <code>{html.escape(source.source_id)}</code></div><p><strong>{html.escape(source.display_name)}</strong> · {html.escape(source.source_type)} · trust: {html.escape(source.trust_class)}</p><div class="small">configuration_fingerprint: {html.escape(source.configuration_fingerprint)}</div></div>'
            if source
            else '<p class="muted">Source отсутствует.</p>'
        )
        item_sections.append(
            f'''<section class="panel"><h2>Публикация</h2>{source_markup}<div class="record"><div class="record-title">RawItem <code>{html.escape(raw_item.id)}</code></div><h3>{html.escape(raw_item.raw_title)}</h3><p>{html.escape(raw_item.raw_content)}</p><dl><dt>source_url</dt><dd>{html.escape(raw_item.source_url)}</dd><dt>published_at</dt><dd>{html.escape(raw_item.published_at)}</dd><dt>fetched_at</dt><dd>{html.escape(raw_item.fetched_at)}</dd><dt>content_hash</dt><dd><code>{html.escape(raw_item.content_hash)}</code></dd></dl><details><summary>Raw payload</summary><pre>{html.escape(raw_item.raw_payload)}</pre></details></div>{normalized_markup}<h3>Утверждения публикации</h3>{claim_markup}</section>'''
        )

    fact_sections: list[str] = []
    for fact in snapshot.facts:
        claim_ids = links_by_fact.get(fact.id, [])
        claim_links = "".join(f"<li><code>{html.escape(claim_id)}</code></li>" for claim_id in claim_ids) or "<li>Нет связанного Claim</li>"
        verification_markup = "".join(
            f'<div class="record"><div class="record-title">VerificationResult <code>{html.escape(verification.id)}</code></div><p><span class="state">{html.escape(verification.status)}</span> · policy <code>{html.escape(verification.policy_version)}</code></p><p>{html.escape(verification.reason)}</p><div class="small">reason_codes: {html.escape(", ".join(verification.reason_codes))} · evaluated_at: {html.escape(verification.evaluated_at)}</div></div>'
            for verification in verifications_by_fact.get(fact.id, [])
        ) or '<p class="muted">VerificationResult отсутствует.</p>'
        fact_sections.append(
            f'''<div class="record"><div class="record-title">Fact <code>{html.escape(fact.id)}</code></div><h3>{html.escape(fact.canonical_text)}</h3><p>Editorial status: <strong>{html.escape(fact.editorial_status)}</strong></p><div class="small">editor_id: {html.escape(fact.editor_id)} · decided_at: {html.escape(fact.decided_at)}</div><h4>Поддерживающие Claim</h4><ul>{claim_links}</ul>{verification_markup}</div>'''
        )

    provenance_markup = "".join(
        f'<li><code>{html.escape(edge.source_type)}:{html.escape(edge.source_id)}</code> <strong>{html.escape(edge.relation)}</strong> <code>{html.escape(edge.target_type)}:{html.escape(edge.target_id)}</code></li>'
        for edge in snapshot.provenance
    ) or "<li>Связи provenance отсутствуют.</li>"

    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>КПNEWS — доказательная цепочка</title><style>
body{{margin:0;background:#f4f5f7;color:#17191d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}header{{padding:24px max(24px,calc((100vw - 1100px)/2));background:#17191d;color:white}}main{{max-width:1100px;margin:auto;padding:24px}}.panel{{background:white;border:1px solid #dfe2e7;border-radius:14px;padding:20px;margin-bottom:16px}}.record{{border-left:4px solid #d6dce5;background:#fafbfc;padding:14px 16px;margin:12px 0}}.record-title{{font-weight:700;color:#47505d}}.small,.muted{{color:#68707d;font-size:13px}}.state{{background:#e8f5ec;color:#176335;border-radius:999px;padding:4px 8px;font-weight:700}}dl{{display:grid;grid-template-columns:130px 1fr;gap:6px 12px}}dt{{font-weight:700}}dd{{margin:0;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}a{{color:#9fc5ff}}code{{overflow-wrap:anywhere}}
</style></head><body><header><a href="/">← Редакционная лента</a><h1>{html.escape(snapshot.story.title)}</h1><p>Story <code>{html.escape(snapshot.story.id)}</code> · доказательная цепочка · только чтение</p></header><main><section class="panel"><h2>Story</h2><dl><dt>id</dt><dd><code>{html.escape(snapshot.story.id)}</code></dd><dt>canonical_key</dt><dd><code>{html.escape(snapshot.story.canonical_key)}</code></dd><dt>created_at</dt><dd>{html.escape(snapshot.story.created_at)}</dd></dl></section>{''.join(item_sections)}<section class="panel"><h2>Факты и проверка</h2>{''.join(fact_sections) or '<p class="muted">Fact отсутствует.</p>'}</section><section class="panel"><h2>Provenance</h2><p>Явные связи между сохранёнными доменными записями.</p><ol>{provenance_markup}</ol></section><p class="muted">SQLite открыта read-only · никаких редакционных или доменных изменений не выполняется.</p></main></body></html>'''


def _render_feed_error(message: str) -> str:
    return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>КПNEWS — ошибка</title></head><body><main><h1>Не удалось открыть ленту</h1><p>{html.escape(message)}</p><p>Проверьте путь к базе и обновите страницу.</p></main></body></html>'


def _render_story_error(title: str, message: str) -> str:
    return f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>КПNEWS — {html.escape(title)}</title></head><body><main><p><a href="/">← Редакционная лента</a></p><h1>{html.escape(title)}</h1><p>{html.escape(message)}</p></main></body></html>'


def _handler(feed_service: EditorialFeedService, evidence_service: StoryEvidenceService) -> type[BaseHTTPRequestHandler]:
    class EditorialFeedHandler(BaseHTTPRequestHandler):
        server_version = "radio-news-p2"

        def _send(self, status: HTTPStatus, content_type: str, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def _send_story(self, story_id: str, *, as_json: bool) -> None:
            try:
                snapshot = evidence_service.snapshot(story_id)
            except StoryNotFound as exc:
                if as_json:
                    payload = json.dumps({"error": str(exc)}, ensure_ascii=False).encode()
                    self._send(HTTPStatus.NOT_FOUND, "application/json; charset=utf-8", payload)
                else:
                    self._send(HTTPStatus.NOT_FOUND, "text/html; charset=utf-8", _render_story_error("Сюжет не найден", str(exc)).encode())
                return
            except RadioNewsError as exc:
                if as_json:
                    payload = json.dumps({"error": str(exc)}, ensure_ascii=False).encode()
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE, "application/json; charset=utf-8", payload)
                else:
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE, "text/html; charset=utf-8", _render_story_error("Не удалось открыть доказательную цепочку", str(exc)).encode())
                return
            if as_json:
                payload = json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True).encode()
                self._send(HTTPStatus.OK, "application/json; charset=utf-8", payload)
            else:
                self._send(HTTPStatus.OK, "text/html; charset=utf-8", _render_story_evidence(snapshot).encode())

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/healthz":
                self._send(HTTPStatus.OK, "application/json; charset=utf-8", b'{"status":"ok"}')
                return
            if path == "/":
                try:
                    snapshot = feed_service.snapshot()
                except RadioNewsError as exc:
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE, "text/html; charset=utf-8", _render_feed_error(str(exc)).encode())
                    return
                self._send(HTTPStatus.OK, "text/html; charset=utf-8", _render_feed(snapshot).encode())
                return
            if path == "/api/feed":
                try:
                    snapshot = feed_service.snapshot()
                except RadioNewsError as exc:
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE, "application/json; charset=utf-8", json.dumps({"error": str(exc)}, ensure_ascii=False).encode())
                    return
                self._send(HTTPStatus.OK, "application/json; charset=utf-8", json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True).encode())
                return
            if path.startswith("/stories/"):
                self._send_story(unquote(path[len("/stories/") :]), as_json=False)
                return
            if path.startswith("/api/stories/"):
                self._send_story(unquote(path[len("/api/stories/") :]), as_json=True)
                return
            self._send(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", b"not found")

        def log_message(self, format: str, *args: object) -> None:
            return

    return EditorialFeedHandler


def create_editorial_feed_server(database_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    _validate_loopback_host(host)
    if not 0 <= port <= 65535:
        raise RadioNewsError("port must be between 0 and 65535")
    feed_service = EditorialFeedService(database_path)
    evidence_service = StoryEvidenceService(database_path)
    return ThreadingHTTPServer((host, port), _handler(feed_service, evidence_service))


def serve_editorial_feed(database_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    if port == 0:
        raise RadioNewsError("CLI port must be between 1 and 65535")
    server = create_editorial_feed_server(database_path, host=host, port=port)
    print(f"КПNEWS: http://{host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
