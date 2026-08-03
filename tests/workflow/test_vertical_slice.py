from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from radio_news.domain import DomainGraph
from radio_news.errors import IdentityConflict, SourceConfigurationConflict
from radio_news.sources import load_fixture_bytes
from radio_news.storage import SQLiteStore
from radio_news.verification import VerificationPolicy
from radio_news.workflow import run_fixture_pipeline


def test_exact_replay_is_noop(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    first = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    second = run_fixture_pipeline(
        app_config,
        database_path=database,
        editor_id="editor-1",
        now=now + timedelta(hours=1),
    )
    assert first.items[0].status == "created"
    assert second.items[0].status == "existing"
    assert first.items[0].raw_item_id == second.items[0].raw_item_id
    assert first.counts == second.counts


def test_same_external_id_changed_payload_fails(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    run_fixture_pipeline(app_config, database_path=database, editor_id="editor-1", now=now)
    changed = load_fixture_bytes("sample.xml").replace(
        "Новые правила вступят".encode("utf-8"),
        "Изменённые правила вступят".encode("utf-8"),
    )
    with pytest.raises(IdentityConflict, match="raw_items"):
        run_fixture_pipeline(
            app_config,
            database_path=database,
            editor_id="editor-1",
            now=now + timedelta(hours=1),
            payload_override=changed,
        )


def test_no_partial_graph_after_identity_conflict(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    first = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    store = SQLiteStore(database)
    before = store.counts()
    graph = store.read_graph(first.items[0].raw_item_id)
    source = replace(
        graph.source,
        source_id="fixture-other",
        configuration_fingerprint="f" * 64,
    )
    raw = replace(
        graph.raw,
        id="raw-other",
        source_id=source.source_id,
        source_external_id="fixture-other-001",
    )
    normalized = replace(graph.normalized, id="normalized-other", raw_item_id=raw.id)
    claim = replace(graph.claim, id="claim-other", raw_item_id=raw.id)
    conflicting_story = replace(graph.story, id="story-other", title="Conflicting title")
    claim = replace(claim, story_id=conflicting_story.id)
    fact = replace(
        graph.fact,
        id="fact-other",
        story_id=conflicting_story.id,
        supporting_claim_ids=(claim.id,),
    )
    verification = replace(
        graph.verification,
        id="verification-other",
        fact_id=fact.id,
    )
    with pytest.raises(IdentityConflict, match="stories"):
        store.persist_graph(
            DomainGraph(
                source=source,
                raw=raw,
                normalized=normalized,
                story=conflicting_story,
                claim=claim,
                fact=fact,
                verification=verification,
            )
        )
    assert store.counts() == before
    with store.connect() as conn:
        assert conn.execute(
            "SELECT 1 FROM sources WHERE source_id='fixture-other'"
        ).fetchone() is None


def test_fact_cannot_use_claim_from_another_story(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    result = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    graph = SQLiteStore(database).read_graph(result.items[0].raw_item_id)
    bad_fact = replace(graph.fact, story_id="other-story")
    with pytest.raises(IdentityConflict, match="story linkage"):
        SQLiteStore(database).persist_graph(replace(graph, fact=bad_fact))


def test_source_record_is_persisted_and_raw_references_it(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    result = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    graph = SQLiteStore(database).read_graph(result.items[0].raw_item_id)
    assert graph.source.source_id == app_config.source.source_id
    assert graph.raw.source_id == graph.source.source_id
    assert len(graph.source.configuration_fingerprint) == 64


def test_duplicate_source_conflicting_config_fails(config_dict, now, tmp_path: Path) -> None:
    from radio_news.config import AppConfig

    database = tmp_path / "news.db"
    original = AppConfig.from_dict(config_dict)
    run_fixture_pipeline(original, database_path=database, editor_id="editor-1", now=now)
    changed_dict = {
        "source": {**config_dict["source"], "display_name": "Changed name"}
    }
    changed = AppConfig.from_dict(changed_dict)
    with pytest.raises(SourceConfigurationConflict):
        run_fixture_pipeline(
            changed,
            database_path=database,
            editor_id="editor-1",
            now=now + timedelta(minutes=1),
        )


def test_full_domain_graph_survives_restart(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    result = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    raw_id = result.items[0].raw_item_id
    first_graph = SQLiteStore(database).read_graph(raw_id)
    restarted_graph = SQLiteStore(database).read_graph(raw_id)
    assert restarted_graph == first_graph
    assert restarted_graph.fact.supporting_claim_ids == (restarted_graph.claim.id,)
    assert restarted_graph.verification.policy_version == "manual-fact-v1"


def test_verifier_same_after_restart(app_config, now, tmp_path: Path) -> None:
    database = tmp_path / "news.db"
    result = run_fixture_pipeline(
        app_config, database_path=database, editor_id="editor-1", now=now
    )
    graph = SQLiteStore(database).read_graph(result.items[0].raw_item_id)
    decision = VerificationPolicy().evaluate(graph.fact, (graph.claim,))
    assert decision.status == graph.verification.status
    assert decision.reason_codes == graph.verification.reason_codes
    assert decision.reason == graph.verification.reason
    assert decision.policy_version == graph.verification.policy_version
