from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from radio_news.application import DraftEditionService, EditorialSelectionItem, EditorialSelectionService
from radio_news.errors import RadioNewsError
from radio_news.storage.sqlite import SQLiteStore


def _database(tmp_path):
    path = tmp_path / "radio-news.sqlite"
    store = SQLiteStore(path)
    assert store.migrate() == (1, 2, 3)
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?)",
            ("source-1", "fixture", "РИА Новости", 1, "trusted", "fp", "2026-08-05T10:00:00+00:00"),
        )
        for index in range(1, 4):
            story_id = f"story-{index}"
            raw_id = f"raw-{index}"
            claim_id = f"claim-{index}"
            fact_id = f"fact-{index}"
            connection.execute(
                "INSERT INTO stories VALUES (?,?,?,?)",
                (story_id, f"key-{index}", f"Story {index}", f"2026-08-05T10:0{index}:00+00:00"),
            )
            connection.execute(
                "INSERT INTO raw_items VALUES (?,?,?,?,?,?,?,?,?,?)",
                (raw_id, "source-1", f"ext-{index}", f"https://example/{index}", "2026-08-05T10:00:00+00:00", "2026-08-05T10:00:00+00:00", f"Raw {index}", f"Body {index}", "{}", f"hash-{index}"),
            )
            connection.execute(
                "INSERT INTO claims VALUES (?,?,?,?,?)",
                (claim_id, story_id, raw_id, f"Claim {index}", "2026-08-05T10:00:00+00:00"),
            )
            connection.execute(
                "INSERT INTO facts VALUES (?,?,?,?,?,?)",
                (fact_id, story_id, f"Approved fact {index}", "editor", "2026-08-05T10:00:00+00:00", "APPROVED"),
            )
            connection.execute("INSERT INTO fact_claims VALUES (?,?)", (fact_id, claim_id))
            connection.execute(
                "INSERT INTO verification_results VALUES (?,?,?,?,?,?,?)",
                (f"verification-{index}", fact_id, "READY", "[]", "ready", "v1", "2026-08-05T10:00:00+00:00"),
            )
    selection = EditorialSelectionService(path).save(
        selection_id="current",
        title="Morning edition",
        items=(
            EditorialSelectionItem("story-1", "lead", 0),
            EditorialSelectionItem("story-2", "body", 1),
            EditorialSelectionItem("story-3", "reserve", 2),
        ),
        now=datetime(2026, 8, 5, 10, 30, tzinfo=UTC),
    )
    return path, selection


def _protected_rows(path):
    store = SQLiteStore(path)
    with store.connect() as connection:
        tables = (
            "editorial_selections", "editorial_selection_items", "sources", "raw_items",
            "stories", "claims", "facts", "fact_claims", "verification_results",
        )
        return {name: connection.execute(f"SELECT * FROM {name} ORDER BY rowid").fetchall() for name in tables}


def test_generation_is_deterministic_and_survives_restart(tmp_path) -> None:
    database, selection = _database(tmp_path)
    before = _protected_rows(database)
    service = DraftEditionService(database)
    now = datetime(2026, 8, 5, 11, 0, tzinfo=UTC)

    first = service.generate(selection_id=selection.id, now=now)
    second = service.generate(selection_id=selection.id, now=now + timedelta(minutes=1))

    assert first.id == second.id
    assert [item.generated_baseline for item in first.items] == [
        "Approved fact 1", "Approved fact 2", "Approved fact 3"
    ]
    assert [item.generated_baseline for item in second.items] == [
        "Approved fact 1", "Approved fact 2", "Approved fact 3"
    ]
    assert [(item.story_id, item.role, item.position) for item in second.items] == [
        ("story-1", "lead", 0), ("story-2", "body", 1), ("story-3", "reserve", 2)
    ]
    assert all(item.source_attribution == "РИА Новости" for item in second.items)
    assert DraftEditionService(database).load(first.id) == second
    assert _protected_rows(database) == before


def test_manual_edit_does_not_change_generated_baseline(tmp_path) -> None:
    database, selection = _database(tmp_path)
    service = DraftEditionService(database)
    generated = service.generate(
        selection_id=selection.id,
        now=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
    )
    baselines = {item.story_id: item.generated_baseline for item in generated.items}

    edited = service.save_edits(
        edition_id=generated.id,
        edited_text_by_story={item.story_id: f"Edited {item.story_id}" for item in generated.items},
        now=datetime(2026, 8, 5, 11, 5, tzinfo=UTC),
    )

    assert {item.story_id: item.generated_baseline for item in edited.items} == baselines
    assert all(item.edited_text.startswith("Edited ") for item in edited.items)
    assert DraftEditionService(database).load(generated.id) == edited


def test_fail_closed_and_rollback_on_invalid_write(tmp_path) -> None:
    database, selection = _database(tmp_path)
    service = DraftEditionService(database)

    with pytest.raises(RadioNewsError, match="not found"):
        service.generate(
            selection_id="missing",
            now=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
        )

    generated = service.generate(
        selection_id=selection.id,
        now=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
    )
    before = service.load(generated.id)
    with pytest.raises(RadioNewsError, match="exactly"):
        service.save_edits(
            edition_id=generated.id,
            edited_text_by_story={"story-1": "partial"},
            now=datetime(2026, 8, 5, 11, 1, tzinfo=UTC),
        )
    assert service.load(generated.id) == before
