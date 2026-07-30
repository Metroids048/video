# Agent Video Studio V1 — 实施路线图

> 版本：1.1 | 日期：2026-07-31 | 状态：模块 0–10 已实现，待持续运行验证
> 每个模块均有可执行验证；本路线图记录实际仓库状态，不替代验收日志。

---

## 模块依赖顺序

```
模块 0（设计冻结）
    ↓
模块 1（Bootstrap / Doctor / 跨 Agent 基础）
    ↓
模块 2（Episode / 状态机 / Schema / CLI）
    ↓
模块 3（输入接收与素材标准化）
    ↓
模块 4（参考视频分析）
    ↓
模块 5（内容简报 / 脚本 / 分镜）
    ↓
模块 6（时间线与 FFmpeg 粗剪）
    ↓
模块 7（HyperFrames 动效集成）
    ↓
模块 8（QA / 交付包 / 发布文案）
    ↓
模块 9（双 Demo / 端到端测试 / 最终审计）
    ↓
模块 10（Codex 全链路编排 / 证据台账 / 运行手册）
```

---

## 模块 0：设计冻结与仓库审计

**状态：已完成**
**提交：** `docs: freeze Agent Video Studio V1 architecture`

### 交付

| 产物 | 路径 | 状态 |
|------|------|------|
| 系统架构文档 | `docs/architecture.md` | 已创建 |
| ADR-0001 唯一 CLI | `docs/decisions/0001-python-cli.md` | 已创建 |
| ADR-0002 时间线合同 | `docs/decisions/0002-timeline-contract.md` | 已创建 |
| ADR-0003 HyperFrames 边界 | `docs/decisions/0003-hyperframes-boundary.md` | 已创建 |
| ADR-0004 Skills 布局 | `docs/decisions/0004-agent-skill-layout.md` | 已创建 |
| 实施路线图 | `docs/implementation-roadmap.md` | 已创建 |
| 工具版本清单 | `tools-manifest.yaml` | 已创建 |
| Skills 锁文件初始结构 | `skills.lock.json` | 已创建 |
| Git 忽略规则 | `.gitignore` | 已创建 |
| 项目规范副本 | `docs/Agent-Video-Studio-V1.md` | 已创建 |
| 目录骨架 | 各目录 `.gitkeep` | 已创建 |
| 审计报告 | `docs/architecture.md` §9 | 已嵌入 |

### 验收

- [x] 无实现代码
- [x] 所有决策明确，无 TBD / TODO
- [x] 不存在两个业务 CLI
- [x] V1 与未来功能分开
- [x] `tools-manifest.yaml` 列出所有必需工具及版本
- [x] 4 个 ADR 均为 Status: Accepted
- [x] 目录树与职责说明完整
- [x] 规范、AGENTS.md 与 ADR 不互相冲突

---

## 模块 1：Bootstrap、Doctor 与跨 Agent 基础

**状态：已完成**
**前置：** 模块 0 通过
**提交：** `build: add bootstrap doctor and agent compatibility`

### 交付

- `package.json`、`pyproject.toml`、`.env.example`
- `CLAUDE.md`（引用 `AGENTS.md`）
- `.claude/settings.json`
- `.claude/agents/content-worker.md`
- `.claude/agents/media-worker.md`
- `.claude/agents/reviewer.md`
- `.cursor/rules/project.mdc`、`.cursor/rules/media.mdc`
- `scripts/bootstrap.ps1`、`scripts/bootstrap.sh`
- `scripts/sync_skills.py`、`scripts/install_skills.mjs`、`scripts/verify.mjs`
- `skills-src/` 各目录的 `SKILL.md` 骨架（frontmatter 齐全，无占位内容）
- HyperFrames 官方 Skills 安装
- `skills.lock.json`（填充 HyperFrames 实际版本）

### 验收门槛

- `npm run bootstrap` 完整运行，新环境可安装
- `python -m avs doctor` 返回稳定退出码
- 缺少 FFmpeg 时返回非零退出码且提示可读
- Claude / Codex / Cursor 配置文件存在且可解析
- Skills 可同步，重复运行结果一致
- 无媒体业务逻辑

---

## 模块 2：Episode、状态机、Schema 与统一 CLI

**状态：已完成**
**前置：** 模块 1 通过
**提交：** `feat: add episode domain state machine and schemas`

### 交付

- `src/avs/__main__.py`、`cli.py`、`state.py`、`config.py`、`paths.py`、`models/`
- `config/*.yaml`（全部配置文件）
- `schemas/*.schema.json`（全部 8 个 Schema）
- `python -m avs episode create/status/validate/fail/reset`

### 验收门槛

- `python -m avs episode create TEST-0001` 实际运行
- 无效状态转换被拒绝，返回非零退出码
- 全部 Schema 校验可运行
- `REFERENCE_CLONE` 自动设置 `publishable: false`
- 单元测试全部通过

---

## 模块 3：输入接收与素材标准化

**状态：已完成**
**前置：** 模块 2 通过
**提交：** `feat: add safe media ingestion and asset manifest`

### 交付

- `src/avs/ingest/`（discovery / probe / hashing / normalize / manifest）
- `python -m avs ingest <ID>`、`assets list`、`assets validate`
- `work/asset-manifest.json`（通过 Schema）
- `skills-src/prepare-assets/SKILL.md`（完整）

### 验收门槛

- 文本 / 图片 / 音频 / 视频均能识别
- 原始文件 SHA-256 前后完全相同
- 损坏文件被标记且不进入下游
- 重复执行不重复转码
- 横屏录屏生成竖屏代理
- Episode 状态转为 `INGESTED`

---

## 模块 4：参考视频分析

**状态：已完成**
**前置：** 模块 3 通过
**提交：** `feat: add reference video analysis pipeline`

### 交付

- `src/avs/reference/`（audio / shots / keyframes / contact_sheet / transcription / recipe）
- `python -m avs reference analyze <ID>`、`reference validate <ID>`
- `work/reference/reference-recipe.json`（通过 Schema）
- `skills-src/analyze-reference/SKILL.md`（完整）

### 验收门槛

- 无音轨视频可处理
- 无转写 Provider 时降级
- 镜头切分可重复
- Recipe 区分事实、推测和置信度
- Episode 状态转为 `REFERENCE_READY`

---

## 模块 5：内容简报、脚本与分镜

**状态：已完成**
**前置：** 模块 4 通过（或明确无参考视频）
**提交：** `feat: add agent-driven brief script and storyboard workflow`

### 交付

- `skills-src/write-video-script/SKILL.md`（完整）
- `skills-src/create-storyboard/SKILL.md`（完整）
- CLI 支持：Schema 校验 + 状态推进
- `work/content/brief.md`、`script.json`、`script.md`、`storyboard.json`、`storyboard.md`

### 验收门槛

- Script / Storyboard JSON 通过 Schema
- 每个 Scene 可追溯到 Script Segment
- 缺少素材生成 `missing-assets.md`，不虚构
- Agent 实际执行一次 Fixture
- Episode 状态正确

---

## 模块 6：时间线与 FFmpeg 粗剪

**状态：已完成**
**前置：** 模块 5 通过
**提交：** `feat: add timeline engine and ffmpeg rough cut`

### 交付

- `src/avs/timeline/`（builder / models / validate / csv_export）
- `src/avs/render/`（ffmpeg / filters / audio / captions / layouts）
- `timeline.json`、`timeline.csv`、`captions.srt`
- `renders/preview-clean.mp4`、`renders/preview-with-captions.mp4`
- `skills-src/create-rough-cut/SKILL.md`（完整）

### 验收门槛

- 两个 MP4 可通过 FFprobe 解码
- 1080×1920、30fps
- 时间线通过 Schema
- 不依赖 HyperFrames
- Episode 状态经过 `TIMELINE_READY` → `ROUGH_CUT_READY`
- 实际生成一个 Demo MP4

---

## 模块 7：HyperFrames 动效集成

**状态：已完成**
**前置：** 模块 6 通过
**提交：** `feat: integrate hyperframes motion graphics`

### 交付

- `renderers/hyperframes/components/HookTitle/`
- `renderers/hyperframes/components/InfoCard/`
- `renderers/hyperframes/components/EndCard/`
- `renderers/hyperframes/compositions/demo/`
- FFmpeg 合成管道
- 降级机制（HyperFrames 失败 → FFmpeg 静态卡片）

### 验收门槛

- `npx hyperframes doctor`、`lint`、`render` 有真实日志
- 三个组件出现在 Demo 中
- 生成真实 MP4
- HyperFrames 失败时基础粗剪仍然存在

---

## 模块 8：QA、交付包与发布文案

**状态：已完成**
**前置：** 模块 7 通过（或已验证 HyperFrames 降级）
**提交：** `feat: add deterministic qa and editable delivery package`

### 交付

- `src/avs/qa/`（decode / metadata / black_frames / silence / audio_levels / timeline_checks / subtitle_checks / contact_sheet / report）
- `src/avs/delivery/`（manifest / package / paths）
- `python -m avs qa <ID>`、`deliver <ID>`
- `delivery/qa-report.md`、`delivery-manifest.json`、`edit-notes.md`
- `skills-src/quality-review/SKILL.md`（完整）
- `skills-src/create-publish-pack/SKILL.md`（完整）
- `delivery/publish/douyin.md`、`delivery/publish/xiaohongshu.md`

### 验收门槛

- 故意黑帧 / 长静音 / 字幕越界被检测
- Delivery Manifest 可校验，无绝对路径
- `REFERENCE_CLONE` 不生成可发布标记
- 不触发发布动作

---

## 模块 9：双 Demo、端到端测试与最终审计

**状态：已完成**
**前置：** 模块 1–8 均独立通过
**提交：** `test: add end to end demos and harden v1 pipeline`

### 交付

- `fixtures/reference-adapt-demo/`（完整 Fixture + 预期元数据）
- `fixtures/screen-explainer-demo/`（完整 Fixture + 预期元数据）
- `npm run demo`、`npm run demo:reference`、`npm run demo:screen`、`npm run verify`
- 恢复测试（中断后继续，不重复已完成阶段）
- 降级测试（无转写、无 HyperFrames、无音轨、缺失素材）
- `README.md`、`docs/getting-started.md`、`docs/input-guide.md`
- `docs/editing-guide.md`、`docs/troubleshooting.md`、`docs/compatibility.md`

### 验收门槛

- 两个 Demo 生成可播放 MP4
- 交付包完整，无绝对路径
- `npm run verify` 返回 0
- 重复执行幂等
- 无 TODO / TBD / 空实现 / 跳过测试

---

## 模块 10：Codex 全链路编排、证据台账与运行手册

**状态：已完成**
**ADR：** `docs/decisions/0005-workflow-orchestration.md`

### 交付

- `python -m avs workflow status/next/resume`：只续跑确定性命令，返回机器可读下一步；
- `src/avs/workflow.py`：从 `episode.json` 和既有工作区推导状态，不创建第二套状态；
- `skills-src/orchestrate-video-production/SKILL.md`：将 Codex 的内容、素材和渲染协作固定为项目 Skill；
- `docs/reference-research/douyin-codex-short-video-study.md`：对 18 条用户提供参考的证据分级台账；
- `README.md`、输入、编辑、排障、兼容性文档；
- 验证门禁：检查运行手册、工作流 CLI、Skill 同步和路线图状态。

### 验收门槛

- `workflow resume` 只执行 ingest/reference/content init/既有 run，遇 Agent 或人工关口安全停止；
- 不自动下载第三方链接，不自动审批内容/素材，不自动发布；
- 完整 `npm run verify`、HyperFrames doctor/lint/render 与两套真实 Demo 均通过；
- 参考台账不能把未打开页面伪装成已观看分析。

---

## Post-V1 优先级（不在本仓库实施）

### P1（V1 稳定后优先）

- `revise-video` Skill 自然语言修改
- 更多 HyperFrames 组件（KeywordCaption / ScreenRecordingFrame 等）
- 本地转写 Provider（whisper.cpp）
- TTS Provider 接入
- 三种自有内容模板
- 封面源文件与多版本标题

### P2

- OpenTimelineIO / Premiere / Resolve XML 适配
- 剪映草稿（稳定后评估）
- Remotion 模板
- 多平台横竖屏适配

### P3

- 自动发布
- 云端分布式渲染
- 多账号内容矩阵

---

## 风险清单

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Windows 符号链接权限 | Skills 同步失败 | 使用 `--copy` 模式，`sync_skills.py` 强制复制 |
| HyperFrames Chromium 安装 | 模块7 无法完成 | 降级路径：FFmpeg 静态卡片；doctor 调用框架自检 |
| 转写 Provider 缺失 | 参考分析不完整 | `manual` 降级，用户可提供文本 |
| 跨机器视频输出不一致 | 黄金测试误判 | 比较元数据和感知差异，不要求逐像素一致 |
| 大型媒体 Fixture 进 Git | 仓库膨胀 | `episodes/*/input/` 在 `.gitignore`；Fixture 使用小型样本 |
