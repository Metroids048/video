# cut.skill — 统一视频剪辑操控 Skill

> 让 AI 编程 agent（Codex CLI / Claude Code / OpenCode / Kimi Code / Qwen Code / GLM Code 等任意支持 skill 或 MCP 的工具）能够操控 **剪映 (JianYing/CapCut)** 与 **Adobe Premiere Pro** 两款视频剪辑软件。

[English](./README.en.md) | 中文

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-8%2F8%20passed-brightgreen.svg)](#测试)

## 特性

- **双后端支持**：剪映（draft 文件操控）+ Premiere（pymiere）
- **跨平台**：Windows + macOS
- **6 大核心能力**：素材导入 / 剪辑裁切 / 字幕文本 / 特效转场 / 音频混音 / 导出渲染
- **6 大专业能力**（基于剪映大神工作流调研）：
  - 🎬 **一键成片**：`auto-edit` 自动套模板+转场+调色+字幕+ducking
  - 📹 **爆款模板**：8种（教程/测评/vlog/知识/剧情/对比/情感/卡点），含黄金3秒钩子结构
  - 🎨 **调色 LUT**：7种（青橙/赛博朋克/日系/小清新/黑金/复古/莫兰迪），可生成 .cube 文件
  - ✨ **专业转场**：8种（不透明度/闪白闪黑/推拉/动态模糊/文字蒙版等）
  - 💬 **花字字幕**：10种预设 + ASR 自动字幕（whisper 集成）
  - 🎵 **节拍卡点**：BGM 节拍识别 + 片段自动对齐
- **模仿爆款**：给定参考视频元数据，生成同类型视频
- **4 种集成形态**：纯文档 / CLI / MCP Server / HTTP API
- **多家 agent 适配**：Codex / Claude / OpenCode / Kimi / Qwen / GLM
- **上下文感知**：反向读取项目状态、素材池、时间轴、选中片段
- **专业导演层**：一句话生成长视频/短视频剪辑计划，覆盖节奏、字幕、混音、调色、导出与 QA
- **导出验收**：用 ffprobe 检查时长、码率、视频/音频流、分辨率和帧率
- **安全设计**：原子写入、自动备份、dry-run 预览、JSON 校验

详见 [`references/pro-features.md`](./references/pro-features.md)

## 快速开始

### 一键安装（推荐）

**方式 1：curl 一键脚本**（不需要 Node.js）

```bash
# 安装到自动检测到的 agent
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

# 安装到指定 agent
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --agent claude

# 安装到全部 6 家 agent
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --all
```

**国内网络不稳定时用镜像**：

```bash
# 方式 A：用镜像下载脚本
curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

# 方式 B：指定镜像让 git clone 走代理
curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash -s -- --mirror https://gh-proxy.com/
```

**方式 2：npx 直接从 GitHub 跑**（需要 Node.js 18+）

```bash
# 安装到自动检测到的 agent
npx github:ygtec/cut.skill/installer install

# 安装到全部 6 家 agent
npx github:ygtec/cut.skill/installer install --all

# 国内镜像
npx github:ygtec/cut.skill/installer install --all --mirror https://gh-proxy.com/
```

**方式 3：手动 clone + Python 运行**（适合开发者/离线环境）

```bash
# 1. clone 仓库（国内可用镜像：https://gh-proxy.com/https://github.com/ygtec/cut.skill.git）
git clone https://github.com/ygtec/cut.skill.git
cd cut.skill/scripts

# 2. 创建虚拟环境（避免污染系统 Python）
python -m venv .venv

# 3. 激活虚拟环境
#    macOS/Linux:
source .venv/bin/activate
#    Windows PowerShell:
.venv\Scripts\Activate.ps1
#    Windows CMD:
.venv\Scripts\activate.bat

# 4. 安装 Python 依赖
pip install -r requirements.txt
# 全功能安装（含 pymiere/flask/mcp 等可选依赖）
pip install -e ".[all]"

# 5. 验证安装
python -m cut.cli detect
# 应输出本机剪映/CapCut/Premiere 安装情况

# 6. 开始使用
python -m cut.cli list-drafts              # 列出剪映项目
python -m cut.cli get-state --backend jianying --project <项目名>
python -m cut.cli split --backend jianying --project <项目名> --track 0 --at 5s
```

> 后续使用时只需 `source .venv/bin/activate` 激活环境即可，无需重复安装依赖。

如需把 cut.skill 配置到你的 agent 工具（自动创建 skill 目录、更新配置文件），在仓库根目录运行：

```bash
node installer/cli.mjs install --all --source .
```

### 集成到 agent

cut.skill 支持自动安装到 6 家 agent（自动创建 skill 目录、更新配置文件）：

```bash
# 自动检测本机已安装的 agent 工具并安装
npx github:ygtec/cut.skill/installer install

# 或指定 agent
npx github:ygtec/cut.skill/installer install --agent claude,codex
```

安装完成后，在 agent 中直接说“检测一下我电脑上有什么视频剪辑软件”即可触发 skill。

支持 6 家 agent：Codex CLI / Claude Code / OpenCode / Kimi Code / Qwen Code / GLM Code。详见 [installer/README.md](./installer/README.md) 和 [references/agent-integration.md](./references/agent-integration.md)。

### 验证安装

```bash
# 查看安装位置
npx github:ygtec/cut.skill/installer list

# 或直接用 Python（方式 3 用户）
cd ~/.claude/skills/cut/scripts  # 路径因 agent 而异
python -m cut.cli detect
```

## 使用示例

### CLI

```bash
# 检测环境
python -m cut.cli detect

# 读取项目状态（修改前必做）
python -m cut.cli get-state --backend jianying --project my_vlog

# 一句话生成专业剪辑计划
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音，节奏轻快" \
    --backend jianying --project my_vlog

# 导入视频
python -m cut.cli import --backend jianying --project my_vlog \
    --type video --path /path/to/clip.mp4

# 在 5 秒处切分
python -m cut.cli split --backend jianying --project my_vlog --track 0 --at 5s

# 加字幕
python -m cut.cli add-text --backend jianying --project my_vlog \
    --content "Hello World" --start 0 --duration 3000000

# 导出
python -m cut.cli export --backend jianying --project my_vlog \
    --output out.mp4 --method ffmpeg

# 导出后 QA
python -m cut.cli qa --output out.mp4 --expected-duration 60s
```

### MCP

```json
{"tool": "cut.get_state", "input": {"backend": "jianying", "project": "my_vlog"}}
{"tool": "cut.create_plan", "input": {"backend": "jianying", "brief": "自动做一个60秒旅行vlog，适合抖音"}}
{"tool": "cut.split", "input": {"backend": "jianying", "project": "my_vlog", "track_index": 0, "at_us": 5000000}}
{"tool": "cut.quality_check", "input": {"output": "out.mp4", "expected_duration_us": 60000000}}
```

### Python

```python
from cut.jianying.draft import Draft
from cut.jianying import materials, segments, text, effects

draft = Draft.open(project_name="my_vlog")

# 导入并加到时间轴
mid = materials.import_video(draft, "/path/to/clip.mp4")
sid = materials.add_video_segment(draft, mid, start_us=0)

# 在 2.5s 处切分
seg = draft.video_tracks[0].segments[0]
segments.split_segment(draft, seg, at_us=2_500_000)

# 加字幕
text.add_subtitle(draft, "Hello World", start_us=0, duration_us=3_000_000)

# 加转场
effects.add_transition_simple(draft, draft.video_tracks[0].id, 0, preset="fade")

# 保存（原子写入 + 自动备份）
draft.save()
print("完成。请在剪映中重新打开项目查看。")
```

## 项目结构

```
cut/
├── SKILL.md                       # 主入口（agent 首读）
├── installer/                     # 一键安装器（npx / curl）
│   ├── cli.mjs                    # Node.js CLI
│   ├── install.sh                 # bash 一键脚本
│   ├── src/                       # 检测/下载/配置逻辑
│   └── README.md                  # 安装器文档
├── references/                    # 参考文档（按需加载）
│   ├── jianying-draft-schema.md   # 剪映 draft 文件结构详解
│   ├── jianying-operations.md     # 剪映所有操作详解
│   ├── premiere-operations.md     # Premiere pymiere 操作详解
│   ├── cross-platform.md          # 跨平台路径与差异
│   ├── context-awareness.md       # 上下文感知与反向读取
│   └── agent-integration.md       # 各家 agent 集成方式
├── scripts/                       # Python 核心包
│   ├── cut/
│   │   ├── platform.py            # 跨平台检测
│   │   ├── context.py             # 统一上下文感知接口
│   │   ├── cli.py                 # cut-cli 命令行（22 命令）
│   │   ├── mcp_server.py          # MCP Server（14 工具）
│   │   ├── http_api.py            # Flask HTTP API（16 路由）
│   │   ├── director.py            # 一句话生成专业剪辑计划
│   │   ├── quality.py             # 导出后质量验收
│   │   ├── jianying/              # 剪映后端
│   │   └── premiere/              # Premiere 后端
│   ├── requirements.txt
│   └── setup.py
├── agents/                        # 各家 agent 入口
│   ├── AGENTS.md                  # Codex CLI
│   ├── CLAUDE.md                  # Claude Code
│   ├── OPENCODE.md                # OpenCode
│   ├── KIMI.md                    # Kimi Code
│   ├── QWEN.md                    # Qwen Code
│   └── GLM.md                     # GLM Code
├── examples/                      # 完整示例
│   ├── batch-cut.py               # 批量裁切
│   ├── auto-subtitle.py           # ASR 自动字幕
│   └── multi-track.py             # 双轨混剪 + ducking
└── tests/                         # 测试套件
    ├── test_draft.py
    ├── test_e2e.py
    ├── test_mcp.py
    ├── test_cli.py
    ├── test_http.py
    ├── test_regression.py
    └── run_all.py
```

## 核心概念

### 三层抽象

```
agent 适配层（Codex/Claude/OpenCode/Kimi/Qwen/GLM）
        ↓
集成形态层（CLI / MCP / HTTP / 纯文档）
        ↓
统一操作接口（plan / import / split / trim / text / transition / effect / audio / export / qa）
        ↓
后端实现层（剪映 draft 操控 / Premiere pymiere）
        ↓
跨平台抽象层（platform.detect）
```

### 上下文感知

**修改前必先读取状态**。所有 agent 在做任何修改前，应先调用：

```python
from cut.context import get_project_state
state = get_project_state(backend="jianying", project_name="my_vlog")
```

拿到项目快照后，再决定下一步操作。这避免盲目修改导致 draft 损坏。

### 剪映 draft 操控原理

剪映没有官方 API，但工程文件 `draft_content.json` 是 JSON 格式，结构公开可解析。本 skill 直接读写该文件：

1. 解析三层结构：materials → tracks → segments
2. 修改对应字段
3. 原子写入（临时文件 + os.replace，失败不破坏原文件）
4. 自动备份到 `.bak.<timestamp>.<rand>`
5. 用户在剪映中重新打开项目即可看到效果

不需要剪映运行，离线编辑，最稳定。

### Premiere pymiere 集成

Premiere 有官方扩展机制（CEP + ExtendScript），pymiere 已封装好大部分常用操作。本 skill 通过 pymiere 与运行中的 Premiere 通信，所有操作实时反映在 UI 上。

### 专业剪辑导演层

`cut.director.create_edit_plan()` 会把一句话需求转成可执行计划：识别长视频/短视频、平台、目标时长、节奏、叙事结构，并安排素材导入、粗剪、字幕、混音、调色、导出与 QA。它是确定性计划器，适合让 agent 先规划再调用具体 CLI/MCP 动作。

### 导出质量验收

`cut.quality.analyze_export()` 使用 ffprobe 输出或传入的探测 JSON，检查导出文件时长、码率、视频/音频流、分辨率和帧率。所有自动导出流程都应在最后跑 QA。

## 测试

```bash
cd cut.skill
python tests/run_all.py
```

测试覆盖（8 个套件，所有断言通过）：

| 套件 | 描述 | 项数 |
|---|---|---|
| `test_draft.py` | Draft 解析、切分、字幕、备份 | 4 |
| `test_e2e.py` | 端到端工作流：导入→切分→字幕→转场→特效→ducking→保存重读→反向读取 | 20 |
| `test_mcp.py` | MCP 14 工具的 dispatch_tool 验证 | 16 |
| `test_cli.py` | CLI 22 命令的 help、时间格式、dry-run、错误处理、plan | 11 |
| `test_pro.py` | 一键成片、爆款模板、LUT、卡点、专业特效等能力 | 4 |
| `test_http.py` | HTTP API 16 路由端到端验证 | 11 |
| `test_regression.py` | Bug 修复回归测试 | 13 |
| `test_agent_compat.py` | Agent 兼容路径、工具名、skill 元数据 | 4 |
| `test_professional_workflow.py` | 专业剪辑计划与导出 QA | 3 |

所有测试不依赖剪映/Premiere 实际运行，纯 Python 验证 draft 操控逻辑。

## 安全规则

1. **原子写入**：`Draft.save()` 用临时文件 + os.replace，写入失败不破坏原文件
2. **自动备份**：默认备份到 `.bak.<timestamp>.<rand>`
3. **Premiere 操作前先 save 项目**：pymiere 的 undo 不可靠
4. **不要并发写 draft**：用文件锁或串行调用
5. **不要改 draft_meta_info.json**：那是索引文件
6. **大文件导出用 HTTP API**：CLI 会阻塞，MCP 超时 30s
7. **ffmpeg 命令无 shell 注入**：用 list 形式构造命令

## 兼容性

- **剪映**：5.0+（draft schema 在 4.x 与 5.x 有差异，目前以 5.x 为准）
- **CapCut**：与剪映 draft schema 完全一致
- **Premiere Pro**：2022+
- **Python**：3.9+
- **OS**：Windows + macOS

## 限制

### 剪映

- 修改后需用户在剪映中重新打开项目才生效（不热加载）
- 导出大视频只能 UI 自动化（脆弱）或 ffmpeg 简单合成（无特效）
- 无法读取选中状态、播放头位置

### Premiere

- 必须 Premiere 运行中
- 首次连接慢（2-3s）
- QE DOM 部分操作不稳定，依赖版本

## 文档导航

| 你想做的事 | 看哪里 |
|---|---|
| 快速上手 | `SKILL.md` |
| 理解剪映 draft 结构 | `references/jianying-draft-schema.md` |
| 查剪映某操作参数 | `references/jianying-operations.md` |
| 查 Premiere 操作 | `references/premiere-operations.md` |
| 跨平台问题 | `references/cross-platform.md` |
| 实现上下文感知 | `references/context-awareness.md` |
| 一句话专业剪辑计划与导出 QA | `references/professional-workflow.md` |
| 集成到某 agent | `references/agent-integration.md` |
| 看完整示例 | `examples/*.py` |
| 贡献代码 | `CONTRIBUTING.md` |
| 更新历史 | `CHANGELOG.md` |

## 贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 许可证

MIT License. 见 [LICENSE](./LICENSE)。

## 致谢

- 剪映 draft 结构参考社区逆向工程文档
- pymiere 由 Quentin McGaw 开发
- MCP 协议由 Anthropic 提出
