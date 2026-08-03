from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .domain import Claim, Fact, NormalizedItem, RawItem, Story, VerificationResult

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS raw_items (
 id TEXT PRIMARY KEY,
 source_id TEXT NOT NULL,
 source_external_id TEXT NOT NULL,
 source_url TEXT NOT NULL,
 published_at TEXT NOT NULL,
 fetched_at TEXT NOT NULL,
 raw_title TEXT NOT NULL,
 raw_content TEXT NOT NULL,
 raw_payload TEXT NOT NULL,
 content_hash TEXT NOT NULL,
 UNIQUE(source_id, source_external_id)
);
CREATE TABLE IF NOT EXISTS normalized_items (
 id TEXT PRIMARY KEY,
 raw_item_id TEXT NOT NULL UNIQUE REFERENCES raw_items(id),
 title TEXT NOT NULL,
 content TEXT NOT NULL,
 canonical_url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stories (
 id TEXT PRIMARY KEY,
 canonical_key TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
 id TEXT PRIMARY KEY,
 story_id TEXT NOT NULL REFERENCES stories(id),
 raw_item_id TEXT NOT NULL UNIQUE REFERENCES raw_items(id),
 text TEXT NOT NULL,
 asserted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS facts (
 id TEXT PRIMARY KEY,
 story_id TEXT NOT NULL REFERENCES stories(id),
 canonical_text TEXT NOT NULL,
 editor_id TEXT NOT NULL,
 decided_at TEXT NOT NULL,
 editorial_status TEXT NOT NULL,
 UNIQUE(story_id, canonical_text)
);
CREATE TABLE IF NOT EXISTS fact_claims (
 fact_id TEXT NOT NULL REFERENCES facts(id),
 claim_id TEXT NOT NULL REFERENCES claims(id),
 PRIMARY KEY(fact_id, claim_id)
);
CREATE TABLE IF NOT EXISTS verification_results (
 id TEXT PRIMARY KEY,
 fact_id TEXT NOT NULL UNIQUE REFERENCES facts(id),
 status TEXT NOT NULL,
 reason TEXT NOT NULL,
 policy_version TEXT NOT NULL,
 evaluated_at TEXT NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)

    def upsert_graph(
        self,
        raw: RawItem,
        normalized: NormalizedItem,
        story: Story,
        claim: Claim,
        fact: Fact,
        verification: VerificationResult,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO raw_items VALUES (?,?,?,?,?,?,?,?,?,?)",
                (raw.id, raw.source_id, raw.source_external_id, raw.source_url,
                 raw.published_at.isoformat(), raw.fetched_at.isoformat(),
                 raw.raw_title, raw.raw_content, raw.raw_payload, raw.content_hash),
            )
            conn.execute("INSERT OR IGNORE INTO normalized_items VALUES (?,?,?,?,?)", (normalized.id, normalized.raw_item_id, normalized.title, normalized.content, normalized.canonical_url))
            conn.execute("INSERT OR IGNORE INTO stories VALUES (?,?,?,?)", (story.id, story.canonical_key, story.title, story.created_at.isoformat()))
            conn.execute("INSERT OR IGNORE INTO claims VALUES (?,?,?,?,?)", (claim.id, claim.story_id, claim.raw_item_id, claim.text, claim.asserted_at.isoformat()))
            conn.execute("INSERT OR IGNORE INTO facts VALUES (?,?,?,?,?,?)", (fact.id, fact.story_id, fact.canonical_text, fact.editor_id, fact.decided_at.isoformat(), fact.editorial_status))
            conn.execute("INSERT OR IGNORE INTO fact_claims VALUES (?,?)", (fact.id, claim.id))
            conn.execute("INSERT OR IGNORE INTO verification_results VALUES (?,?,?,?,?,?)", (verification.id, verification.fact_id, verification.status, verification.reason, verification.policy_version, verification.evaluated_at.isoformat()))

    def counts(self) -> dict[str, int]:
        tables = ["raw_items", "normalized_items", "stories", "claims", "facts", "verification_results"]
        with self.connect() as conn:
            return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}

    def read_graph(self, raw_item_id: str) -> dict[str, dict[str, str]]:
        with self.connect() as conn:
            raw = dict(conn.execute("SELECT * FROM raw_items WHERE id=?", (raw_item_id,)).fetchone())
            normalized = dict(conn.execute("SELECT * FROM normalized_items WHERE raw_item_id=?", (raw_item_id,)).fetchone())
            claim = dict(conn.execute("SELECT * FROM claims WHERE raw_item_id=?", (raw_item_id,)).fetchone())
            story = dict(conn.execute("SELECT * FROM stories WHERE id=?", (claim["story_id"],)).fetchone())
            fact = dict(conn.execute("SELECT f.* FROM facts f JOIN fact_claims fc ON fc.fact_id=f.id WHERE fc.claim_id=?", (claim["id"],)).fetchone())
            verification = dict(conn.execute("SELECT * FROM verification_results WHERE fact_id=?", (fact["id"],)).fetchone())
            return {"raw": raw, "normalized": normalized, "story": story, "claim": claim, "fact": fact, "verification": verification}
