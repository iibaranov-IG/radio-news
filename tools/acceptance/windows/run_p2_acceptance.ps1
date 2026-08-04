param(
    [Parameter(Mandatory = $true)]
    [string]$Wheel,

    [string]$Database = "D:\kpnews\work\radio-news.sqlite",
    [string]$WorkDir = "D:\kpnews\p2-acceptance",
    [int]$Port = 8877,
    [int]$ExpectedFeedCount = 20,
    [string]$ExpectedSourceDisplayName = "РИА Новости · офлайн-снимок",
    [string]$ProductHead = "1aafddaaae2747585847642b2c2ba46253fa20b4",
    [string]$ExpectedWheelSha256 = "7d2da463519e0640a8cfbd718f6779f4b82eecdf6b4e7e0b69b1e41dc6e58e9e"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Invoke-Git([string[]]$Arguments) {
    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $output"
    }
    return @($output)
}

if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be between 1 and 65535"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..")).Path
$wheelPath = (Resolve-Path $Wheel).Path
$databasePath = (Resolve-Path $Database).Path

$gitTop = (Invoke-Git @("-C", $repositoryRoot, "rev-parse", "--show-toplevel"))[0].Trim()
if ([IO.Path]::GetFullPath($gitTop).TrimEnd('\') -ne [IO.Path]::GetFullPath($repositoryRoot).TrimEnd('\')) {
    throw "Acceptance script is not running from the expected repository root: $repositoryRoot"
}

$dirty = Invoke-Git @("-C", $repositoryRoot, "status", "--porcelain")
if ($dirty.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace(($dirty -join ""))) {
    throw "Repository working tree is not clean. Commit or discard local changes before acceptance."
}

$harnessHead = (Invoke-Git @("-C", $repositoryRoot, "rev-parse", "HEAD"))[0].Trim()
& git -C $repositoryRoot merge-base --is-ancestor $ProductHead $harnessHead
if ($LASTEXITCODE -ne 0) {
    throw "Product head $ProductHead is not an ancestor of current checkout $harnessHead"
}

$allowedHarnessPaths = @(
    "tools/acceptance/windows/README.md",
    "tools/acceptance/windows/run_p2_acceptance.ps1"
)
$changedSinceProduct = Invoke-Git @("-C", $repositoryRoot, "diff", "--name-only", "$ProductHead..$harnessHead")
$unexpected = @($changedSinceProduct | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_) -and $_ -notin $allowedHarnessPaths
})
if ($unexpected.Count -gt 0) {
    throw "Unexpected product changes after exact product head $ProductHead: $($unexpected -join ', ')"
}

$wheelSha = (Get-FileHash $wheelPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($wheelSha -ne $ExpectedWheelSha256.ToLowerInvariant()) {
    throw "Wheel SHA-256 mismatch. Expected $ExpectedWheelSha256, got $wheelSha"
}

$databaseShaBefore = (Get-FileHash $databasePath -Algorithm SHA256).Hash.ToLowerInvariant()
New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
$workPath = (Resolve-Path $WorkDir).Path
$venv = Join-Path $workPath ".venv"
$evidenceDir = Join-Path $workPath "evidence"
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null

if (Test-Path $venv) {
    Remove-Item $venv -Recurse -Force
}

& py -3.11 -m venv $venv
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 venv creation failed"
}

$python = Join-Path $venv "Scripts\python.exe"
$radioNews = Join-Path $venv "Scripts\radio-news.exe"
& $python -m pip install --disable-pip-version-check --force-reinstall $wheelPath
if ($LASTEXITCODE -ne 0) {
    throw "Wheel installation failed"
}
& $python -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "pip check failed"
}

$stdout = Join-Path $evidenceDir "server.stdout.log"
$stderr = Join-Path $evidenceDir "server.stderr.log"
Remove-Item $stdout, $stderr -Force -ErrorAction SilentlyContinue

$process = $null
try {
    $process = Start-Process -FilePath $radioNews -ArgumentList @(
        "serve", "--database", $databasePath,
        "--host", "127.0.0.1", "--port", "$Port"
    ) -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            throw "KPNEWS exited before readiness. See $stderr"
        }
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/healthz" -TimeoutSec 2
            if ($health.status -eq "ok") {
                $ready = $true
                break
            }
        } catch {
            # Retry until timeout.
        }
    }
    if (-not $ready) {
        throw "KPNEWS did not answer /healthz within 30 seconds"
    }

    $feedUrl = "http://127.0.0.1:$Port/api/feed"
    $feedResponse = Invoke-WebRequest $feedUrl -UseBasicParsing -TimeoutSec 10
    $feed = $feedResponse.Content | ConvertFrom-Json

    if ($ExpectedFeedCount -gt 0 -and [int]$feed.count -ne $ExpectedFeedCount) {
        throw "P1 regression: expected $ExpectedFeedCount feed items, got $($feed.count)"
    }

    $first = @($feed.items | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.story_id) }) | Select-Object -First 1
    if ($null -eq $first) {
        throw "P2 failure: no feed card contains story_id"
    }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedSourceDisplayName) -and [string]$first.source_name -ne $ExpectedSourceDisplayName) {
        throw "P1 attribution regression: expected '$ExpectedSourceDisplayName', got '$($first.source_name)'"
    }

    $storyId = [string]$first.story_id
    $storyPath = [Uri]::EscapeDataString($storyId)
    $storyUrl = "http://127.0.0.1:$Port/stories/$storyPath"
    $storyApiUrl = "http://127.0.0.1:$Port/api/stories/$storyPath"

    $storyApiResponse = Invoke-WebRequest $storyApiUrl -UseBasicParsing -TimeoutSec 10
    $story = $storyApiResponse.Content | ConvertFrom-Json
    $storyHtmlResponse = Invoke-WebRequest $storyUrl -UseBasicParsing -TimeoutSec 10
    $storyHtml = $storyHtmlResponse.Content

    if ([string]$story.story.id -ne $storyId) {
        throw "P2 failure: Story id does not match feed story_id"
    }

    foreach ($name in @("sources", "raw_items", "normalized_items", "claims", "facts", "verification_results", "provenance")) {
        if ($null -eq $story.$name -or @($story.$name).Count -lt 1) {
            throw "P2 failure: linked section '$name' is empty"
        }
    }

    foreach ($marker in @("Story", "Source", "RawItem", "NormalizedItem", "Claim", "Fact", "VerificationResult", "Provenance")) {
        if (-not $storyHtml.Contains($marker)) {
            throw "P2 failure: HTML does not contain '$marker'"
        }
    }

    $relations = @($story.provenance | ForEach-Object { [string]$_.relation })
    foreach ($requiredRelation in @("supported_by", "evaluated_by")) {
        if ($requiredRelation -notin $relations) {
            throw "P2 failure: provenance relation '$requiredRelation' is missing"
        }
    }

    Write-Utf8NoBom (Join-Path $evidenceDir "feed.json") $feedResponse.Content
    Write-Utf8NoBom (Join-Path $evidenceDir "story.json") $storyApiResponse.Content
    Write-Utf8NoBom (Join-Path $evidenceDir "story.html") $storyHtml

    Start-Process $storyUrl
    Write-Host ""
    Write-Host "P2 Story and Evidence View opened: $storyUrl" -ForegroundColor Cyan
    Write-Host "Check the visible chain: Story → RawItem/NormalizedItem → Claim → Fact → Source → VerificationResult → provenance."

    do {
        $verdict = (Read-Host "Editorial verdict: PASS or CHANGES REQUIRED").Trim().ToUpperInvariant()
    } until ($verdict -in @("PASS", "CHANGES REQUIRED"))

    $databaseShaAfter = (Get-FileHash $databasePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($databaseShaBefore -ne $databaseShaAfter) {
        throw "READ-ONLY FAILURE: SQLite SHA-256 changed"
    }

    $evidence = [ordered]@{
        schema_version = 1
        product_slice = "P2_STORY_AND_EVIDENCE_VIEW"
        pull_request = 9
        product_head = $ProductHead
        harness_head = $harnessHead
        wheel_path = $wheelPath
        wheel_sha256 = $wheelSha
        database_path = $databasePath
        database_sha256_before = $databaseShaBefore
        database_sha256_after = $databaseShaAfter
        database_unchanged = $true
        feed_endpoint = $feedUrl
        story_endpoint = $storyUrl
        feed_item_count = [int]$feed.count
        story_id = $storyId
        source_id = [string]$first.source_id
        source_name = [string]$first.source_name
        source_count = @($story.sources).Count
        raw_item_count = @($story.raw_items).Count
        normalized_item_count = @($story.normalized_items).Count
        claim_count = @($story.claims).Count
        fact_count = @($story.facts).Count
        verification_result_count = @($story.verification_results).Count
        provenance_edge_count = @($story.provenance).Count
        p1_regression = "PASS"
        p2_technical_acceptance = "PASS"
        editorial_verdict = $verdict
        accepted = ($verdict -eq "PASS")
    }

    $evidencePath = Join-Path $evidenceDir "p2-acceptance-evidence.json"
    Write-Utf8NoBom $evidencePath ($evidence | ConvertTo-Json -Depth 20)

    Write-Host ""
    Write-Host "P2 TECHNICAL ACCEPTANCE: PASS" -ForegroundColor Green
    Write-Host "P2 EDITORIAL VERDICT: $verdict"
    Write-Host "SQLite SHA-256 unchanged: $databaseShaAfter"
    Write-Host "Evidence: $evidencePath"
} finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
}
