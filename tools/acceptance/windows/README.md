# P2 Windows Acceptance

This directory contains the controlled Windows acceptance harness for PR #9, **P2 — Story and Evidence View**.

The harness validates only the authorized P2 chain:

```text
Feed card
-> Story
-> RawItem / NormalizedItem
-> Claim
-> Fact
-> Source
-> VerificationResult
-> provenance
```

It does not authorize or test P3-P5.

## Source of the wheel

The normal acceptance path does **not** download or copy a wheel manually.

The harness uses Git as the source of truth:

1. verifies that product head `1aafddaaae2747585847642b2c2ba46253fa20b4` is an ancestor of the checked-out harness head;
2. verifies that all later changes are confined to this acceptance directory;
3. creates a detached Git worktree at the exact product head;
4. builds one wheel from that clean worktree with Python 3.11;
5. computes and records the resulting wheel SHA-256;
6. removes the temporary worktree;
7. installs that wheel and runs Windows acceptance.

An externally supplied `-Wheel` remains supported only for checking the published CI artifact. It is not required for the normal Git-driven run.

## Preconditions

- Windows with Python 3.11 available through `py -3.11`;
- local checkout of branch `feature/p2-story-evidence-view`;
- clean Git working tree;
- the existing 20-item offline SQLite database;
- network access for Python build isolation if build requirements are not already cached.

## Update the local PR checkout

```powershell
cd D:\kpnews\radio-news-src
git switch feature/p2-story-evidence-view
git pull --ff-only
git status --short
git rev-parse HEAD
```

`git status --short` must produce no output.

## Optional parser check

```powershell
$scriptPath = (Resolve-Path ".\tools\acceptance\windows\run_p2_acceptance.ps1").Path
$tokens = $null
$parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$parseErrors
) | Out-Null
$parseErrors
```

Empty output means the PowerShell parser gate passed.

## Run acceptance from Git

```powershell
cd D:\kpnews\radio-news-src
Set-ExecutionPolicy -Scope Process Bypass -Force

.\tools\acceptance\windows\run_p2_acceptance.ps1 `
  -Database "D:\kpnews\work\radio-news.sqlite" `
  -WorkDir "D:\kpnews\p2-acceptance" `
  -BuildDir "D:\kpnews\p2-build" `
  -Port 8877
```

No `-Wheel` argument is used. The wheel is built from the exact Git product head.

## Automated checks

The script verifies:

- exact product-head ancestry;
- clean current checkout;
- no product changes after the exact product head;
- clean detached product worktree;
- wheel built from the exact Git commit;
- wheel SHA-256;
- package installation and `pip check`;
- localhost-only launch;
- P1 feed regression, including 20 cards and source attribution;
- complete P2 Story HTML and JSON graph;
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

Key files:

```text
p2-wheel-build-evidence.json
p2-acceptance-evidence.json
```

The build evidence records the exact product head, harness head, clean detached worktree, generated wheel path, Python version, and wheel SHA-256.

The acceptance evidence records the wheel origin, database hashes, graph counts, P1 regression status, P2 technical result, and editorial verdict.

## Scope boundary

The harness performs no domain writes, no migrations, no live RSS, and no outbound product HTTP. PR #9 remains Draft until the Windows-visible editorial verdict is `PASS`.
