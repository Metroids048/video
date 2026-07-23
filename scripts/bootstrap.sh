#!/usr/bin/env bash
# Bootstrap — macOS / Linux
# 用法：bash scripts/bootstrap.sh
# 或通过 npm run bootstrap 调用
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log()  { echo "[BOOTSTRAP] $*"; }
ok()   { echo "[OK] $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

log "Agent Video Studio — Bootstrap (Unix)"
log "Root: $ROOT"

# ── 1. 检查必需工具 ────────────────────────────────────────────────
log "检查 Python 3.11+..."
python3 --version >/dev/null 2>&1 || fail "未找到 python3，请安装 3.11+"
ok "$(python3 --version)"

log "检查 Node.js 22+..."
node --version >/dev/null 2>&1 || fail "未找到 node，请安装 22+"
ok "Node.js $(node --version)"

# ── 2. 创建 Python 虚拟环境 ────────────────────────────────────────
VENV="$ROOT/.venv"
if [ ! -d "$VENV" ]; then
    log "创建 Python 虚拟环境..."
    python3 -m venv "$VENV"
    ok ".venv 已创建"
else
    ok ".venv 已存在，跳过"
fi

source "$VENV/bin/activate"

# ── 3. 安装 Python 依赖 ────────────────────────────────────────────
log "安装 Python 依赖..."
pip install --quiet -e ".[dev]" || fail "pip install 失败"
ok "Python 依赖安装完成"

# ── 4. 安装/同步 Skills ────────────────────────────────────────────
log "安装项目 Skills..."
node scripts/install_skills.mjs || warn "Skills 安装失败，可运行 npm run skills:install 重试"
python scripts/sync_skills.py   || warn "Skills 同步失败，可运行 npm run skills:sync 重试"
ok "Skills 处理完成"

# ── 5. 创建必要目录 ────────────────────────────────────────────────
log "创建必要目录..."
for d in episodes/inbox episodes/active episodes/completed episodes/archived cache logs output; do
    mkdir -p "$ROOT/$d"
done
ok "目录结构就绪"

# ── 6. 创建 .env（如不存在）────────────────────────────────────────
if [ ! -f "$ROOT/.env" ] && [ -f "$ROOT/.env.example" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    ok ".env 已从 .env.example 创建（请填写真实密钥）"
fi

ok "Bootstrap 完成！运行 python -m avs doctor 验证环境。"
