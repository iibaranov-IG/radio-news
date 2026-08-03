# Horizon Controlled Extraction Decision — phase 0.7

## Decision identity

```text
SOURCE REPOSITORY: iibaranov-IG/Horizon
PINNED SOURCE SHA: fd28db14c506ce23bdc0727ed2da4ff318aced32
AUDIT SOURCE: radio-news/main@d30c97f51a0919294c6cc791d75bfa9ab3fd3ad9
TARGET REPOSITORY: iibaranov-IG/radio-news
PHASE: 0.7 CONTROLLED EXTRACTION DECISION
PRODUCT CODE CHANGES: NOT INCLUDED
```

This document converts the phase 0.5 audit classifications into formal migration decisions. It authorizes only the first independent vertical slice defined below. It does not authorize implementation of deferred components.

## Decision principles

1. `radio-news` will not use Horizon as a permanent runtime dependency.
2. The Horizon repository will not be copied as a subtree.
3. The target is a modular monolith with explicit `RawItem`, `NormalizedItem`, `Story`, `Claim`, `Fact`, and `VerificationResult` boundaries.
4. Existing Horizon behavior is reused only where its contract matches the target requirement and equivalent tests can be written.
5. Security-sensitive behavior is never simplified during transfer.
6. SQLite persistence is a new implementation because Horizon provides JSON/Markdown persistence rather than a compatible relational store.
7. AI, profiles, personas, delivery, MCP, and Web UI remain outside the first vertical slice.

## First vertical slice authorized scope

```text
fixed RSS fixture
→ Source Registry
→ RSS ingress
→ RawItem
→ NormalizedItem
→ deterministic Story
→ Claim linked to RawItem
→ Manual Fact with editor/time
→ VerificationResult
→ SQLite persistence
→ restart/readback acceptance
```

The slice must run without importing Horizon and without network access in its acceptance test. A later live RSS test is separate from the deterministic fixture test.

## Formal component decisions

### Foundation and runtime

| ID | Component | Decision | Target | Rationale / condition |
|---|---|---|---|---|
| PKG-01 | Python package/build contract | `REIMPLEMENT` | `pyproject.toml`, `src/radio_news/` | Horizon's public `src` package namespace is not adopted. Build/install acceptance ideas are retained. |
| CLI-01 | Main CLI | `REIMPLEMENT` | `src/radio_news/cli.py` | New command contract for the vertical slice; no compatibility requirement with `horizon`. |
| ORCH-01 | Central orchestrator | `REIMPLEMENT` | `src/radio_news/workflow/` | Horizon stages do not match the target domain states. |
| MODEL-01 | `ContentItem` and processing state | `REIMPLEMENT` | `src/radio_news/domain/` | Explicit domain entities replace the combined Horizon aggregate. |
| CONFIG-01 | Main config contracts | `TRANSFER_WITH_ADAPTATION` | `src/radio_news/config/` | Reuse strict Pydantic validation and fail-closed unknown fields; define a smaller target schema. |
| REG-01 | Source registry/config models | `TRANSFER_WITH_ADAPTATION` | `src/radio_news/sources/registry.py` | Retain explicit source identity/config validation; first slice supports RSS only. |
| SCRAPE-BASE | Base scraper contract | `REIMPLEMENT` | `src/radio_news/sources/base.py` | New result/error/provenance contract is required. |

### RSS ingress and network boundary

| ID | Component | Decision | Target | Rationale / condition |
|---|---|---|---|---|
| RSS-01 | RSS/Atom collector | `TRANSFER_WITH_ADAPTATION` | `src/radio_news/sources/rss.py` | Feed parsing and deterministic source identity may be adapted. Raw bytes/text, canonical URL, timestamps, hash, redirects, and duplicate identity must follow the new contract. |
| EXT-01 | Extractor registry | `DEFER` | — | Extraction is not required for the fixed-fixture slice. |
| EXT-02 | Trafilatura extractor | `DEFER` | — | Add only after raw/normalized ownership and ingress security are accepted. |
| HTTP-GAP | Non-webhook outbound HTTP paths | `REIMPLEMENT` | `src/radio_news/security/ingress.py` and source adapters | A source-ingress policy must be designed explicitly. The webhook transport is not assumed to cover RSS. |
| SSRF-01 | URL validation and pinned webhook transport | `DEFER` | candidate `src/radio_news/security/outbound.py` | The verified transport is preserved as reference but is not copied into the fixture-only slice. Any later transfer requires the full dependency and regression boundary. |
| SSRF-02 | Security design/audit evidence | `TRANSFER_AS_IS` | `docs/migration/reference/` or provenance links | Preserve evidence and source SHA without altering technical claims. |

### Storage and provenance

| ID | Component | Decision | Target | Rationale / condition |
|---|---|---|---|---|
| STORE-01 | File storage/config manager | `TRANSFER_WITH_ADAPTATION` | config loader only; persistence under `src/radio_news/storage/` | Reuse environment expansion, path validation, and atomic-file ideas where needed. Do not reuse JSON/Markdown as the primary domain store. |
| STORE-02 | MCP staged run store | `REJECT` | — | Its stage model is Horizon-specific and incompatible with target persistence. |
| FILE-01 | Atomic write/path safety utilities | `TRANSFER_WITH_ADAPTATION` | migration/fixture/export utilities as needed | Preserve tested path-safety behavior; SQLite transactions replace most state writes. |
| SQLite target | New relational persistence | `REIMPLEMENT` | `src/radio_news/storage/sqlite/`, `migrations/` | New schema, uniqueness constraints, transactions, restart behavior, and migrations are required. |

### Profiles, AI, rendering and localization

| ID | Component | Decision | Target | Rationale / condition |
|---|---|---|---|---|
| PROF-01 | Profile schema/loader | `DEFER` | — | Not needed before deterministic Story/Claim/Fact/Verification. |
| PROF-02 | `tech-news` profile | `DEFER` | — | Later evidence source for configurable processing; not part of first slice. |
| PROF-03 | `tech-blog` profile | `REJECT` | — | No established radio-news product requirement. |
| AI-CLIENT | Provider abstraction | `DEFER` | — | First slice intentionally has no AI. |
| AI-CLASS | Classifier | `DEFER` | — | Later editorial stage. |
| AI-ANALYZE | Analyzer | `DEFER` | — | Output contract does not match target scoring. |
| AI-REPAIR-1 | Analysis repair | `DEFER` | — | Revisit with prompt/model/input provenance requirements. |
| AI-ENRICH | Enrichment/tools | `DEFER` | — | Requires approved Fact and tool-permission boundaries. |
| AI-REPAIR-2 | Enrichment repair | `DEFER` | — | Same provenance requirement as above. |
| RENDER-01 | Localized renderer | `DEFER` | — | Radio Writer and Linter are later stages. |
| I18N-01 | Locale model/loader | `TRANSFER_WITH_ADAPTATION` | later `src/radio_news/localization/` | Preserve strict language validation; no implementation in first slice unless needed for CLI errors. |
| I18N-02 | Russian built-in rendering rules | `TRANSFER_WITH_ADAPTATION` | later localization/radio-writing modules | Must be replaced or transferred with equivalent tests and human language acceptance. |
| I18N-03 | External Russian locale file | `DEFER` | — | Production activation is unknown; schema decision is pending. |
| I18N-CLI | Locale validation CLI | `DEFER` | — | Add after target locale contract exists. |

### Interfaces, delivery and auxiliary collectors

| IDs | Components | Decision | Rationale |
|---|---|---|---|
| HN-01, GH-01, REDDIT-01, TG-01, X-01, X-02, OPENBB-01, OSS-01, GDELT-01, GNEWS-01 | Non-RSS collectors | `DEFER` | Not required for the first independent slice. Each requires its own source, credential, security, and duplicate policy. |
| MCP-01, MCP-02, MCP-03 | MCP interface/stores | `DEFER` | Interface strategy follows stable backend contracts. |
| WEBHOOK-01 | Webhook delivery | `DEFER` | Delivery domain is later; live delivery is unverified. |
| EMAIL-01 | SMTP/IMAP | `DEFER` | Not part of first slice; live path unverified. |
| OUTPUT-01 | Markdown summaries | `DEFER` | Later export/writer stage. |
| OUTPUT-02 | GitHub Pages/Jekyll | `REJECT` | No current product requirement. |
| WIZARD-01 | Setup wizard | `DEFER` | Configuration UX follows stable schema. |
| LOG-01 | Logging/console helpers | `REIMPLEMENT` | Target requires structured workflow and editorial audit logging. |
| DOCKER-01 | Container path | `DEFER` | Existing Docker path is unverified and not the accepted package release path. |
| ASSET-01 | Site/demo assets | `REJECT` | No runtime or migration requirement. |

### CI, tests, documentation and governance

| ID | Component | Decision | Target | Rationale / condition |
|---|---|---|---|---|
| CI-01 | Public release audit workflow | `TRANSFER_WITH_ADAPTATION` | `.github/workflows/ci.yml` | Reuse clean build/install, tests, `pip check`, and hygiene concepts; create radio-news-specific jobs. |
| CI-02 | Disabled daily workflow | `REJECT` | — | Not operational evidence. |
| TEST-01 | Core/source/processing tests | `TRANSFER_WITH_ADAPTATION` | `tests/` | Select behavior-level RSS/config/path tests; do not copy tests whose domain contract is obsolete. |
| TEST-SEC | Security regression suite | `DEFER` for first fixture slice; mandatory with any network/security transfer | later `tests/security/` | No SSRF claim may be made without the complete transport-boundary suite. |
| DOC-01 | Runtime/config/profile/scraper docs | `TRANSFER_WITH_ADAPTATION` | `docs/migration/reference/` and target docs | Preserve provenance; rewrite product instructions for radio-news. |
| DOC-02 | Governance/security policy | `TRANSFER_WITH_ADAPTATION` | repository root/docs | Review ownership and reporting contacts before adoption. |

## Components blocked rather than decided

No component remains implicitly `NEEDS_REVIEW` for the authorized first slice. The following decisions are deliberately blocked from implementation despite having a formal `DEFER` decision:

- SSRF transport: blocked until the target outbound-call inventory, HTTPX/httpcore versions, and equivalence suite are approved.
- Live RSS ingress: blocked until source trust, DNS/redirect policy, response limits, and raw-payload policy are specified.
- Russian editorial output: blocked until a target locale schema and human acceptance fixture exist.
- AI runtime: blocked until model/prompt/input/output provenance tables and deterministic fallback policy are specified.
- Other collectors and delivery integrations: blocked until individual threat and credential boundaries are documented.

## First-slice target contracts

### Source identity

A source has a stable `source_id`, type, display name, enabled flag, trust class, and configuration fingerprint. The fixed fixture source must not depend on a private production config.

### Raw provenance

`RawItem` must retain:

```text
source_id
source_external_id when available
source_url
canonical_url candidate
published_at
fetched_at
raw title
raw content/payload representation
content hash
fetch/fixture metadata
```

No normalization step may overwrite the raw record.

### Duplicate identity

The first slice uses deterministic keys with explicit uniqueness constraints. At minimum:

```text
source_id + source_external_id
```

when an external ID exists, otherwise a documented combination of canonical URL and content hash. Re-running the same fixture must not create duplicate RawItem, Story, Claim, Fact, or VerificationResult rows.

### Story and claim

Story creation for the first fixture is deterministic and does not use embeddings or AI. Every Claim references its source RawItem. A Story can contain multiple Claims, but the fixture acceptance may begin with one.

### Manual Fact

A manual Fact records canonical text, supporting Claim IDs, editor identifier, decision time, and editorial status. It is not inferred automatically in the first slice.

### VerificationResult

Verification is deterministic from the stored source/claim/fact state and records status, reasons, evaluated time, and policy version.

### SQLite

The implementation must provide migrations, foreign keys, uniqueness constraints, transactions, and restart/readback tests. SQLite is the source of truth for the first slice.

## Required acceptance tests before phase 1.5

1. Fixed RSS fixture is ingested without network access.
2. Raw payload and all provenance fields are persisted without destructive normalization.
3. Second execution creates no duplicates.
4. NormalizedItem references RawItem.
5. Story identity is deterministic.
6. Claim references RawItem and Story.
7. Manual Fact records editor and timestamp and references supporting Claims.
8. VerificationResult is reproducible for the same database state and policy version.
9. Process restart followed by readback returns the same domain graph.
10. Installed wheel runs from a directory outside the checkout.
11. No import or runtime access to Horizon occurs.
12. CI records exact target SHA and executes tests, clean install, `pip check`, migration checks, and repository hygiene.

## Provenance requirements

Machine-readable provenance is maintained in `provenance/horizon-components.json`. Each selected/adapted component must record:

- Horizon source repository and pinned SHA;
- exact source paths;
- target paths;
- migration decision;
- local changes or explicit `not_started` state;
- required tests;
- CI run after implementation.

## Authorization boundary

After this decision is merged, phase 1.0 may create the modular-monolith skeleton and implement only the authorized first-slice components.

The following remain unauthorized until separate decisions or roadmap gates:

```text
AI and processing profiles
personas and Chief News Editor
Radio Writer and Linter
Rundown Engine
MCP
email/webhook delivery
other collectors
Web UI
production export
Horizon retirement
```

## Phase 0.7 verdict

```text
CONTROLLED EXTRACTION STRATEGY: APPROVED FOR FIRST VERTICAL SLICE ONLY
PERMANENT HORIZON RUNTIME DEPENDENCY: REJECTED
FULL REPOSITORY SUBTREE: REJECTED
FIRST SLICE IMPLEMENTATION: AUTHORIZED AFTER MERGE
HORIZON RETIREMENT: BLOCKED
```
