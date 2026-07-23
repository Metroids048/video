# Bootstrap — Windows (PowerShell 7+)
# 用法：pwsh -NoProfile -File scripts/bootstrap.ps1
# 或通过 npm run bootstrap 调用
#
# 功能：创建 Python venv、安装依赖、安装/同步 Skills、创建必要目录
# 不会写入真实密钥。

param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = Split-Path $PSScriptRoot -Parent
Set-Location $ROOT

function Write-Step($msg) { Write-Host "[BOOTSTRAP] $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

Write-Step "Agent Video Studio — Bootstrap (Windows)"
Write-Step "DryRun=$DryRun | Root=$ROOT"

# ── 1. 检查必需工具 ────────────────────────────────────────────────
Write-Step "检查 Python 3.11+..."
$pyVer = python --version 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "未找到 Python，请安装 3.11+"; exit 1 }
Write-OK $pyVer

Write-Step "检查 Node.js 22+..."
$nodeVer = node --version 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "未找到 Node.js，请安装 22+"; exit 1 }
Write-OK "Node.js $nodeVer"

# ── 2. 创建 Python 虚拟环境 ────────────────────────────────────────
$VENV = Join-Path $ROOT ".venv"
if (-not (Test-Path $VENV)) {
    Write-Step "创建 Python 虚拟环境..."
    if (-not $DryRun) { python -m venv $VENV }
    Write-OK ".venv 已创建"
} else {
    Write-OK ".venv 已存在，跳过"
}

# ── 3. 安装 Python 依赖 ────────────────────────────────────────────
Write-Step "安装 Python 依赖..."
$PIP = Join-Path $VENV "Scripts\pip.exe"
if (-not $DryRun) {
    & $PIP install --quiet -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { Write-Fail "pip install 失败"; exit 1 }
}
Write-OK "Python 依赖安装完成"

# ── 4. 安装/同步 Skills ────────────────────────────────────────────
Write-Step "安装项目 Skills..."
if (-not $DryRun) {
    node scripts/install_skills.mjs
    if ($LASTEXITCODE -ne 0) { Write-Warn "Skills 安装失败，可运行 npm run skills:install 重试" }
    python scripts/sync_skills.py
    if ($LASTEXITCODE -ne 0) { Write-Warn "Skills 同步失败，可运行 npm run skills:sync 重试" }
}
Write-OK "Skills 处理完成"

# ── 5. 创建必要目录 ────────────────────────────────────────────────
Write-Step "创建必要目录..."
$dirs = @(
    "episodes/inbox", "episodes/active", "episodes/completed", "episodes/archived",
    "cache", "logs", "output"
)
foreach ($d in $dirs) {
    $p = Join-Path $ROOT $d
    if (-not (Test-Path $p)) {
        if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
        Write-OK "  创建 $d"
    }
}

# ── 6. 创建 .env（如不存在）────────────────────────────────────────
$envFile = Join-Path $ROOT ".env"
$envExample = Join-Path $ROOT ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    if (-not $DryRun) { Copy-Item $envExample $envFile }
    Write-OK ".env 已从 .env.example 创建（请填写真实密钥）"
}

Write-OK "Bootstrap 完成！运行 python -m avs doctor 验证环境。"
