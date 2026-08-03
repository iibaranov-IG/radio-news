from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from radio_news.storage import SQLiteStore


def test_database_trigger_rejects_cross_story_fact_claim(app_config, now, tmp_path: Path) -> None:
    from radio_news.workflow import run_fixture_pipeline

    database = tmp_path / "news.db"
    result = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    store = SQLiteStore(database)
    graph = store.read_graph(result.items[0].raw_item_id)
    with store.connect() as conn:
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO stories(id, canonical_key, title, created_at) VALUES (?, ?, ?, ?)",
            ("story-2", "key-2", "Second", now.isoformat()),
        )
        conn.execute(
            "INSERT INTO facts(id, story_id, canonical_text, editor_id, decided_at, editorial_status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("fact-2", "story-2", "Second fact", "editor-1", now.isoformat(), "APPROVED"),
        )
        with pytest.raises(sqlite3.IntegrityError, match="fact_claim_story_mismatch"):
            conn.execute(
                "INSERT INTO fact_claims(fact_id, claim_id) VALUES (?, ?)",
                ("fact-2", graph.claim.id),
            )
        conn.execute("ROLLBACK")
