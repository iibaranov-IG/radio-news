# P2 — Story and Evidence View

## Status

```text
FOUNDATIONAL ROADMAP: COMPLETE
FIRST INDEPENDENT VERTICAL SLICE: COMPLETE
P1: FORMALLY CLOSED
SOURCE OF TRUTH: radio-news/main@b2296481c24098931c27124aef97f649dc9188fe
P2: AUTHORIZED BY MERGE OF THIS DOCUMENTATION PR
```

This document authorizes only the P2 product slice. It does not implement P2 and does not authorize any later product stage.

## Product question

Why is this news item in the system, and how transparent is its evidence chain?

In Russian editorial terms:

> Почему эта новость находится в системе и насколько прозрачна её доказательная цепочка?

## Authorized user flow

```text
Feed card
→ Story
→ RawItem / NormalizedItem
→ Claim
→ Fact
→ Source
→ VerificationResult
→ provenance
```

The editor opens a feed card and receives a read-only view of the complete linked domain graph behind that item.

## P2 product boundary

P2 is limited to transparency of the evidence chain.

The screen must let an editor understand:

- which `Story` the feed item belongs to;
- which `RawItem` and `NormalizedItem` records produced it;
- which `Claim` records were extracted;
- which `Fact` records support those claims;
- which `Source` each assertion originates from;
- which `VerificationResult` applies and what its status is;
- how the records are connected through provenance.

P2 remains read-only. It explains what is already stored; it does not change editorial or domain state.

## Acceptance criteria

P2 is accepted only when all of the following are true:

```text
editor opens a feed card
→ sees the complete linked graph
→ understands the origin of each assertion
→ sees Source and VerificationResult context
→ can follow provenance through the stored records
→ database remains read-only
→ P1 does not regress
```

Required acceptance evidence:

- the P1 feed remains available and functionally unchanged;
- a feed card can open the corresponding Story and Evidence view;
- all displayed records are read from the existing SQLite domain graph;
- the view exposes the linked `Story`, `RawItem`, `NormalizedItem`, `Claim`, `Fact`, `Source`, and `VerificationResult` records;
- provenance links are understandable to a human editor;
- serving the P2 view does not alter the SQLite database;
- localhost-only behavior and the P1 security boundary remain intact.

## Explicitly prohibited scope

```text
NO DOMAIN WRITES
NO DATABASE MIGRATIONS
NO EDITORIAL SELECTION
NO TEXT GENERATION
NO AI SCORING
NO PERSONAS
NO CHIEF EDITOR
NO RUNDOWN
NO DRAFT EDITION
NO LIVE RSS
NO OUTBOUND HTTP
```

The following are therefore outside P2:

- selecting stories for an edition;
- approving or rejecting stories as editorial actions;
- generating, rewriting, or summarizing text;
- creating a rundown or draft edition;
- introducing AI ranking, scoring, personas, Chief Editor, or Writer roles;
- adding live ingestion or any outbound network access;
- changing the database schema or writing domain data.

## Implementation authorization

Before this documentation PR is merged:

```text
P2 IMPLEMENTATION: BLOCKED
NEW P2 ENDPOINTS: BLOCKED
NEW P2 UI: BLOCKED
P2 CODE: BLOCKED
```

After this documentation PR is merged:

```text
P2: AUTHORIZED
AUTHORIZED IMPLEMENTATION: READ-ONLY STORY AND EVIDENCE VIEW ONLY
P3–P5: BLOCKED
```

Implementation must occur in a separate PR based on the resulting `main` commit. Any expansion beyond this document requires a separate authorization decision.