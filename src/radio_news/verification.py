from __future__ import annotations

from collections.abc import Sequence

from .domain import Claim, Fact, VerificationDecision


class VerificationPolicy:
    version = "manual-fact-v1"

    def evaluate(
        self,
        fact: Fact,
        supporting_claims: Sequence[Claim],
    ) -> VerificationDecision:
        if fact.editorial_status != "APPROVED":
            return VerificationDecision(
                status="NEEDS_REVIEW",
                reason_codes=("FACT_NOT_APPROVED",),
                reason="manual fact is not in APPROVED editorial status",
                policy_version=self.version,
            )
        if not supporting_claims:
            return VerificationDecision(
                status="BLOCKED",
                reason_codes=("NO_SUPPORTING_CLAIMS",),
                reason="approved manual fact has no supporting claims",
                policy_version=self.version,
            )
        if tuple(claim.id for claim in supporting_claims) != fact.supporting_claim_ids:
            return VerificationDecision(
                status="BLOCKED",
                reason_codes=("SUPPORTING_CLAIM_SET_MISMATCH",),
                reason="provided supporting claims do not match the fact contract",
                policy_version=self.version,
            )
        if any(claim.story_id != fact.story_id for claim in supporting_claims):
            return VerificationDecision(
                status="BLOCKED",
                reason_codes=("CROSS_STORY_CLAIM",),
                reason="supporting claim belongs to a different story",
                policy_version=self.version,
            )
        return VerificationDecision(
            status="READY",
            reason_codes=(
                "MANUAL_FACT_APPROVED",
                "SUPPORTING_CLAIM_PRESENT",
                "CLAIM_STORY_MATCH",
            ),
            reason="approved manual fact is supported by a claim from the same story",
            policy_version=self.version,
        )
