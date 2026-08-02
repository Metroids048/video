#!/usr/bin/env bash
# cut.skill 一键安装脚本
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --all
#   curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --agent claude
#
# 国内网络不稳定时可改用镜像：
#   curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash
#
# 选项：
#   --agent <name>   目标 agent（codex/claude/opencode/kimi/qwen/glm），可逗号分隔
#   --all            安装到全部 6 家 agent
#   --user           安装到用户级目录（默认）
#   --project        安装到当前项目目录
#   --repo <github>  自定义仓库（默认 ygtec/cut.skill）
#   --ref <git-ref>  自定义分支/tag（默认 main）
#   --mirror <url>   指定 git clone 镜像前缀（如 https://gh-proxy.com/）
#   --force          覆盖已存在的安装
#   --help           显示帮助

set -euo pipefail

# 默认值
REPO="ygtec/cut.skill"
REF="main"
AGENTS=""
ALL=false
SCOPE="user"
FORCE=false
MIRROR=""  # 用户指定的镜像

# 颜色（TTY 时启用）
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$'\033[1m'
  RED=$'\033[31m'
  GREEN=$'\033[32m'
  YELLOW=$'\033[33m'
  CYAN=$'\033[36m'
  DIM=$'\033[2m'
  RESET=$'\033[0m'
else
  BOLD="" RED="" GREEN="" YELLOW="" CYAN="" DIM="" RESET=""
fi

# 解析参数
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENTS="$2"; shift 2 ;;
    --all) ALL=true; shift ;;
    --user) SCOPE="user"; shift ;;
    --project) SCOPE="project"; shift ;;
    --repo) REPO="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --mirror) MIRROR="$2"; shift 2 ;;
    --force) FORCE=true; shift ;;
    --help|-h)
      cat <<EOF
${BOLD}cut.skill 一键安装脚本${RESET}

${BOLD}用法：${RESET}
  curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- [options]

${BOLD}选项：${RESET}
  ${CYAN}--agent <name>${RESET}   目标 agent（codex/claude/opencode/kimi/qwen/glm），可逗号分隔
  ${CYAN}--all${RESET}            安装到全部 6 家 agent
  ${CYAN}--user${RESET}           安装到用户级目录（默认）
  ${CYAN}--project${RESET}        安装到当前项目目录
  ${CYAN}--repo <github>${RESET}  自定义仓库（默认 ygtec/cut.skill）
  ${CYAN}--ref <git-ref>${RESET}  自定义分支/tag（默认 main）
  ${CYAN}--mirror <url>${RESET}   git clone 镜像前缀（如 https://gh-proxy.com/）
  ${CYAN}--force${RESET}          覆盖已存在的安装
  ${CYAN}--help${RESET}           显示此帮助

${BOLD}国内网络不稳定时：${RESET}
  # 方式 A：用镜像下载本脚本
  curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

  # 方式 B：手动指定镜像让 git clone 走代理
  curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --mirror https://gh-proxy.com/

  # 方式 C：完全离线（先手动 clone，再用 Python 跑）
  git clone https://gh-proxy.com/https://github.com/ygtec/cut.skill.git
  cd cut.skill && bash installer/install.sh --all --source .

${BOLD}示例：${RESET}
  ${DIM}# 安装到所有 agent${RESET}
  curl ... | bash -s -- --all

  ${DIM}# 仅安装到 Claude${RESET}
  curl ... | bash -s -- --agent claude
EOF
      exit 0
      ;;
    *)
      echo "${RED}未知参数: $1${RESET}" >&2
      exit 1
      ;;
  esac
done

echo "${BOLD}cut.skill 安装器${RESET}"
echo "${DIM}仓库: ${REPO}@${REF}${RESET}"
echo "${DIM}范围: ${SCOPE}${RESET}"
echo ""

# ---------------------------------------------------------------------------
# 1. git clone 函数：支持镜像回退
# ---------------------------------------------------------------------------
clone_repo() {
  local target_dir="$1"
  local repo="$2"
  local ref="$3"
  local mirror="$4"

  # 候选 URL 列表：用户指定镜像 → 直连 → 公共镜像
  local urls=()
  if [ -n "$mirror" ]; then
    urls+=("${mirror}https://github.com/${repo}.git")
  fi
  urls+=("https://github.com/${repo}.git")
  # 公共镜像回退（仅当用户没指定镜像时才尝试）
  if [ -z "$mirror" ]; then
    urls+=("https://gh-proxy.com/https://github.com/${repo}.git")
  fi

  for url in "${urls[@]}"; do
    echo "${CYAN}尝试: ${url}${RESET}"
    if git clone --depth 1 --branch "$ref" "$url" "$target_dir" 2>/dev/null; then
      echo "${GREEN}✓${RESET} 下载成功"
      return 0
    else
      echo "${YELLOW}⚠${RESET} 失败，尝试下一个"
      rm -rf "$target_dir" 2>/dev/null || true
    fi
  done

  echo "${RED}✗ 所有 git clone 源都失败${RESET}" >&2
  echo "" >&2
  echo "${BOLD}可能的解决方案：${RESET}" >&2
  echo "  1. 检查网络连接" >&2
  echo "  2. 用镜像：bash install.sh --mirror https://gh-proxy.com/" >&2
  echo "  3. 手动 clone 后本地运行：" >&2
  echo "     git clone https://gh-proxy.com/https://github.com/${repo}.git" >&2
  echo "     cd cut.skill && bash installer/install.sh --all --source ." >&2
  return 1
}

# ---------------------------------------------------------------------------
# 2. 检测 Node.js（优先用 Node 安装器，功能更完整）
# ---------------------------------------------------------------------------
USE_NODE=false
if command -v node >/dev/null 2>&1; then
  NODE_VERSION=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
  if [ "$NODE_VERSION" -ge 18 ]; then
    USE_NODE=true
    echo "${GREEN}✓${RESET} 检测到 Node.js $(node -v)"
  fi
fi

if [ "$USE_NODE" = "true" ]; then
  TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d -t cut-skill)
  trap "rm -rf '$TMPDIR'" EXIT

  echo "${CYAN}下载 cut.skill 仓库...${RESET}"
  if ! command -v git >/dev/null 2>&1; then
    echo "${RED}错误: 需要 git。请先安装 git${RESET}" >&2
    exit 1
  fi

  clone_repo "$TMPDIR/repo" "$REPO" "$REF" "$MIRROR" || exit 1
  rm -rf "$TMPDIR/repo/.git"

  # 检查 installer 目录是否存在（旧版本可能没有）
  if [ -f "$TMPDIR/repo/installer/cli.mjs" ]; then
    ARGS=()
    if [ "$ALL" = "true" ]; then ARGS+=("--all"); fi
    if [ -n "$AGENTS" ]; then ARGS+=("--agent" "$AGENTS"); fi
    if [ "$SCOPE" = "project" ]; then ARGS+=("--project"); else ARGS+=("--user"); fi
    if [ "$FORCE" = "true" ]; then ARGS+=("--force"); fi
    ARGS+=("--source" "$TMPDIR/repo")

    node "$TMPDIR/repo/installer/cli.mjs" install "${ARGS[@]}"
    exit $?
  else
    echo "${YELLOW}⚠${RESET} 仓库无 installer 目录（旧版本），改用纯 bash 安装"
    USE_NODE=false
  fi
fi

# ---------------------------------------------------------------------------
# 3. 纯 bash 回退方案（无 Node.js）：用 git clone + 手动复制
# ---------------------------------------------------------------------------
if [ "$USE_NODE" = "true" ]; then
  echo "${YELLOW}⚠${RESET} 使用纯 bash 安装（功能简化）"
else
  echo "${YELLOW}⚠${RESET} 未检测到 Node.js 18+，使用纯 bash 安装（功能简化）"
fi

if ! command -v git >/dev/null 2>&1; then
  echo "${RED}错误: 需要 git。请先安装 git${RESET}" >&2
  exit 1
fi

if [ -z "${TMPDIR:-}" ]; then
  TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d -t cut-skill)
  trap "rm -rf '$TMPDIR'" EXIT
  echo "${CYAN}下载 cut.skill...${RESET}"
  clone_repo "$TMPDIR/repo" "$REPO" "$REF" "$MIRROR" || exit 1
fi
rm -rf "$TMPDIR/repo/.git"

# 确定目标 agent
if [ "$ALL" = "true" ]; then
  TARGETS="codex claude opencode kimi qwen glm"
elif [ -n "$AGENTS" ]; then
  TARGETS=$(echo "$AGENTS" | tr ',' ' ')
else
  TARGETS=""
  command -v codex >/dev/null 2>&1 && TARGETS="$TARGETS codex"
  command -v claude >/dev/null 2>&1 && TARGETS="$TARGETS claude"
  command -v opencode >/dev/null 2>&1 && TARGETS="$TARGETS opencode"
  command -v kimi >/dev/null 2>&1 && TARGETS="$TARGETS kimi"
  command -v qwen >/dev/null 2>&1 && TARGETS="$TARGETS qwen"
  command -v glm >/dev/null 2>&1 && TARGETS="$TARGETS glm"
  [ -d "/Applications/Claude.app" ] && [[ "$TARGETS" != *"claude"* ]] && TARGETS="$TARGETS claude"

  if [ -z "$TARGETS" ]; then
    echo "${YELLOW}未检测到任何 agent 工具，安装到全部 6 家${RESET}"
    TARGETS="codex claude opencode kimi qwen glm"
  fi
fi

echo "${CYAN}目标: $(echo $TARGETS | tr ' ' ', ')${RESET}"
echo ""

# 安装函数
install_to_dir() {
  local target="$1"
  local agent_name="$2"

  if [ -f "$target/SKILL.md" ] && [ "$FORCE" = "false" ]; then
    echo "${YELLOW}  ⚠ $agent_name: 已安装（用 --force 覆盖）${RESET}"
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  rm -rf "$target"
  mkdir -p "$target"
  for item in SKILL.md README.md README.en.md LICENSE CHANGELOG.md CONTRIBUTING.md .gitignore references scripts agents examples tests; do
    [ -e "$TMPDIR/repo/$item" ] && cp -R "$TMPDIR/repo/$item" "$target/"
  done
  find "$target" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
  find "$target" -name node_modules -type d -exec rm -rf {} + 2>/dev/null || true
  echo "${GREEN}  ✓ $agent_name: $target${RESET}"
}

for agent in $TARGETS; do
  case "$agent" in
    codex)
      if [ "$SCOPE" = "project" ]; then DIR="./.agents/skills/cut"; else DIR="$HOME/.agents/skills/cut"; fi
      install_to_dir "$DIR" "Codex CLI"
      ;;
    claude)
      if [ "$SCOPE" = "project" ]; then DIR="./.claude/skills/cut"; else DIR="$HOME/.claude/skills/cut"; fi
      install_to_dir "$DIR" "Claude Code"
      ;;
    opencode)
      if [ "$SCOPE" = "project" ]; then DIR="./.opencode/skills/cut"; else DIR="$HOME/.config/opencode/skills/cut"; fi
      install_to_dir "$DIR" "OpenCode"
      ;;
    kimi)
      DIR="$HOME/.kimi/skills/cut"
      install_to_dir "$DIR" "Kimi Code"
      mkdir -p "$HOME/.kimi"
      CONFIG="$HOME/.kimi/skills.yaml"
      if [ ! -f "$CONFIG" ]; then
        echo "skills:" > "$CONFIG"
      fi
      if ! grep -q "name: cut" "$CONFIG" 2>/dev/null; then
        cat >> "$CONFIG" <<EOF
  - name: cut
    path: $DIR
    description: 视频剪辑操控（剪映 + Premiere）
    triggers: [剪映, CapCut, Premiere, 视频剪辑, 字幕, 转场, 特效]
    entry: SKILL.md
EOF
      fi
      ;;
    qwen)
      if [ "$SCOPE" = "project" ]; then DIR="./.qwen/skills/cut"; else DIR="$HOME/.qwen/skills/cut"; fi
      install_to_dir "$DIR" "Qwen Code"
      ;;
    glm)
      if [ "$SCOPE" = "project" ]; then DIR="./skills/cut"; else DIR="$HOME/.glm/skills/cut"; fi
      install_to_dir "$DIR" "GLM Code"
      ;;
    *)
      echo "${RED}  ✗ 未知 agent: $agent${RESET}"
      ;;
  esac
done

echo ""
echo "${BOLD}完成！${RESET}"
echo "${DIM}重启你的 agent 工具让它加载新 skill。${RESET}"
echo "${DIM}验证安装：cd ~/.glm/skills/cut/scripts && python -m cut.cli detect${RESET}"
