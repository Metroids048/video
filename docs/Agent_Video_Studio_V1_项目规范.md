# Agent Video Studio V1 项目规范（优化版）

> 版本：1.0  
> 日期：2026-07-20  
> 状态：可作为 Codex、Claude Code 或 Cursor 的开发基线  
> 目标平台：抖音、小红书  
> 核心交付：可继续人工编辑的视频粗稿与完整编辑包

---

## 1. 项目结论

Agent Video Studio V1 是一个**通用短视频结构分析与粗剪生产系统**。

用户只需提供任意组合的：

- 零散想法或文本；
- 图片、截图；
- 参考视频；
- 产品或项目录屏；
- 原始口播或音频；
- 网页、GitHub 等资料链接；

系统便将输入整理为：

1. 输入与素材清单；
2. 参考视频结构拆解；
3. 内容简报；
4. 口播脚本；
5. 分镜与素材缺口；
6. 字幕、旁白与媒体预处理结果；
7. 基础时间线；
8. 带字幕和无字幕的视频粗稿；
9. HyperFrames 动效素材；
10. 可继续导入剪映等软件的编辑交付包；
11. 抖音和小红书发布文案；
12. 人工修改清单。

V1 的完成标准不是“无人干预生成可直接发布的爆款视频”，而是：

> 用户投入原始内容后，系统能够稳定产出一个结构完整、可正常播放、可继续修改的粗稿；用户完成最后约 10%—30% 的剪辑、审美和发布工作。

---

## 2. 对原始方案的优化

原始材料的核心方向是正确的，但需要做以下收敛。

### 2.1 保留的核心设计

- `reference-recipe.json`：把参考视频转化为机器可读的视频配方。
- 三种模式：
  - `REFERENCE_CLONE`：仅供内部临摹学习；
  - `REFERENCE_ADAPT`：默认公开生产模式；
  - `ORIGINAL`：使用自有模板。
- 自定义 `timeline.json` 作为渲染器之间的中间协议。
- FFmpeg 负责基础媒体加工与粗剪。
- HyperFrames 负责标题、字幕、信息卡和解释动画。
- 最终发布始终人工完成。
- 剪映草稿只是未来适配器，不是 V1 的核心依赖。
- 项目本地 Skills 是主干，Codex/Claude/Cursor 专属插件只是增强。

### 2.2 删除或延后的内容

以下内容移出 V1：

- Remotion 主渲染器；
- 自动发布抖音或小红书；
- 自动登录、评论、私信和多账号矩阵；
- 数字人和声音克隆；
- 剪映草稿逆向工程；
- Premiere XML、Resolve XML 和 FCPXML；
- 云端分布式渲染；
- 自动抓取或下载任意平台视频；
- 完整运营数据平台；
- 十几个同时运行的 Agent；
- 对字幕位置、音乐节拍和镜头意图做过度承诺的“全自动识别”。

### 2.3 修复的结构问题

- 只保留一套目录，不再重复维护多个版本。
- 只保留一个业务 CLI，不同时维护互相冲突的 CLI 与 npm 命令。
- 将一次性“大总 Prompt”拆成九个有依赖顺序的模块。
- 每个模块均有独立测试、验收和审计门槛。
- 将确定性程序与大模型判断分开：
  - 程序负责文件、媒体、状态、Schema、渲染和 QA；
  - Agent 负责理解内容、参考风格、脚本、分镜和修改建议。
- 将“必须能力”和“增强能力”分开，避免初期过度工程化。

---

## 3. 范围

### 3.1 V1 必须支持

#### 输入

- `.txt`、`.md`；
- `.png`、`.jpg`、`.webp`；
- `.mp4`、`.mov`、`.mkv`、`.webm`；
- `.wav`、`.mp3`、`.m4a`；
- `links.txt` 中的网页或 GitHub 链接。

链接在 V1 中用于 Agent 研究和事实提取，**不承诺自动下载第三方平台视频**。参考视频应优先由用户作为本地文件提供。

#### 视频类型

V1 只需完整跑通两类样片：

1. **参考视频改编**
   - 输入：参考视频、自己的文本、图片和录屏；
   - 输出：参考原视频结构和节奏、替换内容后的粗稿。

2. **录屏讲解**
   - 输入：工具或项目录屏、说明文字、截图；
   - 输出：标题、字幕、局部重点画面、信息卡和粗剪。

#### 输出

- `preview-with-captions.mp4`
- `preview-clean.mp4`
- `captions.srt`
- `captions.ass`（可选）
- `timeline.json`
- `timeline.csv`
- `script.md`
- `storyboard.md`
- `edit-notes.md`
- `qa-report.md`
- `assets-used/`
- `motion-graphics/`
- `publish/douyin.md`
- `publish/xiaohongshu.md`

### 3.2 V1 不保证

- 成片不需要人工修改；
- 完全复刻参考视频；
- 自动理解所有审美；
- 自动生成所有缺失素材；
- 自动获得流量；
- 自动发布；
- 输出可直接被剪映识别的项目草稿。

---

## 4. 架构原则

### 4.1 单一真相来源

- `AGENTS.md`：所有 Agent 的项目总规则。
- `config/`：运行和制作配置。
- `schemas/`：结构化文件合同。
- `episode.json`：单期视频状态。
- `timeline.json`：所有渲染器共享的时间线。
- `skills-src/`：项目自有 Skills 的唯一编辑源。

### 4.2 分离确定性与生成式任务

#### 确定性程序

- 环境诊断；
- 文件识别和复制；
- FFprobe 元数据；
- 转码、裁切、缩放；
- 镜头切分和关键帧；
- 状态机；
- Schema 校验；
- 时间线合法性；
- FFmpeg 粗剪；
- 视频解码、黑帧、静音和尺寸 QA；
- 交付包组装。

#### Agent 任务

- 参考视频风格解释；
- 内容简报；
- 事实整理；
- 脚本和钩子；
- 分镜和素材建议；
- 视觉方案；
- 编辑建议；
- 平台标题和发布文案。

### 4.3 可降级运行

任一增强模块失败时，核心流程仍应继续：

- 没有参考视频：使用通用模板。
- 无法转写：允许用户提供脚本或手工字幕。
- 没有 TTS：生成无旁白粗稿或使用用户音频。
- HyperFrames 失败：使用 FFmpeg 静态标题卡与基础字幕。
- 缺少素材：生成占位卡并写入 `edit-notes.md`。
- 无网络：本地媒体流程可正常运行。

### 4.4 原始素材不可变

- `input/` 内文件只读；
- 所有加工使用复制文件；
- 绝不覆盖、重命名或移动原始素材；
- 输出尽量使用相对路径；
- 缓存可删除并重新生成。

---

## 5. 技术基线

### 5.1 必需

- Git
- Node.js 22+
- Python 3.11+
- FFmpeg / FFprobe
- HyperFrames CLI
- Codex、Claude Code 或 Cursor 至少一个

### 5.2 推荐但非硬依赖

- Git LFS：仅在确实需要跟踪较大 Fixture 或测试基准时启用；真实用户素材默认不进入 Git。
- Chrome/Chromium：由 HyperFrames/Puppeteer 的实际安装方式决定，`doctor` 应调用框架自检而不是硬编码系统浏览器路径。
- Whisper 类本地转写模型：通过 Provider 适配器安装。
- 剪映专业版：人工最终修改。

### 5.3 延后

- Remotion
- ChatCut
- video-use
- HeyGen 数字人
- 云渲染

---

## 6. 跨 Agent 设计

### 6.1 指令层

```text
AGENTS.md
├─ Codex：直接读取
├─ Cursor：可直接读取；复杂规则补充于 .cursor/rules/
└─ Claude Code：CLAUDE.md 引用 AGENTS.md 和核心配置
```

### 6.2 Skills 层

```text
skills-src/                   # 项目自有 Skill 唯一编辑源
├─ create-episode/
├─ analyze-reference/
├─ write-video-script/
├─ create-storyboard/
├─ prepare-assets/
├─ create-rough-cut/
├─ revise-video/
├─ quality-review/
└─ create-publish-pack/

.claude/skills/               # 同步产物，供 Claude Code
.agents/skills/               # 同步产物，供 Codex/兼容 Agent
```

规则：

- 项目自有 Skill 只在 `skills-src/` 修改。
- `scripts/sync_skills.py` 负责复制和校验。
- Windows 默认使用复制，不依赖管理员权限和符号链接。
- 第三方 Skills 通过清单安装，不手工修改。
- 每次安装或更新都写入 `skills.lock.json`。

### 6.3 第三方 Skills

V1 必装：

```bash
npx skills add heygen-com/hyperframes -a claude-code -a codex -a cursor --copy -y
```

Codex 的 HyperFrames 插件可以安装，但它不是核心运行依赖。即使插件不可用，Agent 仍应通过项目 CLI、HyperFrames CLI 和项目 Skills 完成任务。

### 6.4 Claude Code

```text
CLAUDE.md
.claude/settings.json
.claude/settings.local.json       # 不提交
.claude/agents/
.claude/skills/
```

V1 只需要以下 Subagents：

- `content-worker`
- `media-worker`
- `reviewer`

不要一开始创建六到十个角色。

### 6.5 Cursor

```text
.cursor/rules/project.mdc
.cursor/rules/media.mdc
```

- `project.mdc`：始终应用的项目规则。
- `media.mdc`：仅对媒体处理目录自动附加。

---

## 7. 统一 CLI

业务命令的唯一正式入口为 Python CLI：

```bash
python -m avs doctor
python -m avs episode create EP-0001
python -m avs episode status EP-0001
python -m avs ingest EP-0001
python -m avs reference analyze EP-0001
python -m avs content prepare EP-0001
python -m avs assets prepare EP-0001
python -m avs timeline build EP-0001
python -m avs render rough EP-0001
python -m avs qa EP-0001
python -m avs deliver EP-0001
python -m avs run EP-0001
```

`package.json` 只提供便捷包装：

```bash
npm run bootstrap
npm run doctor
npm run demo
npm run verify
npm run skills:install
npm run skills:sync
npm run skills:check
```

不得在两套接口中分别实现业务逻辑。npm 命令必须调用同一个 Python CLI 或脚本。

---

## 8. 目录结构

```text
agent-video-studio/
├─ AGENTS.md
├─ CLAUDE.md
├─ README.md
├─ package.json
├─ pyproject.toml
├─ requirements.lock.txt
├─ skills.lock.json
├─ tools-manifest.yaml
├─ .env.example
├─ .gitignore
│
├─ config/
│  ├─ project.yaml
│  ├─ workflow.yaml
│  ├─ platforms.yaml
│  ├─ visual.yaml
│  ├─ audio.yaml
│  ├─ providers.yaml
│  └─ content-pillars.yaml
│
├─ schemas/
│  ├─ episode.schema.json
│  ├─ asset-manifest.schema.json
│  ├─ reference-recipe.schema.json
│  ├─ script.schema.json
│  ├─ storyboard.schema.json
│  ├─ timeline.schema.json
│  ├─ qa-report.schema.json
│  └─ delivery-manifest.schema.json
│
├─ src/avs/
│  ├─ __main__.py
│  ├─ cli.py
│  ├─ config.py
│  ├─ paths.py
│  ├─ state.py
│  ├─ models/
│  ├─ ingest/
│  ├─ reference/
│  ├─ assets/
│  ├─ timeline/
│  ├─ render/
│  ├─ qa/
│  └─ delivery/
│
├─ renderers/
│  ├─ ffmpeg/
│  └─ hyperframes/
│     ├─ components/
│     ├─ compositions/
│     └─ templates/
│
├─ skills-src/
├─ .agents/skills/
├─ .claude/
│  ├─ skills/
│  ├─ agents/
│  ├─ settings.json
│  └─ settings.local.json
├─ .cursor/rules/
│
├─ scripts/
│  ├─ bootstrap.ps1
│  ├─ bootstrap.sh
│  ├─ sync_skills.py
│  ├─ install_skills.mjs
│  └─ verify.mjs
│
├─ templates/
│  ├─ reference-adapt/
│  ├─ screen-explainer/
│  └─ generic/
│
├─ episodes/
│  ├─ inbox/
│  ├─ active/
│  ├─ completed/
│  └─ archived/
│
├─ fixtures/
│  ├─ reference-adapt-demo/
│  └─ screen-explainer-demo/
│
├─ tests/
├─ cache/
├─ logs/
└─ output/
```

`cache/`、`logs/`、`output/` 和真实 Episode 媒体默认不提交 Git。

---

## 9. Episode 工作目录

```text
episodes/active/EP-0001/
├─ episode.json
├─ input/                         # 原始输入，只读
│  ├─ idea.md
│  ├─ links.txt
│  ├─ reference/
│  ├─ screen/
│  ├─ images/
│  └─ audio/
│
├─ work/
│  ├─ asset-manifest.json
│  ├─ reference/
│  │  ├─ transcript.json
│  │  ├─ shots.json
│  │  ├─ keyframes/
│  │  ├─ contact-sheet.jpg
│  │  ├─ reference-report.md
│  │  └─ reference-recipe.json
│  ├─ content/
│  │  ├─ brief.md
│  │  ├─ script.json
│  │  ├─ script.md
│  │  ├─ storyboard.json
│  │  └─ storyboard.md
│  ├─ prepared/
│  ├─ motion/
│  ├─ timeline.json
│  └─ timeline.csv
│
├─ renders/
│  ├─ preview-clean.mp4
│  └─ preview-with-captions.mp4
│
├─ delivery/
│  ├─ captions.srt
│  ├─ captions.ass
│  ├─ narration.wav
│  ├─ edit-notes.md
│  ├─ qa-report.md
│  ├─ delivery-manifest.json
│  ├─ assets-used/
│  ├─ motion-graphics/
│  └─ publish/
│     ├─ douyin.md
│     └─ xiaohongshu.md
│
└─ logs/
```

---

## 10. 状态机

```text
CREATED
  ↓
INGESTED
  ↓
REFERENCE_READY ─────────────┐
  ↓                         │ 无参考视频可跳过
CONTENT_READY ◀─────────────┘
  ↓
ASSETS_READY
  ↓
TIMELINE_READY
  ↓
ROUGH_CUT_READY
  ↓
QA_PASSED
  ↓
DELIVERY_READY
```

辅助状态：

- `WAITING_FOR_INPUT`
- `WAITING_FOR_REVIEW`
- `FAILED`

状态写入 `episode.json`：

```json
{
  "id": "EP-0001",
  "mode": "REFERENCE_ADAPT",
  "publishable": true,
  "status": "ASSETS_READY",
  "platforms": ["douyin", "xiaohongshu"],
  "completed_stages": ["ingest", "reference", "content", "assets"],
  "last_error": null,
  "artifacts": {},
  "updated_at": "2026-07-20T16:00:00-04:00"
}
```

规则：

- `REFERENCE_CLONE` 自动设置 `publishable: false`。
- 任何阶段失败均保留已完成产物。
- `--force` 才能强制重新生成。
- 输入或配置变化后，基于 Hash 使下游产物失效。
- Agent 不得手工伪造已完成状态。

---

## 11. 数据合同

### 11.1 `asset-manifest.json`

每个素材至少包含：

- `asset_id`
- `source_path`
- `working_path`
- `kind`
- `mime_type`
- `duration`
- `width`
- `height`
- `fps`
- `has_audio`
- `sha256`
- `status`
- `notes`

### 11.2 `reference-recipe.json`

V1 必需字段：

- 原视频时长、比例和帧率；
- 镜头列表；
- 每个镜头起止时间；
- 关键帧路径；
- 转写文本；
- 画面类型的 Agent 分类；
- 字幕、信息卡、录屏和 B-roll 的粗略使用比例；
- 开头钩子；
- 叙事段落；
- 结尾方式；
- 可迁移的结构规则；
- 不应复制的原始内容。

字幕位置、转场意图和音乐节拍允许使用 `confidence`，不得假装确定。

### 11.3 `script.json`

每段至少包含：

- `segment_id`
- `text`
- `purpose`
- `target_duration`
- `visual_hint`
- `source_refs`
- `status`

### 11.4 `storyboard.json`

每个镜头至少包含：

- `scene_id`
- `script_segment_ids`
- `duration`
- `visual_type`
- `asset_ids`
- `caption`
- `motion_template`
- `missing_assets`
- `notes`

### 11.5 `timeline.json`

```json
{
  "version": "1.0",
  "canvas": {
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "duration": 60,
  "tracks": {
    "video": [],
    "overlay": [],
    "captions": [],
    "voice": [],
    "music": [],
    "effects": []
  }
}
```

每个 Clip 必须有：

- 唯一 `clip_id`
- 起始时间和时长；
- 素材引用；
- 源素材 in/out；
- 布局；
- 音量；
- 转场；
- 可选渲染器；
- 缺失状态。

### 11.6 `qa-report.json`

QA 分为：

1. **确定性 QA**
   - 文件存在；
   - 可解码；
   - 分辨率、帧率、时长；
   - 黑帧；
   - 长静音；
   - 峰值和削波；
   - 时间线越界与重叠；
   - 字幕时间越界；
   - 素材缺失；
   - 未完成占位符。

2. **Agent 视觉 QA**
   - 字幕可读性；
   - 画面与口播匹配；
   - 录屏文字是否过小；
   - 节奏是否明显拖沓；
   - 是否存在无意义重复；
   - 哪些位置需人工修改。

视觉 QA 应读取渲染后抽取的联系表，不依赖 Agent 凭空判断。

---

## 12. Provider 设计

V1 不将任何模型供应商写死。

```yaml
transcription:
  provider: auto
  fallback: manual
  language: zh

tts:
  provider: disabled
  fallback: none

llm:
  provider: agent
  structured_output: true
```

规则：

- 转写 Provider 必须拥有统一接口。
- 无转写服务时允许用户提供文本。
- TTS 默认不是硬依赖。
- API Key 只存在于 `.env` 或工具自身安全存储。
- `.env`、Cookie、Token 和登录状态不得提交。

---

## 13. HyperFrames 边界

HyperFrames 只负责：

- HookTitle
- KeywordCaption
- InfoCard
- ScreenRecordingFrame
- RankingCard
- BeforeAfter
- EndCard
- 其他可复用的解释动画

它不负责：

- Episode 状态；
- 输入管理；
- 参考视频语义分析；
- 完整业务时间线；
- 发布；
- 事实判断。

集成必须有降级路径：

```text
timeline.json
   ├─ FFmpeg 渲染主视频
   └─ HyperFrames 渲染带透明背景或独立背景的动效片段
          ↓
       FFmpeg 合成
```

V1 验收只要求至少三个组件真正参与 Demo：

- HookTitle
- InfoCard
- EndCard

其余组件可在后续迭代添加。

---

## 14. 项目 Skills

V1 只创建九个项目 Skill：

1. `create-episode`
2. `analyze-reference`
3. `write-video-script`
4. `create-storyboard`
5. `prepare-assets`
6. `create-rough-cut`
7. `revise-video`
8. `quality-review`
9. `create-publish-pack`

每个 Skill 的 `SKILL.md` 必须包含：

- 触发条件；
- 输入文件；
- 不允许修改的文件；
- 输出文件；
- 执行命令；
- 验证命令；
- 停止条件；
- 缺失输入时的行为；
- 完成报告格式。

Skill 不应复制大量通用规则，而应引用 `AGENTS.md` 和对应 Schema。

---

## 15. 开发模块与依赖顺序

### 模块 0：设计冻结与仓库审计

交付：

- 最终目录；
- ADR；
- 技术版本清单；
- 开发计划；
- 风险清单。

验收：

- 没有实现代码；
- 所有决策明确；
- 不存在两个业务 CLI；
- V1 与未来功能分开。

### 模块 1：Bootstrap、Doctor 与跨 Agent 基础

交付：

- 安装脚本；
- Doctor；
- Skills 安装/同步；
- AGENTS.md、CLAUDE.md、Cursor Rules；
- 最小 HyperFrames 自检。

验收：

- 新环境可安装；
- 缺少依赖时返回可理解错误；
- 三类 Agent 能读取自己的项目配置；
- 不要求完成视频业务。

### 模块 2：Episode、状态机、Schema 与 CLI

交付：

- Python CLI；
- 配置加载；
- Episode 创建、状态与错误恢复；
- 所有基础 Schema；
- 单元测试。

验收：

- 可创建 Episode；
- 无效状态转换被拒绝；
- Schema 校验可运行；
- CLI 返回稳定退出码。

### 模块 3：输入接收与素材标准化

交付：

- 文件识别；
- 原始素材保护；
- FFprobe；
- Proxy；
- Asset Manifest；
- 损坏文件处理；
- 缓存 Hash。

验收：

- 文本、图片、音频和视频均能识别；
- 原文件 Hash 不变；
- 横屏录屏可生成竖屏代理；
- 重复执行不会重复处理。

### 模块 4：参考视频分析

交付：

- 音频提取；
- 可选转写；
- 镜头检测；
- 关键帧；
- 联系表；
- `reference-recipe.json`；
- Agent 分析 Skill。

验收：

- 无音轨视频可处理；
- 无转写 Provider 时降级；
- 镜头和关键帧可复现；
- 报告区分事实、推测和置信度。

### 模块 5：内容简报、脚本与分镜

交付：

- `brief.md`
- `script.json` / `script.md`
- `storyboard.json` / `storyboard.md`
- 相关 Skills；
- 素材缺口清单。

验收：

- 可有参考视频或无参考视频；
- 每个脚本段落可追溯到输入；
- 每个分镜映射脚本；
- 缺少素材不会被虚构。

### 模块 6：时间线与 FFmpeg 粗剪

交付：

- `timeline.json`
- `timeline.csv`
- 字幕；
- 图片和视频拼接；
- 旁白与 BGM 混合；
- clean / captions 两个 MP4。

验收：

- 可正常解码；
- 9:16；
- 无明显长黑屏；
- 时间线 Schema 通过；
- Demo 不依赖 HyperFrames 也能渲染。

### 模块 7：HyperFrames 动效集成

交付：

- 三个最小组件；
- 动效片段渲染；
- FFmpeg 合成；
- 降级机制。

验收：

- `doctor`、`lint`、`render` 实际通过；
- 输出真实 MP4；
- HyperFrames 失败时基础粗剪仍可生成。

### 模块 8：QA、交付包与发布文案

交付：

- 确定性 QA；
- 视觉联系表；
- Agent Review Skill；
- Delivery Manifest；
- edit-notes；
- 抖音和小红书文案。

验收：

- 故意制造的错误可以被检测；
- 交付包没有绝对路径；
- 用户可直接找到所有人工修改点；
- 不自动发布。

### 模块 9：双 Demo、端到端测试与最终审计

交付：

- 参考改编 Demo；
- 录屏讲解 Demo；
- 一键 Demo；
- 恢复测试；
- 兼容性文档；
- 最终审计报告。

验收：

- 从空 Episode 到 Delivery 完整运行；
- 有真实可播放 MP4；
- 中断后可继续；
- 第二个 Agent 可在只读审计中复现结果。

---

## 16. 测试策略

### 16.1 测试层级

- 单元测试：Schema、状态、路径、Hash、命令构建。
- 集成测试：FFprobe、转码、镜头切分、渲染。
- 黄金测试：小型 Fixture 的输出元数据，而非跨机器逐像素相等。
- E2E：两个 Demo。
- 故障测试：损坏文件、无音轨、无 FFmpeg、无 HyperFrames、缺失素材、流程中断。

### 16.2 跨机器视频测试

不要在不同 Chrome/FFmpeg 版本之间强求逐像素一致。V1 比较：

- 是否可解码；
- 分辨率；
- 帧率；
- 时长容差；
- 音轨存在；
- 黑帧和静音阈值；
- 关键帧截图的感知差异容差。

### 16.3 完成声明

Agent 只有在提供以下证据后才能声称完成：

- 执行命令；
- 返回码；
- 测试摘要；
- 生成文件路径；
- FFprobe 摘要；
- 已知限制；
- 未完成项。

---

## 17. Git 与文件策略

提交：

- 源代码；
- 配置；
- Schema；
- Skills；
- Agent 配置；
- 小型 Fixture；
- 依赖锁文件；
- 文档。

忽略：

- `.env`
- `.venv`
- `node_modules`
- 用户原始素材；
- 缓存；
- 日志；
- 临时渲染；
- 完整输出；
- Cookie 和认证信息。

每个模块单独分支或单独提交。一个模块通过审计后再进入下一个模块。

---

## 18. V1 最终验收清单

### 环境

- [ ] `npm run bootstrap` 可运行
- [ ] `npm run doctor` 能报告真实环境
- [ ] Skills 可安装和同步
- [ ] HyperFrames 最小自检通过

### 跨 Agent

- [ ] Codex 读取 AGENTS.md 与项目 Skill
- [ ] Claude Code 读取 CLAUDE.md、Skill 和 Subagent
- [ ] Cursor 读取 AGENTS.md 或 `.cursor/rules`
- [ ] 三者调用相同业务 CLI

### 核心流程

- [ ] 可创建 Episode
- [ ] 可接收文本、图片、音频、录屏和参考视频
- [ ] 原始素材不被修改
- [ ] 可生成素材清单
- [ ] 可生成参考分析和 Recipe
- [ ] 可生成脚本和分镜
- [ ] 可生成时间线
- [ ] 可生成 SRT
- [ ] 可生成 clean MP4
- [ ] 可生成 captions MP4
- [ ] 可生成 HyperFrames 动效
- [ ] 可生成 QA
- [ ] 可生成编辑交付包
- [ ] 可生成抖音和小红书文案

### 可靠性

- [ ] 重复执行具有幂等性
- [ ] `--force` 可重新生成
- [ ] 中断后可继续
- [ ] 无 HyperFrames 时可降级
- [ ] 无转写时可降级
- [ ] QA 能检测故意错误
- [ ] 第二个 Agent 可复现 Demo

---

## 19. V1 之后的优先级

### P1

- 自然语言局部修改 `revise-video`
- 更多 HyperFrames 组件
- 本地转写 Provider
- TTS Provider
- 三种自有内容模板
- 封面源文件与多版本标题

### P2

- OpenTimelineIO / Premiere / Resolve 适配
- 稳定后再评估剪映草稿
- Remotion 模板
- 数据复盘
- 多平台横竖屏适配

### P3

- 自动发布
- 云渲染
- 多账号和内容矩阵

---

## 20. 已核实的技术事实

截至 2026-07-20：

- HyperFrames 官方支持通过 `npx skills add heygen-com/hyperframes` 安装 Agent Skills，并明确列出 Claude Code、Cursor 和 Codex；基础要求为 Node.js 22+ 与 FFmpeg。
- HyperFrames 为纯 HTML/CSS/可寻址动画的确定性视频框架，支持 CLI 的 preview、lint 和 render。
- Codex 插件是工作流能力容器，可以包含 Skills 和 Apps；项目不能假定其他 Agent 自动拥有 Codex 插件。
- Codex 可通过仓库中的 `AGENTS.md` 获取项目指令。
- Claude Code 将 `CLAUDE.md`、`.claude/skills/`、`.claude/agents/` 和 Hooks 分别用于持久规则、工作流、隔离 Agent 和确定性自动化。
- Cursor 的项目规则位于 `.cursor/rules/`，也支持根目录 `AGENTS.md` 作为简单项目指令。
- `npx skills` 支持项目级安装以及 Claude Code、Codex 和 Cursor 等多个 Agent；可以使用复制模式避免 Windows 符号链接问题。

官方来源：

- https://github.com/heygen-com/hyperframes
- https://help.openai.com/en/articles/20001256-plugins-in-codex
- https://openai.com/index/introducing-codex/
- https://code.claude.com/docs/en/features-overview
- https://code.claude.com/docs/en/claude-directory
- https://docs.cursor.com/context/rules
- https://github.com/vercel-labs/skills
