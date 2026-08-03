# Horizon Migration Audit — reproducible baseline

## Baseline identity

```text
SOURCE REPOSITORY: iibaranov-IG/Horizon
PINNED AUDIT SHA: fd28db14c506ce23bdc0727ed2da4ff318aced32
PINNED COMMIT MESSAGE: Merge public release audit and blocker remediation
DEFAULT BRANCH: main
UPSTREAM REFERENCE: Thysrael/Horizon
COMMON UPSTREAM BASE: f37ec60a14b3cc5f0f73535b66ed822acef82056
FORK DISTANCE FROM COMMON BASE: ahead 23, behind 0
AUDIT MODE: REMOTE READ-ONLY
```

The pinned SHA is the only source revision used for component classification. A later Horizon commit does not update this baseline automatically.

## Baseline verdict

```text
SOURCE SHA EXISTS: PASS
SOURCE TREE IMMUTABLE: PASS
PACKAGE METADATA READABLE: PASS
PYTHON CONTRACT IDENTIFIED: PASS
DEPENDENCY CONTRACT IDENTIFIED: PASS
CONSOLE ENTRYPOINTS IDENTIFIED: PASS
TEST SUITE EVIDENCE: PASS ON FINAL PR TEST MERGE SHA
PACKAGE BUILD/CLEAN INSTALL EVIDENCE: PASS ON FINAL PR TEST MERGE SHA
PUBLICATION HYGIENE EVIDENCE: PASS ON FINAL PR TEST MERGE SHA
FINAL PR HEAD WORKFLOW: SUCCESS
PINNED MERGE SHA FILE TREE VS FINAL PR HEAD: IDENTICAL
SEPARATE CI RUN ON PINNED MERGE SHA: NOT PRESENT
LIVE EXTERNAL INTEGRATIONS: PARTIALLY NOT VERIFIED
LOCAL WORKING TREE CLEANLINESS: NOT APPLICABLE TO REMOTE COMMIT AUDIT
```

The baseline is sufficient for a migration audit, but it must not be described as “CI passed on exact pinned SHA.” The exact pinned merge commit has no separate surfaced workflow run. The final PR head has a successful blocking run, and the merge commit contains no file changes relative to that head.

## Commit lineage and audit provenance

### Upstream common base

```text
f37ec60a14b3cc5f0f73535b66ed822acef82056
chore(profile): shorten the enrichment
repository: Thysrael/Horizon
```

The same commit exists in the fork history and is the merge base for the local public-release audit changes.

### Final audit branch head

```text
3e158ccf8bdb3f46c6bb2d2eb84bd64d4a2161db
ci(audit): run blocking checks on main
branch: audit/public-release-blockers
```

### Pinned merge commit

```text
fd28db14c506ce23bdc0727ed2da4ff318aced32
Merge public release audit and blocker remediation
```

Comparison result:

```text
base: 3e158ccf8bdb3f46c6bb2d2eb84bd64d4a2161db
head: fd28db14c506ce23bdc0727ed2da4ff318aced32
commits ahead: 1
changed files: 0
```

Therefore the pinned commit tree is file-identical to the final audit branch head, although the commit IDs differ.

## Package contract

Evidence: `pyproject.toml@fd28db14c506ce23bdc0727ed2da4ff318aced32`.

```text
project name: horizon
version: 0.1.0
requires Python: >=3.11
build backend: hatchling.build
wheel package: src
force-included profiles: profiles → src/_builtin_profiles
pytest test root: tests
```

### Console scripts

```text
horizon = src.main:main
horizon-mcp = src.mcp.server:main
horizon-wizard = src.setup.wizard_cli:main
horizon-webhook = src.services.webhook_cli:main
horizon-locales = src.services.locales_cli:main
```

The blocking package workflow invokes `--help` for all five scripts after installing the wheel in an isolated virtual environment and changing the working directory outside the checkout.

## Dependency contract

### Required dependencies declared in `pyproject.toml`

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

### Optional groups

```text
dev:
  pytest>=8.0.0
  pytest-cov>=5.0.0

openbb:
  openbb>=4.4.0
  openbb-benzinga>=1.6.0

twitter:
  playwright>=1.40.0
  playwright-stealth>=1.0.0
```

### Security-sensitive dependency pin

`httpcore==1.0.9` is an explicit exact pin. Existing audit documentation identifies it as a maintenance constraint for the pinned webhook transport. Any dependency update affecting HTTPX/httpcore must rerun the transport-boundary suite before migration equivalence is claimed.

## Blocking CI definition

Evidence: `.github/workflows/public-release-audit.yml` at the pinned SHA.

Workflow name:

```text
Public release audit
```

Triggers:

```text
push:
  audit/public-release-blockers
  main
pull_request:
  main
workflow_dispatch
```

Permissions:

```text
contents: read
```

### Job 1 — Full test suite

Environment and actions:

```text
runner: ubuntu-latest
Python: 3.11
install: pip install -e '.[dev]'
command: python -m pytest --durations=20
artifacts: environment.txt, pytest.txt
```

### Job 2 — Build and clean wheel install

Checks:

```text
python -m build
isolated virtual environment
install dist/*.whl
import src outside checkout
horizon --help
horizon-mcp --help
horizon-wizard --help
horizon-webhook --help
horizon-locales --help
pip check
wheel content inventory
```

### Job 3 — Publication hygiene scan

Checks:

```text
repository file inventory
changed-file inventory from upstream base
largest tracked files
rejection of tracked private/runtime filenames
```

Forbidden tracked filename patterns include runtime config, state, databases, logs, certificates, and private key formats.

## Final blocking workflow evidence

Workflow run:

```text
run ID: 30803855113
name: Public release audit
run number: 38
status: completed
conclusion: success
head branch: audit/public-release-blockers
head SHA reported by Actions API: 3e158ccf8bdb3f46c6bb2d2eb84bd64d4a2161db
```

Jobs:

```text
Full test suite: SUCCESS
Build and clean wheel install: SUCCESS
Publication hygiene scan: SUCCESS
```

All recorded steps in all three jobs completed successfully.

## Test artifact evidence

The test artifact from workflow run `30803855113` records:

```text
GITHUB_SHA inside pull_request job: 5d12e5f200f7e1d20aa3c3aad13ec74bc8ccb6fc
commit message: Merge 3e158cc... into f37ec60...
Python: 3.11.15
pip: 26.2
pytest result: 483 passed in 7.73s
```

The test SHA is GitHub's synthetic pull-request merge commit for the final branch head against base `f37ec60...`. This is valid pull-request integration evidence, but it is not the later repository merge SHA `fd28db14...`.

Observed installed versions in the test artifact include:

```text
httpx 0.28.1
httpcore 1.0.9
feedparser 6.0.14
anthropic 0.120.2
openai 2.52.0
google-genai 2.16.0
pydantic 2.13.4
mcp 1.29.0
trafilatura 2.2.0
pytest 9.1.1
```

This environment snapshot is evidence for that workflow run only. It does not replace the declared dependency contract or `uv.lock` analysis.

## Package artifact evidence

The same workflow run produced non-expired artifacts for:

- package build and clean install;
- complete test output and environment;
- publication hygiene.

The package job succeeded through:

- wheel and sdist build;
- isolated wheel install;
- import outside source checkout;
- all console-script smoke checks;
- `pip check`;
- package contents recording.

No wheel bytes are copied into `radio-news`; they are audit evidence only.

## Test coverage inventory

The passing suite includes test modules for the following migration-relevant boundaries:

### Runtime and orchestration

```text
tests/test_main.py
tests/test_fetch_reporting.py
tests/test_cross_source_duplicates.py
tests/test_balanced_digest.py
tests/test_content_selection.py
tests/test_category_wiring.py
```

### Collectors and extractors

```text
tests/test_rss.py
tests/test_reddit.py
tests/test_telegram.py
tests/test_twitter.py
tests/test_openbb_scraper.py
tests/test_gdelt.py
tests/test_google_news.py
tests/test_extractors_registry.py
tests/test_extractors_trafilatura.py
```

### AI processing and output contracts

```text
tests/test_classifier.py
tests/test_analyzer.py
tests/test_enricher.py
tests/test_prompting.py
tests/test_summarizer.py
tests/test_chained_client.py
tests/test_azure_client.py
tests/test_minimax_client.py
```

### Profiles, config, storage, localization

```text
tests/test_profiles.py
tests/test_storage.py
tests/test_cli_parsers.py
tests/test_wizard_cli.py
tests/test_setup_wizard.py
```

### Interfaces and delivery

```text
tests/test_email.py
tests/test_webhook.py
tests/test_mcp_adapter.py
tests/test_mcp_errors.py
tests/test_mcp_run_store.py
tests/test_mcp_service_smoke.py
```

### Security

```text
tests/test_url_security.py
```

The numeric result `483 passed` proves the suite state of the pull-request integration commit. This audit does not claim that every test maps one-to-one to a migration component; the component map references only tests relevant to each row.

## SSRF baseline

### Implementation paths

```text
src/url_security.py
src/services/webhook.py
pyproject.toml
```

### Evidence paths

```text
tests/test_url_security.py
tests/test_webhook.py
docs/security/pre_send_ssrf_design.md
docs/audits/public-release-blockers.md
.github/workflows/public-release-audit.yml
```

### Accepted security implementation lineage

Existing Horizon audit documentation identifies:

```text
7161d1379bd86780e35ecf1665d319b9b5d8950b
  fix(security): pin validated webhook connections

1a63b49eda4621fee1b7c17c23c657fb6cc173a6
  test(security): cover pinned connection backend

5a9c71ccb5fdb000bfa04ae93b9848e3434863b2
  fix(security): close pinned transport on connection failure

f963ce8f506194d39175c75599520556acb6af04
  test(security): prove pinned HTTPS request boundary

679e3aac9b80efbe5aca25b44801b53d3388145b
  test(security): normalize HTTP header assertion
```

The existing audit report also records successful run `30803212957` for accepted security implementation SHA `679e3aa...`. The later final branch run `30803855113` additionally passed the complete suite, build/install, and publication scan.

### Security properties covered by tests

```text
URL form validation
public-address requirement for every DNS answer
private/reserved/loopback/link-local rejection
DNS-to-TCP address pinning
original hostname retained as HTTP Host
original hostname retained as TLS SNI
certificate hostname verification enabled
request bytes written only after TLS start
peer address verification
response size bounds
redirect validation and repinning per hop
no fallback after pinned connection failure
resource closure on success/failure
```

### Boundary limitation

The proven transport is called by `WebhookNotifier.notify`. The audit found no evidence that it is a universal HTTP transport used by all collectors, extractors, search tools, or provider SDKs. `src/scrapers/rss.py` directly invokes the shared HTTPX client.

Baseline classification:

```text
WEBHOOK PRE-SEND SSRF BOUNDARY: VERIFIED BY UNIT/TRANSPORT TESTS
UNIVERSAL OUTBOUND HTTP BOUNDARY: NOT ESTABLISHED
MIGRATION RISK: CRITICAL
```

## Configuration baseline

Tracked configuration evidence:

```text
data/config.example.json
data/config.github.json
src/models.py
src/storage/manager.py
docs/configuration.md
```

The example config demonstrates:

- AI provider/model and concurrency;
- output languages and production locale mode;
- profiles relative to the configuration directory;
- source definitions and profile references;
- optional Trafilatura extraction;
- collection and digest settings;
- optional email;
- optional webhook template/platform/layout behavior.

The actual private production `data/config.json` is intentionally not tracked and was not available to this audit.

Consequences:

```text
actual enabled source set: UNKNOWN
actual AI provider/model: UNKNOWN
actual webhook endpoint/platform: UNKNOWN
actual email activation: UNKNOWN
actual locales_dir activation: UNKNOWN
actual production profile overrides: UNKNOWN
```

## Profiles baseline

Tracked profile roots:

```text
profiles/tech-news/
profiles/tech-blog/
```

The package build force-includes them as built-in profiles. The profile loader validates schema, prompt paths, source references, and output-language names. Tests cover package fallback and profile behavior.

The exact prompt text is part of runtime behavior and must be included in provenance if any profile is later extracted.

## Localization baseline

Evidence paths:

```text
src/models.py
src/storage/manager.py
src/processing/profiles.py
src/ai/summarizer.py
src/services/locales_cli.py
src/services/webhook.py
data/locales/ru.json
profiles/tech-news/profile.json
profiles/tech-blog/profile.json
tests/test_storage.py
tests/test_profiles.py
tests/test_summarizer.py
```

Verified by static and test evidence:

- language-tag validation;
- external locale JSON loading;
- inline locale override merging;
- production-mode completeness validation;
- profile display-name validation;
- Russian plural and date rendering rules;
- Russian webhook titles;
- locale-validation console entrypoint.

Not verified in this migration audit:

- live paid-provider Russian generation;
- actual production activation of `data/locales/ru.json`;
- editorial quality of generated Russian output.

## Storage baseline

Horizon uses filesystem persistence:

```text
configuration: JSON
subscribers: JSON
daily summaries: Markdown
MCP run metadata: JSON
MCP stages: JSON
MCP summaries: Markdown
```

Evidence:

- `src/storage/manager.py`;
- `src/mcp/run_store.py`;
- `src/_file_utils.py`;
- storage/MCP tests.

SQLite baseline:

```text
SQLite package/schema/migration evidence: NOT FOUND
```

Therefore radio-news SQLite persistence must be designed and tested as a new target implementation. Horizon file storage can still provide behavioral and provenance reference data.

## Local changes from upstream base

Comparison from `f37ec60...` to `fd28db14...` reports 23 commits and the following migration-relevant changed files.

### Added files

```text
.github/workflows/public-release-audit.yml
data/locales/ru.json
docs/audits/public-release-audit-contract.md
docs/audits/public-release-blockers.md
docs/security/pre_send_ssrf_design.md
src/services/locales_cli.py
src/setup/wizard_cli.py
tests/test_cli_parsers.py
tests/test_wizard_cli.py
```

### Modified runtime/package files

```text
pyproject.toml
src/ai/client.py
src/ai/summarizer.py
src/main.py
src/mcp/horizon_adapter.py
src/mcp/service.py
src/models.py
src/orchestrator.py
src/processing/profiles.py
src/services/webhook.py
src/services/webhook_cli.py
src/storage/manager.py
src/url_security.py
profiles/tech-blog/profile.json
profiles/tech-news/profile.json
data/config.example.json
data/config.github.json
```

### Modified tests

```text
tests/test_chained_client.py
tests/test_extractors_trafilatura.py
tests/test_mcp_adapter.py
tests/test_mcp_service_smoke.py
tests/test_profiles.py
tests/test_storage.py
tests/test_summarizer.py
tests/test_url_security.py
tests/test_webhook.py
```

### Modified docs/governance

```text
README.md
CODE_OF_CONDUCT.md
SECURITY.md
docs/configuration.md
docs/profiles.md
```

The local fork's unique migration value is therefore concentrated in security hardening, audit evidence, localization, profile/config path behavior, CLI/package acceptance, and associated regression tests.

## Disabled and unverified operational paths

### Disabled workflow

`.github/workflows/daily-summary.yml.disabled` is not active CI/runtime evidence. It describes a scheduled Horizon run and GitHub Pages deployment but is disabled at the pinned SHA.

### External integrations explicitly not verified

Existing audit documentation records:

```text
Live SMTP delivery: NOT VERIFIED
Live webhook delivery against an external endpoint: NOT VERIFIED
Paid AI-provider calls: NOT VERIFIED
Docker release path: NOT VERIFIED
```

These remain open evidence gaps. Unit tests and clean packaging do not convert them into verified integrations.

## Baseline stop conditions

Controlled extraction must not start if any transfer proposal relies on one of the following unsupported claims:

- “CI passed on `fd28db14...`” without qualifying the tree-equivalent final-head evidence;
- “all HTTP is SSRF-safe”;
- “Horizon already persists to SQLite”;
- “Russian locale file is definitely active in production”;
- “all optional collectors are used in the current deployment”;
- “live delivery/provider integrations passed”;
- “the package namespace can be renamed without compatibility impact”;
- “profile prompts are data only and can be separated from loader semantics without tests.”

## Reproduction record for later migration work

Any later equivalence test should record at minimum:

```text
Horizon source SHA
radio-news target SHA
Python version
resolved dependency versions
profile ID and prompt hashes
config fixture hash
input fixture hash
output artifact hash or normalized comparison
test names and result
CI run ID
```

## Baseline conclusion

The pinned Horizon tree has strong package, unit-test, transport-security, and publication-hygiene evidence through its final pull-request integration run. The exact merge SHA itself was not separately executed by CI, but it is file-identical to the successful final PR head.

This baseline is adequate for component classification. It is not permission to copy code, and it does not close the evidence gaps for live integrations, production configuration, universal outbound-network security, or SQLite persistence.
