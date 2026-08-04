param(
    [string]$Wheel = "",
    [string]$Database = "D:\kpnews\work\radio-news.sqlite",
    [string]$WorkDir = "D:\kpnews\p2-acceptance",
    [string]$BuildDir = "D:\kpnews\p2-build",
    [int]$Port = 8877,
    [int]$ExpectedFeedCount = 20,
    [string]$ExpectedSourceDisplayName = [Text.Encoding]::UTF8.GetString(
        [Convert]::FromBase64String(
            "0KDQmNCQINCd0L7QstC+0YHRgtC4IMK3INC+0YTQu9Cw0LnQvS3RgdC90LjQvNC+0Lo="
        )
    ),
    [string]$ProductHead = "1aafddaaae2747585847642b2c2ba46253fa20b4",
    [string]$ExpectedWheelSha256 = "7d2da463519e0640a8cfbd718f6779f4b82eecdf6b4e7e0b69b1e41dc6e58e9e"
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
        # Windows PowerShell 5.1 turns native stderr into ErrorRecord objects.
        # A successful native command may legitimately write progress to stderr,
        # so success is determined exclusively by the process exit code.
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

function Test-GitWorktreeRegistered(
    [string]$RepositoryRoot,
    [string]$CandidatePath
) {
    $candidateFullPath = [IO.Path]::GetFullPath($CandidatePath).TrimEnd('\')
    $worktreeList = @(Invoke-Git @(
        "-C", $RepositoryRoot,
        "worktree", "list", "--porcelain"
    ))

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

function Remove-ProductBuildWorktree(
    [string]$RepositoryRoot,
    [string]$SourcePath
) {
    if (Test-GitWorktreeRegistered $RepositoryRoot $SourcePath) {
        Invoke-Git @(
            "-C", $RepositoryRoot,
            "worktree", "remove", "--force", $SourcePath
        ) | Out-Null
    }

    Invoke-Git @(
        "-C", $RepositoryRoot,
        "worktree", "prune"
    ) | Out-Null

    if (Test-Path -LiteralPath $SourcePath) {
        Remove-Item -LiteralPath $SourcePath -Recurse -Force
    }
}

if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be between 1 and 65535"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..")).Path
$databasePath = (Resolve-Path $Database).Path

$gitTop = @(Invoke-Git @(
    "-C", $repositoryRoot,
    "rev-parse", "--show-toplevel"
))[0].Trim()
if (
    [IO.Path]::GetFullPath($gitTop).TrimEnd('\') -ne
    [IO.Path]::GetFullPath($repositoryRoot).TrimEnd('\')
) {
    throw "Acceptance script is not running from the expected repository root: $repositoryRoot"
}

$dirty = @(Invoke-Git @(
    "-C", $repositoryRoot,
    "status", "--porcelain"
))
if ($dirty.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace(($dirty -join ""))) {
    throw "Repository working tree is not clean. Commit or discard local changes before acceptance."
}

$harnessHead = @(Invoke-Git @(
    "-C", $repositoryRoot,
    "rev-parse", "HEAD"
))[0].Trim()
Invoke-Git @(
    "-C", $repositoryRoot,
    "merge-base", "--is-ancestor", $ProductHead, $harnessHead
) | Out-Null

$allowedHarnessPaths = @(
    "tools/acceptance/windows/README.md",
    "tools/acceptance/windows/run_p2_acceptance.ps1"
)
$changedSinceProduct = @(Invoke-Git @(
    "-C", $repositoryRoot,
    "diff", "--name-only", "$ProductHead..$harnessHead"
))
$unexpected = @($changedSinceProduct | Where-Object {
    -not [string]::IsNullOrWhiteSpace($_) -and $_ -notin $allowedHarnessPaths
})
if ($unexpected.Count -gt 0) {
    throw "Unexpected product changes after exact product head ${ProductHead}: $($unexpected -join ', ')"
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
$workPath = (Resolve-Path $WorkDir).Path
$evidenceDir = Join-Path $workPath "evidence"
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null

$wheelOrigin = "provided"
if ([string]::IsNullOrWhiteSpace($Wheel)) {
    New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
    $buildPath = (Resolve-Path $BuildDir).Path
    $shortHead = $ProductHead.Substring(0, 12)
    $sourcePath = Join-Path $buildPath "source-$shortHead"
    $distPath = Join-Path $buildPath "dist-$shortHead"

    Remove-ProductBuildWorktree $repositoryRoot $sourcePath
    if (Test-Path -LiteralPath $distPath) {
        Remove-Item -LiteralPath $distPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $distPath -Force | Out-Null

    Invoke-Git @(
        "-C", $repositoryRoot,
        "worktree", "add", "--quiet", "--detach",
        $sourcePath, $ProductHead
    ) | Out-Null

    try {
        $builtHead = @(Invoke-Git @(
            "-C", $sourcePath,
            "rev-parse", "HEAD"
        ))[0].Trim()
        if ($builtHead -ne $ProductHead) {
            throw "Detached build worktree is on $builtHead instead of $ProductHead"
        }

        $buildDirty = @(Invoke-Git @(
            "-C", $sourcePath,
            "status", "--porcelain"
        ))
        if (
            $buildDirty.Count -gt 0 -and
            -not [string]::IsNullOrWhiteSpace(($buildDirty -join ""))
        ) {
            throw "Detached product worktree is not clean"
        }

        $buildOutput = @(Invoke-NativeCommand "py" @(
            "-3.11", "-m", "pip", "wheel",
            "--disable-pip-version-check",
            "--no-deps",
            "--wheel-dir", $distPath,
            $sourcePath
        ) "Building the exact-head wheel from Git failed")
        $buildOutput | ForEach-Object { Write-Host $_ }

        $wheels = @(Get-ChildItem $distPath -Filter "*.whl" -File)
        if ($wheels.Count -ne 1) {
            throw "Expected exactly one wheel in $distPath, found $($wheels.Count)"
        }

        $wheelPath = $wheels[0].FullName
        $ExpectedWheelSha256 = (
            Get-FileHash $wheelPath -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        $wheelOrigin = "git-build"

        $pythonVersion = @(
            Invoke-NativeCommand "py" @("-3.11", "--version") `
                "Reading Python version failed"
        ) -join " "

        $buildEvidence = [ordered]@{
            schema_version = 1
            product_head = $ProductHead
            harness_head = $harnessHead
            source_worktree = $sourcePath
            wheel_path = $wheelPath
            wheel_sha256 = $ExpectedWheelSha256
            built_from_clean_detached_worktree = $true
            python = $pythonVersion.Trim()
        }
        Write-Utf8NoBom (
            Join-Path $evidenceDir "p2-wheel-build-evidence.json"
        ) ($buildEvidence | ConvertTo-Json -Depth 10)
    } finally {
        Remove-ProductBuildWorktree $repositoryRoot $sourcePath
    }
} else {
    $wheelPath = (Resolve-Path $Wheel).Path
}

$wheelSha = (
    Get-FileHash $wheelPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($wheelSha -ne $ExpectedWheelSha256.ToLowerInvariant()) {
    throw "Wheel SHA-256 mismatch. Expected $ExpectedWheelSha256, got $wheelSha"
}

$databaseShaBefore = (
    Get-FileHash $databasePath -Algorithm SHA256
).Hash.ToLowerInvariant()

$venv = Join-Path $workPath ".venv"
if (Test-Path -LiteralPath $venv) {
    Remove-Item -LiteralPath $venv -Recurse -Force
}

$venvOutput = @(Invoke-NativeCommand "py" @(
    "-3.11", "-m", "venv", $venv
) "Python 3.11 venv creation failed")
$venvOutput | ForEach-Object { Write-Host $_ }

$python = Join-Path $venv "Scripts\python.exe"
$radioNews = Join-Path $venv "Scripts\radio-news.exe"

$installOutput = @(Invoke-NativeCommand $python @(
    "-m", "pip", "install",
    "--disable-pip-version-check",
    "--force-reinstall",
    $wheelPath
) "Wheel installation failed")
$installOutput | ForEach-Object { Write-Host $_ }

$pipCheckOutput = @(Invoke-NativeCommand $python @(
    "-m", "pip", "check"
) "pip check failed")
$pipCheckOutput | ForEach-Object { Write-Host $_ }

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
            $health = Invoke-RestMethod \
                "http://127.0.0.1:$Port/healthz" -TimeoutSec 2
            if ($health.status -eq "ok") {
                $ready = $true
                break
            }
        } catch {
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

    $first = @($feed.items | Where-Object {
        -not [string]::IsNullOrWhiteSpace([string]$_.story_id)
    }) | Select-Object -First 1
    if ($null -eq $first) {
        throw "P2 failure: no feed card contains story_id"
    }
    if (
        -not [string]::IsNullOrWhiteSpace($ExpectedSourceDisplayName) -and
        [string]$first.source_name -ne $ExpectedSourceDisplayName
    ) {
        throw "P1 attribution regression: expected '$ExpectedSourceDisplayName', got '$($first.source_name)'"
    }

    $storyId = [string]$first.story_id
    $storyPath = [Uri]::EscapeDataString($storyId)
    $storyUrl = "http://127.0.0.1:$Port/stories/$storyPath"
    $storyApiUrl = "http://127.0.0.1:$Port/api/stories/$storyPath"

    $storyApiResponse = Invoke-WebRequest \
        $storyApiUrl -UseBasicParsing -TimeoutSec 10
    $story = $storyApiResponse.Content | ConvertFrom-Json
    $storyHtmlResponse = Invoke-WebRequest \
        $storyUrl -UseBasicParsing -TimeoutSec 10
    $storyHtml = $storyHtmlResponse.Content

    if ([string]$story.story.id -ne $storyId) {
        throw "P2 failure: Story id does not match feed story_id"
    }

    foreach ($name in @(
        "sources", "raw_items", "normalized_items", "claims",
        "facts", "verification_results", "provenance"
    )) {
        if ($null -eq $story.$name -or @($story.$name).Count -lt 1) {
            throw "P2 failure: linked section '$name' is empty"
        }
    }

    foreach ($marker in @(
        "Story", "Source", "RawItem", "NormalizedItem",
        "Claim", "Fact", "VerificationResult", "Provenance"
    )) {
        if (-not $storyHtml.Contains($marker)) {
            throw "P2 failure: HTML does not contain '$marker'"
        }
    }

    $relations = @($story.provenance | ForEach-Object {
        [string]$_.relation
    })
    foreach ($requiredRelation in @("supported_by", "evaluated_by")) {
        if ($requiredRelation -notin $relations) {
            throw "P2 failure: provenance relation '$requiredRelation' is missing"
        }
    }

    Write-Utf8NoBom (
        Join-Path $evidenceDir "feed.json"
    ) $feedResponse.Content
    Write-Utf8NoBom (
        Join-Path $evidenceDir "story.json"
    ) $storyApiResponse.Content
    Write-Utf8NoBom (
        Join-Path $evidenceDir "story.html"
    ) $storyHtml

    Start-Process $storyUrl
    Write-Host ""
    Write-Host "P2 Story and Evidence View opened: $storyUrl" -ForegroundColor Cyan
    Write-Host "Check Story, Source, RawItem, NormalizedItem, Claim, Fact, VerificationResult, and Provenance."

    do {
        $verdict = (
            Read-Host "Editorial verdict: PASS or CHANGES REQUIRED"
        ).Trim().ToUpperInvariant()
    } until ($verdict -in @("PASS", "CHANGES REQUIRED"))

    $databaseShaAfter = (
        Get-FileHash $databasePath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($databaseShaBefore -ne $databaseShaAfter) {
        throw "READ-ONLY FAILURE: SQLite SHA-256 changed"
    }

    $evidence = [ordered]@{
        schema_version = 1
        product_slice = "P2_STORY_AND_EVIDENCE_VIEW"
        pull_request = 9
        product_head = $ProductHead
        harness_head = $harnessHead
        wheel_origin = $wheelOrigin
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

    $evidencePath = Join-Path \
        $evidenceDir "p2-acceptance-evidence.json"
    Write-Utf8NoBom $evidencePath (
        $evidence | ConvertTo-Json -Depth 20
    )

    Write-Host ""
    Write-Host "P2 TECHNICAL ACCEPTANCE: PASS" -ForegroundColor Green
    Write-Host "P2 EDITORIAL VERDICT: $verdict"
    Write-Host "Wheel origin: $wheelOrigin"
    Write-Host "Wheel SHA-256: $wheelSha"
    Write-Host "SQLite SHA-256 unchanged: $databaseShaAfter"
    Write-Host "Evidence: $evidencePath"
} finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
        $process.WaitForExit()
    }
}
