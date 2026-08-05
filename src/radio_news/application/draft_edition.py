from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..errors import RadioNewsError

GENERATOR_VERSION = "p4-template-v1"
_BLOCKED_BASELINE = "[НЕТ ПОДТВЕРЖДЁННЫХ ФАКТОВ]"
_BLOCKED_ATTRIBUTION = "Источник не подтверждён"


@dataclass(frozen=True, slots=True)
class DraftEditionItem:
    story_id: str
    role: str
    position: int
    generated_baseline: str
    edited_text: str
    source_attribution: str
    estimated_seconds: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DraftEdition:
    id: str
    selection_id: str
    title: str
    status: str
    generator_version: str
    created_at: str
    updated_at: str
    items: tuple[DraftEditionItem, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "selection_id": self.selection_id,
            "title": self.title,
            "status": self.status,
            "generator_version": self.generator_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "items": [item.to_dict() for item in self.items],
        }


class DraftEditionService:
    """Deterministic generation and transactional persistence for P4 state."""

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
    def _edition_id(selection_id: str, generator_version: str) -> str:
        digest = hashlib.sha256(
            f"{selection_id}\0{generator_version}".encode("utf-8")
        ).hexdigest()
        return f"edition_{digest}"

    @staticmethod
    def _duration_seconds(text: str) -> int:
        words = len(text.split())
        return 0 if words == 0 else (words * 24 + 59) // 60

    @staticmethod
    def _story_material(connection: sqlite3.Connection, story_id: str) -> tuple[str, str]:
        story = connection.execute(
            "SELECT title FROM stories WHERE id=?", (story_id,)
        ).fetchone()
        if story is None:
            raise RadioNewsError(f"Draft Edition references unknown Story: {story_id}")

        facts = connection.execute(
            """
            SELECT DISTINCT f.canonical_text
            FROM facts AS f
            JOIN verification_results AS vr ON vr.fact_id=f.id
            WHERE f.story_id=?
              AND f.editorial_status='APPROVED'
              AND vr.status='READY'
            ORDER BY f.decided_at, f.id
            """,
            (story_id,),
        ).fetchall()
        baseline = " ".join(row["canonical_text"].strip() for row in facts if row["canonical_text"].strip())
        if not baseline:
            baseline = _BLOCKED_BASELINE

        sources = connection.execute(
            """
            SELECT DISTINCT s.display_name
            FROM claims AS c
            JOIN raw_items AS r ON r.id=c.raw_item_id
            JOIN sources AS s ON s.source_id=r.source_id
            WHERE c.story_id=?
            ORDER BY s.display_name
            """,
            (story_id,),
        ).fetchall()
        attribution = "; ".join(row["display_name"].strip() for row in sources if row["display_name"].strip())
        if not attribution:
            attribution = _BLOCKED_ATTRIBUTION
        return baseline, attribution

    def generate(
        self,
        *,
        selection_id: str,
        now: datetime,
        generator_version: str = GENERATOR_VERSION,
    ) -> DraftEdition:
        if not selection_id.strip():
            raise RadioNewsError("selection_id must not be empty")
        if not generator_version.strip():
            raise RadioNewsError("generator_version must not be empty")
        if now.tzinfo is None:
            raise RadioNewsError("now must be timezone-aware")
        timestamp = now.astimezone(UTC).isoformat()
        edition_id = self._edition_id(selection_id, generator_version)

        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                selection = connection.execute(
                    "SELECT title FROM editorial_selections WHERE id=?",
                    (selection_id,),
                ).fetchone()
                if selection is None:
                    raise RadioNewsError(f"editorial selection not found: {selection_id}")
                selected = connection.execute(
                    """
                    SELECT story_id,role,position
                    FROM editorial_selection_items
                    WHERE selection_id=?
                    ORDER BY position,story_id
                    """,
                    (selection_id,),
                ).fetchall()
                if not selected:
                    raise RadioNewsError("editorial selection is empty")

                generated: list[DraftEditionItem] = []
                for expected_position, row in enumerate(selected):
                    if row["position"] != expected_position:
                        raise RadioNewsError("selection positions are not contiguous")
                    baseline, attribution = self._story_material(connection, row["story_id"])
                    generated.append(
                        DraftEditionItem(
                            story_id=row["story_id"],
                            role=row["role"],
                            position=row["position"],
                            generated_baseline=baseline,
                            edited_text=baseline,
                            source_attribution=attribution,
                            estimated_seconds=self._duration_seconds(baseline),
                        )
                    )

                existing = connection.execute(
                    "SELECT created_at FROM draft_editions WHERE id=?", (edition_id,)
                ).fetchone()
                created_at = existing["created_at"] if existing else timestamp
                connection.execute(
                    """
                    INSERT INTO draft_editions(id,selection_id,title,status,generator_version,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        status='DRAFT',
                        updated_at=excluded.updated_at
                    """,
                    (
                        edition_id,
                        selection_id,
                        selection["title"],
                        "DRAFT",
                        generator_version,
                        created_at,
                        timestamp,
                    ),
                )
                connection.execute(
                    "DELETE FROM draft_edition_items WHERE edition_id=?", (edition_id,)
                )
                connection.executemany(
                    """
                    INSERT INTO draft_edition_items(
                        edition_id,story_id,role,position,generated_baseline,
                        edited_text,source_attribution,estimated_seconds
                    ) VALUES (?,?,?,?,?,?,?,?)
                    """,
                    [
                        (
                            edition_id,
                            item.story_id,
                            item.role,
                            item.position,
                            item.generated_baseline,
                            item.edited_text,
                            item.source_attribution,
                            item.estimated_seconds,
                        )
                        for item in generated
                    ],
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return self.load(edition_id)

    def save_edits(
        self,
        *,
        edition_id: str,
        edited_text_by_story: dict[str, str],
        now: datetime,
    ) -> DraftEdition:
        if now.tzinfo is None:
            raise RadioNewsError("now must be timezone-aware")
        timestamp = now.astimezone(UTC).isoformat()
        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    "SELECT story_id FROM draft_edition_items WHERE edition_id=? ORDER BY position",
                    (edition_id,),
                ).fetchall()
                if not rows:
                    raise RadioNewsError(f"Draft Edition not found: {edition_id}")
                expected = {row["story_id"] for row in rows}
                if set(edited_text_by_story) != expected:
                    raise RadioNewsError("edited text must cover exactly the Draft Edition Stories")
                for story_id in expected:
                    edited = edited_text_by_story[story_id].strip()
                    if not edited:
                        raise RadioNewsError("edited text must not be empty")
                    connection.execute(
                        "UPDATE draft_edition_items SET edited_text=? WHERE edition_id=? AND story_id=?",
                        (edited, edition_id, story_id),
                    )
                connection.execute(
                    "UPDATE draft_editions SET updated_at=? WHERE id=?",
                    (timestamp, edition_id),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return self.load(edition_id)

    def load(self, edition_id: str) -> DraftEdition:
        with closing(self._connect()) as connection:
            try:
                edition = connection.execute(
                    "SELECT * FROM draft_editions WHERE id=?", (edition_id,)
                ).fetchone()
            except sqlite3.OperationalError as exc:
                raise RadioNewsError(
                    "P4 schema is not available; apply packaged migrations before use"
                ) from exc
            if edition is None:
                raise RadioNewsError(f"Draft Edition not found: {edition_id}")
            rows = connection.execute(
                """
                SELECT story_id,role,position,generated_baseline,edited_text,
                       source_attribution,estimated_seconds
                FROM draft_edition_items
                WHERE edition_id=?
                ORDER BY position,story_id
                """,
                (edition_id,),
            ).fetchall()
        return DraftEdition(
            id=edition["id"],
            selection_id=edition["selection_id"],
            title=edition["title"],
            status=edition["status"],
            generator_version=edition["generator_version"],
            created_at=edition["created_at"],
            updated_at=edition["updated_at"],
            items=tuple(
                DraftEditionItem(
                    story_id=row["story_id"],
                    role=row["role"],
                    position=row["position"],
                    generated_baseline=row["generated_baseline"],
                    edited_text=row["edited_text"],
                    source_attribution=row["source_attribution"],
                    estimated_seconds=row["estimated_seconds"],
                )
                for row in rows
            ),
        )
