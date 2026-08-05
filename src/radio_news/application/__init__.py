"""Application services for KPNEWS product slices."""

from .editorial_selection import (
    EditorialSelection,
    EditorialSelectionItem,
    EditorialSelectionService,
)
from .feed import EditorialFeedItem, EditorialFeedService, FeedSnapshot
from .story_evidence import (
    ClaimEvidenceRecord,
    FactClaimEvidenceLink,
    FactEvidenceRecord,
    NormalizedItemEvidenceRecord,
    ProvenanceEdge,
    RawItemEvidenceRecord,
    SourceEvidenceRecord,
    StoryEvidenceService,
    StoryEvidenceSnapshot,
    StoryRecord,
    VerificationEvidenceRecord,
)

__all__ = [
    "ClaimEvidenceRecord",
    "EditorialFeedItem",
    "EditorialFeedService",
    "EditorialSelection",
    "EditorialSelectionItem",
    "EditorialSelectionService",
    "FactClaimEvidenceLink",
    "FactEvidenceRecord",
    "FeedSnapshot",
    "NormalizedItemEvidenceRecord",
    "ProvenanceEdge",
    "RawItemEvidenceRecord",
    "SourceEvidenceRecord",
    "StoryEvidenceService",
    "StoryEvidenceSnapshot",
    "StoryRecord",
    "VerificationEvidenceRecord",
]
