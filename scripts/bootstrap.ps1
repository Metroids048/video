# Bootstrap — Windows (PowerShell 7+)
# 用法：pwsh -NoProfile -File scripts/bootstrap.ps1
# 或通过 npm run bootstrap 调用
#
# 功能：使用全局 Agent Python 安装依赖、安装/同步 Skills、创建必要目录
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
Write-Step "检查 AGENT_PYTHON (Python 3.11+)..."
$agentPython = $env:AGENT_PYTHON
if (-not $agentPython -or -not (Test-Path -LiteralPath $agentPython)) {
    Write-Fail "AGENT_PYTHON 未配置或文件不存在。请先运行全局 Agent Python 安装脚本。"
    exit 1
}
$pyVer = & $agentPython --version 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "AGENT_PYTHON 无法运行"; exit 1 }
Write-OK $pyVer

Write-Step "检查 Node.js 22+..."
$nodeVer = node --version 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "未找到 Node.js，请安装 22+"; exit 1 }
Write-OK "Node.js $nodeVer"

# ── 2. 安装 Node/Python 依赖 ───────────────────────────────────────
Write-Step "安装锁定的 Node.js 依赖..."
if (-not $DryRun) {
    npm ci
    if ($LASTEXITCODE -ne 0) { Write-Fail "npm ci 失败"; exit 1 }
}
Write-OK "Node.js 依赖安装完成"

Write-Step "安装 Python 依赖..."
if (-not $DryRun) {
    & $agentPython -m pip install --disable-pip-version-check -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { Write-Fail "pip install 失败"; exit 1 }
}
Write-OK "Python 依赖安装完成"

# ── 3. 安装/同步 Skills 与 HyperFrames 浏览器 ─────────────────────
Write-Step "安装项目 Skills..."
if (-not $DryRun) {
    node scripts/install_skills.mjs
    if ($LASTEXITCODE -ne 0) { Write-Fail "HyperFrames Skills 安装失败"; exit 1 }
    & $agentPython scripts/sync_skills.py
    if ($LASTEXITCODE -ne 0) { Write-Fail "项目 Skills 同步失败"; exit 1 }
    node node_modules/hyperframes/bin/hyperframes.mjs browser ensure
    if ($LASTEXITCODE -ne 0) { Write-Fail "HyperFrames 浏览器安装失败"; exit 1 }
}
Write-OK "Skills 处理完成"

# ── 4. 创建必要目录 ────────────────────────────────────────────────
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

# ── 5. 创建 .env（如不存在）────────────────────────────────────────
$envFile = Join-Path $ROOT ".env"
$envExample = Join-Path $ROOT ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    if (-not $DryRun) { Copy-Item $envExample $envFile }
    Write-OK ".env 已从 .env.example 创建（请填写真实密钥）"
}

Write-OK "Bootstrap 完成！运行 npm run doctor 验证环境。"
