# Horizon Migration Audit — preliminary component map

## Scope and decision rule

```text
SOURCE: iibaranov-IG/Horizon
PINNED SOURCE SHA: fd28db14c506ce23bdc0727ed2da4ff318aced32
TARGET: iibaranov-IG/radio-news
PHASE: 0.5 READ-ONLY AUDIT
EXTRACTION AUTHORIZATION: NONE
```

This map classifies the audited components. It does not authorize copying, refactoring, or reimplementation.

At phase 0.5 every migration decision remains `NEEDS_REVIEW`. Candidate target paths and likely directions are recorded only to make evidence gaps explicit; they become binding only after the controlled-extraction decision in phase 0.7.

Formal values:

```text
Usage Status:
ACTIVE_RUNTIME
ACTIVE_DEV_ONLY
ACTIVE_TEST_ONLY
LEGACY
DEAD_CODE
UNKNOWN

Migration Decision:
TRANSFER_AS_IS
TRANSFER_WITH_ADAPTATION
REIMPLEMENT
DEFER
REJECT
NEEDS_REVIEW

Migration Risk:
LOW
MEDIUM
HIGH
CRITICAL
```

## Decision gates

A component may leave `NEEDS_REVIEW` only when all required gates are satisfied:

1. source path and full SHA are recorded;
2. runtime usage is supported by imports, entrypoints, config, tests, or workflows;
3. dependencies and data contracts are identified;
4. relevant tests are linked;
5. local fork changes are separated from upstream behavior;
6. target boundary is defined;
7. equivalence or replacement acceptance tests are specified;
8. security implications are reviewed separately where applicable.

## Component matrix

| ID | Component | Source paths at pinned SHA | Usage status | Runtime evidence | Tests / workflows | Risk | Migration decision | Candidate target or disposition | Evidence gap |
|---|---|---|---|---|---|---|---|---|---|
| PKG-01 | Python package/build contract | `pyproject.toml`, `uv.lock` | `ACTIVE_RUNTIME` | wheel packages namespace `src`; five console scripts; profiles force-included | `.github/workflows/public-release-audit.yml` package job | HIGH | `NEEDS_REVIEW` | new `radio-news/pyproject.toml`; preserve provenance, not package namespace automatically | compatibility impact of replacing public `src` namespace not yet specified |
| CLI-01 | Main CLI | `src/main.py` | `ACTIVE_RUNTIME` | `horizon = src.main:main`; constructs storage/config/orchestrator | `tests/test_main.py`, `tests/test_cli_parsers.py`, package smoke | MEDIUM | `NEEDS_REVIEW` | likely `src/radio_news/cli.py` or application command layer | exact CLI compatibility required by radio-news is not defined |
| ORCH-01 | Central orchestrator | `src/orchestrator.py` | `ACTIVE_RUNTIME` | imported by main and MCP; coordinates complete pipeline | `tests/test_fetch_reporting.py`, `tests/test_cross_source_duplicates.py`, `tests/test_balanced_digest.py`, `tests/test_content_selection.py` | HIGH | `NEEDS_REVIEW` | likely recompose into application services/workflow layer | Horizon stages and radio-news domain stages are not equivalent |
| MODEL-01 | Unified `ContentItem` and processing state | `src/models.py` | `ACTIVE_RUNTIME` | consumed by collectors, AI, storage, MCP, renderers, delivery | broad suite including source, AI, storage, MCP tests | HIGH | `NEEDS_REVIEW` | map selectively to explicit `RawItem`, `NormalizedItem`, `Story`, `Claim`, `Fact` contracts | field-level mapping and provenance-loss analysis not completed |
| CONFIG-01 | Main Pydantic config contracts | `src/models.py`, `src/storage/manager.py` | `ACTIVE_RUNTIME` | loaded by all entrypoints and orchestrator/MCP | `tests/test_storage.py`, `tests/test_main.py`, `tests/test_mcp_adapter.py` | HIGH | `NEEDS_REVIEW` | candidate `src/radio_news/config/` | target config schema and backward-compatibility policy are undefined |
| REG-01 | Source registry and source config models | `src/models.py` (`SourceType`, `SOURCE_REGISTRY`, source config classes) | `ACTIVE_RUNTIME` | orchestrator imports/branches by configured source; config examples enumerate sources | `tests/test_category_wiring.py`, source tests | MEDIUM | `NEEDS_REVIEW` | candidate `src/radio_news/sources/registry.py` plus source-specific config | first vertical slice requires only RSS; treatment of other sources not decided |
| SCRAPE-BASE | Base scraper contract | `src/scrapers/base.py` | `ACTIVE_RUNTIME` | inherited by collectors | source-specific tests | MEDIUM | `NEEDS_REVIEW` | candidate source-port interface | exact base API and error semantics not yet compared to target requirements |
| RSS-01 | RSS/Atom collector | `src/scrapers/rss.py` | `ACTIVE_RUNTIME` | instantiated by orchestrator when RSS list is non-empty; example config contains enabled feeds | `tests/test_rss.py`, orchestrator tests | HIGH | `NEEDS_REVIEW` | candidate `src/radio_news/sources/rss.py` | raw payload preservation, canonical URL rules, duplicate contract, and SSRF threat model differ from target |
| HN-01 | Hacker News collector | `src/scrapers/hackernews.py` | `ACTIVE_RUNTIME` | direct orchestrator import and config model | source/config/selection tests | MEDIUM | `NEEDS_REVIEW` | not needed for first vertical slice | actual production activation unknown |
| GH-01 | GitHub collector | `src/scrapers/github.py` | `ACTIVE_RUNTIME` | direct orchestrator import; example config contains GitHub sources | source/config tests | MEDIUM | `NEEDS_REVIEW` | not needed for first vertical slice | actual production activation and token behavior unknown |
| REDDIT-01 | Reddit collector | `src/scrapers/reddit.py` | `ACTIVE_RUNTIME` | direct orchestrator import; enabled example config | `tests/test_reddit.py` | MEDIUM | `NEEDS_REVIEW` | not needed for first vertical slice | external API behavior/limits not exercised live |
| TG-01 | Telegram collector | `src/scrapers/telegram.py` | `ACTIVE_RUNTIME` | direct orchestrator import and config model | `tests/test_telegram.py` | MEDIUM | `NEEDS_REVIEW` | not needed for first vertical slice | actual production activation unknown |
| X-01 | Twitter/X actor mode | `src/scrapers/twitter.py` | `ACTIVE_RUNTIME` | imported; selected by Twitter config mode | `tests/test_twitter.py` | HIGH | `NEEDS_REVIEW` | defer from first vertical slice | credentials, actor dependency, and live behavior not verified |
| X-02 | Twitter/X Playwright mode | `src/scrapers/twitter_playwright.py` | `ACTIVE_RUNTIME` | imported; selected by config mode; optional dependency group | `tests/test_twitter.py` | HIGH | `NEEDS_REVIEW` | defer from first vertical slice | browser/cookie security and live behavior not verified |
| OPENBB-01 | OpenBB collector | `src/scrapers/openbb.py` | `ACTIVE_RUNTIME` | imported; optional config and package extras | `tests/test_openbb_scraper.py` | HIGH | `NEEDS_REVIEW` | defer from first vertical slice | optional provider credentials and live integrations not verified |
| OSS-01 | OSS Insight collector | `src/scrapers/ossinsight.py` | `ACTIVE_RUNTIME` | direct orchestrator import; disabled by default but executable through config | source-specific test mapping not independently confirmed | MEDIUM | `NEEDS_REVIEW` | defer from first vertical slice | exact dedicated regression coverage and production activation unknown |
| GDELT-01 | GDELT collector | `src/scrapers/gdelt.py` | `ACTIVE_RUNTIME` | direct orchestrator import; optional config | `tests/test_gdelt.py` | MEDIUM | `NEEDS_REVIEW` | defer from first vertical slice | live API behavior not verified |
| GNEWS-01 | Google News RSS collector | `src/scrapers/google_news.py` | `ACTIVE_RUNTIME` | direct orchestrator import; optional config | `tests/test_google_news.py` | MEDIUM | `NEEDS_REVIEW` | defer from first vertical slice | overlap with generic RSS and canonicalization policy not resolved |
| EXT-01 | Extractor base and registry | `src/extractors/` | `ACTIVE_RUNTIME` | RSS can resolve `content_extractor`; example uses Trafilatura | `tests/test_extractors_registry.py` | MEDIUM | `NEEDS_REVIEW` | candidate optional source-enrichment adapter | raw versus extracted content ownership is not defined in target domain |
| EXT-02 | Trafilatura extractor | `src/extractors/`, `pyproject.toml` | `ACTIVE_RUNTIME` | selected by tracked RSS example; dependency is required | `tests/test_extractors_trafilatura.py` | MEDIUM | `NEEDS_REVIEW` | defer from minimal RSS fixture unless required by acceptance test | network security and deterministic extraction contract need specification |
| STORE-01 | Primary file storage/config manager | `src/storage/manager.py`, `src/_file_utils.py` | `ACTIVE_RUNTIME` | main CLI, locale CLI, orchestrator, MCP adapter | `tests/test_storage.py` | HIGH | `NEEDS_REVIEW` | likely split config loading from target SQLite repositories | Horizon persistence is JSON/Markdown, not SQLite |
| STORE-02 | MCP staged run store | `src/mcp/run_store.py` | `ACTIVE_RUNTIME` | used by MCP service for raw/scored/filtered/enriched JSON stages | `tests/test_mcp_run_store.py`, `tests/test_mcp_service_smoke.py` | HIGH | `NEEDS_REVIEW` | possible reference fixture format; not target persistence as-is | stage semantics and invalidation rules differ from planned domain/audit model |
| PROF-01 | Profile schema and loader | `src/processing/profiles.py` | `ACTIVE_RUNTIME` | loaded by main and MCP; validates source/profile/language references | `tests/test_profiles.py` | HIGH | `NEEDS_REVIEW` | candidate `src/radio_news/core/profiles/` or later editorial processing module | target stage using profiles and compatibility boundary not yet defined |
| PROF-02 | `tech-news` profile package | `profiles/tech-news/` | `ACTIVE_RUNTIME` | built-in package; default profile in config | `tests/test_profiles.py` | MEDIUM | `NEEDS_REVIEW` | defer until AI/editorial scoring stage | prompt hash, exact output semantics, and relevance to radio news require review |
| PROF-03 | `tech-blog` profile package | `profiles/tech-blog/` | `ACTIVE_RUNTIME` | built-in package and tracked RSS example | `tests/test_profiles.py` | MEDIUM | `NEEDS_REVIEW` | likely defer/reject for first radio-news pipeline | product relevance not established |
| AI-CLIENT | AI provider abstraction and chains | `src/ai/client.py` and provider modules | `ACTIVE_RUNTIME` | constructed by orchestrator; AI config required | provider/client tests, `tests/test_chained_client.py` | HIGH | `NEEDS_REVIEW` | candidate provider adapter layer after non-AI vertical slice | live paid-provider calls not verified; target model versioning requirements differ |
| AI-CLASS | Content classifier | `src/ai/classifier.py` | `ACTIVE_RUNTIME` | called by analyzer to resolve profile | `tests/test_classifier.py` | HIGH | `NEEDS_REVIEW` | defer until editorial scoring/persona stages | Horizon profile classification is not Story/Claim classification |
| AI-ANALYZE | First-pass analyzer | `src/ai/analyzer.py` | `ACTIVE_RUNTIME` | orchestrator calls analysis; validates `ContentAnalysis` | `tests/test_analyzer.py`, `tests/test_prompting.py` | HIGH | `NEEDS_REVIEW` | defer until after deterministic domain pipeline | output model and fallback behavior do not match radio-news editorial scoring contract |
| AI-REPAIR-1 | Analysis structured-output repair | `src/ai/analyzer.py`, `src/ai/utils.py` | `ACTIVE_RUNTIME` | failed response receives one temperature-zero corrective model call | `tests/test_analyzer.py` | HIGH | `NEEDS_REVIEW` | candidate reusable policy only with versioned input/output contracts | repair prompt/version/provenance are not currently persisted as required by radio-news architecture |
| AI-ENRICH | Enrichment runtime and tool planner | `src/ai/enricher.py`, `src/processing/tools.py`, `src/ai/prompting/` | `ACTIVE_RUNTIME` | orchestrator enriches selected items according to profile blocks | `tests/test_enricher.py`, prompting tests | HIGH | `NEEDS_REVIEW` | defer until after Story/Claim/Fact/Verification vertical slice | tool permissions, citation semantics, and target Fact boundary differ |
| AI-REPAIR-2 | Enrichment structured-output repair | `src/ai/enricher.py`, `src/ai/utils.py` | `ACTIVE_RUNTIME` | Pydantic validation plus one corrective model call at temperature zero | `tests/test_enricher.py` | HIGH | `NEEDS_REVIEW` | candidate shared structured-output service later | must add model/prompt/input hashes and raw response provenance in target |
| RENDER-01 | Deterministic localized renderer | `src/ai/summarizer.py`, `src/ai/markdown_utils.py` | `ACTIVE_RUNTIME` | called after enrichment for Markdown/webhook output | `tests/test_summarizer.py` | HIGH | `NEEDS_REVIEW` | defer until Radio Writer/Linter/output stages | current renderer consumes Horizon artifacts, not verified Facts/scripts |
| I18N-01 | Locale model and loader | `src/models.py`, `src/storage/manager.py` | `ACTIVE_RUNTIME` | config loading and validation path | `tests/test_storage.py`, `tests/test_summarizer.py` | HIGH | `NEEDS_REVIEW` | candidate `src/radio_news/localization/` plus locale data | target locale contract and fallback policy not yet approved |
| I18N-02 | Russian built-in rendering rules | `src/ai/summarizer.py`, `src/services/webhook.py`, profile JSON files | `ACTIVE_RUNTIME` | normal rendering code contains Russian labels/plural/date/title behavior | `tests/test_summarizer.py`, `tests/test_webhook.py`, `tests/test_profiles.py` | HIGH | `NEEDS_REVIEW` | must transfer or replace with tested equivalent | editorial Russian output quality and target terminology require human acceptance |
| I18N-03 | External Russian locale file | `data/locales/ru.json` | `UNKNOWN` | file is loadable through `locales_dir`; no tracked production config activates it | locale-loader tests | MEDIUM | `NEEDS_REVIEW` | candidate `locales/ru.json` after schema decision | production usage and precedence versus built-in labels are not established |
| I18N-CLI | Locale validation CLI | `src/services/locales_cli.py` | `ACTIVE_RUNTIME` | declared `horizon-locales` entrypoint; loads config/profiles and validates languages | package smoke; profile/storage/summarizer tests | MEDIUM | `NEEDS_REVIEW` | candidate CI validation command | target command/interface not designed |
| MCP-01 | MCP server | `src/mcp/server.py` | `ACTIVE_RUNTIME` | declared console entrypoint; exposes pipeline tools/resources | MCP tests and package smoke | HIGH | `NEEDS_REVIEW` | defer from first vertical slice | Web UI/automation interface strategy for radio-news not decided |
| MCP-02 | MCP staged pipeline service | `src/mcp/service.py`, `src/mcp/horizon_adapter.py` | `ACTIVE_RUNTIME` | server tools delegate to service; composes orchestrator/storage/profile runtime | `tests/test_mcp_adapter.py`, `tests/test_mcp_service_smoke.py` | HIGH | `NEEDS_REVIEW` | possible behavioral reference, not direct target service | Horizon run stages are not radio-news workflow states |
| MCP-03 | MCP error and run-artifact contracts | `src/mcp/errors.py`, `src/mcp/run_store.py` | `ACTIVE_RUNTIME` | server returns structured tool errors and stage artifacts | `tests/test_mcp_errors.py`, `tests/test_mcp_run_store.py` | MEDIUM | `NEEDS_REVIEW` | defer; selectively reuse ideas after API boundary decision | public compatibility requirements unknown |
| WEBHOOK-01 | Webhook rendering/delivery service | `src/services/webhook.py` | `ACTIVE_RUNTIME` | orchestrator constructs notifier when enabled; webhook CLI also uses it | `tests/test_webhook.py` | HIGH | `NEEDS_REVIEW` | defer from first vertical slice | live external delivery not verified; target delivery domain later |
| SSRF-01 | URL validation and pinned transport | `src/url_security.py`, `pyproject.toml` | `ACTIVE_RUNTIME` | `WebhookNotifier.notify` calls `safe_request`; exact httpcore pin | `tests/test_url_security.py`, `tests/test_webhook.py`, public-release audit workflow | CRITICAL | `NEEDS_REVIEW` | candidate `src/radio_news/security/`; no simplification allowed | target HTTP stack, dependency pin, and complete outbound call inventory must be approved |
| SSRF-02 | Security audit/design evidence | `docs/security/pre_send_ssrf_design.md`, `docs/audits/public-release-blockers.md` | `ACTIVE_DEV_ONLY` | records threat, implementation lineage, accepted tests/runs | public-release audit workflow | CRITICAL | `NEEDS_REVIEW` | preserve as provenance/reference evidence | documentation must be reconciled with target threat model and exact transferred code |
| HTTP-GAP | Non-webhook outbound HTTP paths | collectors, extractors, tools, provider SDKs; confirmed example `src/scrapers/rss.py` | `ACTIVE_RUNTIME` | RSS directly calls shared HTTPX client; other paths require enumeration | source/extractor/provider tests | CRITICAL | `NEEDS_REVIEW` | define separate source-ingress and outbound-network policies | universal SSRF coverage is not established; trust boundaries differ by caller |
| EMAIL-01 | Email/IMAP service | `src/services/email.py` | `ACTIVE_RUNTIME` | orchestrator invokes when enabled | `tests/test_email.py` | HIGH | `NEEDS_REVIEW` | defer from first vertical slice | live SMTP/IMAP explicitly not verified |
| OUTPUT-01 | Markdown summary persistence | `src/storage/manager.py`, `src/ai/summarizer.py` | `ACTIVE_RUNTIME` | orchestrator writes daily summary | storage/summarizer tests | MEDIUM | `NEEDS_REVIEW` | defer until writer/export stages | target script/rundown output format not defined |
| OUTPUT-02 | GitHub Pages/Jekyll post output | `src/orchestrator.py`, `docs/_posts` runtime destination | `ACTIVE_RUNTIME` | main pipeline attempts to write posts | direct dedicated test not confirmed | MEDIUM | `NEEDS_REVIEW` | likely defer/reject for first vertical slice | dedicated regression evidence and product requirement absent |
| WIZARD-01 | Setup wizard | `src/setup/`, `src/setup/wizard_cli.py` | `ACTIVE_RUNTIME` | declared console script and non-interactive help acceptance | `tests/test_setup_wizard.py`, `tests/test_wizard_cli.py`, package smoke | LOW | `NEEDS_REVIEW` | defer from first vertical slice | target config UX not designed |
| LOG-01 | Logging/console output | `src/logging_config.py`, `src/console_icons.py` | `ACTIVE_RUNTIME` | shared by CLI/orchestrator/services | `tests/test_logging_config.py`, `tests/test_console_icons.py` | LOW | `NEEDS_REVIEW` | likely reimplement using target observability contract | target structured logging/audit requirements differ |
| FILE-01 | Atomic write/path safety utilities | `src/_file_utils.py`, `src/storage/manager.py`, `src/mcp/run_store.py` | `ACTIVE_RUNTIME` | used by config, state, and summary persistence | storage/MCP tests | MEDIUM | `NEEDS_REVIEW` | selectively reuse behavior or tests | target SQLite transaction boundary reduces but does not remove file-write needs |
| CI-01 | Public release audit workflow | `.github/workflows/public-release-audit.yml` | `ACTIVE_DEV_ONLY` | runs tests, package acceptance, hygiene on PR/push | workflow run `30803855113` success | HIGH | `NEEDS_REVIEW` | use as evidence source; create radio-news-specific blocking CI in phase 1.0 | exact radio-news jobs and provenance-schema validation not implemented |
| CI-02 | Disabled daily summary workflow | `.github/workflows/daily-summary.yml.disabled` | `LEGACY` | disabled by filename | no active run evidence | LOW | `NEEDS_REVIEW` | likely reference only | cannot classify as operational workflow |
| TEST-01 | Core/source/processing tests | `tests/` | `ACTIVE_TEST_ONLY` | 483-test integration suite passed | run `30803855113` | HIGH | `NEEDS_REVIEW` | transfer or replace tests component-by-component | exact minimal equivalence suite for first vertical slice not selected |
| TEST-SEC | Security regression suite | `tests/test_url_security.py`, relevant webhook tests | `ACTIVE_TEST_ONLY` | deterministic transport boundary | successful blocking runs | CRITICAL | `NEEDS_REVIEW` | must accompany any SSRF transfer/adaptation | target dependency versions and all outbound callers not classified |
| DOC-01 | Runtime/config/profile/scraper docs | `README.md`, `docs/configuration.md`, `docs/profiles.md`, `docs/scrapers.md`, `docs/extractors.md` | `ACTIVE_DEV_ONLY` | describes public usage; linked to code/config | publication workflow | LOW | `NEEDS_REVIEW` | preserve as reference; rewrite for radio-news boundaries | docs may describe Horizon product behavior outside target scope |
| DOC-02 | Governance/security policy | `SECURITY.md`, `CODE_OF_CONDUCT.md` | `ACTIVE_DEV_ONLY` | repository governance | publication hygiene | LOW | `NEEDS_REVIEW` | repository-level policy decision outside extraction | ownership/reporting process for radio-news not reviewed |
| DOCKER-01 | Container path | `Dockerfile`, `docker-compose.yml` | `UNKNOWN` | tracked, but audit report says Docker release path is not verified/official | no accepted Docker release evidence | MEDIUM | `NEEDS_REVIEW` | defer | build/runtime equivalence not established |
| ASSET-01 | Screenshots/site/demo assets | `docs/assets/` and site files | `ACTIVE_DEV_ONLY` | README/site presentation | publication workflow inventories files | LOW | `NEEDS_REVIEW` | likely reject or defer | no runtime dependency established |

## Security boundary map

The security boundary is split into distinct zones. They must not be collapsed into a generic “HTTP client” component.

### Zone A — verified pre-send webhook transport

```text
WebhookNotifier.notify
→ safe_request
→ URL syntax validation
→ DNS resolution
→ require every answer to be public
→ deterministic validated IP selection
→ one-use pinned HTTPX/httpcore transport
→ TLS/Host/SNI preserved for original hostname
→ peer verification
→ response-size bound
→ redirect revalidation and repinning
```

Paths:

```text
src/services/webhook.py
src/url_security.py
```

Risk: `CRITICAL`.

Decision: `NEEDS_REVIEW`.

### Zone B — collector and extractor HTTP

Confirmed RSS path:

```text
src/orchestrator.py
→ shared httpx.AsyncClient
→ src/scrapers/rss.py
→ client.get(feed_url, follow_redirects=True)
→ optional extractor
```

No invocation of `safe_request` is present in the audited RSS collector path.

Risk: `CRITICAL` until the target trust model is defined.

Decision: `NEEDS_REVIEW`.

### Zone C — AI/provider SDK networking

Paths begin under:

```text
src/ai/client.py
src/ai/provider modules
```

These use provider SDKs or compatible HTTP endpoints. The pinned webhook transport is not proven to wrap them.

Risk: `HIGH`.

Decision: `NEEDS_REVIEW`.

### Zone D — email and other protocols

```text
src/services/email.py
```

SMTP/IMAP has a different threat and credential boundary. It must not be included in the HTTP SSRF transfer by assumption.

Risk: `HIGH`.

Decision: `NEEDS_REVIEW`.

## First vertical slice relevance

Only the following audited components are directly relevant to the first independent radio-news slice:

```text
RSS-01              RSS parsing and source identity behavior
MODEL-01            evidence for existing item fields, not direct domain transfer
CONFIG-01 / REG-01  source/config contracts
STORE-01            config/atomic-write behavior; not target SQLite persistence
FILE-01             safe fixture/file handling
HTTP-GAP / SSRF-01  source network threat-model decision
TEST-01             RSS/config/storage tests to select or replace
```

The following are explicitly not prerequisites for the first slice and remain classified without implementation:

```text
AI classification and analysis
AI structured-output repair
AI enrichment and tools
processing profiles beyond source/config compatibility questions
MCP
email
webhook delivery
GitHub Pages
setup wizard
other collectors
personas
Chief News Editor
Radio Writer
Rundown
Web UI
```

This relevance filter does not equal `DEFER` or `REJECT`; formal migration decisions remain `NEEDS_REVIEW` until phase 0.7.

## Evidence gaps requiring review

### G-01 — actual production configuration

```text
Usage Status: UNKNOWN for deployment-specific activation
Migration Decision: NEEDS_REVIEW
Evidence Gap: private data/config.json and runtime traces were not available
```

Affected components:

- exact enabled sources;
- email/webhook activation;
- AI provider/model;
- external locale directory;
- profile overrides;
- optional dependencies.

### G-02 — exact pinned-SHA CI

```text
Usage Status: ACTIVE_DEV_ONLY
Migration Decision: NEEDS_REVIEW
Evidence Gap: no separate workflow run is exposed for fd28db14...; successful final-head/test-merge evidence is tree-equivalent, not exact-commit execution
```

### G-03 — universal outbound security

```text
Usage Status: UNKNOWN as a repository-wide invariant
Migration Decision: NEEDS_REVIEW
Evidence Gap: safe_request is proven for webhook delivery, not all collectors/extractors/tools/providers
```

### G-04 — live integrations

```text
Usage Status: UNKNOWN for live environment behavior
Migration Decision: NEEDS_REVIEW
Evidence Gap: SMTP/IMAP, external webhook, paid AI calls, and Docker release path were not verified
```

### G-05 — target domain equivalence

```text
Usage Status: ACTIVE_RUNTIME for Horizon ContentItem/stages
Migration Decision: NEEDS_REVIEW
Evidence Gap: no approved field/state mapping to RawItem, NormalizedItem, Story, Claim, Fact, VerificationResult
```

### G-06 — SQLite replacement

```text
Usage Status: UNKNOWN in Horizon because no SQLite implementation was found
Migration Decision: NEEDS_REVIEW
Evidence Gap: target schema, migrations, uniqueness constraints, and restart tests have not been designed
```

### G-07 — Russian locale activation and quality

```text
Usage Status: ACTIVE_RUNTIME for built-in Russian rendering; UNKNOWN for data/locales/ru.json production activation
Migration Decision: NEEDS_REVIEW
Evidence Gap: no live provider-generated Russian editorial artifact was accepted by a human in this audit
```

## Preliminary risk concentration

```text
CRITICAL
- pinned SSRF transport and its exact dependency/test boundary
- non-webhook outbound HTTP threat model
- security regression tests

HIGH
- package namespace/build contract
- orchestrator
- ContentItem/domain mapping
- config schema
- file storage to SQLite replacement
- profile loader and prompts
- AI processing and structured-output repair
- localization contract
- MCP staged service
- live delivery/provider integrations

MEDIUM
- RSS collector implementation details
- individual non-core collectors
- extractors
- file utilities
- rendering/output adapters

LOW
- console presentation
- disabled workflow
- presentation assets
- governance/docs as migration components
```

## Provisional conclusion

The component map identifies a reusable evidence base but does not identify a safely copyable “Horizon Core” as one unit.

The smallest migration-relevant boundary for the first vertical slice is:

```text
source/config identity
+ RSS parsing behavior
+ raw provenance requirements
+ deterministic duplicate identity
+ persistence replacement contract
+ source-network security decision
+ selected regression tests
```

Everything else remains outside the first implementation slice or requires a separate phase 0.7 decision.

## Phase 0.5 completion status

```text
COMPONENTS CLASSIFIED: YES, at component level
SOURCE PATHS PINNED: YES
USAGE EVIDENCE RECORDED: YES
SECURITY BOUNDARY SEPARATED: YES
LOCAL FORK DELTA IDENTIFIED: YES
EVIDENCE GAPS PRESERVED: YES
FINAL TRANSFER DECISIONS MADE: NO
CODE EXTRACTION AUTHORIZED: NO
```
