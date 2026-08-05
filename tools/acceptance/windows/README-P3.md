# P3 Windows Product Gate

This harness validates **P3 — Manual Editorial Selection** on the target Windows machine.

It does not require a manually downloaded wheel. The script:

```text
Git exact product head
→ detached worktree
→ local wheel build
→ clean venv install
→ copy of the accepted SQLite database
→ packaged migration 0002
→ P1 feed regression check
→ P2 Story evidence regression check
→ visible P3 browser workflow
→ restart/readback verification
→ removal verification
→ Story/evidence-domain immutability check
→ human PASS / CHANGES REQUIRED verdict
```

## Preconditions

- local branch: `feature/p3-manual-editorial-selection`;
- clean Git worktree;
- Python 3.11 available through `py -3.11`;
- accepted source database at `D:\kpnews\work\radio-news.sqlite`;
- localhost port `8877` available.

The source database is never modified. The harness copies it to:

```text
D:\kpnews\p3-acceptance\radio-news-p3-acceptance.sqlite
```

All P3 writes happen only in that acceptance copy.

## Update the branch

```powershell
cd D:\kpnews\radio-news-src
git switch feature/p3-manual-editorial-selection
git pull --ff-only
git status --short
git rev-parse HEAD
```

`git status --short` must be empty.

## Parse the PowerShell script

```powershell
$scriptPath = (Resolve-Path ".\tools\acceptance\windows\run_p3_acceptance.ps1").Path
$tokens = $null
$parseErrors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$parseErrors
) | Out-Null

$parseErrors
```

Empty output means the parser gate passed.

## Run acceptance

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force

.\tools\acceptance\windows\run_p3_acceptance.ps1 `
  -Database "D:\kpnews\work\radio-news.sqlite" `
  -WorkDir "D:\kpnews\p3-acceptance" `
  -BuildDir "D:\kpnews\p3-build" `
  -Port 8877
```

## Human workflow

When the browser opens:

1. Add at least three existing Stories.
2. Assign the roles `lead`, `body`, and `reserve`.
3. Change their order with the visible controls.
4. Click **Save selection**.
5. Return to PowerShell and press Enter.
6. The harness restarts KPNEWS and verifies identical readback.
7. The browser opens again.
8. Remove exactly one Story and save again.
9. Return to PowerShell and press Enter.
10. Enter `PASS` or `CHANGES REQUIRED`.

## Required final output

```text
P3 TECHNICAL ACCEPTANCE: PASS
P3 EDITORIAL VERDICT: PASS
Wheel origin: git-build
Wheel SHA-256: <sha256>
Restart/readback: PASS
Evidence domain unchanged: PASS
Evidence: D:\kpnews\p3-acceptance\evidence\p3-acceptance-evidence.json
```

## Evidence files

```text
D:\kpnews\p3-acceptance\evidence\p3-acceptance-evidence.json
D:\kpnews\p3-acceptance\evidence\selection-before-restart.json
D:\kpnews\p3-acceptance\evidence\selection-after-restart.json
D:\kpnews\p3-acceptance\evidence\selection-after-removal.json
D:\kpnews\p3-acceptance\evidence\evidence-domain-before.json
D:\kpnews\p3-acceptance\evidence\evidence-domain-after.json
```

P4 and P5 remain blocked. This harness validates only the manually authored, persisted P3 selection workflow.
