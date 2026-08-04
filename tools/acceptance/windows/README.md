# P2 Windows Acceptance

This directory contains the controlled Windows acceptance harness for PR #9, **P2 — Story and Evidence View**.

The harness validates the authorized P2 product chain:

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

It does not authorize or test P3–P5.

## Preconditions

- Windows target with Python 3.11 available through `py -3.11`;
- local checkout of branch `feature/p2-story-evidence-view`;
- clean Git working tree;
- the existing 20-item offline SQLite database;
- the exact P2 wheel built from product head `1aafddaaae2747585847642b2c2ba46253fa20b4`;
- expected wheel SHA-256:

```text
7d2da463519e0640a8cfbd718f6779f4b82eecdf6b4e7e0b69b1e41dc6e58e9e
```

The acceptance harness itself may be committed after that product head. It verifies that every later change is confined to this directory.

## Update the local PR checkout

```powershell
cd D:\kpnews\radio-news-src
git switch feature/p2-story-evidence-view
git pull --ff-only
git status --short
git rev-parse HEAD
```

`git status --short` must produce no output.

## Run acceptance

```powershell
cd D:\kpnews\radio-news-src
Set-ExecutionPolicy -Scope Process Bypass -Force
.\tools\acceptance\windows\run_p2_acceptance.ps1 `
  -Wheel "D:\kpnews\acceptance\radio_news-0.1.0-p2-1aafddaa-py3-none-any.whl" `
  -Database "D:\kpnews\work\radio-news.sqlite" `
  -WorkDir "D:\kpnews\p2-acceptance" `
  -Port 8877
```

The wheel filename is not significant; its SHA-256 must match the expected value.

## Automated checks

The script verifies:

- the exact product head is an ancestor of the checked-out harness commit;
- no product file changed after the exact product head;
- the repository working tree is clean;
- wheel SHA-256;
- Python package installation and `pip check`;
- localhost-only launch;
- P1 feed regression, including 20 cards and source attribution;
- the complete P2 Story HTML and JSON graph;
- required provenance relations;
- byte-identical SQLite SHA-256 before and after HTTP serving.

The browser then opens the Story and Evidence screen and asks for one human verdict:

```text
PASS
```

or

```text
CHANGES REQUIRED
```

## Evidence

Evidence is written to:

```text
D:\kpnews\p2-acceptance\evidence\
```

Key file:

```text
p2-acceptance-evidence.json
```

It records the product head, harness head, wheel hash, database hashes, graph counts, P1 regression status, P2 technical result, and editorial verdict.

## Scope boundary

The harness performs no domain writes, no migrations, no live RSS, and no outbound HTTP. PR #9 remains Draft until the Windows-visible editorial verdict is `PASS`.
