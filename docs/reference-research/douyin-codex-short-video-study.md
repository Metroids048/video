# 抖音 Codex 短视频流程研究台账

更新时间：2026-07-31

本台账只记录本次会话可验证的内容。它用于提炼工作流能力，不用于复制原文案、素材、观点、封面或发布内容。远程链接不被项目自动下载。

## 证据等级

- **A：已观看并按时间点记录。**
- **C：仅有用户提供的分享卡片标题/作者/短链。** 可作为待研究主题，不能据此宣称视频中的具体流程或结论。

## 参考清单

| # | 作者 | 用户提供的标题/主题 | 链接 | 证据 |
|---|---|---|---|---|
| 1 | 阿柴ChayAI | 我用 Codex 搭了一个视频剪辑的工作流 | `www.douyin.com/video/7663735393996508452` | A |
| 2 | Mysteryboxed | 如何用 AI 获得被动收入？五分钟精读油管大神教程 | `v.douyin.com/S2quX2BOus4` | C |
| 3 | 比高 | 2026 年 AI 智能体的红利，藏在下沉市场里 | `v.douyin.com/8WWWuuUs4Hg` | C |
| 4 | 阿金成长记 | codex 帮我赚钱了 | `v.douyin.com/Efj8lmmN7Bw` | C |
| 5 | 宗雷AI | Codex 最强玩法：6 个 skill 做一整条视频 | `v.douyin.com/4ZVQBJjK6Zo` | C |
| 6 | 班斑 | AI 创业教程：AI 时代的创业全局观 | `v.douyin.com/PvZzIKZZ3Pw` | C |
| 7 | 小屿AI实战笔记 | Hermes Agent Team 五角色 v3.1 | `v.douyin.com/WI4vHvmJVTE` | C |
| 8 | 小澈的赛博茶水间 | 视频生成 skill | `v.douyin.com/ygrhKE_yHjk` | C |
| 9 | 子昂从零出发 | Codex 视频剪辑 skill 免费分享，一键智能剪辑 | `v.douyin.com/BhobwOhiFeM` | C |
| 10 | Tam | video-shotcraft 视频生成 skill | `v.douyin.com/BR3mE_pXc2M` | C |
| 11 | AI科技视野 | Codex 完整自动化链路：Seedance 拆分 | `v.douyin.com/xk32wZMjQdw` | C |
| 12 | 子昂从零出发 | Codex 智能剪辑 skill 分享 | `v.douyin.com/L3IUJAM_QXc` | C |
| 13 | Vincent | 产品宣传片 Skill 正式开源 | `v.douyin.com/QU9SERbnsXI` | C |
| 14 | 墨白Neo | 三步制作 vox 风格视频 | `v.douyin.com/6Q7lI4sCD_I` | C |
| 15 | 见舟AI | Codex 自动剪辑完整实操教程 | `v.douyin.com/I_VjZu8dxJc` | C |
| 16 | 郑茜茜（xi） | 纯知识分享视频 | `v.douyin.com/G5FwNdPp2tw` | C |
| 17 | AskCc | 被面试官拷打了，程序员的命运 | `v.douyin.com/Pes1MGAcGsg` | C |
| 18 | 普通人的AI | 一个人做自媒体配上 10 个 Skill | `v.douyin.com/rTEzadqM7iE` | C |

## 已验证参考：阿柴 ChayAI（6:43）

| 时间点 | 可验证流程 | 落地到 AVS |
|---|---|---|
| 00:39 | 选题 → 文案 → 音频 → 视觉/动画 → 可编辑交付 | `workflow resume` 串联已有步骤，交付为 timeline/SRT/素材/编辑说明而非剪映草稿 |
| 01:06 | 采集竞品文案，分析成模板并沉淀标准文档 | `reference-recipe.json` + 本台账；改编模式禁止复制原文案 |
| 02:21 | 先生成音频，以声音时长确定分镜与时间线 | `timeline.json` 的音频轨为共享时间基准；素材准备优先检查配音 |
| 02:56 | 根据文案时间线和参考图设计分镜，再调用图片能力 | `write-video-script` → `create-storyboard` → `prepare-assets`；缺口必须写入 `missing-assets.md` |
| 04:02 | 用首帧图生成动画，并由 AI 选择效果 | HyperFrames 仅负责标题/信息卡/结尾卡包装；外部生成素材须由用户提供并经素材确认 |
| 04:20 | 输出可继续编辑的剪辑结果 | 交付 `MP4`、`SRT`、`timeline.json`、素材、QA、编辑说明；不逆向生成剪映草稿 |
| 05:31 | 流程仍是粗稿，需要针对内容自定义 | `workflow` 停在 Agent/人工审核关口；不自动发布 |

## 由标题可识别的待验证主题

下面是研究队列，不是对视频内容的转述：

| 主题 | 关联条目 | 当前项目决策 |
|---|---|---|
| 多 Skill 串联一条视频 | 5、9、12、15、18 | 已实现项目内 10 个 Skill 与 `workflow` 协调；核心仍可纯 CLI 运行 |
| AI 视频/视觉生成 | 8、10、11、13、14 | 保持“用户提供或经授权素材”的输入边界；不安装来源/许可证未核实的第三方 Skill |
| 多角色 Agent 协作 | 7 | 目前用明确的内容、素材、QA Skill 分工；不引入第二套 Episode 状态或无人审核审批 |
| 商业化与创业选题 | 2、3、4、6 | 属于内容选题，不进入渲染核心；所有收益、案例、数据必须由用户提供可核来源 |
| 知识表达/录屏叙事 | 16、17 | 已由录屏讲解 Fixture、字幕与信息卡链路覆盖 |

## 已落实的完整链路

```text
用户输入/本地授权参考
  -> ingest + asset-manifest
  -> 本地参考 recipe（可选）
  -> brief / script / storyboard（Agent，人工审核）
  -> assets approve（人工）
  -> timeline.json + SRT
  -> FFmpeg 粗剪 + HyperFrames 包装
  -> 确定性 QA + 人工视觉复核
  -> 可编辑 delivery/，人工发布
```

当其余 17 条链接在 Chrome 中被用户打开为 `www.douyin.com/video/<id>` 页面后，可在本台账补充 A 级时间点证据；在此之前它们不会被编造为已分析内容。
