# P3 — Manual Editorial Selection

## Status

```text
P1: FORMALLY CLOSED
P2: FORMALLY CLOSED
P2 IMPLEMENTATION MERGE: 3ed3aa6623d5dbe16458c8bc45f76def1a921910
SOURCE OF TRUTH: radio-news/main@3ed3aa6623d5dbe16458c8bc45f76def1a921910
P3: AUTHORIZED BY MERGE OF THIS DOCUMENTATION PR
```

This document authorizes only the P3 product slice. It does not implement P3 and does not authorize P4, P5, or any later architecture stage.

## Product question

Which stories has the editor manually chosen for the upcoming edition, in what order, and with what editorial role?

In Russian editorial terms:

> Какие сюжеты редактор вручную отобрал в будущий выпуск, в каком порядке они стоят и какую роль выполняют?

## Authorized user flow

```text
Editorial Feed or Story view
→ add an existing Story to a draft Editorial Selection
→ remove a Story when needed
→ assign lead / body / reserve
→ reorder selected Stories
→ save the draft selection
→ restart KPNEWS
→ reopen the same saved selection
```

The editor remains the sole decision-maker. P3 records the editor's explicit choices; it does not propose, rank, score, or generate them.

## P3 product boundary

P3 is limited to manual construction and persistence of a draft Editorial Selection.

The product must let an editor:

- create or open a draft Editorial Selection;
- add an existing persisted `Story` from the P1/P2 interface;
- remove a selected `Story`;
- assign exactly one role to each selected item: `lead`, `body`, or `reserve`;
- set and change a deterministic order;
- save the selection;
- reopen the same saved state after page reload and application restart;
- understand which selection is currently open and whether the latest changes were saved.

P3 does not create an edition text. It produces only a durable, human-authored ordered list of Story references and their editorial roles.

## Authorized persistence boundary

P3 introduces controlled domain writes for P3-owned selection state only.

An implementation may add an additive database migration through the repository's existing migration mechanism, limited to the minimum persistence required for:

- stable Editorial Selection identity;
- draft status only;
- references to existing `Story` records;
- one role per selected Story: `lead`, `body`, or `reserve`;
- deterministic integer position;
- uniqueness of a Story within one selection;
- persistence across process restart.

Required invariants:

- a selection item must reference an existing `Story`;
- the same `Story` cannot appear twice in one selection;
- item ordering must be deterministic and recoverable;
- role values outside `lead`, `body`, and `reserve` must be rejected;
- save, reorder, add, and remove operations must be transactional;
- existing `Source`, `RawItem`, `NormalizedItem`, `Story`, `Claim`, `Fact`, and `VerificationResult` records must not be mutated;
- P1 and P2 views remain read-only with respect to the existing evidence graph;
- runtime DDL and unrelated schema changes are prohibited.

The P3 write permission is therefore narrow: it applies only to the new Editorial Selection state owned by P3.

## Acceptance criteria

P3 is accepted only when all of the following are true:

```text
editor opens the existing feed
→ selects at least three persisted Stories
→ assigns lead / body / reserve roles
→ changes their order
→ saves the draft Editorial Selection
→ reloads the page
→ restarts KPNEWS
→ reopens the same selection with identical Stories, roles, and order
→ removes one Story and saves again
→ the removal remains after another reload
```

Required acceptance evidence:

- P1 Editorial Feed remains available and does not regress;
- P2 Story and Evidence View remains available and does not regress;
- selection actions are available through the local browser UI, not only through CLI, JSON, or direct SQLite access;
- add, remove, role assignment, reorder, and save are visibly confirmed;
- the saved selection survives a full application restart;
- duplicate Story selection is prevented or resolved deterministically;
- invalid Story references and invalid roles are rejected with a human-readable error;
- writes are confined to P3-owned selection persistence;
- existing evidence-domain rowsets remain unchanged during P3 acceptance;
- localhost-only behavior, no-outbound-network behavior, and no-Horizon-runtime-dependency remain intact;
- one human editor provides a final `PASS` or `CHANGES REQUIRED` verdict on the visible selection workflow.

## Explicitly prohibited scope

```text
NO AUTOMATIC STORY SELECTION
NO AI SCORING OR RANKING
NO RECOMMENDATION ENGINE
NO PERSONAS
NO CHIEF EDITOR
NO TEXT GENERATION
NO SUMMARIZATION OR REWRITING
NO DRAFT EDITION
NO RUNDOWN SOLVER
NO TIMING OPTIMIZATION
NO APPROVAL OR PUBLISH LIFECYCLE
NO LIVE RSS
NO OUTBOUND HTTP
NO HORIZON RUNTIME DEPENDENCY
NO MUTATION OF STORY OR EVIDENCE RECORDS
NO UNRELATED DATABASE MIGRATIONS
```

The following are therefore outside P3:

- automatically deciding which Stories belong in the edition;
- proposing or ranking Stories using rules, AI, embeddings, personas, or a Chief Editor;
- generating headlines, links, transitions, scripts, summaries, or radio copy;
- calculating edition duration or solving rundown constraints;
- approving, publishing, exporting, or broadcasting an edition;
- editing `Claim`, `Fact`, `VerificationResult`, provenance, or source data;
- adding live ingestion, external integrations, or outbound network access.

## Regression boundary

P3 extends the product but must preserve the already accepted behavior:

```text
P1 Editorial Feed: PASS MUST REMAIN PASS
P2 Story and Evidence View: PASS MUST REMAIN PASS
P3 Manual Editorial Selection: NEW CONTROLLED WRITE SLICE
```

The selection UI may link from P1 and P2, but those screens must continue to explain the stored news and evidence graph without silently changing it.

## Implementation authorization

Before this documentation PR is merged:

```text
P3 IMPLEMENTATION: BLOCKED
P3 DATABASE MIGRATION: BLOCKED
P3 WRITE ENDPOINTS: BLOCKED
P3 SELECTION UI: BLOCKED
P3 CODE: BLOCKED
```

After this documentation PR is merged:

```text
P3: AUTHORIZED
AUTHORIZED IMPLEMENTATION: MANUAL PERSISTED EDITORIAL SELECTION ONLY
AUTHORIZED WRITES: P3-OWNED SELECTION STATE ONLY
P4–P5: BLOCKED
```

Implementation must occur in a separate PR based on the resulting `main` commit. Any expansion beyond this document requires a separate authorization decision.
