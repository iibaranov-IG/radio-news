from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

from ..errors import RadioNewsError, StoryNotFound


@dataclass(frozen=True, slots=True)
class StoryRecord:
    id: str
    canonical_key: str
    title: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SourceEvidenceRecord:
    source_id: str
    source_type: str
    display_name: str
    enabled: bool
    trust_class: str
    configuration_fingerprint: str
    created_at: str


@dataclass(frozen=True, slots=True)
class RawItemEvidenceRecord:
    id: str
    source_id: str
    source_external_id: str
    source_url: str
    published_at: str
    fetched_at: str
    raw_title: str
    raw_content: str
    raw_payload: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class NormalizedItemEvidenceRecord:
    id: str
    raw_item_id: str
    title: str
    content: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class ClaimEvidenceRecord:
    id: str
    story_id: str
    raw_item_id: str
    text: str
    asserted_at: str


@dataclass(frozen=True, slots=True)
class FactEvidenceRecord:
    id: str
    story_id: str
    canonical_text: str
    editor_id: str
    decided_at: str
    editorial_status: str


@dataclass(frozen=True, slots=True)
class FactClaimEvidenceLink:
    fact_id: str
    claim_id: str


@dataclass(frozen=True, slots=True)
class VerificationEvidenceRecord:
    id: str
    fact_id: str
    status: str
    reason_codes: tuple[str, ...]
    reason: str
    policy_version: str
    evaluated_at: str


@dataclass(frozen=True, slots=True)
class ProvenanceEdge:
    source_type: str
    source_id: str
    relation: str
    target_type: str
    target_id: str


@dataclass(frozen=True, slots=True)
class StoryEvidenceSnapshot:
    story: StoryRecord
    sources: tuple[SourceEvidenceRecord, ...]
    raw_items: tuple[RawItemEvidenceRecord, ...]
    normalized_items: tuple[NormalizedItemEvidenceRecord, ...]
    claims: tuple[ClaimEvidenceRecord, ...]
    facts: tuple[FactEvidenceRecord, ...]
    fact_claims: tuple[FactClaimEvidenceLink, ...]
    verification_results: tuple[VerificationEvidenceRecord, ...]
    provenance: tuple[ProvenanceEdge, ...]
    database_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "story": asdict(self.story),
            "sources": [asdict(item) for item in self.sources],
            "raw_items": [asdict(item) for item in self.raw_items],
            "normalized_items": [asdict(item) for item in self.normalized_items],
            "claims": [asdict(item) for item in self.claims],
            "facts": [asdict(item) for item in self.facts],
            "fact_claims": [asdict(item) for item in self.fact_claims],
            "verification_results": [asdict(item) for item in self.verification_results],
            "provenance": [asdict(item) for item in self.provenance],
            "database_path": self.database_path,
        }


class StoryEvidenceService:
    """Expose a persisted Story and its evidence graph without modifying SQLite."""

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

    def snapshot(self, story_id: str) -> StoryEvidenceSnapshot:
        if not story_id:
            raise StoryNotFound("story not found: empty id")
        try:
            with closing(self._connect_read_only()) as connection:
                story_row = connection.execute("SELECT * FROM stories WHERE id=?", (story_id,)).fetchone()
                if story_row is None:
                    raise StoryNotFound(f"story not found: {story_id}")

                source_rows = connection.execute(
                    """
                    SELECT DISTINCT s.*
                    FROM sources s
                    JOIN raw_items r ON r.source_id=s.source_id
                    JOIN claims c ON c.raw_item_id=r.id
                    WHERE c.story_id=?
                    ORDER BY s.display_name, s.source_id
                    """,
                    (story_id,),
                ).fetchall()
                raw_rows = connection.execute(
                    """
                    SELECT r.*
                    FROM raw_items r
                    JOIN claims c ON c.raw_item_id=r.id
                    WHERE c.story_id=?
                    ORDER BY r.published_at, r.id
                    """,
                    (story_id,),
                ).fetchall()
                normalized_rows = connection.execute(
                    """
                    SELECT n.*
                    FROM normalized_items n
                    JOIN claims c ON c.raw_item_id=n.raw_item_id
                    WHERE c.story_id=?
                    ORDER BY n.raw_item_id, n.id
                    """,
                    (story_id,),
                ).fetchall()
                claim_rows = connection.execute(
                    "SELECT * FROM claims WHERE story_id=? ORDER BY asserted_at,id",
                    (story_id,),
                ).fetchall()
                fact_rows = connection.execute(
                    "SELECT * FROM facts WHERE story_id=? ORDER BY decided_at,id",
                    (story_id,),
                ).fetchall()
                fact_claim_rows = connection.execute(
                    """
                    SELECT fc.fact_id,fc.claim_id
                    FROM fact_claims fc
                    JOIN facts f ON f.id=fc.fact_id
                    WHERE f.story_id=?
                    ORDER BY fc.fact_id,fc.claim_id
                    """,
                    (story_id,),
                ).fetchall()
                verification_rows = connection.execute(
                    """
                    SELECT v.*
                    FROM verification_results v
                    JOIN facts f ON f.id=v.fact_id
                    WHERE f.story_id=?
                    ORDER BY v.fact_id,v.policy_version,v.id
                    """,
                    (story_id,),
                ).fetchall()
        except StoryNotFound:
            raise
        except sqlite3.Error as exc:
            raise RadioNewsError(f"database is not a compatible radio-news database: {exc}") from exc

        story = StoryRecord(story_row["id"], story_row["canonical_key"], story_row["title"], story_row["created_at"])
        sources = tuple(
            SourceEvidenceRecord(
                row["source_id"],
                row["source_type"],
                row["display_name"],
                bool(row["enabled"]),
                row["trust_class"],
                row["configuration_fingerprint"],
                row["created_at"],
            )
            for row in source_rows
        )
        raw_items = tuple(
            RawItemEvidenceRecord(
                row["id"],
                row["source_id"],
                row["source_external_id"],
                row["source_url"],
                row["published_at"],
                row["fetched_at"],
                row["raw_title"],
                row["raw_content"],
                row["raw_payload"],
                row["content_hash"],
            )
            for row in raw_rows
        )
        normalized_items = tuple(
            NormalizedItemEvidenceRecord(row["id"], row["raw_item_id"], row["title"], row["content"], row["canonical_url"])
            for row in normalized_rows
        )
        claims = tuple(
            ClaimEvidenceRecord(row["id"], row["story_id"], row["raw_item_id"], row["text"], row["asserted_at"])
            for row in claim_rows
        )
        facts = tuple(
            FactEvidenceRecord(
                row["id"],
                row["story_id"],
                row["canonical_text"],
                row["editor_id"],
                row["decided_at"],
                row["editorial_status"],
            )
            for row in fact_rows
        )
        fact_claims = tuple(FactClaimEvidenceLink(row["fact_id"], row["claim_id"]) for row in fact_claim_rows)
        verification_results = tuple(
            VerificationEvidenceRecord(
                row["id"],
                row["fact_id"],
                row["status"],
                tuple(json.loads(row["reason_codes"])),
                row["reason"],
                row["policy_version"],
                row["evaluated_at"],
            )
            for row in verification_rows
        )

        provenance: list[ProvenanceEdge] = []
        normalized_by_raw = {item.raw_item_id: item.id for item in normalized_items}
        for claim in claims:
            provenance.append(ProvenanceEdge("Story", story.id, "contains", "Claim", claim.id))
            provenance.append(ProvenanceEdge("Claim", claim.id, "asserted_from", "RawItem", claim.raw_item_id))
        for raw_item in raw_items:
            provenance.append(ProvenanceEdge("RawItem", raw_item.id, "ingested_from", "Source", raw_item.source_id))
            normalized_id = normalized_by_raw.get(raw_item.id)
            if normalized_id:
                provenance.append(ProvenanceEdge("RawItem", raw_item.id, "normalized_as", "NormalizedItem", normalized_id))
        for fact in facts:
            provenance.append(ProvenanceEdge("Story", story.id, "contains", "Fact", fact.id))
        for link in fact_claims:
            provenance.append(ProvenanceEdge("Fact", link.fact_id, "supported_by", "Claim", link.claim_id))
        for verification in verification_results:
            provenance.append(ProvenanceEdge("Fact", verification.fact_id, "evaluated_by", "VerificationResult", verification.id))

        return StoryEvidenceSnapshot(
            story=story,
            sources=sources,
            raw_items=raw_items,
            normalized_items=normalized_items,
            claims=claims,
            facts=facts,
            fact_claims=fact_claims,
            verification_results=verification_results,
            provenance=tuple(provenance),
            database_path=str(self.database_path),
        )
