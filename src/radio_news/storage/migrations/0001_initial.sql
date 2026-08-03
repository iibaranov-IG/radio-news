CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL
);

CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    trust_class TEXT NOT NULL,
    configuration_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE raw_items (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_external_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    raw_title TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(source_id, source_external_id)
);

CREATE TABLE normalized_items (
    id TEXT PRIMARY KEY,
    raw_item_id TEXT NOT NULL UNIQUE REFERENCES raw_items(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    canonical_url TEXT NOT NULL
);

CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE claims (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES stories(id),
    raw_item_id TEXT NOT NULL UNIQUE REFERENCES raw_items(id),
    text TEXT NOT NULL,
    asserted_at TEXT NOT NULL
);

CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES stories(id),
    canonical_text TEXT NOT NULL,
    editor_id TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    editorial_status TEXT NOT NULL CHECK (editorial_status IN ('APPROVED', 'DRAFT', 'REJECTED')),
    UNIQUE(story_id, canonical_text)
);

CREATE TABLE fact_claims (
    fact_id TEXT NOT NULL REFERENCES facts(id),
    claim_id TEXT NOT NULL REFERENCES claims(id),
    PRIMARY KEY(fact_id, claim_id)
);

CREATE TRIGGER fact_claim_story_guard
BEFORE INSERT ON fact_claims
FOR EACH ROW
WHEN (
    SELECT story_id FROM facts WHERE id = NEW.fact_id
) != (
    SELECT story_id FROM claims WHERE id = NEW.claim_id
)
BEGIN
    SELECT RAISE(ABORT, 'fact_claim_story_mismatch');
END;

CREATE TABLE verification_results (
    id TEXT PRIMARY KEY,
    fact_id TEXT NOT NULL REFERENCES facts(id),
    status TEXT NOT NULL CHECK (status IN ('READY', 'NEEDS_REVIEW', 'BLOCKED')),
    reason_codes TEXT NOT NULL,
    reason TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    UNIQUE(fact_id, policy_version)
);

CREATE INDEX idx_raw_items_source ON raw_items(source_id);
CREATE INDEX idx_claims_story ON claims(story_id);
CREATE INDEX idx_facts_story ON facts(story_id);
CREATE INDEX idx_fact_claims_claim ON fact_claims(claim_id);
CREATE INDEX idx_verification_fact ON verification_results(fact_id);
