# AGENTS.md

## 1. 项目目标

Agent Video Studio 是一个通用短视频辅助制作系统。

用户可能只提供文本、图片、参考视频、录屏、音频和链接。系统应将这些输入整理为参考分析、内容简报、脚本、分镜、素材清单、时间线、字幕、视频粗稿、质量报告和可人工编辑的交付包。

V1 的目标不是无人审核的最终成片，而是一个可以继续在剪映等软件中修改的可靠粗稿。

## 2. V1 边界

必须支持：

- 参考视频改编；
- 录屏讲解；
- 抖音和小红书竖屏输出；
- FFmpeg 基础粗剪；
- HyperFrames 标题、信息卡和结尾卡；
- 带字幕和无字幕两个 MP4；
- SRT、时间线、素材包和编辑说明；
- 人工发布。

不得自行扩展到：

- 自动发布；
- 自动登录、评论或私信（ChatCut MCP 登录除外，且不得把凭证写入仓库）；
- 数字人和声音克隆；
- 云渲染；
- 多账号矩阵。

允许进入正式链路（须按路由表调用，产物回挂 Episode，见 ADR-0006）：

- Remotion 代码驱动渲染；
- CapCut/剪映草稿工具（`capcut-david` / `cut-skill`，原 cut-motion 继任）；
- ChatCut、video-use、Seedance、OpenMontage、Pixelle-Video、IP Strategist。

## 3. 制作模式

### REFERENCE_CLONE

仅用于内部学习。必须设置 `publishable: false`，不得默认生成公开发布包。

### REFERENCE_ADAPT

默认公开模式。可以参考结构、节奏、镜头语法和动效逻辑，但必须替换原文案、配音、素材、案例、数据、观点、标题和封面。

### ORIGINAL

使用项目自有模板，不依赖单条参考视频。

## 4. 核心规则

1. 原始素材不可移动、覆盖或修改。
2. 所有处理使用工作副本。
3. 不虚构事实、数据、产品功能、运行结果或用户经历。
4. 缺失素材必须标记，不使用明显无关内容硬凑。
5. Codex 插件只能作为增强，核心流程必须能通过项目 CLI 运行。
6. `timeline.json` 是渲染器共享的中间协议。
7. HyperFrames 只负责动效和包装，不管理 Episode 状态。
8. 不自动发布。
9. 不将密钥、Cookie、Token 或登录状态写入仓库。
10. 未运行验证命令，不得声称完成。

## 5. 单一真相来源

- 项目规则：`AGENTS.md`
- Claude 入口：`CLAUDE.md`
- 配置：`config/`
- 数据合同：`schemas/`
- Episode 状态：`episode.json`
- 项目自有 Skills：`skills-src/`
- 第三方视频 Skills：`third_party_skills/`（`npm run skills:vendor`）
- 视频插件强制路由：`docs/video-plugin-routing.md`
- 业务 CLI：`python -m avs`
- 时间线：`timeline.json`

禁止创建第二套互相独立的状态、配置或 CLI。

## 5.1 视频任务强制 Skills

**任何视频相关任务开始前，必须先读 `docs/video-plugin-routing.md`，并按场景加载对应第三方 Skill。** 不得跳过路由表。旁路渲染器不得伪造状态机完成态。

路由表覆盖（含本批强制接入）：HyperFrames、Remotion、video-use、Seedance / seedance-free、ChatCut、CapCut（`capcut-david` + `cut-skill`）、**jianying-editor**（与 cut-skill 并存分流）、**ffmpeg**、**azure-speech**、**elevenlabs**、**ai-video-shot-prompt**、**ltx-prompt-director**、**epidemic-sound**、**moneyprinterturbo**、**pixelle-video**、IP Strategist、OpenMontage。

## 6. 标准流程

1. 创建 Episode。
2. 清点并标准化输入。
3. 有参考视频时生成参考分析。
4. 生成内容简报、脚本和分镜。
5. 准备素材并列出缺口。
6. 构建时间线。
7. FFmpeg 生成基础粗剪。
8. HyperFrames 生成必要动效并合成。
9. 运行确定性 QA 和视觉 QA。
10. 生成可编辑交付包。
11. 等待用户人工修改和发布。

## 7. 状态机

正式状态：

- `CREATED`
- `INGESTED`
- `REFERENCE_READY`
- `CONTENT_READY`
- `ASSETS_READY`
- `TIMELINE_READY`
- `ROUGH_CUT_READY`
- `QA_PASSED`
- `DELIVERY_READY`

辅助状态：

- `WAITING_FOR_INPUT`
- `WAITING_FOR_REVIEW`
- `FAILED`

不得跳过前置状态或手工伪造完成状态。

## 8. 开发规则

开始任务前：

1. 阅读本文件。
2. 阅读项目规范和当前模块 Prompt。
3. 检查 Git 状态。
4. 检查前置模块是否通过。
5. 先输出本模块实施计划，不执行下一模块。

### Git 分支（硬约束）

- 本仓库**只使用 `main` 一个分支**。
- 禁止创建、检出或推送任何其他分支（含 `codex/*`、`feature/*`、临时分支）。
- Codex / Claude / Cursor / 任何 Agent：所有提交与推送必须在 `main` 上完成；发现自己不在 `main` 时立即切回，不得另开分支「凑合」。
- 远程出现非 `main` 分支时，合并进 `main` 后删除该远程分支。

开发时：

- 一次只实现当前模块。
- 使用小而清晰的文件和接口。
- 先写失败测试，再写最小实现。
- 所有结构化输出必须通过 Schema。
- 所有外部命令必须检查退出码。
- 使用项目相对路径。
- 为错误提供明确消息和非零退出码。
- 同一命令重复执行应保持幂等。
- 只有 `--force` 可以覆盖可再生成产物。
- 不修改与当前模块无关的代码。

## 9. 媒体规则

- V1 默认画布：1080×1920、30fps、H.264、AAC。
- 所有输入先用 FFprobe 检查。
- 损坏文件不得进入渲染。
- 横屏素材必须明确使用 contain、cover 或布局模板，不能静默拉伸。
- 缺少音频时必须正常降级。
- 字幕必须位于安全区。
- 不同机器的视频输出不要求逐像素相等；测试元数据、解码和容差。

## 10. HyperFrames 与其它渲染器

- 安装并使用官方 HyperFrames Skills（项目内：`third_party_skills/hyperframes`）。
- 实际运行 doctor、lint 和 render。
- V1 最少实现 HookTitle、InfoCard、EndCard。
- HyperFrames 失败时必须保留 FFmpeg 基础粗剪。
- 不得把整个业务流程写进 HyperFrames HTML。
- Remotion / ChatCut / CapCut / JianyingEditor / video-use / OpenMontage / Pixelle-Video / MoneyPrinterTurbo / FFmpeg·Azure·ElevenLabs·Epidemic Sound·镜头脚本 Skills 按 `docs/video-plugin-routing.md` 启用；失败不得静默冒充成功（见 ADR-0006）。

## 11. 完成报告

每个模块结束时必须报告：

- 完成内容；
- 修改文件；
- 执行命令；
- 测试及返回码；
- 生成产物；
- 已知限制；
- 未完成项；
- Git commit；
- 是否满足本模块验收。

只要验收项未全部通过，就必须明确标记为“未完成”，不得进入下一个模块。
