from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    source_type: str
    display_name: str
    enabled: bool
    trust_class: str
    configuration_fingerprint: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RawItem:
    id: str
    source_id: str
    source_external_id: str
    source_url: str
    published_at: datetime
    fetched_at: datetime
    raw_title: str
    raw_content: str
    raw_payload: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class NormalizedItem:
    id: str
    raw_item_id: str
    title: str
    content: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class Story:
    id: str
    canonical_key: str
    title: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Claim:
    id: str
    story_id: str
    raw_item_id: str
    text: str
    asserted_at: datetime


@dataclass(frozen=True, slots=True)
class Fact:
    id: str
    story_id: str
    canonical_text: str
    editor_id: str
    decided_at: datetime
    editorial_status: str
    supporting_claim_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VerificationDecision:
    status: str
    reason_codes: tuple[str, ...]
    reason: str
    policy_version: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    id: str
    fact_id: str
    status: str
    reason_codes: tuple[str, ...]
    reason: str
    policy_version: str
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class DomainGraph:
    source: SourceRecord
    raw: RawItem
    normalized: NormalizedItem
    story: Story
    claim: Claim
    fact: Fact
    verification: VerificationResult
