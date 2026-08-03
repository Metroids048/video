# 抖音 Codex 短视频流程研究台账

更新时间：2026-08-03

本台账记录本次会话通过用户 Chrome 打开的 18 条参考页面。研究只提炼流程、镜头语法和工程取舍，不复制原文案、素材、观点、封面或发布内容，也不由项目自动下载第三方视频。

## 证据口径

- **A：页面已解析为 `www.douyin.com/video|note/<id>` 长链，并核验页面可见文案、图文页或视频内容。** 有明确时间点时单独记录；A 级不等于已下载原视频或取得逐字转写。
- 本轮 18 条均达到 A 级。标题卡信息与页面内可见证据分开记录，无法从页面确认的功能不写成事实。

### 重要限制

A 级表示页面已解析并完成页面级核验，不等于仓库保存了原始视频、逐帧联系表或完整音轨转写。因此本台账不能支持“我已经完整看过 18 条原片并能精确复刻其剪辑”的表述。需要精确判断画面、节奏、字幕和声音时，必须取得有权使用的本地副本，按 `analyze-reference` 生成 `ffprobe`、镜头边界、关键帧、联系表、转写和采样帧证据；只有这些产物齐全，才允许把观察写入分镜规则。

## 18 条已核验参考

| # | 作者 / 类型 | 解析后的页面 | 页面核验要点 | 落地到 AVS 的取舍 | 证据 |
|---|---|---|---|---|---|
| 1 | 阿柴ChayAI / 视频（6:43） | `www.douyin.com/video/7663735393996508452` | 选题、文案、音频、视觉/动画、可编辑交付；先用音频确定时间线，最终仍需人工精修 | 已落为 `workflow resume`、参考 recipe、音频时间基准、可编辑交付包和人工关口 | A |
| 2 | Mysteryboxed / 视频 | `www.douyin.com/video/7663689770068921609` | AI 被动收入的五种内容模式：KDP、联盟博客、YouTube、长期答疑、记录工作 | 仅作为内容选题样例；收益、案例和数据必须由用户提供可靠来源，不进入渲染核心 | A |
| 3 | 比高 / 视频 | `www.douyin.com/video/7654162614997552434` | AI Agent 的价值要转化为传统行业的业务结果，重点是场景包装、话术和投放 | 内容简报必须写清目标用户、业务场景和可验证结果，不虚构转化数据 | A |
| 4 | 阿金成长记 / 图文（3 页） | `www.douyin.com/note/7662595050442522292` | 将对标文案蒸馏为 Skill，再用商业方法论优化 hook；工具不能代替解决用户问题和数据迭代 | `analyze-reference` 只提炼结构，脚本必须原创；发布后的数据复盘留给人工流程 | A |
| 5 | 宗雷AI / 视频 | `www.douyin.com/video/7661621223671575141` | 展示六类能力：HyperFrames、Video Use、Promotion、Generative Media、Video Cut、AI Video Workflow | HyperFrames 已作为受控动效层；其余名称无可审计来源时不盲装，核心 CLI 不依赖插件 | A |
| 6 | 班斑 / 视频 | `www.douyin.com/video/7661912972772028138` | 创业流程分为想法、MVP、发布、规模化；标准文档让团队和 AI 可重复协作 | 项目用 ADR、Schema、Skill 和 Episode 状态固定流程；V1 停在人工发布前 | A |
| 7 | 小屿AI实战笔记 / 视频 | `www.douyin.com/video/7666709034884044499` | coordinator、researcher、writer、editor、builder 五角色，配合三层质量防护和信息路由 | AVS 用内容、素材、审查 Skill 分工，但共享 `episode.json`，不创建第二套 Agent 状态 | A |
| 8 | 小澈的赛博茶水间 / 图文 | `www.douyin.com/note/7665652596241075519` | 推荐 `video-shotcraft` 的镜头卡、动态样片和产品宣传片能力 | 已审计并固定安装该 Skill，仅复用镜头语法、节奏和声音设计，不采用其 Remotion 主链 | A |
| 9 | 子昂从零出发 / 视频 | `www.douyin.com/video/7665966861477088555` | 展示作者自有的一键智能剪辑与封面 Skill，页面仅指向主页领取 | 无公开、可审计仓库和许可，不写入项目依赖；AVS 继续用自有剪辑/交付 Skill | A |
| 10 | Tam / 图文 | `www.douyin.com/note/7666821695352868714` | 介绍 `video-shotcraft` 的镜头卡、样片、Remotion 模板和声音设计资产 | 与第 8、13 条交叉验证同一开源项目；安装固定 commit，并显式隔离 Remotion | A |
| 11 | AI科技视野 / 视频 | `www.douyin.com/video/7662716941353749775` | Seedance 创意拆解、Gen 素材、Hyper 渲染、Video Use 精修、Remotion 包装 | AVS 只吸收“拆解→素材→包装→精修”顺序；外部生成素材需授权，主渲染仍为 FFmpeg + HyperFrames | A |
| 12 | 子昂从零出发 / 视频 | `www.douyin.com/video/7666770325815823642` | 再次展示作者自有智能剪辑 Skill 的一键剪辑和封面能力 | 页面没有可审计 GitHub 来源，因此不安装；对应能力由现有 `create-rough-cut` 和交付流程覆盖 | A |
| 13 | Vincent / 视频 | `www.douyin.com/video/7664602646754581482` | `video-shotcraft` 正式开源，包含大量镜头卡、动态样片和产品宣传片模板 | 已核对作者仓库、Apache-2.0 许可并固定 commit `d491544`；只作参考库 | A |
| 14 | 墨白Neo / 视频 | `www.douyin.com/video/7666310910251916667` | VOX 风格三步：风格板、分镜、Omni 生成视频 | AVS 将风格约束写入 brief/分镜；生成式视频不是 V1 必需依赖，缺失素材必须标记 | A |
| 15 | 见舟AI / 视频 | `www.douyin.com/video/7647556381230591592` | 视频/文稿、转写校对、章节、画面设计、QA、渲染；先把剪辑标准沉淀为 Skill | 与 AVS 的 ingest→content→timeline→QA→delivery 一致；转写不可用时保留人工降级 | A |
| 16 | 郑茜茜（xi） / 视频 | `www.douyin.com/video/7664444532058033449` | Codex + Obsidian 自生长知识库、定时任务、Skill 蒸馏和数据复盘 | 可借鉴知识沉淀方式，但 AVS 不引入独立知识库或定时发布，项目文档仍是单一规则来源 | A |
| 17 | AskCc / 视频（19 秒） | `www.douyin.com/video/7666820677693396075` | 虚构面试情境用短冲突、快速反转和明确结尾完成叙事 | 只作为短剧情节奏参考；不把虚构经历包装成真实案例 | A |
| 18 | 普通人的AI / 视频 | `www.douyin.com/video/7666766502665686315` | 十类 Skill：安装检查、对标雷达、爆款拆解、人话口播、分镜、录屏清单、封面标题、字幕剪辑、素材归档、数据复盘 | AVS 已覆盖安装/参考/脚本/分镜/素材/字幕/归档/QA；发布和数据复盘保持人工 | A |

## 第 1 条的时间点证据

| 时间点 | 可验证流程 | AVS 实现 |
|---|---|---|
| 00:39 | 选题 → 文案 → 音频 → 视觉/动画 → 可编辑交付 | `workflow resume` 串联已有步骤，交付 timeline/SRT/素材/编辑说明而非剪映草稿 |
| 01:06 | 采集竞品文案，分析成模板并沉淀标准文档 | `reference-recipe.json` + 本台账；改编模式禁止复制原文案 |
| 02:21 | 先生成音频，以声音时长确定分镜与时间线 | `timeline.json` 的音频轨为共享时间基准；素材准备优先检查配音 |
| 02:56 | 根据文案时间线和参考图设计分镜，再调用图片能力 | `write-video-script` → `create-storyboard` → `prepare-assets`；缺口写入 `missing-assets.md` |
| 04:02 | 用首帧图生成动画，并由 AI 选择效果 | HyperFrames 只负责标题、信息卡和结尾卡；外部生成素材须由用户提供并确认 |
| 04:20 | 输出可继续编辑的剪辑结果 | 交付 MP4、SRT、`timeline.json`、素材、QA 和编辑说明，不逆向生成剪映草稿 |
| 05:31 | 流程仍是粗稿，需要针对内容自定义 | `workflow` 停在 Agent/人工审核关口，不自动发布 |

## 交叉结论与项目决策

1. **可靠主链：** 输入清点 → 参考结构提炼 → 原创 brief/script/storyboard → 素材确认 → `timeline.json` → FFmpeg 粗剪 → HyperFrames 包装 → QA → 可编辑交付 → 人工发布。
2. **Agent 编排：** 可以分角色执行，但所有角色必须读写同一个 Episode 工作区；确定性命令可续跑，事实判断、素材批准和发布必须停在人工关口。
3. **参考改编：** 只迁移结构、节奏、镜头语法和动效逻辑，替换文案、配音、素材、案例、数据、观点、标题和封面。
4. **Skill 安全：** 只有来源、许可、版本和依赖可审计的 Skill 才安装。社交页面只写“主页领取”的 Skill 不作为项目依赖。
5. **渲染边界：** `video-shotcraft` 的 Remotion 实现只作知识参考；V1 的共享协议和主渲染器仍是 `timeline.json`、FFmpeg 与 HyperFrames。

## 第三方 Skill 审计

| Skill | 来源与固定版本 | 处理结果 | 原因 |
|---|---|---|---|
| HyperFrames | npm `hyperframes@0.7.68` 官方内置 Skills | 已安装并纳入 doctor/lint/check/render 验收 | V1 的标题、信息卡和结尾卡动效层 |
| video-shotcraft | `Vincentwei1021/video-shotcraft@d4915443232e89527fdc9d7e79f132ba411fc440`，Apache-2.0 | 项目 vendor 至 `third_party_skills/video-shotcraft`（`usage: reference_only`）；`skills.lock.json` 已固定 | 仅作镜头语法、节奏和声音设计参考，Remotion 不进入核心管线 |
| 子昂自有剪辑 Skill | 页面仅指向作者主页 | 未安装 | 无公开可审计来源、版本和许可，现有项目能力已覆盖 |
| dy-note 研究辅助 | `Rimagination/dy-note@9a65f0d`，MIT | 未安装 | 核心依赖 `web-access` 在当前环境不存在；本轮已通过 Chrome 完成页面取证，避免制造半可用安装 |

## 已落实的完整链路

```text
用户输入/本地授权参考
  -> ingest + asset-manifest
  -> 本地 reference recipe（可选）
  -> brief / script / storyboard（Agent，人工审核）
  -> assets approve（人工）
  -> timeline.json + SRT
  -> FFmpeg 粗剪 + HyperFrames 包装
  -> 确定性 QA + 人工视觉复核
  -> 可编辑 delivery/，人工发布
```

## 2026-08-03 A+1 查漏

本轮只做缺口对齐与可审计 Skill 入仓，不重爬抖音原片，不把旁路渲染器接到 Episode 完成态，不安装无公开仓的社交 Skill。

参考改编仍只迁移结构、节奏、镜头语法和动效逻辑；不复制原文案、素材、观点、封面；不把抖音短链视频批量写入 `input/`。

### 已 vendor（本轮 `--check` 确认）

| Skill | 本地路径 | 备注 |
|---|---|---|
| HyperFrames / hyperframes-cli | `third_party_skills/hyperframes*` | 生产动效层 |
| Remotion skills | `third_party_skills/remotion*` | 代码驱动成片旁路 |
| video-use | `third_party_skills/video-use` | 转写/粗剪旁路 |
| seedance | `third_party_skills/seedance` | 提示词 / 付费路径可选 |
| ChatCut | `third_party_skills/chatcut/` | MCP 登录本机完成 |
| capcut-david / cut-skill | `third_party_skills/capcut-david`、`cut-skill` | 剪映草稿旁路 |
| ip-strategist | `third_party_skills/ip-strategist` | 选题口播，不碰剪辑 |
| openmontage | `third_party_skills/openmontage` | AGPL；sparse vendor |
| jianying-editor | `third_party_skills/jianying-editor` | 与 cut-skill 并存分流 |
| ffmpeg | `third_party_skills/ffmpeg` | 本地 FFmpeg CLI skill |
| azure-speech | `third_party_skills/azure-speech` | 可选；默认免费 TTS/STT |
| elevenlabs（+ text-to-speech） | `third_party_skills/elevenlabs` | 可选高清晰配音 |
| ai-video-shot-prompt | `third_party_skills/ai-video-shot-prompt` | 镜头脚本提示词 |
| ltx-prompt-director | `third_party_skills/ltx-prompt-director` | LTX 生产提示词 |
| epidemic-sound | `third_party_skills/epidemic-sound` | curated MCP 入口 |
| moneyprinterturbo | `third_party_skills/moneyprinterturbo` | 仅 sparse docs/skill |

### 本轮补装 / 对齐

| Skill | 处理 |
|---|---|
| video-shotcraft | 从仅全局 `~/.codex/skills` 改为项目 `third_party_skills/video-shotcraft`，pin `d491544`，`reference_only`；已写入 routing / doctor / ensure |
| seedance-free | 项目自有平替；登记 lock 为 `status: local`，不伪造 GitHub 上游 |

### 明确拒绝（不下载）

| 项 | 原因 |
|---|---|
| 子昂 Codex 智能剪辑 / 封面 Skill | 无公开可审计仓库与许可 |
| dy-note 研究辅助 | 依赖当前环境缺失的 `web-access` |
| Hermes 全自动发布 / 热搜爬取流水线 | 违反「不自动发布」；角色分工已由 content/media/reviewer 覆盖 |
| 抖音短链原视频批量入库 | 项目禁止自动下载第三方平台视频 |
| 宗雷页面中无可审计来源的命名插件 | 不盲装；已有可审计同名能力走现有 vendor |
