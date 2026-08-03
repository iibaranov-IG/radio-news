from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from ..domain import Claim, DomainGraph, Fact, NormalizedItem, RawItem, SourceRecord, Story, VerificationResult
from ..errors import IdentityConflict, MigrationChecksumMismatch, MigrationError, RadioNewsError, SourceConfigurationConflict

_PACKAGE = "radio_news.storage.migrations"
_PATTERN = re.compile(r"^(\d+)_.*\.sql$")
_BOOTSTRAP = "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL,checksum TEXT NOT NULL)"


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str

    @classmethod
    def from_sql(cls, version: int, name: str, sql: str) -> "Migration":
        return cls(version, name, sql, hashlib.sha256(sql.encode()).hexdigest())


@dataclass(frozen=True, slots=True)
class PersistResult:
    status: str
    source_status: str


def load_packaged_migrations() -> tuple[Migration, ...]:
    result = []
    for resource in files(_PACKAGE).iterdir():
        match = _PATTERN.match(resource.name)
        if match and resource.is_file():
            result.append(Migration.from_sql(int(match.group(1)), resource.name, resource.read_text(encoding="utf-8")))
    result.sort(key=lambda item: item.version)
    if not result or len({item.version for item in result}) != len(result):
        raise MigrationError("packaged migration set is empty or has duplicate versions")
    return tuple(result)


def _statements(sql: str) -> Iterator[str]:
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement, buffer = buffer.strip(), ""
            if statement:
                yield statement
    if buffer.strip():
        raise MigrationError("migration contains an incomplete SQL statement")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            conn.close()
            raise MigrationError("SQLite foreign_keys pragma could not be enabled")
        try:
            yield conn
        finally:
            conn.close()

    def migrate(self, migrations: Iterable[Migration] | None = None) -> tuple[int, ...]:
        ordered = tuple(sorted(migrations or load_packaged_migrations(), key=lambda item: item.version))
        with self.connect() as conn:
            conn.execute(_BOOTSTRAP)
            for migration in ordered:
                row = conn.execute("SELECT name,checksum FROM schema_migrations WHERE version=?", (migration.version,)).fetchone()
                if row:
                    if row["name"] != migration.name or row["checksum"] != migration.checksum:
                        raise MigrationChecksumMismatch(f"migration {migration.version} checksum/name mismatch")
                    continue
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    for statement in _statements(migration.sql):
                        conn.execute(statement)
                    conn.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (migration.version, migration.name, datetime.now(UTC).isoformat(), migration.checksum))
                    conn.execute("COMMIT")
                except Exception as exc:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    if isinstance(exc, MigrationError):
                        raise
                    raise MigrationError(f"migration {migration.version} failed: {exc}") from exc
            return tuple(row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version"))

    def migration_versions(self) -> tuple[int, ...]:
        with self.connect() as conn:
            try:
                return tuple(row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version"))
            except sqlite3.OperationalError:
                return ()

    def foreign_keys_enabled(self) -> bool:
        with self.connect() as conn:
            return conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    @staticmethod
    def _put(conn: sqlite3.Connection, table: str, select: str, key: tuple[object, ...], insert: str, values: tuple[object, ...], expected: dict[str, object], conflict: type[IdentityConflict] = IdentityConflict) -> bool:
        row = conn.execute(select, key).fetchone()
        if row is None:
            conn.execute(insert, values)
            return True
        actual = dict(row)
        differences = {name: (actual.get(name), value) for name, value in expected.items() if actual.get(name) != value}
        if differences:
            raise conflict(f"{table} identity conflict: {differences}")
        return False

    def persist_graph(self, graph: DomainGraph) -> PersistResult:
        s, r, n, st, c, f, v = graph.source, graph.raw, graph.normalized, graph.story, graph.claim, graph.fact, graph.verification
        if c.story_id != st.id or f.story_id != st.id:
            raise IdentityConflict("story linkage is inconsistent before persistence")
        if c.id not in f.supporting_claim_ids or r.source_id != s.source_id or n.raw_item_id != r.id:
            raise IdentityConflict("provenance linkage is inconsistent before persistence")
        created = False
        source_created = False
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                source_created = self._put(conn, "sources", "SELECT * FROM sources WHERE source_id=?", (s.source_id,), "INSERT INTO sources VALUES (?,?,?,?,?,?,?)", (s.source_id, s.source_type, s.display_name, int(s.enabled), s.trust_class, s.configuration_fingerprint, _iso(s.created_at)), {"source_id": s.source_id, "source_type": s.source_type, "display_name": s.display_name, "enabled": int(s.enabled), "trust_class": s.trust_class, "configuration_fingerprint": s.configuration_fingerprint}, SourceConfigurationConflict)
                created |= source_created
                created |= self._put(conn, "raw_items", "SELECT * FROM raw_items WHERE source_id=? AND source_external_id=?", (r.source_id, r.source_external_id), "INSERT INTO raw_items VALUES (?,?,?,?,?,?,?,?,?,?)", (r.id, r.source_id, r.source_external_id, r.source_url, _iso(r.published_at), _iso(r.fetched_at), r.raw_title, r.raw_content, r.raw_payload, r.content_hash), {"id": r.id, "source_id": r.source_id, "source_external_id": r.source_external_id, "source_url": r.source_url, "published_at": _iso(r.published_at), "raw_title": r.raw_title, "raw_content": r.raw_content, "raw_payload": r.raw_payload, "content_hash": r.content_hash})
                created |= self._put(conn, "normalized_items", "SELECT * FROM normalized_items WHERE raw_item_id=?", (n.raw_item_id,), "INSERT INTO normalized_items VALUES (?,?,?,?,?)", (n.id, n.raw_item_id, n.title, n.content, n.canonical_url), {"id": n.id, "raw_item_id": n.raw_item_id, "title": n.title, "content": n.content, "canonical_url": n.canonical_url})
                created |= self._put(conn, "stories", "SELECT * FROM stories WHERE canonical_key=?", (st.canonical_key,), "INSERT INTO stories VALUES (?,?,?,?)", (st.id, st.canonical_key, st.title, _iso(st.created_at)), {"id": st.id, "canonical_key": st.canonical_key, "title": st.title, "created_at": _iso(st.created_at)})
                created |= self._put(conn, "claims", "SELECT * FROM claims WHERE raw_item_id=?", (c.raw_item_id,), "INSERT INTO claims VALUES (?,?,?,?,?)", (c.id, c.story_id, c.raw_item_id, c.text, _iso(c.asserted_at)), {"id": c.id, "story_id": c.story_id, "raw_item_id": c.raw_item_id, "text": c.text, "asserted_at": _iso(c.asserted_at)})
                created |= self._put(conn, "facts", "SELECT * FROM facts WHERE story_id=? AND canonical_text=?", (f.story_id, f.canonical_text), "INSERT INTO facts VALUES (?,?,?,?,?,?)", (f.id, f.story_id, f.canonical_text, f.editor_id, _iso(f.decided_at), f.editorial_status), {"id": f.id, "story_id": f.story_id, "canonical_text": f.canonical_text, "editor_id": f.editor_id, "editorial_status": f.editorial_status})
                for claim_id in f.supporting_claim_ids:
                    row = conn.execute("SELECT story_id FROM claims WHERE id=?", (claim_id,)).fetchone()
                    if row is None or row["story_id"] != f.story_id:
                        raise IdentityConflict(f"supporting claim {claim_id} is missing or belongs to another story")
                    if conn.execute("SELECT 1 FROM fact_claims WHERE fact_id=? AND claim_id=?", (f.id, claim_id)).fetchone() is None:
                        conn.execute("INSERT INTO fact_claims VALUES (?,?)", (f.id, claim_id))
                        created = True
                linked = tuple(row[0] for row in conn.execute("SELECT claim_id FROM fact_claims WHERE fact_id=? ORDER BY claim_id", (f.id,)))
                if linked != tuple(sorted(f.supporting_claim_ids)):
                    raise IdentityConflict("persisted supporting claim set conflicts with the fact contract")
                codes = json.dumps(v.reason_codes, ensure_ascii=False)
                created |= self._put(conn, "verification_results", "SELECT * FROM verification_results WHERE fact_id=? AND policy_version=?", (v.fact_id, v.policy_version), "INSERT INTO verification_results VALUES (?,?,?,?,?,?,?)", (v.id, v.fact_id, v.status, codes, v.reason, v.policy_version, _iso(v.evaluated_at)), {"id": v.id, "fact_id": v.fact_id, "status": v.status, "reason_codes": codes, "reason": v.reason, "policy_version": v.policy_version})
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
        return PersistResult("created" if created else "existing", "created" if source_created else "existing")

    def counts(self) -> dict[str, int]:
        names = ("sources", "raw_items", "normalized_items", "stories", "claims", "facts", "verification_results")
        with self.connect() as conn:
            return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in names}

    def read_graph(self, raw_item_id: str) -> DomainGraph:
        with self.connect() as conn:
            r = conn.execute("SELECT * FROM raw_items WHERE id=?", (raw_item_id,)).fetchone()
            if r is None:
                raise RadioNewsError(f"raw item not found: {raw_item_id}")
            s = conn.execute("SELECT * FROM sources WHERE source_id=?", (r["source_id"],)).fetchone()
            n = conn.execute("SELECT * FROM normalized_items WHERE raw_item_id=?", (raw_item_id,)).fetchone()
            c = conn.execute("SELECT * FROM claims WHERE raw_item_id=?", (raw_item_id,)).fetchone()
            st = conn.execute("SELECT * FROM stories WHERE id=?", (c["story_id"],)).fetchone() if c else None
            f = conn.execute("SELECT f.* FROM facts f JOIN fact_claims fc ON fc.fact_id=f.id WHERE fc.claim_id=?", (c["id"],)).fetchone() if c else None
            if None in (s, n, c, st, f):
                raise RadioNewsError("persisted graph is incomplete")
            linked = tuple(row[0] for row in conn.execute("SELECT claim_id FROM fact_claims WHERE fact_id=? ORDER BY claim_id", (f["id"],)))
            v = conn.execute("SELECT * FROM verification_results WHERE fact_id=? ORDER BY policy_version LIMIT 1", (f["id"],)).fetchone()
            if v is None:
                raise RadioNewsError("persisted graph is incomplete")
            return DomainGraph(
                SourceRecord(s["source_id"], s["source_type"], s["display_name"], bool(s["enabled"]), s["trust_class"], s["configuration_fingerprint"], _dt(s["created_at"])),
                RawItem(r["id"], r["source_id"], r["source_external_id"], r["source_url"], _dt(r["published_at"]), _dt(r["fetched_at"]), r["raw_title"], r["raw_content"], r["raw_payload"], r["content_hash"]),
                NormalizedItem(n["id"], n["raw_item_id"], n["title"], n["content"], n["canonical_url"]),
                Story(st["id"], st["canonical_key"], st["title"], _dt(st["created_at"])),
                Claim(c["id"], c["story_id"], c["raw_item_id"], c["text"], _dt(c["asserted_at"])),
                Fact(f["id"], f["story_id"], f["canonical_text"], f["editor_id"], _dt(f["decided_at"]), f["editorial_status"], linked),
                VerificationResult(v["id"], v["fact_id"], v["status"], tuple(json.loads(v["reason_codes"])), v["reason"], v["policy_version"], _dt(v["evaluated_at"])),
            )
