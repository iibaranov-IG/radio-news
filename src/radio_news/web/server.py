from __future__ import annotations

import html
import ipaddress
import json
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from ..application import EditorialFeedService, EditorialSelectionItem, EditorialSelectionService, FeedSnapshot, StoryEvidenceService, StoryEvidenceSnapshot
from ..errors import RadioNewsError, StoryNotFound

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_SELECTION_ID = "current"
_MAX_REQUEST_BYTES = 1_048_576


def _validate_loopback_host(host: str) -> None:
    if host in _LOOPBACK_HOSTS:
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise RadioNewsError("KPNEWS server may listen only on localhost/loopback")


def _page(title: str, body: str, *, wide: bool = False) -> str:
    width = "1160px" if wide else "980px"
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
body{{margin:0;background:#f4f5f7;color:#17191d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}header{{padding:24px max(24px,calc((100vw - {width})/2));background:#17191d;color:white}}main{{max-width:{width};margin:auto;padding:24px}}a{{color:#174d9b;text-decoration:none}}header a{{color:#a9ccff}}a:hover{{text-decoration:underline}}.panel,.card{{background:white;border:1px solid #dfe2e7;border-radius:14px;padding:20px;margin-bottom:14px}}.feed{{display:grid;gap:14px}}.meta{{display:flex;justify-content:space-between;gap:14px;color:#68707d;font-size:13px}}.state{{background:#e8f5ec;color:#176335;border-radius:999px;padding:5px 9px;font-weight:700}}.record{{border-left:4px solid #d6dce5;background:#fafbfc;padding:14px 16px;margin:12px 0}}.small,.muted{{color:#68707d;font-size:13px}}code,pre{{overflow-wrap:anywhere;white-space:pre-wrap}}button,select,input{{font:inherit}}button{{cursor:pointer;border:1px solid #b9c1cc;background:white;border-radius:8px;padding:7px 10px}}button.primary{{background:#174d9b;color:white;border-color:#174d9b}}button.danger{{color:#9c2525}}.toolbar{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}.workspace{{display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,0.8fr);gap:18px}}.story-row,.selection-row{{display:grid;gap:8px;align-items:center;border:1px solid #e1e4e8;border-radius:10px;padding:12px;margin:9px 0}}.story-row{{grid-template-columns:1fr auto}}.selection-row{{grid-template-columns:36px minmax(0,1fr) 120px auto}}.position{{font-weight:700;text-align:center}}.notice{{padding:10px 12px;border-radius:8px;background:#edf4ff;color:#174d9b}}.error{{background:#fff0f0;color:#8e2020}}@media(max-width:850px){{.workspace{{grid-template-columns:1fr}}.selection-row{{grid-template-columns:30px 1fr}}}}
</style></head><body>{body}</body></html>'''


def _render_feed(snapshot: FeedSnapshot) -> str:
    cards = []
    for item in snapshot.items:
        title = html.escape(item.title)
        story_markup = "Story: недоступен"
        if item.story_id:
            title = f'<a href="/stories/{quote(item.story_id, safe="")}">{title}</a>'
            story_markup = f"Story: {html.escape(item.story_id)}"
            add_button = f'<button type="button" data-add-story="{html.escape(item.story_id, quote=True)}">В подборку</button>'
        else:
            add_button = ""
        cards.append(f'<article class="card"><div class="meta"><strong>{html.escape(item.source_name)}</strong><span>{html.escape(item.published_at)}</span></div><h2>{title}</h2><div class="meta"><span><code>{html.escape(item.source_id)}</code> · <code>{story_markup}</code></span><span class="state">{html.escape(item.processing_state)}</span></div><div class="toolbar" style="margin-top:12px">{add_button}</div></article>')
    content = f'<section class="feed">{"".join(cards)}</section>' if cards else '<section class="panel"><h2>Лента пока пуста</h2></section>'
    body = f'''<header><h1>КПNEWS</h1><p>Редакционная лента</p><p><a href="/selections/{_SELECTION_ID}">Открыть ручную подборку →</a></p></header><main><p>Новостей: {len(snapshot.items)}</p>{content}</main>
<script>for(const b of document.querySelectorAll('[data-add-story]'))b.onclick=async()=>{{const r=await fetch('/api/selections/{_SELECTION_ID}'),d=await r.json();if(!r.ok){{alert(d.error);return}};if(!d.selection.items.some(x=>x.story_id===b.dataset.addStory))d.selection.items.push({{story_id:b.dataset.addStory,role:'body',position:d.selection.items.length}});const s=await fetch('/api/selections/{_SELECTION_ID}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:d.selection.title,items:d.selection.items}})}}),j=await s.json();if(!s.ok){{alert(j.error);return}};location.href='/selections/{_SELECTION_ID}'}};</script>'''
    return _page("КПNEWS — редакционная лента", body)


def _record(title: str, identifier: str, text: str) -> str:
    return f'<div class="record"><strong>{html.escape(title)}</strong> <code>{html.escape(identifier)}</code><p>{html.escape(text)}</p></div>'


def _render_story_evidence(snapshot: StoryEvidenceSnapshot) -> str:
    sections = [f'<section class="panel"><h2>Story</h2><h3>{html.escape(snapshot.story.title)}</h3><code>{html.escape(snapshot.story.id)}</code><p><button id="add-story">Добавить в подборку</button></p></section>']
    sections += [_record("Source", x.source_id, x.display_name) for x in snapshot.sources]
    sections += [_record("RawItem", x.id, x.raw_title + "\n" + x.raw_content) for x in snapshot.raw_items]
    sections += [_record("NormalizedItem", x.id, x.title + "\n" + x.content) for x in snapshot.normalized_items]
    sections += [_record("Claim", x.id, x.text) for x in snapshot.claims]
    sections += [_record("Fact", x.id, x.canonical_text) for x in snapshot.facts]
    sections += [_record("VerificationResult", x.id, x.status + " · " + x.reason) for x in snapshot.verification_results]
    provenance = "".join(f'<li><code>{html.escape(x.source_type)}:{html.escape(x.source_id)}</code> <strong>{html.escape(x.relation)}</strong> <code>{html.escape(x.target_type)}:{html.escape(x.target_id)}</code></li>' for x in snapshot.provenance)
    sections.append(f'<section class="panel"><h2>Provenance</h2><ol>{provenance}</ol></section>')
    sections.append('<p class="muted">SQLite открыта read-only · доказательный граф не изменяется.</p>')
    story_id = json.dumps(snapshot.story.id)
    body = f'''<header><a href="/">← Лента</a><h1>{html.escape(snapshot.story.title)}</h1><p>Story and Evidence View</p></header><main>{''.join(sections)}</main><script>document.getElementById('add-story').onclick=async()=>{{const r=await fetch('/api/selections/{_SELECTION_ID}'),d=await r.json();if(!r.ok){{alert(d.error);return}};if(!d.selection.items.some(x=>x.story_id==={story_id}))d.selection.items.push({{story_id:{story_id},role:'body',position:d.selection.items.length}});const s=await fetch('/api/selections/{_SELECTION_ID}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:d.selection.title,items:d.selection.items}})}}),j=await s.json();if(!s.ok){{alert(j.error);return}};location.href='/selections/{_SELECTION_ID}'}};</script>'''
    return _page("КПNEWS — доказательная цепочка", body, wide=True)


def _render_selection(selection: dict[str, object], stories: list[dict[str, str]]) -> str:
    payload = json.dumps({"selection": selection, "stories": stories}, ensure_ascii=False).replace("</", "<\\/")
    body = f'''<header><a href="/">← Лента</a><h1>Ручная редакционная подборка</h1><p>P3 · только решения редактора · без автоматического отбора</p></header><main><div id="notice" class="notice">Загружено. Сохранение выполняется явно.</div><div class="workspace"><section class="panel"><h2>Доступные Story</h2><div id="available"></div></section><section class="panel"><div class="toolbar"><input id="title" aria-label="Название подборки"><button id="save" class="primary">Сохранить</button></div><p class="small">Статус: DRAFT · <span id="saved-at"></span></p><div id="selected"></div></section></div></main>
<script>
const initial={payload};let items=initial.selection.items.map(x=>({{...x}}));const storyById=new Map(initial.stories.map(x=>[x.story_id,x]));const title=document.getElementById('title');title.value=initial.selection.title;const notice=document.getElementById('notice');
function esc(v){{return String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}function norm(){{items.forEach((x,i)=>x.position=i)}}function dirty(){{notice.textContent='Есть несохранённые изменения';notice.className='notice'}}
function render(){{norm();document.getElementById('saved-at').textContent=initial.selection.updated_at?('сохранено '+initial.selection.updated_at):'ещё не сохранено';document.getElementById('available').innerHTML=initial.stories.map(s=>`<div class="story-row"><div><strong>${{esc(s.title)}}</strong><div class="small"><code>${{esc(s.story_id)}}</code></div></div><button data-add="${{esc(s.story_id)}}" ${{items.some(x=>x.story_id===s.story_id)?'disabled':''}}>Добавить</button></div>`).join('');document.getElementById('selected').innerHTML=items.length?items.map((x,i)=>{{const s=storyById.get(x.story_id)||{{title:x.story_id}};return `<div class="selection-row"><div class="position">${{i+1}}</div><div><strong>${{esc(s.title)}}</strong><div class="small"><code>${{esc(x.story_id)}}</code></div></div><select data-role="${{i}}"><option value="lead" ${{x.role==='lead'?'selected':''}}>lead</option><option value="body" ${{x.role==='body'?'selected':''}}>body</option><option value="reserve" ${{x.role==='reserve'?'selected':''}}>reserve</option></select><div class="toolbar"><button data-up="${{i}}" ${{i===0?'disabled':''}}>↑</button><button data-down="${{i}}" ${{i===items.length-1?'disabled':''}}>↓</button><button class="danger" data-remove="${{i}}">Удалить</button></div></div>`}}).join(''):'<p class="muted">Подборка пуста.</p>';bind()}}
function bind(){{document.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>{{items.push({{story_id:b.dataset.add,role:'body',position:items.length}});dirty();render()}});document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{{items.splice(+b.dataset.remove,1);dirty();render()}});document.querySelectorAll('[data-up]').forEach(b=>b.onclick=()=>{{const i=+b.dataset.up;[items[i-1],items[i]]=[items[i],items[i-1]];dirty();render()}});document.querySelectorAll('[data-down]').forEach(b=>b.onclick=()=>{{const i=+b.dataset.down;[items[i+1],items[i]]=[items[i],items[i+1]];dirty();render()}});document.querySelectorAll('[data-role]').forEach(s=>s.onchange=()=>{{items[+s.dataset.role].role=s.value;dirty()}})}}
document.getElementById('save').onclick=async()=>{{norm();const r=await fetch('/api/selections/{_SELECTION_ID}',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:title.value,items}})}}),d=await r.json();if(!r.ok){{notice.textContent=d.error||'Ошибка сохранения';notice.className='notice error';return}};initial.selection=d.selection;items=d.selection.items.map(x=>({{...x}}));notice.textContent='Подборка сохранена';notice.className='notice';render()}};title.oninput=dirty;render();
</script>'''
    return _page("КПNEWS — ручная подборка", body, wide=True)


def _error_page(title: str, message: str) -> str:
    return _page(f"КПNEWS — {title}", f'<header><a href="/">← Лента</a><h1>{html.escape(title)}</h1></header><main><section class="panel"><p>{html.escape(message)}</p></section></main>')


def _handler(feed_service: EditorialFeedService, evidence_service: StoryEvidenceService, selection_service: EditorialSelectionService) -> type[BaseHTTPRequestHandler]:
    class KPNewsHandler(BaseHTTPRequestHandler):
        server_version = "radio-news-p3"
        def _send(self, status: HTTPStatus, content_type: str, payload: bytes) -> None:
            self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Content-Length",str(len(payload)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.send_header("X-Frame-Options","DENY");self.end_headers();self.wfile.write(payload)
        def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
            self._send(status,"application/json; charset=utf-8",json.dumps(payload,ensure_ascii=False,sort_keys=True).encode())
        def _selection_payload(self) -> dict[str, object]:
            selection=selection_service.load_or_empty(_SELECTION_ID);stories=selection_service.list_story_options();return {"selection":selection.to_dict(),"stories":[x.to_dict() for x in stories]}
        def do_GET(self) -> None:  # noqa: N802
            path=urlsplit(self.path).path
            if path=="/healthz":self._json(HTTPStatus.OK,{"status":"ok"});return
            try:
                if path=="/":self._send(HTTPStatus.OK,"text/html; charset=utf-8",_render_feed(feed_service.snapshot()).encode());return
                if path=="/api/feed":self._json(HTTPStatus.OK,feed_service.snapshot().to_dict());return
                if path==f"/selections/{_SELECTION_ID}":
                    p=self._selection_payload();self._send(HTTPStatus.OK,"text/html; charset=utf-8",_render_selection(p["selection"],p["stories"]).encode());return
                if path==f"/api/selections/{_SELECTION_ID}":self._json(HTTPStatus.OK,self._selection_payload());return
                if path.startswith("/stories/"):self._send(HTTPStatus.OK,"text/html; charset=utf-8",_render_story_evidence(evidence_service.snapshot(unquote(path[len('/stories/'):]))).encode());return
                if path.startswith("/api/stories/"):self._json(HTTPStatus.OK,evidence_service.snapshot(unquote(path[len('/api/stories/'):])).to_dict());return
                self._send(HTTPStatus.NOT_FOUND,"text/plain; charset=utf-8",b"not found")
            except StoryNotFound as exc:
                if path.startswith("/api/"):self._json(HTTPStatus.NOT_FOUND,{"error":str(exc)})
                else:self._send(HTTPStatus.NOT_FOUND,"text/html; charset=utf-8",_error_page("Сюжет не найден",str(exc)).encode())
            except RadioNewsError as exc:
                if path=="/api/feed" or path.startswith("/api/"):self._json(HTTPStatus.SERVICE_UNAVAILABLE,{"error":str(exc)})
                elif path=="/":self._send(HTTPStatus.SERVICE_UNAVAILABLE,"text/html; charset=utf-8",_error_page("Не удалось открыть ленту",str(exc)).encode())
                else:self._send(HTTPStatus.SERVICE_UNAVAILABLE,"text/html; charset=utf-8",_error_page("Ошибка",str(exc)).encode())
        def do_POST(self) -> None:  # noqa: N802
            if urlsplit(self.path).path!=f"/api/selections/{_SELECTION_ID}":self._send(HTTPStatus.NOT_FOUND,"text/plain; charset=utf-8",b"not found");return
            try:
                length=int(self.headers.get("Content-Length","0"))
                if length<=0 or length>_MAX_REQUEST_BYTES:raise RadioNewsError("invalid request body size")
                if self.headers.get_content_type()!="application/json":raise RadioNewsError("Content-Type must be application/json")
                data=json.loads(self.rfile.read(length).decode())
                if not isinstance(data,dict) or not isinstance(data.get("items"),list):raise RadioNewsError("selection payload must contain an items array")
                items=[]
                for position,raw in enumerate(data["items"]):
                    if not isinstance(raw,dict):raise RadioNewsError("each selection item must be an object")
                    items.append(EditorialSelectionItem(str(raw.get("story_id","")),str(raw.get("role","")),position))
                saved=selection_service.save(selection_id=_SELECTION_ID,title=str(data.get("title","")),items=items,now=datetime.now(UTC));self._json(HTTPStatus.OK,{"selection":saved.to_dict()})
            except (json.JSONDecodeError,UnicodeDecodeError) as exc:self._json(HTTPStatus.BAD_REQUEST,{"error":f"invalid JSON: {exc}"})
            except (RadioNewsError,ValueError) as exc:self._json(HTTPStatus.BAD_REQUEST,{"error":str(exc)})
        def log_message(self, format: str, *args: object) -> None:return
    return KPNewsHandler


def create_editorial_feed_server(database_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    _validate_loopback_host(host)
    if not 0 <= port <= 65535:raise RadioNewsError("port must be between 0 and 65535")
    return ThreadingHTTPServer((host,port),_handler(EditorialFeedService(database_path),StoryEvidenceService(database_path),EditorialSelectionService(database_path)))


def serve_editorial_feed(database_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    server=create_editorial_feed_server(database_path,host=host,port=port)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
