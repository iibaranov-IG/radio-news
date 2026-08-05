from __future__ import annotations

import sqlite3
from importlib.resources import files
from pathlib import Path

import pytest

from radio_news.errors import MigrationChecksumMismatch, MigrationError
from radio_news.storage import Migration, SQLiteStore, load_packaged_migrations


def test_migrate_empty_database(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "news.db")
    assert store.migrate() == (1, 2, 3)
    assert store.counts()["sources"] == 0
    with store.connect() as conn:
        for table in (
            "editorial_selections",
            "editorial_selection_items",
            "draft_editions",
            "draft_edition_items",
        ):
            assert conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone() is not None


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "news.db")
    assert store.migrate() == (1, 2, 3)
    assert store.migrate() == (1, 2, 3)


def test_migration_checksum_mismatch_fails(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "news.db")
    original = load_packaged_migrations()[0]
    store.migrate((original,))
    changed = Migration.from_sql(original.version, original.name, original.sql + "\n-- changed")
    with pytest.raises(MigrationChecksumMismatch):
        store.migrate((changed,))


def test_migration_rolls_back_on_error(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "news.db")
    bad = Migration.from_sql(
        99,
        "0099_bad.sql",
        "CREATE TABLE transient_table(id INTEGER);\nTHIS IS NOT SQL;",
    )
    with pytest.raises(MigrationError):
        store.migrate((bad,))
    with store.connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='transient_table'"
        ).fetchone()
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=99"
        ).fetchone()
    assert exists is None
    assert applied is None


def test_foreign_keys_are_enabled(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "news.db")
    store.migrate()
    assert store.foreign_keys_enabled()
    with store.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("BEGIN")
            conn.execute(
                "INSERT INTO raw_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("x", "missing", "e", "u", "t", "t", "a", "b", "c", "d"),
            )


def test_migrations_available_from_installed_package() -> None:
    package = files("radio_news.storage.migrations")
    initial = package.joinpath("0001_initial.sql")
    selection = package.joinpath("0002_editorial_selections.sql")
    edition = package.joinpath("0003_draft_editions.sql")
    assert initial.is_file()
    assert selection.is_file()
    assert edition.is_file()
    assert "CREATE TABLE sources" in initial.read_text(encoding="utf-8")
    assert "CREATE TABLE editorial_selections" in selection.read_text(encoding="utf-8")
    assert "CREATE TABLE draft_editions" in edition.read_text(encoding="utf-8")
