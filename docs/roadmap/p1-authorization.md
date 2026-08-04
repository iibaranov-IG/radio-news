# Product Slice P1 — implementation authorization

## Purpose

Product slices `P1–P5` define the order in which visible editorial value is delivered. This document authorizes implementation of **P1 only**.

```text
P1 Read-only Editorial Feed: AUTHORIZED
P2 Story and Evidence View: BLOCKED UNTIL P1 PRODUCT GATE
P3 Manual Editorial Selection: BLOCKED UNTIL P2 PRODUCT GATE
P4 Deterministic Draft Edition: BLOCKED UNTIL P3 PRODUCT GATE
P5 First Editorial Acceptance: BLOCKED UNTIL P4 PRODUCT GATE
```

A later slice is not authorized merely because it appears in the Product-First Roadmap.

## Authorized user outcome

```text
one-command local start
→ browser opens a local editorial feed
→ editor sees persisted Source and RawItem records
→ editor can understand empty/error states
→ no terminal JSON is required for normal viewing
```

## Security and runtime boundary

P1 is strictly local and read-only:

- bind only to `127.0.0.1` or `::1`;
- no external bind such as `0.0.0.0`;
- no authentication claim and no remote access;
- read-only access to the existing SQLite database;
- no schema or domain writes;
- no live RSS or network ingress;
- no outbound HTTP requests;
- no SSRF transport transfer or security-equivalence claim;
- no AI, profiles, MCP, delivery, localization, personas, Chief News Editor, Radio Writer or Rundown;
- no Horizon import or runtime dependency.

Any request to add writes, remote binding, live ingress, or later product functionality is a stop condition and requires a new authorization change.

## Authorized implementation paths

New P1 paths:

```text
src/radio_news/application/
src/radio_news/api/
src/radio_news/web/
src/radio_news/web/templates/
src/radio_news/web/static/
tests/application/
tests/api/
tests/web/
```

Existing components may be changed only where needed for P1:

```text
PKG-01
CLI-01
CONFIG-01
SQLITE-TARGET — read-only query methods only
CI-01
TEST-01
```

The P1 implementation PR must not change ingestion, verification, migrations, identity rules or persisted domain semantics unless a separately reviewed blocker proves such a change is necessary.

## Product Gate P1

P1 is accepted only when a non-programmer can:

1. install or launch the application using one documented command;
2. open a localhost URL in a browser;
3. see at least one persisted news item with title, source and time;
4. see a useful empty state when the database has no items;
5. see a clear error when the database cannot be opened;
6. restart the application without changing the database;
7. confirm that no write occurred during browsing.

Engineering evidence remains mandatory:

- automated API and page tests;
- localhost-only bind test;
- read-only database test;
- wheel/install/start acceptance outside checkout;
- exact-head and PR CI success;
- machine-readable authorization validation.

## Machine-readable authority

The controlling manifest is:

```text
provenance/product-stages.json
```

Only entries with both:

```text
implementation_authorized: true
authorized_stage: PRODUCT_SLICE_P1
```

may be implemented in the P1 PR.
