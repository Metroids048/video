param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $Root).Path
$PreserveName = "第一期视频_7x24自动交易"
$Preserve = Join-Path $Root $PreserveName

if (-not (Test-Path -LiteralPath $Preserve -PathType Container)) {
    throw "保护目录不存在，拒绝执行任何删除：$Preserve"
}

# Project/runtime/resource directories that are NOT historical episode residue.
$ProtectedTopLevel = @(
    ".git", ".agents", ".claude", ".cursor", ".venv", "venv", "node_modules",
    "assets", "config", "docs", "episodes", "fixtures", "knowledge", "renderers", "reports",
    "schemas", "scripts", "skills-src", "src", "templates", "tests",
    "third_party_skills", "vendor", $PreserveName
)

$KnownLegacyRootFiles = @(
    "AI量化交易视频项目完成报告.md", "AI量化交易账号完整方案.md",
    "DELIVERY_REPORT.md", "FINAL_COMPLETION_REPORT.md", "FINAL_EXECUTION_REPORT.md",
    "FINAL_VIDEO_QUALITY_CLOSURE.md", "PLEASE_VERIFY_VIDEO.md", "PROGRESS_UPDATE.md",
    "REAL_PROGRESS_REPORT.md", "RENDERING_PROGRESS.md", "TASK_COMPLETION_SUMMARY.txt",
    "TASK_EXECUTION_REPORT.md", "VIDEO_FIX_REPORT.md", "create_video_with_jianying.py",
    "create_visuals.py", "final_summary.py", "generate_voiceover.py"
)

$MediaExtensions = @(
    ".mp4", ".mov", ".mkv", ".webm", ".avi",
    ".wav", ".mp3", ".m4a", ".aac", ".flac",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".srt", ".ass"
)

$Candidates = New-Object System.Collections.Generic.List[string]

foreach ($name in $KnownLegacyRootFiles) {
    $p = Join-Path $Root $name
    if (Test-Path -LiteralPath $p) { $Candidates.Add($p) }
}

# User requested aggressive slimming: any top-level directory that is not part
# of the frozen project/runtime/resource set is treated as historical residue.
Get-ChildItem -LiteralPath $Root -Directory -Force | ForEach-Object {
    if ($ProtectedTopLevel -notcontains $_.Name) {
        $Candidates.Add($_.FullName)
    }
}

# Top-level historical media are safe cleanup candidates. Do not recursively
# scan protected source/plugin/project directories for media deletion.
Get-ChildItem -LiteralPath $Root -File -Force | ForEach-Object {
    if ($MediaExtensions -contains $_.Extension.ToLowerInvariant()) {
        $Candidates.Add($_.FullName)
    }
}

# Old generated Episode work is disposable; keep only bucket skeletons.
foreach ($bucket in @("active", "completed", "archived")) {
    $bucketPath = Join-Path (Join-Path $Root "episodes") $bucket
    if (Test-Path -LiteralPath $bucketPath -PathType Container) {
        Get-ChildItem -LiteralPath $bucketPath -Force | Where-Object { $_.Name -ne ".gitkeep" } | ForEach-Object {
            $Candidates.Add($_.FullName)
        }
    }
}

$quantFixture = Join-Path $Root "fixtures\golden-ai-quant"
if (Test-Path -LiteralPath $quantFixture) { $Candidates.Add($quantFixture) }

$Candidates = @($Candidates | Sort-Object -Unique)

Write-Host "Creator OS V2 local cleanup"
Write-Host "Root:     $Root"
Write-Host "Preserve: $Preserve"
Write-Host "Mode:     $(if ($Apply) { 'APPLY' } else { 'DRY-RUN' })"
Write-Host ""

if ($Candidates.Count -eq 0) {
    Write-Host "No recognized historical artifacts found."
    exit 0
}

foreach ($p in $Candidates) {
    if ($p.StartsWith($Preserve, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "SKIP protected: $p"
        continue
    }
    Write-Host "DELETE candidate: $p"
    if ($Apply) {
        Remove-Item -LiteralPath $p -Recurse -Force
    }
}

Write-Host ""
if ($Apply) {
    Write-Host "Cleanup applied. Preserved: $Preserve"
} else {
    Write-Host "Dry-run only. Review the list, then rerun with -Apply."
}
Write-Host "Protected project/runtime/plugin/Skill directories were not recursively cleaned."
