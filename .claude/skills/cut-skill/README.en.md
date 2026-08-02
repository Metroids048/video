# cut.skill — Unified Video Editing Control Skill

> Empower AI coding agents (Codex CLI / Claude Code / OpenCode / Kimi Code / Qwen Code / GLM Code, or any tool that supports skills or MCP) to control **JianYing/CapCut** and **Adobe Premiere Pro** — two major video editing software.

English | [中文](./README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-8%2F8%20passed-brightgreen.svg)](#tests)

## Features

- **Dual backend**: JianYing (draft file manipulation) + Premiere (pymiere)
- **Cross-platform**: Windows + macOS
- **6 core capabilities**: media import / clip splitting / subtitles & text / transitions & effects / audio mixing / export & rendering
- **4 integration forms**: pure docs / CLI / MCP Server / HTTP API
- **Multi-agent compatibility**: Codex / Claude / OpenCode / Kimi / Qwen / GLM
- **Context-aware**: reverse-read project state, media pool, timeline, selection
- **Professional director layer**: turn a one-line short-form or long-form brief into an edit plan
- **Export QA**: validate duration, bitrate, streams, resolution, and frame rate after rendering
- **Safe by design**: atomic writes, auto-backup, dry-run preview, JSON validation

## Quick Start

### One-line Install (Recommended)

**Option 1: curl one-liner** (no Node.js required)

```bash
# Install to auto-detected agents
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

# Install to a specific agent
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --agent claude

# Install to all 6 agents
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --all
```

**For users in China (unstable GitHub connection)**:

```bash
# Option A: download the script via mirror
curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

# Option B: tell git clone to use mirror
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --mirror https://gh-proxy.com/
```

**Option 2: npx directly from GitHub** (requires Node.js 18+)

```bash
# Install to auto-detected agents
npx github:ygtec/cut.skill/installer install

# Install to all 6 agents
npx github:ygtec/cut.skill/installer install --all

# Use mirror for China
npx github:ygtec/cut.skill/installer install --all --mirror https://gh-proxy.com/
```

**Option 3: Manual clone + Python** (for developers / offline)

```bash
# 1. Clone the repo (China mirror: https://gh-proxy.com/https://github.com/ygtec/cut.skill.git)
git clone https://github.com/ygtec/cut.skill.git
cd cut.skill/scripts

# 2. Create a virtual environment (avoid polluting system Python)
python -m venv .venv

# 3. Activate the virtual environment
#    macOS/Linux:
source .venv/bin/activate
#    Windows PowerShell:
.venv\Scripts\Activate.ps1
#    Windows CMD:
.venv\Scripts\activate.bat

# 4. Install Python dependencies
pip install -r requirements.txt
# Full install (with optional deps: pymiere/flask/mcp)
pip install -e ".[all]"

# 5. Verify installation
python -m cut.cli detect
# Should print detected JianYing/CapCut/Premiere installations

# 6. Start using
python -m cut.cli list-drafts              # List JianYing projects
python -m cut.cli get-state --backend jianying --project <name>
python -m cut.cli split --backend jianying --project <name> --track 0 --at 5s
```

> For subsequent uses, just run `source .venv/bin/activate` to activate the environment — no need to reinstall dependencies.

To integrate cut.skill with your agent tools (auto-create skill directories, update config files), run from the repo root:

```bash
node installer/cli.mjs install --all --source .
```

### Integrate with Agents

cut.skill can auto-install to 6 agents (creates skill directories, updates config files):

```bash
# Auto-detect installed agent tools and install
npx github:ygtec/cut.skill/installer install

# Or specify agents
npx github:ygtec/cut.skill/installer install --agent claude,codex
```

After installation, just say "detect what video editing software I have" in your agent to trigger the skill.

Supports 6 agents: Codex CLI / Claude Code / OpenCode / Kimi Code / Qwen Code / GLM Code. See [installer/README.md](./installer/README.md) and [references/agent-integration.md](./references/agent-integration.md).

### Verify Installation

```bash
# List installed locations
npx github:ygtec/cut.skill/installer list

# Or use Python directly (Option 3 users)
cd ~/.claude/skills/cut/scripts  # path varies by agent
python -m cut.cli detect
```

## Usage Examples

### CLI

```bash
# Detect environment
python -m cut.cli detect

# Read project state (must do before any modification)
python -m cut.cli get-state --backend jianying --project my_vlog

# Create a professional edit plan from one sentence
python -m cut.cli plan "Create a fast 60s travel vlog for TikTok" \
    --backend jianying --project my_vlog

# Import video
python -m cut.cli import --backend jianying --project my_vlog \
    --type video --path /path/to/clip.mp4

# Split at 5 seconds
python -m cut.cli split --backend jianying --project my_vlog --track 0 --at 5s

# Add subtitle
python -m cut.cli add-text --backend jianying --project my_vlog \
    --content "Hello World" --start 0 --duration 3000000

# Export
python -m cut.cli export --backend jianying --project my_vlog \
    --output out.mp4 --method ffmpeg

# Run post-export QA
python -m cut.cli qa --output out.mp4 --expected-duration 60s
```

### MCP

```json
{"tool": "cut.get_state", "input": {"backend": "jianying", "project": "my_vlog"}}
{"tool": "cut.create_plan", "input": {"backend": "jianying", "brief": "Create a fast 60s travel vlog for TikTok"}}
{"tool": "cut.split", "input": {"backend": "jianying", "project": "my_vlog", "track_index": 0, "at_us": 5000000}}
{"tool": "cut.quality_check", "input": {"output": "out.mp4", "expected_duration_us": 60000000}}
```

### Python

```python
from cut.jianying.draft import Draft
from cut.jianying import materials, segments, text, effects

draft = Draft.open(project_name="my_vlog")

# Import and add to timeline
mid = materials.import_video(draft, "/path/to/clip.mp4")
sid = materials.add_video_segment(draft, mid, start_us=0)

# Split at 2.5s
seg = draft.video_tracks[0].segments[0]
segments.split_segment(draft, seg, at_us=2_500_000)

# Add subtitle
text.add_subtitle(draft, "Hello World", start_us=0, duration_us=3_000_000)

# Add transition
effects.add_transition_simple(draft, draft.video_tracks[0].id, 0, preset="fade")

# Save (atomic write + auto-backup)
draft.save()
print("Done. Reopen the project in JianYing to see the result.")
```

## Project Structure

```
cut/
├── SKILL.md                       # Main entry (agent reads first)
├── installer/                     # One-line installer (npx / curl)
│   ├── cli.mjs                    # Node.js CLI
│   ├── install.sh                 # bash one-liner
│   ├── src/                       # detect/download/config logic
│   └── README.md                  # Installer docs
├── references/                    # Reference docs (loaded on demand)
│   ├── jianying-draft-schema.md   # JianYing draft file schema
│   ├── jianying-operations.md     # All JianYing operations
│   ├── premiere-operations.md     # Premiere pymiere operations
│   ├── cross-platform.md          # Cross-platform paths & differences
│   ├── context-awareness.md       # Context awareness & reverse read
│   └── agent-integration.md       # Agent integration guides
├── scripts/                       # Python core package
│   ├── cut/
│   │   ├── platform.py            # Cross-platform detection
│   │   ├── context.py             # Unified context-aware interface
│   │   ├── cli.py                 # cut-cli (22 commands)
│   │   ├── mcp_server.py          # MCP Server (14 tools)
│   │   ├── http_api.py            # Flask HTTP API (16 routes)
│   │   ├── director.py            # One-line professional edit planning
│   │   ├── quality.py             # Post-export QA
│   │   ├── jianying/              # JianYing backend
│   │   └── premiere/              # Premiere backend
│   ├── requirements.txt
│   └── setup.py
├── agents/                        # Agent-specific entry files
│   ├── AGENTS.md                  # Codex CLI
│   ├── CLAUDE.md                  # Claude Code
│   ├── OPENCODE.md                # OpenCode
│   ├── KIMI.md                    # Kimi Code
│   ├── QWEN.md                    # Qwen Code
│   └── GLM.md                     # GLM Code
├── examples/                      # End-to-end examples
│   ├── batch-cut.py               # Batch splitting
│   ├── auto-subtitle.py           # ASR auto-subtitles
│   └── multi-track.py             # Multi-track mixing + ducking
└── tests/                         # Test suite
    ├── test_draft.py
    ├── test_e2e.py
    ├── test_mcp.py
    ├── test_cli.py
    ├── test_http.py
    ├── test_regression.py
    └── run_all.py
```

## Core Concepts

### Three-Layer Abstraction

```
Agent adaptation layer (Codex/Claude/OpenCode/Kimi/Qwen/GLM)
        ↓
Integration form layer (CLI / MCP / HTTP / pure docs)
        ↓
Unified operation interface (import / split / trim / text / transition / effect / audio / export)
        ↓
Backend implementation (JianYing draft / Premiere pymiere)
        ↓
Cross-platform abstraction (platform.detect)
```

### Context Awareness

**Always read state before modifying.** Before any modification, agents should call:

```python
from cut.context import get_project_state
state = get_project_state(backend="jianying", project_name="my_vlog")
```

Get a project snapshot first, then decide the next action. This avoids blind edits that could corrupt the draft.

### How JianYing Draft Manipulation Works

JianYing has no official API, but its project file `draft_content.json` is JSON with a publicly parseable structure. This skill reads/writes the file directly:

1. Parse the three-layer structure: materials → tracks → segments
2. Modify fields
3. Atomic write (temp file + os.replace — failure won't corrupt the original)
4. Auto-backup to `.bak.<timestamp>.<rand>`
5. User reopens the project in JianYing to see the result

No need for JianYing to be running — offline editing, most stable approach.

### Premiere pymiere Integration

Premiere has an official extension mechanism (CEP + ExtendScript); pymiere wraps most common operations. This skill communicates with a running Premiere instance via pymiere — all operations reflect in the UI in real time.

### Professional Director Layer

`cut.director.create_edit_plan()` turns a one-line brief into a deterministic edit plan: format, platform, target duration, pacing, story structure, subtitles, sound mix, color, export, and QA. Agents should plan first, then execute concrete CLI/MCP operations.

### Export QA

`cut.quality.analyze_export()` validates rendered files with ffprobe output: duration, bitrate, video/audio streams, resolution, and frame rate. Automated exports should run QA as the final step.

## Tests

```bash
cd cut.skill
python tests/run_all.py
```

Test coverage (9 suites, all assertions pass):

| Suite | Description | Count |
|---|---|---|
| `test_draft.py` | Draft parsing, splitting, subtitles, backup | 4 |
| `test_e2e.py` | End-to-end workflow: import → split → subtitles → transitions → effects → ducking → save → reverse read | 20 |
| `test_mcp.py` | MCP 14 tools dispatch_tool verification | 16 |
| `test_cli.py` | CLI 22 commands: help, time formats, dry-run, error handling, plan | 11 |
| `test_pro.py` | Pro editing features: auto-edit, viral templates, LUT, beat sync, pro effects | 4 |
| `test_http.py` | HTTP API 16 routes end-to-end verification | 11 |
| `test_regression.py` | Bug-fix regression tests | 13 |
| `test_agent_compat.py` | Agent path, tool naming, and skill metadata compatibility | 4 |
| `test_professional_workflow.py` | Professional edit planning and export QA | 3 |

All tests run without JianYing/Premiere installed — pure Python validation of draft manipulation logic.

## Safety Rules

1. **Atomic writes**: `Draft.save()` uses temp file + os.replace; failed writes never corrupt the original
2. **Auto-backup**: defaults to `.bak.<timestamp>.<rand>`
3. **Save project before Premiere ops**: pymiere's undo is unreliable
4. **No concurrent draft writes**: use file locks or serialize calls
5. **Never modify `draft_meta_info.json`**: it's an index file
6. **Use HTTP API for large exports**: CLI blocks, MCP times out at 30s
7. **No shell injection in ffmpeg commands**: list-form command construction

## Compatibility

- **JianYing**: 5.0+ (draft schema differs between 4.x and 5.x; 5.x is the baseline)
- **CapCut**: identical draft schema to JianYing
- **Premiere Pro**: 2022+
- **Python**: 3.9+
- **OS**: Windows + macOS

## Limitations

### JianYing

- Edits require reopening the project in JianYing to take effect (no hot-reload)
- Large exports only via UI automation (fragile) or ffmpeg simple concat (no effects)
- Cannot read selection state or playhead position

### Premiere

- Premiere must be running
- First connection is slow (2-3s)
- QE DOM operations are version-dependent and may be unstable

## Documentation Navigation

| What you want | Where to look |
|---|---|
| Quick start | `SKILL.md` |
| Understand JianYing draft structure | `references/jianying-draft-schema.md` |
| JianYing operation parameters | `references/jianying-operations.md` |
| Premiere operations | `references/premiere-operations.md` |
| Cross-platform issues | `references/cross-platform.md` |
| Context awareness | `references/context-awareness.md` |
| One-line professional edit planning and export QA | `references/professional-workflow.md` |
| Integrate with an agent | `references/agent-integration.md` |
| Full examples | `examples/*.py` |
| Contribute code | `CONTRIBUTING.md` |
| Changelog | `CHANGELOG.md` |

## Contributing

Issues and Pull Requests welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT License. See [LICENSE](./LICENSE).

## Acknowledgements

- JianYing draft structure references community reverse-engineering work
- pymiere by Quentin McGaw
- MCP protocol by Anthropic
