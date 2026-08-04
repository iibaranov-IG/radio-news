from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

from ..errors import RadioNewsError


@dataclass(frozen=True, slots=True)
class EditorialFeedItem:
    raw_item_id: str
    story_id: str | None
    title: str
    source_id: str
    source_name: str
    published_at: str
    fetched_at: str
    processing_state: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FeedSnapshot:
    items: tuple[EditorialFeedItem, ...]
    database_path: str

    def to_dict(self) -> dict[str, object]:
        return {"items": [item.to_dict() for item in self.items], "count": len(self.items), "database_path": self.database_path}


class EditorialFeedService:
    """Read persisted news without creating or modifying database state."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path).expanduser().resolve()

    def _connect_read_only(self) -> sqlite3.Connection:
        if not self.database_path.is_file():
            raise RadioNewsError(f"database not found: {self.database_path}")
        uri = f"file:{quote(str(self.database_path))}?mode=ro"
        try:
            connection = sqlite3.connect(uri, uri=True)
        except sqlite3.Error as exc:
            raise RadioNewsError(f"cannot open database read-only: {exc}") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
            connection.close()
            raise RadioNewsError("SQLite query_only could not be enabled")
        return connection

    def snapshot(self) -> FeedSnapshot:
        try:
            with closing(self._connect_read_only()) as connection:
                rows = connection.execute(
                    """
                    SELECT r.id AS raw_item_id, claim_link.story_id,
                           COALESCE(n.title, r.raw_title) AS title,
                           s.source_id, s.display_name AS source_name,
                           r.published_at, r.fetched_at,
                           CASE
                             WHEN EXISTS (
                               SELECT 1 FROM claims c
                               JOIN fact_claims fc ON fc.claim_id=c.id
                               JOIN verification_results v ON v.fact_id=fc.fact_id
                               WHERE c.raw_item_id=r.id AND v.status='READY'
                             ) THEN 'READY'
                             WHEN EXISTS (
                               SELECT 1 FROM claims c
                               JOIN fact_claims fc ON fc.claim_id=c.id
                               JOIN verification_results v ON v.fact_id=fc.fact_id
                               WHERE c.raw_item_id=r.id
                             ) THEN 'VERIFIED'
                             WHEN EXISTS (
                               SELECT 1 FROM claims c JOIN fact_claims fc ON fc.claim_id=c.id
                               WHERE c.raw_item_id=r.id
                             ) THEN 'FACT_RECORDED'
                             WHEN EXISTS (SELECT 1 FROM claims c WHERE c.raw_item_id=r.id) THEN 'CLAIM_RECORDED'
                             WHEN n.id IS NOT NULL THEN 'NORMALIZED'
                             ELSE 'RAW'
                           END AS processing_state
                    FROM raw_items r
                    JOIN sources s ON s.source_id=r.source_id
                    LEFT JOIN normalized_items n ON n.raw_item_id=r.id
                    LEFT JOIN claims claim_link ON claim_link.raw_item_id=r.id
                    ORDER BY r.published_at DESC, r.id ASC
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            raise RadioNewsError(f"database is not a compatible radio-news database: {exc}") from exc
        return FeedSnapshot(
            items=tuple(
                EditorialFeedItem(
                    row["raw_item_id"],
                    row["story_id"],
                    row["title"],
                    row["source_id"],
                    row["source_name"],
                    row["published_at"],
                    row["fetched_at"],
                    row["processing_state"],
                )
                for row in rows
            ),
            database_path=str(self.database_path),
        )
