# cut-skill Installer

> One-command installer for [cut.skill](https://github.com/ygtec/cut.skill) — unified video editing control skill for AI agents.

## Quick Start

### Option 1: curl one-liner (no Node.js required)

```bash
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash
```

Install to a specific agent:

```bash
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --agent claude
```

Install to all 6 agents:

```bash
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --all
```

**For users in China (unstable GitHub connection)**:

```bash
# Option A: download the script via mirror
curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

# Option B: tell git clone to use mirror
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --mirror https://gh-proxy.com/
```

### Option 2: npx from GitHub (requires Node.js 18+)

```bash
# Install to auto-detected agents
npx github:ygtec/cut.skill/installer install

# Install to all 6 agents
npx github:ygtec/cut.skill/installer install --all

# Install to a specific agent
npx github:ygtec/cut.skill/installer install --agent claude

# Use mirror for China
npx github:ygtec/cut.skill/installer install --all --mirror https://gh-proxy.com/
```

### Option 3: clone & run (offline)

```bash
# Clone (China mirror: prefix with https://gh-proxy.com/)
git clone https://github.com/ygtec/cut.skill.git
cd cut.skill/scripts

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\Activate.ps1     # Windows PowerShell

# Install Python dependencies
pip install -r requirements.txt
pip install -e ".[all]"          # full install with optional deps

# Verify
python -m cut.cli detect

# Then install to agents (from repo root)
cd ..
node installer/cli.mjs install --all --source .
```

## Commands

After cloning the repo, you can run the CLI locally:

```bash
node cli.mjs install [options]    # Install to agents
node cli.mjs uninstall [options]  # Remove from agents
node cli.mjs list                 # Show installed locations
node cli.mjs update               # Update to latest version
node cli.mjs detect               # Detect installed agent tools
```

Or use npx from GitHub directly (no clone needed):

```bash
npx github:ygtec/cut.skill/installer <command> [options]
```

## Install Options

| Option | Description |
|---|---|
| `--agent <name>` | Target agent (comma-separated). One of: `codex`, `claude`, `opencode`, `kimi`, `qwen`, `glm` |
| `--all` | Install to all 6 supported agents |
| `--user` | Install to user-level directory (default) |
| `--project` | Install to current project directory |
| `--source <path>` | Use local repo path instead of downloading |
| `--repo <github>` | Custom GitHub repo (default: `ygtec/cut.skill`) |
| `--ref <git-ref>` | Custom branch/tag (default: `main`) |
| `--mirror <url>` | git clone mirror prefix (e.g. `https://gh-proxy.com/` for China) |
| `--force` | Overwrite existing installation |

## Supported Agents

| Agent | User-level path | Project-level path | Config file |
|---|---|---|---|
| Codex CLI | `~/.agents/skills/cut/` | `./.agents/skills/cut/` | — |
| Claude Code | `~/.claude/skills/cut/` | `./.claude/skills/cut/` | — |
| OpenCode | `~/.config/opencode/skills/cut/` | `./.opencode/skills/cut/` | — |
| Kimi Code | `~/.kimi/skills/cut/` | — | `~/.kimi/skills.yaml` |
| Qwen Code | `~/.qwen/skills/cut/` | `./.qwen/skills/cut/` | — |
| GLM Code | `~/.glm/skills/cut/` | `./skills/cut/` | — |

## Examples

In all examples below, replace `npx github:ygtec/cut.skill/installer` with `node cli.mjs` if you've cloned the repo locally.

### Auto-detect and install

```bash
npx github:ygtec/cut.skill/installer install
# Detects installed agent tools and installs to all of them
```

### Install to specific agents

```bash
npx github:ygtec/cut.skill/installer install --agent claude,codex
```

### Install to all 6 agents (force)

```bash
npx github:ygtec/cut.skill/installer install --all --force
```

### Install to current project

```bash
cd my-project
npx github:ygtec/cut.skill/installer install --agent claude --project
# Creates .claude/skills/cut/ in current directory
```

### Offline install (no network)

```bash
# Pre-download the repo
git clone https://github.com/ygtec/cut.skill.git /tmp/cut.skill

# Install from local path
node /tmp/cut.skill/installer/cli.mjs install --all --source /tmp/cut.skill
```

### List installations

```bash
npx github:ygtec/cut.skill/installer list
```

Output:
```
cut.skill 安装位置：

  ✓ Codex CLI       [user] /home/user/.agents/skills/cut
  ✓ Claude Code     [user] /home/user/.claude/skills/cut
  ✓ GLM Code        [user] /home/user/.glm/skills/cut
```

### Uninstall

```bash
npx github:ygtec/cut.skill/installer uninstall --agent claude
npx github:ygtec/cut.skill/installer uninstall --all
```

### Update

```bash
npx github:ygtec/cut.skill/installer update
# Re-downloads and reinstalls to all previously installed locations
```

## How It Works

1. **Download**: `git clone` (preferred) or HTTPS zip download
2. **Detect**: Check which agent tools are installed (`codex`, `claude`, etc.)
3. **Install**: Copy skill files to each agent's skill directory
4. **Configure**: For Kimi, update `skills.yaml`; directory-scanning agents load `SKILL.md` from their skills folder
5. **Verify**: Check `SKILL.md` exists in each target directory

## Files

```
installer/
├── package.json       # npm package definition
├── cli.mjs            # Node.js CLI entry (main)
├── install.sh         # Bash one-liner installer (fallback)
├── src/
│   ├── agents.mjs     # Agent detection & installation logic
│   ├── download.mjs   # GitHub download (git + HTTPS)
│   └── colors.mjs     # Terminal colors (no dependencies)
└── README.md          # This file
```

## License

MIT
