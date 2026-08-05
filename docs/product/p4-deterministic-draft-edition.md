# P4 — Deterministic Draft Edition

## Status

```text
P1: FORMALLY CLOSED
P2: FORMALLY CLOSED
P3: FORMALLY CLOSED
P3 IMPLEMENTATION MERGE: d3475ded0d1890aaa2af58b2bf9f1cbcfda6b668
SOURCE OF TRUTH: radio-news/main@d3475ded0d1890aaa2af58b2bf9f1cbcfda6b668
P4: AUTHORIZED BY MERGE OF THIS DOCUMENTATION PR
```

This document authorizes only P4 — Deterministic Draft Edition. It does not implement P4 and does not authorize P5 or any later architecture stage.

## Product question

Can KPNEWS turn the editor's saved P3 selection into a visible, editable, attributable draft news edition without AI generation or hidden editorial decisions?

In Russian editorial terms:

> Может ли редактор нажать «Сформировать выпуск» и получить на экране воспроизводимый черновик, собранный только из выбранных им сюжетов и подтверждённых фактов?

## Authorized user flow

```text
saved P3 Editorial Selection
→ click “Сформировать выпуск”
→ deterministic edition assembly
→ visible ordered draft
→ source attribution for every item
→ approximate timing
→ manual text editing
→ explicit save
→ reload and restart
→ reopen the same saved draft
```

P4 consumes the editor-authored P3 selection. It must not choose, rank, remove, or add Stories automatically.

## P4 product boundary

P4 is limited to creation, display, manual editing, persistence, and deterministic regeneration of a Draft Edition derived from one saved P3 Editorial Selection.

The product must let an editor:

- open an existing saved P3 Editorial Selection;
- generate a Draft Edition from exactly the selected Stories, roles, and order;
- see each edition item in deterministic order;
- see the Story title, approved Fact-derived text, source attribution, role, and approximate timing;
- manually edit the visible draft text;
- save the edited Draft Edition explicitly;
- reload the page and restart KPNEWS without losing the saved draft;
- distinguish the generated baseline from the editor-modified saved text;
- regenerate deterministically from the same unchanged P3 selection and obtain the same generated baseline.

P4 creates a draft editorial artifact. It does not approve, publish, export, broadcast, schedule, or automatically evaluate the edition.

## Deterministic generation rules

The first P4 implementation must use explicit deterministic rules, not an LLM.

Required inputs:

- one saved P3 Editorial Selection;
- ordered selection items;
- each item's role: `lead`, `body`, or `reserve`;
- the persisted Story title;
- accepted/manual Facts associated with the Story;
- persisted Source attribution;
- existing VerificationResult state.

Required deterministic behavior:

- selected Story order is preserved exactly;
- no unselected Story is introduced;
- one edition item is produced for each selected Story;
- the same unchanged inputs and generator version produce byte-identical generated baseline text;
- source attribution is explicit and cannot be silently omitted;
- Facts are rendered without inventing unsupported details;
- missing usable Facts produce a visible deterministic placeholder or blocked-item state, not fabricated prose;
- `lead`, `body`, and `reserve` roles remain visible in the draft;
- approximate timing uses one documented deterministic calculation;
- generator version and source selection identity are persisted with the draft.

The deterministic template may be simple. Product correctness, provenance, reproducibility, and editorial visibility are more important than literary quality at P4.

## Authorized persistence boundary

P4 introduces controlled writes for P4-owned Draft Edition state only.

An implementation may add the minimum additive migration required for:

- stable Draft Edition identity;
- reference to one existing P3 Editorial Selection;
- edition status `DRAFT` only;
- deterministic generator version;
- generated baseline text or structured generated items;
- editor-modified saved text;
- ordered edition items;
- per-item Story reference, role, source attribution, and timing estimate;
- created and updated timestamps;
- persistence across restart.

Required invariants:

- every Draft Edition references an existing P3 Editorial Selection;
- every edition item references a Story present in that selection;
- edition order initially matches the saved P3 order exactly;
- regeneration never mutates the P3 selection;
- manual draft edits never mutate Story, Fact, Claim, VerificationResult, Source, or provenance records;
- generated baseline and editor-modified text remain distinguishable;
- saves are transactional;
- runtime DDL and unrelated schema changes are prohibited.

## Timing boundary

P4 may calculate only an approximate duration using a documented deterministic rule, for example a fixed words-per-minute constant plus fixed separators.

It must not implement:

- a Rundown constraint solver;
- hard broadcast clock optimization;
- automatic duration balancing;
- ad-break placement;
- regional window scheduling;
- dynamic shortening or expansion by AI.

Approximate timing is informational and must be labelled as such.

## Acceptance criteria

P4 is accepted only when all of the following are true:

```text
editor opens a saved P3 selection
→ clicks “Сформировать выпуск”
→ sees one ordered draft item per selected Story
→ sees lead / body / reserve roles
→ sees explicit source attribution
→ sees Fact-derived text or a visible blocked placeholder
→ sees approximate total and per-item timing
→ edits at least one draft item manually
→ saves the draft
→ reloads the page
→ restarts KPNEWS
→ reopens the identical saved edited draft
→ regenerates from unchanged inputs
→ generated baseline remains deterministic
```

Required acceptance evidence:

- P1 Editorial Feed remains available;
- P2 Story and Evidence View remains available;
- P3 Manual Editorial Selection remains available and unchanged;
- generation is triggered through the local browser UI, not only CLI or direct API;
- no unselected Story appears in the edition;
- item order and roles match P3 exactly;
- every rendered item shows its source attribution;
- no unsupported statement is introduced beyond persisted title and accepted/manual Facts;
- missing evidence is visible rather than hidden;
- manual edit and save are visibly confirmed;
- saved draft survives full application restart;
- deterministic regeneration is verified from identical inputs;
- writes are confined to P4-owned draft state;
- P3 selection and existing evidence-domain rowsets remain unchanged;
- localhost-only behavior, no-outbound-network behavior, and no-Horizon-runtime-dependency remain intact;
- one human editor provides a final `PASS` or `CHANGES REQUIRED` verdict.

## Explicitly prohibited scope

```text
NO AUTOMATIC STORY SELECTION
NO STORY RANKING OR REORDERING
NO AI OR LLM TEXT GENERATION
NO SUMMARIZATION MODEL
NO PERSONAS
NO CHIEF EDITOR
NO RADIO WRITER
NO RUNDOWN SOLVER
NO APPROVAL WORKFLOW
NO PUBLISH OR EXPORT
NO BROADCAST AUTOMATION
NO LIVE RSS
NO OUTBOUND HTTP
NO HORIZON RUNTIME DEPENDENCY
NO MUTATION OF P3 SELECTION
NO MUTATION OF STORY OR EVIDENCE RECORDS
NO P5 CONTRACTS
```

P4 must not:

- decide which Stories belong in the edition;
- change P3 roles or order automatically;
- generate facts, quotes, names, numbers, or context not supported by persisted evidence;
- use AI to rewrite, score, summarize, shorten, expand, or connect items;
- claim editorial approval;
- produce a production rundown;
- publish, export, send, schedule, or broadcast the result.

## Regression boundary

```text
P1 Editorial Feed: PASS MUST REMAIN PASS
P2 Story and Evidence View: PASS MUST REMAIN PASS
P3 Manual Editorial Selection: PASS MUST REMAIN PASS
P4 Deterministic Draft Edition: NEW CONTROLLED DRAFT WRITE SLICE
```

P4 may consume P3 selection data and evidence-domain data, but it may write only its own Draft Edition state.

## Implementation authorization

Before this documentation PR is merged:

```text
P4 IMPLEMENTATION: BLOCKED
P4 DATABASE MIGRATION: BLOCKED
P4 WRITE ENDPOINTS: BLOCKED
P4 DRAFT UI: BLOCKED
P4 CODE: BLOCKED
P5: BLOCKED
```

After this documentation PR is merged:

```text
P4: AUTHORIZED
AUTHORIZED IMPLEMENTATION: DETERMINISTIC DRAFT EDITION ONLY
AUTHORIZED INPUT: ONE SAVED P3 EDITORIAL SELECTION
AUTHORIZED WRITES: P4-OWNED DRAFT EDITION STATE ONLY
P5: BLOCKED
```

Implementation must occur in a separate PR based on the resulting `main` commit. Any expansion beyond this document requires a separate authorization decision.
