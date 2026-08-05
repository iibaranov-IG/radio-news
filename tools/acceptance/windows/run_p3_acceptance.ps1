param(
    [string]$Database = "D:\kpnews\work\radio-news.sqlite",
    [string]$WorkDir = "D:\kpnews\p3-acceptance",
    [string]$BuildDir = "D:\kpnews\p3-build",
    [int]$Port = 8877,
    [int]$ExpectedFeedCount = 20,
    [string]$ProductHead = "46e053ee505e85b165ac20726609bb1c9975e449"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Invoke-NativeCommand(
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$FailureMessage
) {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $rawOutput = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }

    $output = @($rawOutput | ForEach-Object { [string]$_ })
    if ($exitCode -ne 0) {
        $details = ($output -join [Environment]::NewLine).Trim()
        if ([string]::IsNullOrWhiteSpace($details)) {
            throw "$FailureMessage (exit code $exitCode)"
        }
        throw "$FailureMessage (exit code $exitCode):`n$details"
    }
    return $output
}

function Invoke-Git([string[]]$Arguments) {
    return @(Invoke-NativeCommand "git" $Arguments "git command failed")
}

function Test-GitWorktreeRegistered([string]$RepositoryRoot, [string]$CandidatePath) {
    $candidateFullPath = [IO.Path]::GetFullPath($CandidatePath).TrimEnd('\')
    $worktreeList = @(Invoke-Git @("-C", $RepositoryRoot, "worktree", "list", "--porcelain"))
    foreach ($line in $worktreeList) {
        if ($line.StartsWith("worktree ")) {
            $listedPath = $line.Substring(9).Trim()
            $listedFullPath = [IO.Path]::GetFullPath($listedPath).TrimEnd('\')
            if ($listedFullPath -eq $candidateFullPath) {
                return $true
            }
        }
    }
    return $false
}

function Remove-BuildWorktree([string]$RepositoryRoot, [string]$SourcePath) {
    if (Test-GitWorktreeRegistered $RepositoryRoot $SourcePath) {
        Invoke-Git @("-C", $RepositoryRoot, "worktree", "remove", "--force", $SourcePath) | Out-Null
    }
    Invoke-Git @("-C", $RepositoryRoot, "worktree", "prune") | Out-Null
    if (Test-Path -LiteralPath $SourcePath) {
        Remove-Item -LiteralPath $SourcePath -Recurse -Force
    }
}

function Stop-KpnewsProcess($Process) {
    if ($null -ne $Process) {
        try {
            if (-not $Process.HasExited) {
                Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
                $Process.WaitForExit(5000) | Out-Null
            }
        } catch {
        }
    }
}

function Start-Kpnews(
    [string]$Executable,
    [string]$DatabasePath,
    [int]$ListenPort,
    [string]$StdoutPath,
    [string]$StderrPath
) {
    Remove-Item $StdoutPath, $StderrPath -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $Executable -ArgumentList @(
        "serve", "--database", $DatabasePath,
        "--host", "127.0.0.1", "--port", "$ListenPort"
    ) -PassThru -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath

    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            throw "KPNEWS exited before readiness. See $StderrPath"
        }
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$ListenPort/healthz" -TimeoutSec 2
            if ($health.status -eq "ok") {
                return $process
            }
        } catch {
        }
    }
    Stop-KpnewsProcess $process
    throw "KPNEWS did not answer /healthz within 30 seconds"
}

function Get-Selection([int]$ListenPort) {
    $response = Invoke-WebRequest "http://127.0.0.1:$ListenPort/api/selections/current" -UseBasicParsing -TimeoutSec 10
    $payload = $response.Content | ConvertFrom-Json
    if ($null -eq $payload -or $payload.PSObject.Properties.Name -notcontains "selection") {
        throw "P3 acceptance API returned an unexpected payload without 'selection'"
    }
    $selection = $payload.selection
    if ($null -eq $selection -or $selection.PSObject.Properties.Name -notcontains "items") {
        throw "P3 acceptance API returned a selection without 'items'. Save the selection in the browser and retry."
    }
    return $selection
}

function Get-EvidenceDigest([string]$Python, [string]$DatabasePath, [string]$OutputPath) {
    $helper = Join-Path (Split-Path -Parent $OutputPath) "evidence_digest.py"
    $code = @'
import hashlib
import json
import sqlite3
import sys

path, output = sys.argv[1], sys.argv[2]
tables = [
    "sources", "raw_items", "normalized_items", "stories",
    "claims", "facts", "fact_claims", "verification_results",
]
connection = sqlite3.connect(path)
try:
    result = {}
    for table in tables:
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
        payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        result[table] = {
            "count": len(rows),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
finally:
    connection.close()
with open(output, "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
'@
    Write-Utf8NoBom $helper $code
    Invoke-NativeCommand $Python @($helper, $DatabasePath, $OutputPath) "Evidence digest failed" | Out-Null
    return Get-Content $OutputPath -Raw -Encoding UTF8
}

if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be between 1 and 65535"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..")).Path
$sourceDatabase = (Resolve-Path $Database).Path

$gitTop = @(Invoke-Git @("-C", $repositoryRoot, "rev-parse", "--show-toplevel"))[0].Trim()
if ([IO.Path]::GetFullPath($gitTop).TrimEnd('\') -ne [IO.Path]::GetFullPath($repositoryRoot).TrimEnd('\')) {
    throw "Acceptance script is not running from the expected repository root: $repositoryRoot"
}

$dirty = @(Invoke-Git @("-C", $repositoryRoot, "status", "--porcelain"))
if ($dirty.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace(($dirty -join ""))) {
    throw "Repository working tree is not clean. Commit or discard local changes before acceptance."
}

$harnessHead = @(Invoke-Git @("-C", $repositoryRoot, "rev-parse", "HEAD"))[0].Trim()
Invoke-Git @("-C", $repositoryRoot, "merge-base", "--is-ancestor", $ProductHead, $harnessHead) | Out-Null

$allowedHarnessPaths = @(
    "tools/acceptance/windows/run_p3_acceptance.ps1",
    "tools/acceptance/windows/README-P3.md"
)
$changedSinceProduct = @(Invoke-Git @("-C", $repositoryRoot, "diff", "--name-only", "$ProductHead..$harnessHead"))
$unexpected = @($changedSinceProduct | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_) -and $_ -notin $allowedHarnessPaths
})
if ($unexpected.Count -gt 0) {
    throw "Unexpected product changes after exact product head ${ProductHead}: $($unexpected -join ', ')"
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
$workPath = (Resolve-Path $WorkDir).Path
$buildPath = (Resolve-Path $BuildDir).Path
$evidenceDir = Join-Path $workPath "evidence"
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null

$shortHead = $ProductHead.Substring(0, 12)
$sourcePath = Join-Path $buildPath "source-$shortHead"
$distPath = Join-Path $buildPath "dist-$shortHead"
Remove-BuildWorktree $repositoryRoot $sourcePath
if (Test-Path -LiteralPath $distPath) {
    Remove-Item -LiteralPath $distPath -Recurse -Force
}
New-Item -ItemType Directory -Path $distPath -Force | Out-Null

Invoke-Git @("-C", $repositoryRoot, "worktree", "add", "--quiet", "--detach", $sourcePath, $ProductHead) | Out-Null
try {
    $builtHead = @(Invoke-Git @("-C", $sourcePath, "rev-parse", "HEAD"))[0].Trim()
    if ($builtHead -ne $ProductHead) {
        throw "Detached build worktree is on $builtHead instead of $ProductHead"
    }
    $buildOutput = @(Invoke-NativeCommand "py" @(
        "-3.11", "-m", "pip", "wheel",
        "--disable-pip-version-check", "--no-deps",
        "--wheel-dir", $distPath, $sourcePath
    ) "Building the exact-head wheel from Git failed")
    $buildOutput | ForEach-Object { Write-Host $_ }
} finally {
    Remove-BuildWorktree $repositoryRoot $sourcePath
}

$wheels = @(Get-ChildItem $distPath -Filter "*.whl" -File)
if ($wheels.Count -ne 1) {
    throw "Expected exactly one wheel in $distPath, found $($wheels.Count)"
}
$wheelPath = $wheels[0].FullName
$wheelSha = (Get-FileHash $wheelPath -Algorithm SHA256).Hash.ToLowerInvariant()

$venv = Join-Path $workPath ".venv"
if (Test-Path -LiteralPath $venv) {
    Remove-Item -LiteralPath $venv -Recurse -Force
}
Invoke-NativeCommand "py" @("-3.11", "-m", "venv", $venv) "Python 3.11 venv creation failed" | Out-Null
$python = Join-Path $venv "Scripts\python.exe"
$radioNews = Join-Path $venv "Scripts\radio-news.exe"
Invoke-NativeCommand $python @(
    "-m", "pip", "install", "--disable-pip-version-check", "--force-reinstall", $wheelPath
) "Wheel installation failed" | ForEach-Object { Write-Host $_ }
Invoke-NativeCommand $python @("-m", "pip", "check") "pip check failed" | ForEach-Object { Write-Host $_ }

$acceptanceDatabase = Join-Path $workPath "radio-news-p3-acceptance.sqlite"
Copy-Item -LiteralPath $sourceDatabase -Destination $acceptanceDatabase -Force

$migrateCode = "from radio_news.storage import SQLiteStore; print(SQLiteStore(r'$($acceptanceDatabase.Replace("'", "''"))').migrate())"
$migrationOutput = @(Invoke-NativeCommand $python @("-c", $migrateCode) "Applying packaged migrations failed")
$migrationText = ($migrationOutput -join " ").Trim()
if (-not $migrationText.Contains("2")) {
    throw "Migration 0002 was not applied or detected: $migrationText"
}

$evidenceBeforePath = Join-Path $evidenceDir "evidence-domain-before.json"
$evidenceAfterPath = Join-Path $evidenceDir "evidence-domain-after.json"
$evidenceBefore = Get-EvidenceDigest $python $acceptanceDatabase $evidenceBeforePath

$stdout = Join-Path $evidenceDir "server.stdout.log"
$stderr = Join-Path $evidenceDir "server.stderr.log"
$process = $null
try {
    $process = Start-Kpnews $radioNews $acceptanceDatabase $Port $stdout $stderr

    $feedResponse = Invoke-WebRequest "http://127.0.0.1:$Port/api/feed" -UseBasicParsing -TimeoutSec 10
    $feed = $feedResponse.Content | ConvertFrom-Json
    if ($ExpectedFeedCount -gt 0 -and [int]$feed.count -ne $ExpectedFeedCount) {
        throw "P1 regression: expected $ExpectedFeedCount feed items, got $($feed.count)"
    }

    $storyIds = @($feed.items | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.story_id) } | Select-Object -ExpandProperty story_id)
    if ($storyIds.Count -lt 3) {
        throw "P3 acceptance requires at least three persisted Stories"
    }

    $firstStoryPath = [Uri]::EscapeDataString([string]$storyIds[0])
    $storyResponse = Invoke-WebRequest "http://127.0.0.1:$Port/api/stories/$firstStoryPath" -UseBasicParsing -TimeoutSec 10
    $story = $storyResponse.Content | ConvertFrom-Json
    if ($null -eq $story.story -or @($story.provenance).Count -lt 1) {
        throw "P2 regression: Story evidence graph is incomplete"
    }

    $selectionUrl = "http://127.0.0.1:$Port/selections/current"
    Start-Process $selectionUrl
    Write-Host ""
    Write-Host "P3 Manual Editorial Selection opened: $selectionUrl" -ForegroundColor Cyan
    Write-Host "In the browser: add at least 3 Stories, assign lead/body/reserve, reorder them, and click Save."
    Read-Host "Press ENTER after the first selection is saved" | Out-Null

    $saved = Get-Selection $Port
    $savedItems = @($saved.items)
    if ($savedItems.Count -lt 3) {
        throw "P3 failure: fewer than three Stories were saved"
    }
    $roles = @($savedItems | ForEach-Object { [string]$_.role })
    foreach ($requiredRole in @("lead", "body", "reserve")) {
        if ($requiredRole -notin $roles) {
            throw "P3 failure: role '$requiredRole' is missing"
        }
    }
    $positions = @($savedItems | ForEach-Object { [int]$_.position })
    for ($i = 0; $i -lt $positions.Count; $i++) {
        if ($positions[$i] -ne $i) {
            throw "P3 failure: positions are not deterministic and contiguous"
        }
    }
    $savedCanonical = $saved | ConvertTo-Json -Depth 10 -Compress
    Write-Utf8NoBom (Join-Path $evidenceDir "selection-before-restart.json") ($saved | ConvertTo-Json -Depth 10)

    Stop-KpnewsProcess $process
    $process = Start-Kpnews $radioNews $acceptanceDatabase $Port $stdout $stderr
    $reloaded = Get-Selection $Port
    $reloadedCanonical = $reloaded | ConvertTo-Json -Depth 10 -Compress
    if ($savedCanonical -ne $reloadedCanonical) {
        throw "P3 restart failure: selection changed after KPNEWS restart"
    }
    Write-Utf8NoBom (Join-Path $evidenceDir "selection-after-restart.json") ($reloaded | ConvertTo-Json -Depth 10)

    Start-Process $selectionUrl
    Write-Host ""
    Write-Host "Restart/readback passed. Remove exactly one Story, click Save, then continue." -ForegroundColor Cyan
    Read-Host "Press ENTER after the removal is saved" | Out-Null

    $afterRemoval = Get-Selection $Port
    $afterItems = @($afterRemoval.items)
    if ($afterItems.Count -ne ($savedItems.Count - 1)) {
        throw "P3 removal failure: expected $($savedItems.Count - 1) items, got $($afterItems.Count)"
    }
    Write-Utf8NoBom (Join-Path $evidenceDir "selection-after-removal.json") ($afterRemoval | ConvertTo-Json -Depth 10)

    $evidenceAfter = Get-EvidenceDigest $python $acceptanceDatabase $evidenceAfterPath
    if ($evidenceBefore -ne $evidenceAfter) {
        throw "P3 boundary failure: Story/evidence-domain tables changed"
    }

    do {
        $verdict = (Read-Host "Editorial verdict: PASS or CHANGES REQUIRED").Trim().ToUpperInvariant()
    } until ($verdict -in @("PASS", "CHANGES REQUIRED"))

    $evidence = [ordered]@{
        schema_version = 1
        product_slice = "P3_MANUAL_EDITORIAL_SELECTION"
        pull_request = 11
        product_head = $ProductHead
        harness_head = $harnessHead
        wheel_origin = "git-build"
        wheel_sha256 = $wheelSha
        source_database = $sourceDatabase
        acceptance_database = $acceptanceDatabase
        migration_versions = $migrationText
        feed_count = [int]$feed.count
        initial_selection_count = $savedItems.Count
        selection_count_after_removal = $afterItems.Count
        restart_readback = "PASS"
        evidence_domain_unchanged = $true
        browser_url = $selectionUrl
        editorial_verdict = $verdict
    }
    $evidencePath = Join-Path $evidenceDir "p3-acceptance-evidence.json"
    Write-Utf8NoBom $evidencePath ($evidence | ConvertTo-Json -Depth 10)

    Write-Host ""
    Write-Host "P3 TECHNICAL ACCEPTANCE: PASS" -ForegroundColor Green
    Write-Host "P3 EDITORIAL VERDICT: $verdict" -ForegroundColor Green
    Write-Host "Wheel origin: git-build"
    Write-Host "Wheel SHA-256: $wheelSha"
    Write-Host "Restart/readback: PASS"
    Write-Host "Evidence domain unchanged: PASS"
    Write-Host "Evidence: $evidencePath"

    if ($verdict -ne "PASS") {
        exit 2
    }
} finally {
    Stop-KpnewsProcess $process
}
