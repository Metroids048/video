# Agent Video Studio V1 — 系统架构

> 版本：1.0 | 日期：2026-07-20 | 状态：已冻结（模块 0）

---

## 1. 系统定位

Agent Video Studio V1 是一个**通用短视频结构分析与粗剪生产系统**，目标平台为抖音和小红书。

系统接收用户的零散输入（文本、图片、参考视频、录屏、音频、链接），产出结构完整、可在剪映等软件中继续编辑的视频粗稿与编辑交付包。V1 不追求无人干预的成品，而是稳定交付"最后 10–30% 由用户完成"的高质量粗稿。

---

## 2. 架构决策索引

| ADR | 决策 | 文件 |
|-----|------|------|
| 0001 | 唯一业务 CLI 为 `python -m avs` | [decisions/0001-python-cli.md](decisions/0001-python-cli.md) |
| 0002 | `timeline.json` 为渲染器共享中间协议 | [decisions/0002-timeline-contract.md](decisions/0002-timeline-contract.md) |
| 0003 | HyperFrames 仅负责动效片段 | [decisions/0003-hyperframes-boundary.md](decisions/0003-hyperframes-boundary.md) |
| 0004 | Skills 单一编辑源与三 Agent 同步 | [decisions/0004-agent-skill-layout.md](decisions/0004-agent-skill-layout.md) |

---

## 3. 核心设计原则

### 3.1 单一真相来源

| 数据 | 权威位置 |
|------|---------|
| 项目规则 | `AGENTS.md` |
| Claude 入口 | `CLAUDE.md` |
| 运行配置 | `config/` |
| 数据合同 | `schemas/` |
| Episode 状态 | `episodes/.../episode.json` |
| 时间线 | `episodes/.../work/timeline.json` |
| Skill 源码 | `skills-src/` |
| 业务 CLI | `python -m avs` |

禁止在以上位置之外建立第二套状态、配置或 CLI。

### 3.2 确定性与生成式分离

```
确定性程序（Python CLI）           Agent 任务（LLM）
─────────────────────────         ──────────────────────
环境诊断                           参考视频风格解释
文件识别与保护                     内容简报与事实整理
FFprobe 元数据                     脚本与钩子文案
转码、裁切、缩放                   分镜与素材建议
镜头切分与关键帧                   视觉方案
状态机                             编辑建议
Schema 校验                        平台标题与发布文案
时间线合法性
FFmpeg 粗剪
视频解码/黑帧/静音 QA
交付包组装
```

### 3.3 可降级运行

所有增强模块失败时，核心流程继续：

| 场景 | 降级行为 |
|------|---------|
| 无参考视频 | 使用通用模板 |
| 无转写 Provider | 允许用户提供文本或手工字幕 |
| 无 TTS | 生成无旁白粗稿 |
| HyperFrames 失败 | 使用 FFmpeg 静态标题卡与基础字幕 |
| 缺少素材 | 生成占位卡，写入 `edit-notes.md` |
| 无网络 | 本地媒体流程正常运行 |

### 3.4 原始素材不可变

- `input/` 内文件只读，绝不修改、重命名或移动
- 所有加工使用工作副本（`work/prepared/`）
- 输出使用相对路径
- 缓存可删除并重新生成

---

## 4. 组件与职责

### 4.1 Python 业务层（`src/avs/`）

| 子模块 | 职责 | 实现模块 |
|--------|------|---------|
| `cli.py` | 命令解析与路由 | 2 |
| `state.py` | 状态机与 episode.json | 2 |
| `config.py` | 配置加载与合并 | 2 |
| `paths.py` | 路径解析，防穿越 | 2 |
| `models/` | Pydantic 数据模型 | 2 |
| `ingest/` | 文件识别、FFprobe、Hash、代理 | 3 |
| `reference/` | 音频提取、镜头切分、转写、Recipe | 4 |
| `assets/` | 素材准备与缺口标注 | 3–5 |
| `timeline/` | 时间线构建与校验 | 6 |
| `render/` | FFmpeg 粗剪、字幕、音频混合 | 6 |
| `qa/` | 确定性 QA（解码/黑帧/静音/峰值） | 8 |
| `delivery/` | 交付包组装，路径相对化 | 8 |

### 4.2 HyperFrames 渲染层（`renderers/hyperframes/`）

负责且仅负责动效片段渲染：

- **输入**：`timeline.json` 中的 motion 轨道条目，或独立 motion manifest
- **输出**：独立 MP4 片段（带或不带透明通道，取决于框架能力）
- **合成**：由 `src/avs/render/ffmpeg.py` 负责将动效片段合成到基础粗剪
- **不负责**：Episode 状态、输入管理、参考语义分析、发布

V1 必须实现的三个组件：

```
renderers/hyperframes/components/
├── HookTitle/       开头钩子标题动效
├── InfoCard/        信息卡（关键信息展示）
└── EndCard/         结尾卡（引导关注/点赞）
```

降级路径：HyperFrames 任何阶段失败 → FFmpeg 静态文字卡 → 记录 warning → 基础粗剪仍然交付。

### 4.3 FFmpeg 渲染层（`renderers/ffmpeg/`）

负责：

- 视频/图片拼接
- 字幕嵌入（SRT burn-in 或 soft sub）
- 旁白与 BGM 混音（含 ducking）
- contain/cover 布局
- 占位卡生成
- HyperFrames 片段合成

画布规格：**1080×1920、30fps、H.264、AAC、yuv420p**

### 4.4 Skills 层（`skills-src/`）

项目自有 9 个 Skill，在 `skills-src/` 统一编辑，由 `scripts/sync_skills.py` 同步到：

- `.claude/skills/`（Claude Code）
- `.agents/skills/`（Codex / 兼容 Agent）

第三方 Skill（HyperFrames）通过 `npx skills add` 安装，版本记录在 `skills.lock.json`。

### 4.5 跨 Agent 配置层

```
AGENTS.md           ← Codex / Cursor / Claude Code 均可直接读取
CLAUDE.md           ← Claude Code 入口，引用 AGENTS.md
.claude/agents/     ← Claude Code Subagents（content-worker / media-worker / reviewer）
.claude/skills/     ← Claude Code Skills 同步目标
.agents/skills/     ← Codex / 兼容 Agent Skills 同步目标
.cursor/rules/      ← Cursor 规则（project.mdc / media.mdc）
```

---

## 5. 数据流

```
用户输入（input/）
    │
    ▼  python -m avs ingest
work/asset-manifest.json
    │
    ├─► [有参考视频] python -m avs reference analyze
    │   work/reference/reference-recipe.json
    │
    ▼  Agent Skill: write-video-script / create-storyboard
work/content/script.json + storyboard.json
    │
    ▼  python -m avs timeline build
work/timeline.json + timeline.csv
    │
    ├─► python -m avs render rough   ← FFmpeg 基础粗剪
    │
    └─► npx hyperframes render       ← HyperFrames 动效片段
            │
            ▼ FFmpeg 合成
renders/preview-clean.mp4
renders/preview-with-captions.mp4
    │
    ▼  python -m avs qa
delivery/qa-report.md
    │
    ▼  python -m avs deliver
delivery/（完整交付包）
```

---

## 6. Episode 状态机

```
CREATED → INGESTED → REFERENCE_READY* → CONTENT_READY
                                              │
                         (* 无参考视频可跳过) │
                                              ▼
                                        ASSETS_READY
                                              │
                                              ▼
                                       TIMELINE_READY
                                              │
                                              ▼
                                      ROUGH_CUT_READY
                                              │
                                              ▼
                                          QA_PASSED
                                              │
                                              ▼
                                       DELIVERY_READY
```

辅助状态（不在主链路）：`WAITING_FOR_INPUT`、`WAITING_FOR_REVIEW`、`FAILED`

规则：
- 禁止跳过前置状态
- 任何阶段失败保留已完成产物
- 只有 `--force` 可重新生成可再生成产物
- `REFERENCE_CLONE` 自动设置 `publishable: false`

---

## 7. 目录结构与职责

```
agent-video-studio/（即本仓库根目录）
│
├── AGENTS.md                  ← 所有 Agent 的项目总规则（单一真相）
├── CLAUDE.md                  ← Claude Code 入口，引用 AGENTS.md（模块1创建）
├── README.md                  ← 项目说明与快速上手（模块9创建）
├── package.json               ← npm 包装命令（模块1创建）
├── pyproject.toml             ← Python 包定义（模块1创建）
├── requirements.lock.txt      ← 精确 Python 依赖锁（模块1创建）
├── skills.lock.json           ← Skills 版本清单（已创建）
├── tools-manifest.yaml        ← 工具版本约束（已创建）
├── .env.example               ← 环境变量模板，不含真实值（模块1创建）
├── .gitignore                 ← 已创建
│
├── config/                    ← 运行和制作配置（模块2创建）
│   ├── project.yaml           ← 项目基础配置
│   ├── workflow.yaml          ← 流程控制（review 开关等）
│   ├── platforms.yaml         ← 抖音/小红书平台规格
│   ├── visual.yaml            ← 画布和视觉默认值
│   ├── audio.yaml             ← 音频规格与 ducking 参数
│   ├── providers.yaml         ← 转写/TTS/LLM Provider 配置
│   └── content-pillars.yaml   ← 内容支柱（可选，ORIGINAL 模式使用）
│
├── schemas/                   ← JSON Schema 数据合同（模块2创建）
│   ├── episode.schema.json
│   ├── asset-manifest.schema.json
│   ├── reference-recipe.schema.json
│   ├── script.schema.json
│   ├── storyboard.schema.json
│   ├── timeline.schema.json
│   ├── qa-report.schema.json
│   └── delivery-manifest.schema.json
│
├── src/avs/                   ← Python 业务包（模块2+创建）
│   ├── __main__.py            ← `python -m avs` 入口
│   ├── cli.py                 ← 命令解析与路由
│   ├── config.py              ← 配置加载
│   ├── paths.py               ← 路径解析与安全检查
│   ├── state.py               ← 状态机
│   ├── models/                ← Pydantic 数据模型
│   ├── ingest/                ← 素材识别与标准化（模块3）
│   ├── reference/             ← 参考视频分析（模块4）
│   ├── assets/                ← 素材准备（模块3）
│   ├── timeline/              ← 时间线构建（模块6）
│   ├── render/                ← FFmpeg 粗剪（模块6）
│   ├── qa/                    ← 确定性 QA（模块8）
│   └── delivery/              ← 交付包组装（模块8）
│
├── renderers/
│   ├── ffmpeg/                ← FFmpeg filter 模板（模块6创建）
│   └── hyperframes/           ← HyperFrames 动效组件（模块7创建）
│       ├── components/        ← HookTitle / InfoCard / EndCard
│       ├── compositions/      ← 组合场景
│       └── templates/         ← 可复用模板
│
├── skills-src/                ← 项目自有 Skill 唯一编辑源
│   ├── create-episode/        ← 模块2
│   ├── analyze-reference/     ← 模块4
│   ├── write-video-script/    ← 模块5
│   ├── create-storyboard/     ← 模块5
│   ├── prepare-assets/        ← 模块3
│   ├── create-rough-cut/      ← 模块6
│   ├── revise-video/          ← 模块9
│   ├── quality-review/        ← 模块8
│   └── create-publish-pack/   ← 模块8
│
├── .agents/skills/            ← Skills 同步目标（Codex/兼容Agent）
├── .claude/
│   ├── skills/                ← Skills 同步目标（Claude Code）
│   ├── agents/                ← Subagents（content-worker/media-worker/reviewer）
│   ├── settings.json          ← Claude Code 设置（模块1创建）
│   └── settings.local.json    ← 本地覆盖，不提交
├── .cursor/rules/             ← Cursor 规则（模块1创建）
│
├── scripts/                   ← 安装与维护脚本（模块1创建）
│   ├── bootstrap.ps1          ← Windows 安装
│   ├── bootstrap.sh           ← macOS/Linux 安装
│   ├── sync_skills.py         ← Skills 同步
│   ├── install_skills.mjs     ← 第三方 Skills 安装
│   └── verify.mjs             ← 环境验证
│
├── templates/                 ← 视频结构模板（模块5创建）
│   ├── reference-adapt/
│   ├── screen-explainer/
│   └── generic/
│
├── episodes/                  ← Episode 工作目录（模块2创建结构）
│   ├── inbox/                 ← 新建待处理
│   ├── active/                ← 制作中
│   ├── completed/             ← 已交付
│   └── archived/              ← 已归档
│
├── fixtures/                  ← 测试 Fixture（模块9创建）
│   ├── reference-adapt-demo/
│   └── screen-explainer-demo/
│
├── tests/                     ← 测试（各模块按需创建）
├── cache/                     ← 不提交 Git
├── logs/                      ← 不提交 Git
└── output/                    ← 不提交 Git
```

---

## 8. Provider 设计

V1 不将任何 LLM/转写/TTS 供应商写死：

| Provider | V1 默认 | 降级行为 |
|----------|---------|---------|
| 转写 | `auto`（检测可用实现） | `manual`（用户提供文本） |
| TTS | `disabled` | 生成无旁白粗稿 |
| LLM | `agent`（当前会话 Agent） | 无（Agent 任务必须有 Agent） |

API Key 只存于 `.env` 或工具自身安全存储，绝不提交。

---

## 9. 审计报告（模块0）

### 9.1 双 CLI 检查

**结论：无风险。** 当前为干净仓库。ADR-0001 明确：唯一业务 CLI 为 `python -m avs`，npm 命令必须调用同一 Python CLI，禁止在两套接口中分别实现逻辑。

### 9.2 重复状态检查

**结论：无风险。** 唯一状态载体为每个 Episode 的 `episode.json`。ADR-0002 通过 `timeline.json` 合同防止渲染器各自维护独立状态。

### 9.3 V1 / 未来功能混杂检查

**结论：已分离。** 规范第 2.2 节明确列出移出 V1 的功能：Remotion、自动发布、数字人/声音克隆、剪映草稿逆向、云渲染、多账号矩阵。`tools-manifest.yaml` 中的 `deferred_post_v1` 节列出了所有延后工具。`docs/implementation-roadmap.md` 的 post-V1 小节与规范 P1/P2/P3 路线图对应。

### 9.4 未明确供应商依赖检查

**结论：已处理。** 所有外部依赖均通过适配器或可配置 Provider 接入：
- 转写：Provider 接口，支持 `whisper_cpp`、`openai_whisper`、`manual`、`disabled`
- TTS：默认 `disabled`，后续 P1 通过 Provider 接入
- LLM：`agent`（当前会话），无硬编码模型名
- Chromium：由 HyperFrames/Puppeteer 管理，doctor 通过 `npx hyperframes doctor` 间接检查

唯一强依赖且无适配器的工具：`git`、`python 3.11+`、`node 22+`、`ffmpeg/ffprobe`，均在 `tools-manifest.yaml` 中声明版本约束。

### 9.5 无法验收要求检查

**结论：规范中无此类项。** 所有验收标准均为可命令行验证的客观结果（退出码、文件存在、Schema 通过、FFprobe 元数据）。视觉 QA 依赖联系表，明确标注置信度，不伪装主观判断为确定性结果。
