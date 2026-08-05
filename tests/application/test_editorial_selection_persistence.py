from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from radio_news.application.editorial_selection import (
    EditorialSelectionItem,
    EditorialSelectionService,
)
from radio_news.errors import RadioNewsError
from radio_news.storage.sqlite import SQLiteStore


def _database(tmp_path):
    path = tmp_path / "radio-news.sqlite"
    store = SQLiteStore(path)
    assert store.migrate() == (1, 2)
    with store.connect() as connection:
        connection.executemany(
            "INSERT INTO stories(id,canonical_key,title,created_at) VALUES (?,?,?,?)",
            [
                ("story-1", "key-1", "Story one", "2026-08-05T10:00:00+00:00"),
                ("story-2", "key-2", "Story two", "2026-08-05T10:01:00+00:00"),
                ("story-3", "key-3", "Story three", "2026-08-05T10:02:00+00:00"),
            ],
        )
    return path


def _evidence_counts(store: SQLiteStore) -> dict[str, int]:
    with store.connect() as connection:
        names = (
            "sources",
            "raw_items",
            "normalized_items",
            "stories",
            "claims",
            "facts",
            "fact_claims",
            "verification_results",
        )
        return {
            name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in names
        }


def test_selection_survives_restart_and_replacement_is_transactional(tmp_path) -> None:
    database = _database(tmp_path)
    store = SQLiteStore(database)
    before = _evidence_counts(store)
    service = EditorialSelectionService(database)
    now = datetime(2026, 8, 5, 10, 30, tzinfo=UTC)

    saved = service.save(
        selection_id="selection-main",
        title="Morning draft",
        items=(
            EditorialSelectionItem("story-2", "body", 1),
            EditorialSelectionItem("story-1", "lead", 0),
            EditorialSelectionItem("story-3", "reserve", 2),
        ),
        now=now,
    )

    assert saved.status == "DRAFT"
    assert [(item.story_id, item.role, item.position) for item in saved.items] == [
        ("story-1", "lead", 0),
        ("story-2", "body", 1),
        ("story-3", "reserve", 2),
    ]

    restarted = EditorialSelectionService(database)
    assert restarted.load("selection-main") == saved

    replaced = restarted.save(
        selection_id="selection-main",
        title="Morning draft",
        items=(
            EditorialSelectionItem("story-3", "lead", 0),
            EditorialSelectionItem("story-1", "body", 1),
        ),
        now=now + timedelta(minutes=5),
    )
    assert replaced.created_at == saved.created_at
    assert replaced.updated_at != saved.updated_at
    assert [(item.story_id, item.role, item.position) for item in replaced.items] == [
        ("story-3", "lead", 0),
        ("story-1", "body", 1),
    ]
    assert EditorialSelectionService(database).load("selection-main") == replaced
    assert _evidence_counts(store) == before


def test_invalid_selection_is_rejected_without_partial_write(tmp_path) -> None:
    database = _database(tmp_path)
    service = EditorialSelectionService(database)
    now = datetime(2026, 8, 5, 10, 30, tzinfo=UTC)

    with pytest.raises(RadioNewsError, match="cannot appear twice"):
        service.save(
            selection_id="bad-duplicate",
            title="Bad",
            items=(
                EditorialSelectionItem("story-1", "lead", 0),
                EditorialSelectionItem("story-1", "body", 1),
            ),
            now=now,
        )

    with pytest.raises(RadioNewsError, match="unknown Story"):
        service.save(
            selection_id="bad-reference",
            title="Bad",
            items=(EditorialSelectionItem("missing", "lead", 0),),
            now=now,
        )

    with pytest.raises(RadioNewsError, match="lead, body, or reserve"):
        service.save(
            selection_id="bad-role",
            title="Bad",
            items=(EditorialSelectionItem("story-1", "anchor", 0),),
            now=now,
        )

    with pytest.raises(RadioNewsError, match="contiguous"):
        service.save(
            selection_id="bad-order",
            title="Bad",
            items=(EditorialSelectionItem("story-1", "lead", 3),),
            now=now,
        )

    store = SQLiteStore(database)
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM editorial_selections").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM editorial_selection_items").fetchone()[0] == 0


def test_database_constraints_protect_selection_integrity(tmp_path) -> None:
    database = _database(tmp_path)
    store = SQLiteStore(database)
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO editorial_selections VALUES (?,?,?,?,?)",
            ("selection", "Draft", "DRAFT", "2026-08-05T10:00:00+00:00", "2026-08-05T10:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO editorial_selection_items VALUES (?,?,?,?)",
            ("selection", "story-1", "lead", 0),
        )
        with pytest.raises(Exception):
            connection.execute(
                "INSERT INTO editorial_selection_items VALUES (?,?,?,?)",
                ("selection", "story-1", "body", 1),
            )
        with pytest.raises(Exception):
            connection.execute(
                "INSERT INTO editorial_selection_items VALUES (?,?,?,?)",
                ("selection", "story-2", "invalid", 1),
            )
        with pytest.raises(Exception):
            connection.execute(
                "INSERT INTO editorial_selection_items VALUES (?,?,?,?)",
                ("selection", "missing-story", "body", 1),
            )
