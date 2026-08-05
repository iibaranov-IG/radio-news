from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..errors import RadioNewsError

_ALLOWED_ROLES = {"lead", "body", "reserve"}


@dataclass(frozen=True, slots=True)
class EditorialSelectionItem:
    story_id: str
    role: str
    position: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EditorialSelection:
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    items: tuple[EditorialSelectionItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class SelectionStoryOption:
    story_id: str
    title: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class EditorialSelectionService:
    """Transactional persistence for P3-owned editorial selection state only."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path.is_file():
            raise RadioNewsError(f"database not found: {self.database_path}")
        connection = sqlite3.connect(self.database_path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            connection.close()
            raise RadioNewsError("SQLite foreign_keys could not be enabled")
        return connection

    @staticmethod
    def _normalize_items(
        items: tuple[EditorialSelectionItem, ...] | list[EditorialSelectionItem],
    ) -> tuple[EditorialSelectionItem, ...]:
        normalized = tuple(sorted(items, key=lambda item: item.position))
        story_ids = [item.story_id for item in normalized]
        if any(not story_id.strip() for story_id in story_ids):
            raise RadioNewsError("selection item story_id must not be empty")
        if len(set(story_ids)) != len(story_ids):
            raise RadioNewsError("a Story cannot appear twice in one selection")
        if any(item.role not in _ALLOWED_ROLES for item in normalized):
            raise RadioNewsError("selection role must be lead, body, or reserve")
        expected_positions = list(range(len(normalized)))
        actual_positions = [item.position for item in normalized]
        if actual_positions != expected_positions:
            raise RadioNewsError("selection positions must be contiguous starting at zero")
        return normalized

    def save(
        self,
        *,
        selection_id: str,
        title: str,
        items: tuple[EditorialSelectionItem, ...] | list[EditorialSelectionItem],
        now: datetime,
    ) -> EditorialSelection:
        if not selection_id.strip():
            raise RadioNewsError("selection_id must not be empty")
        if not title.strip():
            raise RadioNewsError("selection title must not be empty")
        if now.tzinfo is None:
            raise RadioNewsError("now must be timezone-aware")
        normalized = self._normalize_items(items)
        timestamp = now.astimezone(UTC).isoformat()

        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT created_at FROM editorial_selections WHERE id=?",
                    (selection_id,),
                ).fetchone()
                created_at = existing["created_at"] if existing else timestamp
                missing = [
                    item.story_id
                    for item in normalized
                    if connection.execute(
                        "SELECT 1 FROM stories WHERE id=?", (item.story_id,)
                    ).fetchone()
                    is None
                ]
                if missing:
                    raise RadioNewsError(f"selection references unknown Story: {missing[0]}")
                connection.execute(
                    """
                    INSERT INTO editorial_selections(id,title,status,created_at,updated_at)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        status='DRAFT',
                        updated_at=excluded.updated_at
                    """,
                    (selection_id, title.strip(), "DRAFT", created_at, timestamp),
                )
                connection.execute(
                    "DELETE FROM editorial_selection_items WHERE selection_id=?",
                    (selection_id,),
                )
                connection.executemany(
                    "INSERT INTO editorial_selection_items(selection_id,story_id,role,position) VALUES (?,?,?,?)",
                    [
                        (selection_id, item.story_id, item.role, item.position)
                        for item in normalized
                    ],
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return self.load(selection_id)

    def load(self, selection_id: str) -> EditorialSelection:
        with closing(self._connect()) as connection:
            try:
                selection = connection.execute(
                    "SELECT * FROM editorial_selections WHERE id=?",
                    (selection_id,),
                ).fetchone()
            except sqlite3.OperationalError as exc:
                raise RadioNewsError(
                    "P3 schema is not available; apply packaged migrations before serving"
                ) from exc
            if selection is None:
                raise RadioNewsError(f"editorial selection not found: {selection_id}")
            rows = connection.execute(
                """
                SELECT story_id,role,position
                FROM editorial_selection_items
                WHERE selection_id=?
                ORDER BY position,story_id
                """,
                (selection_id,),
            ).fetchall()
            return EditorialSelection(
                id=selection["id"],
                title=selection["title"],
                status=selection["status"],
                created_at=selection["created_at"],
                updated_at=selection["updated_at"],
                items=tuple(
                    EditorialSelectionItem(
                        row["story_id"], row["role"], row["position"]
                    )
                    for row in rows
                ),
            )

    def load_or_empty(
        self, selection_id: str, *, title: str = "Редакционная подборка"
    ) -> EditorialSelection:
        try:
            return self.load(selection_id)
        except RadioNewsError as exc:
            if str(exc) != f"editorial selection not found: {selection_id}":
                raise
            return EditorialSelection(
                id=selection_id,
                title=title,
                status="DRAFT",
                created_at="",
                updated_at="",
                items=(),
            )

    def list_story_options(self) -> tuple[SelectionStoryOption, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id,title,created_at FROM stories ORDER BY created_at DESC,id ASC"
            ).fetchall()
        return tuple(
            SelectionStoryOption(row["id"], row["title"], row["created_at"])
            for row in rows
        )
