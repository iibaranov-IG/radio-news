# Horizon Migration Audit — component inventory

## Audit identity

```text
PHASE: 0.5 HORIZON MIGRATION AUDIT
MODE: READ-ONLY
SOURCE REPOSITORY: iibaranov-IG/Horizon
PINNED SOURCE SHA: fd28db14c506ce23bdc0727ed2da4ff318aced32
UPSTREAM REFERENCE: Thysrael/Horizon
UPSTREAM COMMON BASE SHA: f37ec60a14b3cc5f0f73535b66ed822acef82056
TARGET REPOSITORY: iibaranov-IG/radio-news
AUDIT BRANCH: audit/horizon-migration-0.5
RADIO-NEWS BASE SHA: 071ea2bfdb0317706fd31c0a09fb19f156c36a9a
```

All findings below refer to the pinned Horizon commit unless another SHA is stated explicitly. The source commit is immutable for this audit. No Horizon code was changed, copied, reformatted, or executed by this documentation branch.

## Evidence method

A usage classification is assigned only when at least one of the following was found:

- a declared package or console-script entrypoint;
- a direct import from a runtime entrypoint or orchestrator;
- a configuration model or tracked configuration example that activates the component;
- an associated test module;
- a GitHub Actions workflow that invokes the component or its test boundary;
- an existing audit report tied to a commit or workflow run.

Absence of evidence is recorded as `UNKNOWN`; it is not interpreted as dead code. Migration decisions remain preliminary and are recorded in `horizon-component-map.md`.

## Repository and package structure

The build declares one installable Python distribution named `horizon`, version `0.1.0`, requiring Python `>=3.11`. The wheel package namespace is literally `src`, and tracked profiles are force-included into the wheel as `src/_builtin_profiles`.

Evidence:

- `pyproject.toml@fd28db14c506ce23bdc0727ed2da4ff318aced32`

Migration-relevant structure:

```text
Horizon/
├── .github/
│   └── workflows/
│       ├── public-release-audit.yml
│       └── daily-summary.yml.disabled
├── data/
│   ├── config.example.json
│   ├── config.github.json
│   └── locales/
│       └── ru.json
├── docs/
│   ├── audits/
│   │   ├── public-release-audit-contract.md
│   │   └── public-release-blockers.md
│   ├── security/
│   │   └── pre_send_ssrf_design.md
│   ├── configuration.md
│   ├── profiles.md
│   ├── scrapers.md
│   └── extractors.md
├── profiles/
│   ├── tech-news/
│   │   ├── profile.json
│   │   ├── match.md
│   │   ├── analysis.md
│   │   └── enrichment.md
│   └── tech-blog/
│       ├── profile.json
│       ├── match.md
│       ├── analysis.md
│       └── enrichment.md
├── src/
│   ├── ai/
│   ├── extractors/
│   ├── mcp/
│   ├── processing/
│   ├── scrapers/
│   ├── services/
│   ├── setup/
│   ├── storage/
│   ├── main.py
│   ├── models.py
│   ├── orchestrator.py
│   ├── url_security.py
│   ├── _file_utils.py
│   ├── _cli.py
│   ├── logging_config.py
│   └── console_icons.py
├── tests/
├── pyproject.toml
├── README.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── Dockerfile
├── docker-compose.yml
└── uv.lock
```

The tree above is a component-level inventory. Generated runtime files such as `data/config.json`, `seen.json`, subscriber lists, databases, logs, credentials, and build artifacts are intentionally not tracked; the publication workflow explicitly checks for forbidden tracked runtime/private filenames.

## Declared entrypoints

| Command | Python target | Usage status | Evidence |
|---|---|---|---|
| `horizon` | `src.main:main` | `ACTIVE_RUNTIME` | declared in `pyproject.toml`; loads config/storage and runs `HorizonOrchestrator` |
| `horizon-mcp` | `src.mcp.server:main` | `ACTIVE_RUNTIME` | declared in `pyproject.toml`; exposes staged pipeline tools through FastMCP |
| `horizon-wizard` | `src.setup.wizard_cli:main` | `ACTIVE_RUNTIME` | declared console script; package smoke test runs `--help` |
| `horizon-webhook` | `src.services.webhook_cli:main` | `ACTIVE_RUNTIME` | declared console script; package smoke test runs `--help` |
| `horizon-locales` | `src.services.locales_cli:main` | `ACTIVE_RUNTIME` | declared console script; validates locale/profile contracts without fetching or AI calls |

Evidence paths:

- `pyproject.toml`
- `src/main.py`
- `src/mcp/server.py`
- `src/setup/wizard_cli.py`
- `src/services/webhook_cli.py`
- `src/services/locales_cli.py`
- `.github/workflows/public-release-audit.yml`

## Runtime composition

`src/main.py` performs the primary runtime assembly:

1. loads environment variables;
2. creates `StorageManager`;
3. loads and validates `Config`;
4. creates `HorizonOrchestrator` with profile resolution relative to the configuration file;
5. runs the asynchronous pipeline.

`src/orchestrator.py` is the central runtime coordinator. It imports all collector implementations, storage, profile registry, AI client/analyzer/enricher/summarizer, email delivery, and webhook delivery. Its observed top-level sequence is:

```text
fetch configured sources
→ merge cross-source URL duplicates
→ AI classify/analyze
→ profile filtering and topic/digest selection
→ enrichment and tool execution
→ localized Markdown rendering
→ file/GitHub Pages output
→ optional email delivery
→ optional webhook delivery
```

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/main.py`
- `src/orchestrator.py`
- `tests/test_fetch_reporting.py`
- `tests/test_cross_source_duplicates.py`
- `tests/test_balanced_digest.py`
- `tests/test_content_selection.py`

## Core models and configuration contracts

### Unified content model

`src/models.py` defines `ContentItem` as Horizon's common item representation:

```text
id
source_type
title
url
content
author
published_at
fetched_at
metadata
profile
processing
```

`ProcessingResult` contains classification, optional analysis, and localized artifacts. This model is actively consumed by collectors, the orchestrator, AI processing, MCP serialization, storage, rendering, email, and webhook output.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/models.py`
- `src/orchestrator.py`
- `src/mcp/horizon_adapter.py`
- `src/mcp/service.py`
- `src/ai/analyzer.py`
- `src/ai/enricher.py`
- `src/ai/summarizer.py`

Important boundary finding: `ContentItem` is not equivalent to the planned `radio-news` chain `RawItem → NormalizedItem → Story → Claim → Fact`. Horizon combines source payload, normalized fields, analysis, and enriched artifacts in one aggregate. Reuse cannot be assumed from the class name alone.

### Source registry and source config

`src/models.py` defines `SourceType`, `SOURCE_REGISTRY`, and configuration models for:

- GitHub;
- Hacker News;
- RSS;
- Reddit;
- Telegram;
- Twitter/X;
- OpenBB;
- OSS Insight;
- GDELT;
- Google News.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/models.py`
- `src/orchestrator.py`
- `data/config.example.json`
- `tests/test_category_wiring.py`

### General config

The main `Config` contract contains:

- AI provider/model/languages/locales;
- source definitions;
- collection window;
- digest limits and category groups;
- processing profile directory/default profile;
- display settings;
- extractor definitions;
- optional email;
- optional webhook.

Pydantic models use `extra="forbid"` on principal contracts, so unknown configuration fields fail validation rather than being ignored.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/models.py`
- `src/storage/manager.py`
- `data/config.example.json`
- `data/config.github.json`
- `tests/test_storage.py`
- `tests/test_main.py`

## Collectors

All collectors implement or derive from the scraper boundary and return `ContentItem` objects. They are directly imported by `src/orchestrator.py`; execution is configuration-gated.

| Component | Exact path | Runtime evidence | Tests found | Usage status |
|---|---|---|---|---|
| Base scraper contract | `src/scrapers/base.py` | inherited by source scrapers | source-specific tests | `ACTIVE_RUNTIME` |
| RSS/Atom | `src/scrapers/rss.py` | instantiated when `config.sources.rss` is non-empty | `tests/test_rss.py` | `ACTIVE_RUNTIME` |
| Hacker News | `src/scrapers/hackernews.py` | imported and instantiated by orchestrator | source and selection tests | `ACTIVE_RUNTIME` |
| GitHub | `src/scrapers/github.py` | imported and instantiated by orchestrator | source/config tests | `ACTIVE_RUNTIME` |
| Reddit | `src/scrapers/reddit.py` | imported and instantiated by orchestrator | `tests/test_reddit.py` | `ACTIVE_RUNTIME` |
| Telegram | `src/scrapers/telegram.py` | imported and instantiated by orchestrator | `tests/test_telegram.py` | `ACTIVE_RUNTIME` |
| Twitter API/actor mode | `src/scrapers/twitter.py` | imported and selected by Twitter config | `tests/test_twitter.py` | `ACTIVE_RUNTIME` |
| Twitter Playwright mode | `src/scrapers/twitter_playwright.py` | imported and selected by Twitter mode | `tests/test_twitter.py` | `ACTIVE_RUNTIME` |
| OpenBB | `src/scrapers/openbb.py` | optional config and optional package extra | `tests/test_openbb_scraper.py` | `ACTIVE_RUNTIME` |
| OSS Insight | `src/scrapers/ossinsight.py` | imported; disabled by default in model/example | source/config tests not independently confirmed | `ACTIVE_RUNTIME` |
| GDELT | `src/scrapers/gdelt.py` | optional config path | `tests/test_gdelt.py` | `ACTIVE_RUNTIME` |
| Google News | `src/scrapers/google_news.py` | optional config path | `tests/test_google_news.py` | `ACTIVE_RUNTIME` |

### RSS collector details

`src/scrapers/rss.py`:

- uses a shared `httpx.AsyncClient` and `feedparser`;
- follows redirects;
- can expand environment variables in feed URLs;
- filters by publication time;
- creates an item ID from the feed URL plus a truncated SHA-256 hash of the entry ID/link;
- emits `ContentItem` with feed/category/tag metadata;
- optionally invokes an extractor selected by `content_extractor`.

Dependencies:

- `httpx`;
- `feedparser`;
- `src.scrapers.base`;
- `src.models`;
- optional `src.extractors.ExtractorRegistry`.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/scrapers/rss.py`
- `src/orchestrator.py`
- `src/models.py`
- `data/config.example.json`
- `tests/test_rss.py`
- `tests/test_extractors_registry.py`
- `tests/test_extractors_trafilatura.py`

Evidence gap: the current RSS path calls the ordinary shared HTTPX client directly with redirects enabled. The audited pinned SSRF transport is invoked by webhook delivery, not by this RSS request path. This does not by itself establish an exploitable defect because the collector threat model and trust level of source configuration were not documented for this migration audit. It does establish that SSRF protections cannot be assumed to cover all outbound HTTP calls.

## Extractors

The extractor subsystem is under `src/extractors/` and includes:

- a base extractor contract;
- an extractor registry;
- a Trafilatura implementation.

`RSSSourceConfig.content_extractor` selects an extractor by name. `data/config.example.json` includes an RSS example using `trafilatura`. `trafilatura` is a required base dependency at the pinned SHA, despite the older design having treated it as optional.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/extractors/`
- `src/models.py`
- `src/scrapers/rss.py`
- `data/config.example.json`
- `pyproject.toml`
- `tests/test_extractors_registry.py`
- `tests/test_extractors_trafilatura.py`

## Processing profiles

### Loader and schema

`src/processing/profiles.py` defines validated profile contracts and `ProfileRegistry`.

Observed behavior:

- loads `*/profile.json` below the configured profile root;
- reads separate Markdown prompts;
- rejects duplicate IDs;
- prevents prompt paths from escaping the profile directory;
- validates explicit source profile references;
- validates localized profile names in strict production locale mode;
- falls back to built-in profiles packaged at `src/_builtin_profiles` when the default `profiles` directory is unavailable.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/processing/profiles.py`
- `src/main.py`
- `src/orchestrator.py`
- `src/mcp/service.py`
- `tests/test_profiles.py`

### Tracked profiles

`profiles/tech-news/profile.json` defines:

- filter threshold `8.0`;
- localized display names including Russian;
- required `summary` block;
- optional `background` block with `web_search`;
- optional `community_discussion` block.

`profiles/tech-blog/profile.json` is a separate profile with its own match, analysis, enrichment, filter, content, and deduplication behavior.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `profiles/tech-news/`
- `profiles/tech-blog/`
- `tests/test_profiles.py`

## AI processing runtime

| Component | Exact path | Purpose | Usage status |
|---|---|---|---|
| Provider abstraction/factory | `src/ai/client.py` and provider modules under `src/ai/` | create configured AI client/provider chain | `ACTIVE_RUNTIME` |
| Classification | `src/ai/classifier.py` | resolve source override or AI profile match | `ACTIVE_RUNTIME` |
| First-pass analysis | `src/ai/analyzer.py` | score/reason/summary/tags under profile contract | `ACTIVE_RUNTIME` |
| Enrichment | `src/ai/enricher.py` | profile-defined localized artifacts and tools | `ACTIVE_RUNTIME` |
| Rendering | `src/ai/summarizer.py` | deterministic localized Markdown/webhook rendering | `ACTIVE_RUNTIME` |
| Token accounting | `src/ai/tokens.py` | provider usage snapshot | `ACTIVE_RUNTIME` |
| Prompt builders | `src/ai/prompting/` | system/user contracts for AI stages | `ACTIVE_RUNTIME` |
| AI response parser | `src/ai/utils.py` | extract JSON from model responses | `ACTIVE_RUNTIME` |
| Tools | `src/processing/tools.py` | profile-scoped enrichment tool registry | `ACTIVE_RUNTIME` |

### Structured-output repair

Structured-output repair is implemented as a bounded second model call, not only as local JSON cleanup:

- `ContentAnalyzer` parses and validates the first response; on failure it calls the model once more at temperature `0` with the validation reason and then falls back to a default analysis if still invalid.
- `ContentEnricher._complete_model` validates against Pydantic models, performs one corrective model call at temperature `0`, and raises if the contract still fails.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/ai/analyzer.py`
- `src/ai/enricher.py`
- `src/ai/utils.py`
- `tests/test_analyzer.py`
- `tests/test_enricher.py`

Important boundary finding: repair behavior depends on AI client semantics, Pydantic schemas, prompts, and retry policy. It is not a standalone utility that can be transferred safely without its surrounding contracts.

## Storage and persistence

### Primary storage manager

`src/storage/manager.py` is file-based. It manages:

- JSON configuration loading/validation;
- recursive `${ENV_VAR}` expansion;
- external locale JSON loading relative to the config file;
- configuration save/backup;
- Markdown daily summaries;
- subscriber JSON;
- safe output paths;
- atomic text writes through `src/_file_utils.py`.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/storage/manager.py`
- `src/_file_utils.py`
- `src/main.py`
- `src/orchestrator.py`
- `tests/test_storage.py`

### MCP staged run store

`src/mcp/run_store.py` stores per-run stages as JSON and summaries as Markdown:

```text
raw_items.json
scored_items.json
filtered_items.json
enriched_items.json
meta.json
summary-<language>.md
```

It validates run IDs/language names, uses atomic writes, and invalidates downstream artifacts when an upstream stage changes.

Usage status: `ACTIVE_RUNTIME` through `horizon-mcp`.

Evidence:

- `src/mcp/run_store.py`
- `src/mcp/service.py`
- `src/mcp/server.py`
- `tests/test_mcp_run_store.py`
- `tests/test_mcp_service_smoke.py`

### SQLite finding

No SQLite persistence contract is present in the audited Horizon runtime. The inspected storage paths are JSON/Markdown filesystem stores. Therefore SQLite persistence for the first `radio-news` vertical slice is a new target requirement, not an as-is Horizon transfer.

## Localization

Localization spans several layers:

- locale config and validation in `src/models.py`;
- external locale file loading in `src/storage/manager.py`;
- profile display-name validation in `src/processing/profiles.py`;
- deterministic localized rendering and Russian plural/date logic in `src/ai/summarizer.py`;
- configuration-only validation through `src/services/locales_cli.py`;
- tracked Russian locale data at `data/locales/ru.json`;
- Russian profile display names in tracked profile definitions;
- webhook localized titles in `src/services/webhook.py`.

Usage status by subcomponent:

| Subcomponent | Usage status | Evidence |
|---|---|---|
| Built-in Russian rendering rules | `ACTIVE_RUNTIME` | imported by normal summary/webhook rendering |
| Locale model and loader | `ACTIVE_RUNTIME` | config loading path and `horizon-locales` entrypoint |
| `horizon-locales` CLI | `ACTIVE_RUNTIME` | declared console script and package smoke test |
| `data/locales/ru.json` | `UNKNOWN` | tracked and loadable, but no tracked production `config.json` proves `locales_dir` activation |
| Russian profile display names | `ACTIVE_RUNTIME` | strict locale/profile validation and profile rendering |

Evidence gap: live production output in Russian was not executed during this migration audit. Existing unit/CI evidence validates contracts; it does not prove an external AI provider produced acceptable Russian artifacts.

## MCP interface

The MCP subsystem is a second public execution surface, not only a thin wrapper around the main CLI.

`src/mcp/server.py` exposes tools including:

- validate config;
- fetch items;
- score items;
- filter items;
- enrich items;
- generate summary;
- run the complete pipeline;
- list/read run artifacts and metadata.

`src/mcp/service.py` composes the same runtime through adapter functions and persists explicit stages through `RunStore`.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/mcp/server.py`
- `src/mcp/service.py`
- `src/mcp/horizon_adapter.py`
- `src/mcp/run_store.py`
- `src/mcp/errors.py`
- `tests/test_mcp_adapter.py`
- `tests/test_mcp_errors.py`
- `tests/test_mcp_run_store.py`
- `tests/test_mcp_service_smoke.py`
- `pyproject.toml`

Migration relevance: MCP provides useful evidence about stage boundaries (`raw`, `scored`, `filtered`, `enriched`) but those stages are Horizon-specific JSON snapshots and are not equivalent to the planned `radio-news` domain model.

## Delivery and output

### Markdown and GitHub Pages

`src/orchestrator.py` saves localized Markdown through `StorageManager` and also writes Jekyll posts under `docs/_posts`.

Usage status: `ACTIVE_RUNTIME`.

Evidence:

- `src/orchestrator.py`
- `src/storage/manager.py`

### Email

`src/services/email.py` manages SMTP delivery and optional IMAP subscription processing.

Usage status: `ACTIVE_RUNTIME` when enabled by config.

Evidence:

- `src/services/email.py`
- `src/orchestrator.py`
- `src/models.py`
- `tests/test_email.py`

Evidence gap: live SMTP/IMAP delivery is explicitly recorded as `NOT VERIFIED` in `docs/audits/public-release-blockers.md`.

### Webhook

`src/services/webhook.py` handles generic and platform-specific webhook rendering, redaction, dry-run preview, status classification, and actual delivery.

Usage status: `ACTIVE_RUNTIME` when enabled by config.

Evidence:

- `src/services/webhook.py`
- `src/services/webhook_cli.py`
- `src/orchestrator.py`
- `src/models.py`
- `tests/test_webhook.py`

Evidence gap: live delivery to an approved external webhook endpoint is explicitly `NOT VERIFIED`. Unit and transport-boundary evidence is available.

## Security boundary

### SSRF-safe webhook transport

The audited security implementation is concentrated in:

- `src/url_security.py`;
- `src/services/webhook.py`;
- `tests/test_url_security.py`;
- `tests/test_webhook.py`;
- `docs/security/pre_send_ssrf_design.md`;
- `docs/audits/public-release-blockers.md`;
- pinned dependency `httpcore==1.0.9` in `pyproject.toml`.

`safe_request` performs:

1. HTTP/HTTPS URL syntax validation;
2. rejection of embedded credentials and localhost names;
3. DNS resolution;
4. rejection if any resolved address is non-public;
5. deterministic selection of a validated public address;
6. one-use HTTPX/httpcore transport pinned to that address;
7. preservation of original hostname for HTTP authority, TLS SNI, and certificate validation;
8. connected-peer verification;
9. bounded response size;
10. per-hop redirect revalidation and repinning;
11. fail-closed behavior without fallback to ordinary hostname transport.

`WebhookNotifier.notify` calls `safe_request` for both GET and POST delivery.

Usage status: `ACTIVE_RUNTIME`.

Migration risk: `CRITICAL`.

### Security tests

`tests/test_url_security.py` covers, among other cases:

- private, loopback, link-local, multicast, reserved, unspecified, and documentation ranges;
- mixed public/private DNS answers;
- redirect validation before the next connection;
- connected-peer verification;
- pinned TCP destination;
- preserved SNI, certificate checks, and Host header;
- request write ordering after TLS;
- public redirect repinning;
- no fallback after pinned transport failure;
- response-size bounds.

### Security boundary gap

The evidence proves the pinned transport boundary for webhook requests. It does not prove that every Horizon outbound HTTP caller uses `safe_request`. The RSS collector, for example, directly uses the shared HTTPX client with redirects enabled. Other collectors, web-search tools, extractors, AI provider clients, and update/delivery paths require separate threat-model classification before reuse.

No migration decision is made from this observation. The gap is carried forward as `NEEDS_REVIEW`.

## Tests

The repository test suite is under `tests/` and includes coverage for:

- source collectors;
- category/source wiring;
- AI providers, classifier, analyzer, enricher, prompting, structured output, and summarizer;
- profile loading and validation;
- storage and path safety;
- cross-source deduplication, fetch reporting, digest balancing, and content selection;
- email and webhook behavior;
- URL/SSRF security;
- MCP adapter/service/run-store/error behavior;
- setup wizard and console-script parser behavior;
- extractors and optional integrations.

Locally added or materially modified test files after the upstream common base include:

```text
tests/test_chained_client.py
tests/test_cli_parsers.py
tests/test_extractors_trafilatura.py
tests/test_mcp_adapter.py
tests/test_mcp_service_smoke.py
tests/test_profiles.py
tests/test_storage.py
tests/test_summarizer.py
tests/test_url_security.py
tests/test_webhook.py
tests/test_wizard_cli.py
```

Usage status: `ACTIVE_TEST_ONLY` as a component group; individual tests provide evidence for their associated runtime components.

## CI and workflows

### Blocking public-release audit

`.github/workflows/public-release-audit.yml` contains three blocking jobs:

- full test suite;
- wheel/sdist build and clean wheel installation;
- publication hygiene scan.

The package job also verifies import outside the checkout, all five declared console-script `--help` commands, and `pip check`.

Usage status: `ACTIVE_DEV_ONLY`.

### Disabled daily workflow

`.github/workflows/daily-summary.yml.disabled` contains a scheduled/manual pipeline and Pages deployment definition but is disabled by filename.

Usage status: `LEGACY`.

Evidence gap: it uses Python 3.12 and `uv`, but it is not an active workflow at the pinned SHA. Its behavior is not accepted as runtime evidence.

## Documentation and governance

Migration-relevant documentation includes:

- `README.md`;
- `docs/configuration.md`;
- `docs/profiles.md`;
- `docs/scrapers.md`;
- `docs/extractors.md`;
- `docs/audits/public-release-audit-contract.md`;
- `docs/audits/public-release-blockers.md`;
- `docs/security/pre_send_ssrf_design.md`;
- `SECURITY.md`;
- `CODE_OF_CONDUCT.md`.

Usage status: `ACTIVE_DEV_ONLY`.

Documentation is supporting evidence, not sufficient proof of runtime behavior when it conflicts with code or tests.

## Dependencies

### Required runtime dependencies

From `pyproject.toml`:

```text
httpx>=0.27.0
httpcore==1.0.9
feedparser>=6.0.11
anthropic>=0.39.0
openai>=1.54.0
google-genai>=0.3.0
pydantic>=2.9.0
python-dateutil>=2.9.0
rich>=13.9.0
tenacity>=9.0.0
python-dotenv>=1.0.0
ddgs>=7.0.0
beautifulsoup4>=4.12.0
markdown>=3.10.2
mcp>=1.0.0,<2.0.0
trafilatura>=2.1.0
```

### Optional dependency groups

```text
dev: pytest, pytest-cov
openbb: openbb, openbb-benzinga
twitter: playwright, playwright-stealth
```

Dependency risk observations:

- `httpcore==1.0.9` is pinned as part of the verified transport boundary; an upgrade requires rerunning transport-level tests.
- AI SDK lower bounds do not cap major versions, so behavior must be captured by lock/evidence rather than inferred from `pyproject.toml` alone.
- the wheel exposes the unusual package namespace `src`; this is part of the current public package contract.
- optional source integrations expand the dependency and credential surface.

## Local changes relative to `Thysrael/Horizon`

The fork's pinned commit is 23 commits ahead and 0 behind the common upstream base `f37ec60a14b3cc5f0f73535b66ed822acef82056`.

Changed files are grouped below.

### CI, audit, security, governance

```text
.github/workflows/public-release-audit.yml
CODE_OF_CONDUCT.md
SECURITY.md
docs/audits/public-release-audit-contract.md
docs/audits/public-release-blockers.md
docs/security/pre_send_ssrf_design.md
src/url_security.py
src/services/webhook.py
src/services/webhook_cli.py
tests/test_url_security.py
tests/test_webhook.py
```

### Localization and config path behavior

```text
data/config.example.json
data/config.github.json
data/locales/ru.json
docs/configuration.md
README.md
src/models.py
src/storage/manager.py
src/services/locales_cli.py
src/ai/summarizer.py
src/main.py
src/mcp/horizon_adapter.py
src/mcp/service.py
tests/test_storage.py
tests/test_summarizer.py
tests/test_mcp_adapter.py
tests/test_mcp_service_smoke.py
```

### Profiles and processing

```text
profiles/tech-blog/profile.json
profiles/tech-news/profile.json
docs/profiles.md
src/processing/profiles.py
src/ai/client.py
src/ai/summarizer.py
src/orchestrator.py
tests/test_chained_client.py
tests/test_profiles.py
```

### Packaging and CLI acceptance

```text
pyproject.toml
src/setup/wizard_cli.py
src/services/locales_cli.py
tests/test_cli_parsers.py
tests/test_wizard_cli.py
tests/test_extractors_trafilatura.py
```

The local diff is not a single feature patch. It combines release-audit infrastructure, security transport changes, localization, profile/runtime behavior, packaging, CLI behavior, and tests. Provenance must therefore be tracked per component rather than assigning the merge SHA as a single undifferentiated origin.

## Components not proven by this audit

The following remain evidence gaps, not negative findings:

```text
Live SMTP/IMAP behavior: NOT VERIFIED
Live external webhook delivery: NOT VERIFIED
Paid AI-provider calls: NOT VERIFIED
Docker release path: NOT VERIFIED
Actual private production config and enabled source set: NOT AVAILABLE
Actual use of data/locales/ru.json through locales_dir: UNKNOWN
Runtime use of every optional collector: CONFIGURATION-DEPENDENT
Security coverage of all non-webhook outbound HTTP paths: NOT ESTABLISHED
Exact-SHA CI execution on fd28db14...: NOT PRESENT; tree-equivalent final PR head evidence exists
```

## Inventory conclusion

The active Horizon core is not one directory. It is a coupled runtime composed of:

```text
Pydantic config and ContentItem contracts
+ source collectors and extractors
+ central orchestrator
+ profile registry and prompt files
+ AI classification/analysis/enrichment/repair
+ file-based storage and MCP staged storage
+ deterministic localization/rendering
+ delivery interfaces
+ webhook-specific SSRF transport
+ package entrypoints and CI regression gates
```

The inventory does not authorize transfer. It establishes the factual component boundary used by `horizon-component-map.md` and the reproducibility evidence recorded in `horizon-baseline.md`.
