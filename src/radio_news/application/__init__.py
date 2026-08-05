"""Application services for KPNEWS product slices."""

from .draft_edition import (
    GENERATOR_VERSION,
    DraftEdition,
    DraftEditionItem,
    DraftEditionService,
)
from .editorial_selection import (
    EditorialSelection,
    EditorialSelectionItem,
    EditorialSelectionService,
    SelectionStoryOption,
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
    "DraftEdition",
    "DraftEditionItem",
    "DraftEditionService",
    "EditorialFeedItem",
    "EditorialFeedService",
    "EditorialSelection",
    "EditorialSelectionItem",
    "EditorialSelectionService",
    "FactClaimEvidenceLink",
    "FactEvidenceRecord",
    "FeedSnapshot",
    "GENERATOR_VERSION",
    "NormalizedItemEvidenceRecord",
    "ProvenanceEdge",
    "RawItemEvidenceRecord",
    "SelectionStoryOption",
    "SourceEvidenceRecord",
    "StoryEvidenceService",
    "StoryEvidenceSnapshot",
    "StoryRecord",
    "VerificationEvidenceRecord",
]
