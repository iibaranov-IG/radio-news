from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from radio_news.application import StoryEvidenceService
from radio_news.errors import RadioNewsError, StoryNotFound
from radio_news.workflow import run_fixture_pipeline


def _story_id(database: Path, raw_item_id: str) -> str:
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT story_id FROM claims WHERE raw_item_id=?", (raw_item_id,)).fetchone()
    assert row is not None
    return row[0]


def test_story_evidence_reads_complete_graph_without_modifying_database(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    result = run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    story_id = _story_id(database, result.items[0].raw_item_id)
    before = database.read_bytes()

    snapshot = StoryEvidenceService(database).snapshot(story_id)

    assert snapshot.story.id == story_id
    assert len(snapshot.sources) == 1
    assert len(snapshot.raw_items) == 1
    assert len(snapshot.normalized_items) == 1
    assert len(snapshot.claims) == 1
    assert len(snapshot.facts) == 1
    assert len(snapshot.fact_claims) == 1
    assert len(snapshot.verification_results) == 1
    assert snapshot.verification_results[0].status == "READY"
    assert {edge.relation for edge in snapshot.provenance} >= {
        "contains",
        "asserted_from",
        "ingested_from",
        "normalized_as",
        "supported_by",
        "evaluated_by",
    }
    payload = snapshot.to_dict()
    assert payload["story"]["id"] == story_id
    assert payload["sources"][0]["display_name"] == "Fixture KP"
    assert database.read_bytes() == before


def test_story_evidence_returns_all_facts_links_and_verification_policies(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    result = run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    raw_id = result.items[0].raw_item_id
    story_id = _story_id(database, raw_id)
    with sqlite3.connect(database) as connection:
        claim_id = connection.execute("SELECT id FROM claims WHERE raw_item_id=?", (raw_id,)).fetchone()[0]
        connection.execute("INSERT INTO facts VALUES (?,?,?,?,?,?)", ("fact-extra", story_id, "Extra fact", "editor", now.isoformat(), "APPROVED"))
        connection.execute("INSERT INTO fact_claims VALUES (?,?)", ("fact-extra", claim_id))
        connection.execute(
            "INSERT INTO verification_results VALUES (?,?,?,?,?,?,?)",
            ("verification-extra", "fact-extra", "NEEDS_REVIEW", '[\"EXTRA\"]', "extra", "manual-fact-v2", now.isoformat()),
        )
    before = database.read_bytes()

    snapshot = StoryEvidenceService(database).snapshot(story_id)

    assert {fact.id for fact in snapshot.facts} >= {"fact-extra"}
    assert ("fact-extra", claim_id) in {(link.fact_id, link.claim_id) for link in snapshot.fact_claims}
    assert ("fact-extra", "manual-fact-v2", "NEEDS_REVIEW") in {
        (item.fact_id, item.policy_version, item.status) for item in snapshot.verification_results
    }
    assert database.read_bytes() == before


def test_story_evidence_reports_unknown_story(tmp_path: Path, app_config, now) -> None:
    database = tmp_path / "radio-news.sqlite"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor", now=now)
    with pytest.raises(StoryNotFound, match="story not found"):
        StoryEvidenceService(database).snapshot("missing-story")


def test_story_evidence_missing_database_fails_without_creating_it(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite"
    with pytest.raises(RadioNewsError, match="database not found"):
        StoryEvidenceService(database).snapshot("story")
    assert not database.exists()
