---
name: cut
description: >-
  控制 剪映 (JianYing/CapCut) 与 Adobe Premiere Pro 两款视频剪辑软件的统一 skill。
  让 AI 编程 agent（Codex CLI / Claude Code / OpenCode / Kimi Code / Qwen Code 等任意支持 skill 或 MCP 的工具）
  能够读取当前时间轴状态、批量导入素材、裁切片段、添加字幕与转场、混音、并触发导出渲染。
  使用本 skill 的场景包括但不限于：用户说"帮我把这些视频剪一下"、"自动给视频加字幕"、
  "在剪映里把这段切两半"、"让 Premiere 把这几个素材按顺序排到时间轴上"、"批量加水印"、
  "导出 1080p"、"读取一下我剪映里现在有什么素材"、"自动做个 vlog 混剪"。
  涵盖视频剪辑、字幕生成、特效转场、音频处理、批量渲染、跨平台（Windows + macOS）。
  只要用户提到 剪映、CapCut、JianYing、Premiere、Pr、视频剪辑、时间轴、轨道、片段、字幕、转场、
  调色、混音、渲染导出 等任何视频后期相关词，都应优先使用本 skill。
---

# Cut — 统一的视频剪辑操控 skill

本 skill 让你（agent）像操作一个视频剪辑助理一样操作 **剪映** 与 **Premiere Pro**。
两种软件共用一套上层接口（CLI / MCP / HTTP），底层各走各的实现路径：
剪映走 **draft 文件操控**（解析编辑 `draft_content.json`），Premiere 走 **pymiere**（Python 封装 ExtendScript）。

> **设计哲学**：剪映没有官方 API，但它的工程文件是 JSON，结构公开可解析；
> Premiere 有官方扩展机制但接入繁琐，pymiere 已封装好大部分常用操作。
> 本 skill 把两条路径抽象成同一组动词（import / split / trim / text / transition / effect / audio / export），
> agent 只需要学一套接口。

## 兼容性

- Python 3.9+
- 剪映专业版 5.x+（Windows/macOS，draft 文件操控模式）
- Adobe Premiere Pro 2022+（通过 pymiere，需运行中并启用脚本接口）
- 可选：pyautogui（剪映导出辅助）、ffmpeg/ffprobe（音频预处理与导出 QA）、Flask（HTTP API）

---

## 0. 触发判断（你应该用本 skill 当……）

只要满足以下任一条件，立即读本 skill 的 `references/` 深入：

- 用户提到剪映、CapCut、JianYing、Premiere、Pr、视频剪辑
- 用户给出多个视频/音频文件并要求"剪"、"拼接"、"加字幕"、"加转场"、"批量导出"
- 用户已经在剪映/Premiere 里有项目，想读取当前状态或继续编辑
- 用户要做 vlog、混剪、教学视频、产品演示视频等后期工作流
- 用户问"怎么用代码/agent 控制剪映"、"Premiere 能不能脚本化"

不要把本 skill 用于：纯 ffmpeg 命令行转码（用 ffmpeg skill）、视频理解分析（用 video-understand）、AI 生成视频（用 image-generation/video-understand）。

---

## 1. 工作流速总（30 秒上手）

无论用哪种集成形态，工作流都是 4 步：

```text
1. detect        → 检测本机平台、剪映/Premiere 安装、活跃项目
2. get_state     → 读取当前项目状态（素材池、轨道、片段、选中元素）
3. plan/edit      → 对一句话需求先生成专业剪辑计划，再执行 import / split / trim / text / transition / effect / audio
4. export + qa    → 触发渲染输出并做成片质量验收
```

**第 2 步是关键**：本 skill 强调"上下文感知"。在你做任何修改前，**先调一次 `cut-cli get-state` 或对应 MCP 工具**，把当前项目快照读进来，再决定下一步。盲目修改 draft 文件很容易让剪映加载失败。

---

## 2. 集成形态总览

本 skill 同时提供 4 种调用方式，按场景选择：

| 形态 | 适用场景 | 入口 | 学习成本 |
|---|---|---|---|
| 纯 SKILL.md 文档 | agent 想自己写代码、需要深度定制 | 本文件 + `references/` | 最低 |
| 内置 CLI（cut-cli） | Codex/Kimi/Qwen 等 shell 友好的 agent | `python -m cut.cli` | 低 |
| MCP Server | Claude Desktop / OpenCode / 任何 MCP 客户端 | `python -m cut.mcp_server` | 中 |
| HTTP API | 长任务、Web 集成、跨进程协作 | `python -m cut.http_api` | 中 |

**推荐路径**：
- Codex CLI / Kimi Code / Qwen Code → 用 CLI（最快上手）
- Claude Code / Claude Desktop → 用 MCP Server（原生支持 tool_call）
- OpenCode → CLI 或 MCP 都行
- 需要长期协作（如渲染队列）→ HTTP API

具体安装与配置见 `references/agent-integration.md`。

---

## 3. 后端选择

每个操作都可以指定 `--backend`（CLI）/ `backend` 参数（MCP/HTTP）：

| Backend | 标识 | 实现路径 | 限制 |
|---|---|---|---|
| 剪映 | `jianying` | 直接读写 `draft_content.json` | 修改后需重启剪映生效；导出需 UI 辅助 |
| Premiere | `premiere` | pymiere → ExtendScript | 需 Premiere 运行中；首次需信任脚本 |

剪映后端的最大特点是**离线编辑**：你甚至不需要剪映开着就能改 draft，改完用户重开项目即可看到效果。
Premiere 后端是**在线编辑**：必须 Premiere 处于打开状态，所有操作实时反映在 UI 上。

---

## 4. 核心操作动词（与命令一一对应）

| 动词 | 含义 | 剪映支持 | Premiere 支持 |
|---|---|---|---|
| `detect` | 检测环境与活跃项目 | ✅ | ✅ |
| `get-state` | 读取项目概要（上下文感知核心） | ✅ | ✅ |
| `list-materials` | 列出素材池 | ✅ | ✅ |
| `get-timeline` | 读取所有轨道与片段 | ✅ | ✅ |
| `import` | 导入视频/音频/图片到素材池 | ✅ | ✅ |
| `split` | 在指定时间点把片段切成两段 | ✅ | ✅ |
| `trim` | 调整片段入点/出点 | ✅ | ✅ |
| `add-text` | 添加文字/标题/字幕 | ✅ | ✅ |
| `add-transition` | 在两段之间加转场 | ✅ | ✅ |
| `add-effect` | 应用特效（滤镜/调色/动画） | ✅ | ✅ |
| `set-audio` | 音量/淡入淡出/降噪 | ✅ | ✅ |
| `export` | 导出渲染（剪映需 UI 辅助） | ⚠️ | ✅ |
| `plan` / `create_plan` | 从一句话生成专业剪辑执行计划 | ✅ | ✅ |
| `qa` / `quality_check` | 导出后成片质量验收 | ✅ | ✅ |

详细参数、返回结构、错误码见 `references/jianying-operations.md` 与 `references/premiere-operations.md`。

---

## 5. 上下文感知（最重要的事）

**修改前必读状态**。本 skill 的 `state` 模块提供以下只读接口：

```python
from cut.context import get_project_state

state = get_project_state(backend="jianying")  # 或 "premiere"
# state = {
#   "backend": "jianying",
#   "platform": "darwin",
#   "app_version": "5.9.0",
#   "project_path": "/Users/.../drafts/my_vlog",
#   "project_name": "my_vlog",
#   "duration_us": 18000000,        # 微秒
#   "duration_hms": "00:00:18.000",
#   "tracks": [
#     {"id":"...","type":"video","segments_count":12},
#     {"id":"...","type":"audio","segments_count":3},
#     {"id":"...","type":"text","segments_count":5},
#   ],
#   "materials": {"videos":8,"audios":3,"images":2,"stickers":0,"texts":5},
#   "selection": {"segment_id":"...","track_id":"...","in_us":1200000,"out_us":2400000}
# }
```

agent 拿到这个快照后，再决定要不要 `split` / `trim` / `add-text`。这避免了"瞎改 draft"导致的崩溃。

更多上下文接口见 `references/context-awareness.md`。

## 5.5 专业剪辑导演层（一句话到执行计划）

当用户只给一句话（例如"自动做个旅行 vlog"、"剪成 30 分钟影视解说"）时，不要直接堆命令。
先调用 `python -m cut.cli plan "<用户需求>"` 或 MCP `cut.create_plan`：

1. 识别长视频/短视频、平台、目标时长、节奏、叙事结构
2. 生成 edit decision list：素材导入、粗剪、字幕、转场、混音、调色、导出、QA
3. 先读 `get-state`，再按计划执行具体剪辑动作
4. 导出后调用 `quality_check` 验证时长、码率、视频/音频流、分辨率、帧率

导演层是确定性计划器，不替代真正素材理解；如需要镜头语义理解、ASR 或节拍检测，应结合 `examples/` 或外部识别服务生成素材标签后再规划。

---

## 6. 跨平台路径与差异

剪映 draft 路径因平台而异：

| 平台 | 路径 |
|---|---|
| Windows | `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft\` |
| macOS | `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/` |
| Windows (CapCut 国际版) | `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\` |
| macOS (CapCut 国际版) | `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/` |

`cut.platform.detect()` 会自动找路径、识别剪映版本、检测 Premiere 安装。**永远不要硬编码路径**，永远走 platform 模块。

完整差异表与检测逻辑见 `references/cross-platform.md`。

---

## 7. 剪映 draft 文件结构（必读）

`draft_content.json` 是剪映项目的核心，所有素材、轨道、片段、特效、动画都在里面。
你不需要全部记住，但需要理解**三层结构**：

```
materials  →  tracks  →  segments
 (素材池)      (轨道)      (片段)
```

- `materials` 是仓库，记录所有导入的原始素材（视频/音频/图片/文本/贴纸/特效资源）
- `tracks` 是时间轴上的轨道，按类型分组（video/audio/text/sticker/effect）
- `segments` 是轨道上的具体片段，每个 segment 引用一个 material 的 ID，并指定在时间轴上的位置（`target_timerange`）和素材内部的入点（`source_timerange`）

完整 schema（含 `material_animations`、`effects` 链路、`scale_x/scale_y/transform`、`keyframe_refs` 等）见 `references/jianying-draft-schema.md`。
**修改 draft 前务必读这份文档**，否则容易写坏结构。

---

## 8. Premiere pymiere 集成要点

pymiere 通过 ExtendScript 桥接 Premiere，要求：

1. Premiere Pro 已打开，并加载了一个项目
2. 首次运行需在 Premiere 中"编辑 → 首选项 → 脚本"启用脚本调试（具体版本路径略有差异）
3. pymiere 通过 CEP WebSocket 与 Premiere 通信，第一次调用会有 2-3 秒延迟

pymiere 的对象层级：

```python
import pymiere
app = pymiere.objects.app           # Premiere 应用对象
project = app.project               # 当前项目
seq = project.activeSequence        # 当前活动序列
tracks = seq.videoTracks            # 视频轨道集合
clip = tracks[0].clips[0]           # 第一个轨道的第一个片段
```

完整 API 列表与反向读取模板见 `references/premiere-operations.md`。

---

## 9. 安全规则（强制遵守）

1. **永远先备份 draft**：剪映后端任何写操作前，自动复制 `draft_content.json` 到 `.bak`。`cut.jianying.draft.Draft` 类已内置此行为，但如果你直接改文件，必须自己 `cp` 一份。
2. **Premiere 操作不可撤销链式调用**：pymiere 的 `undo` 不可靠，做连续修改前调 `app.project.save()` 先存档。
3. **不要并发写 draft**：剪映后端用文件锁，但你仍应串行调用。
4. **不要修改 `draft_meta_info.json`**：那是剪映的索引文件，改了会导致项目列表错乱。只改 `draft_content.json`。
5. **导出大文件用 HTTP API**：CLI 会阻塞，MCP 超时 30s，HTTP API 是异步的。

---

## 10. 快速示例

### 示例 A：用 CLI 读取剪映项目状态

```bash
$ python -m cut.cli detect
{
  "platform": "darwin",
  "jianying": {"installed": true, "version": "5.9.0", "drafts_dir": "/Users/me/Movies/JianyingPro/User Data/Projects/com.lveditor.draft"},
  "premiere": {"installed": true, "version": "24.0", "running": false}
}

$ python -m cut.cli get-state --backend jianying --project my_vlog
{... 见第 5 节 ...}
```

### 示例 B：用 MCP tool_call 切分片段

```json
{"tool": "cut.split", "input": {
  "backend": "premiere",
  "track_index": 0,
  "clip_index": 2,
  "at_seconds": 15.5
}}
```

### 示例 C：用 Python 直接调

```python
from cut.jianying.draft import Draft
from cut.jianying.segments import split_segment

draft = Draft.open(project_name="my_vlog")  # 自动备份
track = draft.video_tracks[0]
seg = track.segments[2]
split_segment(draft, seg, at_us=15_500_000)
draft.save()  # 写回 draft_content.json
print("完成。请在剪映中重新打开项目查看。")
```

更多完整示例（批量裁切、ASR 自动字幕、双轨混剪）见 `examples/` 目录。

---

## 11. 文件导航

| 你想做的事 | 看哪里 |
|---|---|
| 理解剪映 draft 文件结构 | `references/jianying-draft-schema.md` |
| 查剪映某操作的具体参数与返回 | `references/jianying-operations.md` |
| 查 Premiere pymiere 操作 | `references/premiere-operations.md` |
| 处理 Win/Mac 差异 | `references/cross-platform.md` |
| 实现上下文感知/反向读取 | `references/context-awareness.md` |
| 从一句话生成专业剪辑计划并做成片 QA | `references/professional-workflow.md` |
| 集成到某个 agent 工具 | `references/agent-integration.md` |
| 看完整端到端示例 | `examples/*.py` |
| 看 CLI 完整命令参考 | `scripts/cut/cli.py` 顶部 docstring |

---

## 12. 故障排查速查

| 症状 | 原因 | 解决 |
|---|---|---|
| 剪映打开项目提示"文件已损坏" | draft 改坏了 | 用 `.bak` 恢复；检查 JSON 合法性 |
| pymiere 连接超时 | Premiere 未运行 / 未启用脚本 | 开 Premiere → 首选项启用脚本 |
| `cut-cli detect` 找不到剪映 | 路径检测失败 | 看 `references/cross-platform.md` 手动指定 |
| split 后片段不见了 | `source_timerange` 越界 | 先 `get-timeline` 看 segment 的 source_range |
| 字幕添加后位置错乱 | 没指定 track_index | 默认追加到第一条 text 轨，需精确指定 |

---

## 13. 版本与兼容性

- v1.0：剪映 draft 操控 + Premiere pymiere 封装 + CLI + MCP + HTTP
- 剪映支持版本：5.0+（draft schema 在 4.x 与 5.x 有差异，目前以 5.x 为准）
- Premiere 支持版本：2022+（pymiere 要求）
- Python：3.9+（因 pymiere 依赖 3.9+）

向后兼容策略：剪映版本升级导致 draft schema 变化时，`platform.detect()` 会返回 `schema_version`，`Draft.open()` 据此选择解析器。如遇不兼容，会抛出 `UnsupportedSchemaError` 并提示用户升级 skill。

---

**下一步建议**：先读 `references/agent-integration.md` 选择你的 agent 集成方式，再读对应后端的 operations 文档。
