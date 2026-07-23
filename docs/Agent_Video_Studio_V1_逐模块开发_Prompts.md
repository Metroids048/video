# Agent Video Studio V1 逐模块开发 Prompt 包

> 使用方法：  
> 1. 将《Agent Video Studio V1 项目规范（优化版）》放到仓库 `docs/Agent-Video-Studio-V1.md`。  
> 2. 将配套 `AGENTS.md` 放到仓库根目录。  
> 3. 每次只复制一个模块 Prompt 给 Codex 或 Claude Code。  
> 4. 当前模块未通过审计，不要执行下一模块。  
> 5. 推荐主 Agent 实现、另一个 Agent 只读审计。

---

# 通用前缀

将以下内容放在每个模块 Prompt 的最前面：

```text
你正在开发 Agent Video Studio V1。

开始前必须：

1. 完整阅读根目录 AGENTS.md。
2. 阅读 docs/Agent-Video-Studio-V1.md。
3. 检查 Git 状态、当前分支和最近提交。
4. 检查本模块的前置模块是否已经通过验收。
5. 只实现本 Prompt 指定的模块，不提前开发后续模块。
6. 先给出实施计划、文件清单、测试计划和风险，再修改文件。
7. 使用测试驱动方式：先写失败测试，再实现最小功能。
8. 不得创建空目录、占位函数、伪实现或仅写文档代替运行结果。
9. 不得覆盖或移动任何用户原始媒体。
10. 完成后运行本模块全部验证命令。
11. 只有测试和验收全部通过后，才可提交 Git commit。
12. 不要自动进入下一模块。

最终报告必须包含：

- 完成内容
- 新增或修改文件
- 执行命令及返回码
- 测试结果
- 实际生成产物
- 已知限制
- 未完成项
- Git commit hash
- 本模块验收清单
```

---

# Prompt 0：设计冻结与仓库审计

```text
[粘贴通用前缀]

本次只执行“模块 0：设计冻结与仓库审计”。

目标：

在不实现视频业务代码的前提下，将项目规范转化为无歧义、可实施的仓库设计，并识别当前仓库已有内容与规范之间的冲突。

必须完成：

1. 审计当前仓库：
   - 目录；
   - 已有代码；
   - package manager；
   - Python 环境；
   - Agent 配置；
   - Skills；
   - HyperFrames；
   - Git 忽略规则；
   - 已存在的媒体和输出。

2. 创建或完善：
   - docs/architecture.md
   - docs/decisions/0001-python-cli.md
   - docs/decisions/0002-timeline-contract.md
   - docs/decisions/0003-hyperframes-boundary.md
   - docs/decisions/0004-agent-skill-layout.md
   - docs/implementation-roadmap.md
   - tools-manifest.yaml
   - skills.lock.json 初始结构
   - .gitignore

3. 冻结以下决策：
   - 唯一业务 CLI 为 `python -m avs`；
   - npm 仅提供包装命令；
   - Python 负责状态、媒体、FFmpeg、QA 和交付；
   - HyperFrames 负责动效片段；
   - timeline.json 是共享中间协议；
   - Remotion、自动发布和剪映草稿不属于 V1；
   - 原始用户素材默认不进入 Git；
   - Git LFS 为可选而非强制；
   - 第三方链接不默认自动下载。

4. 给出最终目录树和每个目录职责。

5. 检查规范中是否还存在：
   - 两个 CLI；
   - 重复状态；
   - 重复配置；
   - 无法验收的要求；
   - V1 与未来功能混杂；
   - 未明确的供应商依赖。

禁止：

- 实现 Episode、FFmpeg 或 HyperFrames 业务功能；
- 安装大量可选依赖；
- 创建后续模块的伪代码。

验收：

- 所有架构决策都有明确文件；
- 不存在 TBD、TODO 或“以后再说”式模糊项；
- 目录和依赖关系无循环；
- 开发路线严格按模块 1—9；
- 规范、AGENTS.md 和 ADR 不互相冲突。

完成后提交：

`docs: freeze Agent Video Studio V1 architecture`
```

---

# Prompt 1：Bootstrap、Doctor 与跨 Agent 基础

```text
[粘贴通用前缀]

本次只执行“模块 1：Bootstrap、Doctor 与跨 Agent 基础”。

前置条件：

- 模块 0 已通过。
- 读取 architecture、ADR 和 tools-manifest。

目标：

让新环境能够安装项目、检查依赖，并让 Codex、Claude Code 和 Cursor 读取项目级规则与 Skills。

必须实现：

1. 根目录：
   - package.json
   - pyproject.toml
   - .env.example
   - AGENTS.md
   - CLAUDE.md

2. Agent 配置：
   - .claude/settings.json
   - .claude/agents/content-worker.md
   - .claude/agents/media-worker.md
   - .claude/agents/reviewer.md
   - .cursor/rules/project.mdc
   - .cursor/rules/media.mdc
   - .agents/skills/
   - .claude/skills/

3. Skills：
   - skills-src/ 作为项目自有 Skill 唯一编辑源；
   - scripts/sync_skills.py；
   - scripts/install_skills.mjs；
   - 支持 Windows 的复制模式；
   - 安装 HyperFrames 官方 Skills；
   - 生成 skills.lock.json；
   - 校验 Skill 的 SKILL.md frontmatter。

4. Bootstrap：
   - scripts/bootstrap.ps1
   - scripts/bootstrap.sh
   - 创建 Python 虚拟环境；
   - 安装 Python 和 Node 依赖；
   - 安装/同步 Skills；
   - 创建必要目录；
   - 不自动写入真实密钥。

5. Doctor：
   - Git；
   - Node.js 22+；
   - Python 3.11+；
   - FFmpeg；
   - FFprobe；
   - HyperFrames CLI；
   - Python 环境；
   - 项目目录；
   - Skills；
   - 可用磁盘空间；
   - 可选 Provider 状态。
   - 对 Git LFS 只给出 optional 状态。

6. npm 命令：
   - npm run bootstrap
   - npm run doctor
   - npm run skills:install
   - npm run skills:sync
   - npm run skills:check

7. HyperFrames 最小自检：
   - 调用官方 doctor；
   - 不创建完整视频组件；
   - 自检失败时提供明确修复提示。

测试：

- Doctor 的版本解析单元测试；
- 缺失 FFmpeg 测试；
- 旧 Node 版本测试；
- Skill 缺失测试；
- Windows 路径测试；
- bootstrap 的 dry-run 测试。

验收：

- Doctor 返回稳定退出码；
- 必需依赖缺失返回非零；
- 可选依赖缺失不阻止核心环境；
- Claude、Codex、Cursor 项目配置文件存在且可解析；
- Skills 可同步且重复执行结果一致；
- 不包含媒体业务逻辑。

完成后提交：

`build: add bootstrap doctor and agent compatibility`
```

---

# Prompt 2：Episode、状态机、Schema 与统一 CLI

```text
[粘贴通用前缀]

本次只执行“模块 2：Episode、状态机、Schema 与统一 CLI”。

前置条件：

- 模块 1 全部通过。
- npm run doctor 成功。

目标：

建立项目的数据骨架和唯一业务 CLI，但暂不处理真实媒体。

必须实现：

1. Python 包：
   - src/avs/__main__.py
   - src/avs/cli.py
   - src/avs/config.py
   - src/avs/paths.py
   - src/avs/state.py
   - src/avs/models/

2. 配置：
   - config/project.yaml
   - config/workflow.yaml
   - config/platforms.yaml
   - config/visual.yaml
   - config/audio.yaml
   - config/providers.yaml
   - config/content-pillars.yaml

3. Schema：
   - episode.schema.json
   - asset-manifest.schema.json
   - reference-recipe.schema.json
   - script.schema.json
   - storyboard.schema.json
   - timeline.schema.json
   - qa-report.schema.json
   - delivery-manifest.schema.json

4. CLI：
   - python -m avs doctor
   - python -m avs episode create EP-0001
   - python -m avs episode status EP-0001
   - python -m avs episode validate EP-0001
   - python -m avs episode fail EP-0001 --reason "..."
   - python -m avs episode reset EP-0001 --to <state> --force

5. 状态机：
   - CREATED
   - INGESTED
   - REFERENCE_READY
   - CONTENT_READY
   - ASSETS_READY
   - TIMELINE_READY
   - ROUGH_CUT_READY
   - QA_PASSED
   - DELIVERY_READY
   - WAITING_FOR_INPUT
   - WAITING_FOR_REVIEW
   - FAILED

6. 创建 Episode 时生成规范目录和 episode.json。

7. `REFERENCE_CLONE` 自动设置 publishable=false。

8. 所有时间使用带时区 ISO 8601。

测试：

- 合法和非法状态转换；
- 重复创建；
- 非法 ID；
- 路径穿越；
- 配置覆盖；
- Schema 校验；
- REFERENCE_CLONE 发布标记；
- Windows 和 POSIX 路径。

禁止：

- FFmpeg；
- 参考视频分析；
- 脚本生成；
- 视频渲染；
- HyperFrames 组件。

验收：

- CLI 退出码稳定；
- 无效输入不会留下半成品目录；
- 状态和 Schema 一致；
- `python -m avs episode create TEST-0001` 可真实运行；
- 所有测试通过。

完成后提交：

`feat: add episode domain state machine and schemas`
```

---

# Prompt 3：输入接收与素材标准化

```text
[粘贴通用前缀]

本次只执行“模块 3：输入接收与素材标准化”。

前置条件：

- 模块 2 已通过。
- 可创建 Episode。

目标：

将用户放入 input/ 的文件安全地识别、检查和标准化，生成 asset-manifest.json。

必须实现：

1. src/avs/ingest/
   - discovery.py
   - probe.py
   - hashing.py
   - normalize.py
   - manifest.py
   - errors.py

2. CLI：
   - python -m avs ingest EP-0001
   - python -m avs assets list EP-0001
   - python -m avs assets validate EP-0001

3. 识别：
   - 文本；
   - 图片；
   - 音频；
   - 视频；
   - links.txt；
   - 未知文件。

4. FFprobe：
   - 时长；
   - 尺寸；
   - fps；
   - codec；
   - 音轨；
   - 可解码性。

5. 文件保护：
   - 原始文件 Hash；
   - 工作副本；
   - 不改名、不移动原文件；
   - 相对路径；
   - 防止路径穿越。

6. Proxy：
   - 对高码率视频生成低码率代理；
   - 对横屏录屏生成布局友好代理；
   - 不静默拉伸；
   - 保留音频或明确无音频。

7. 幂等与缓存：
   - 根据输入 Hash 和配置 Hash；
   - 未变化时复用；
   - `--force` 重建。

8. 输出：
   - work/asset-manifest.json
   - work/prepared/
   - ingest 日志。

测试 Fixture：

- 文本；
- 图片；
- 有音轨竖屏视频；
- 无音轨横屏视频；
- 音频；
- 损坏视频；
- 重复文件；
- Unicode 文件名。

验收：

- 原始文件 Hash 前后完全相同；
- 损坏文件被标记且不进入下游；
- 重复执行不重复转码；
- Manifest 通过 Schema；
- Episode 状态转为 INGESTED；
- 输出均为相对路径。

完成后提交：

`feat: add safe media ingestion and asset manifest`
```

---

# Prompt 4：参考视频分析

```text
[粘贴通用前缀]

本次只执行“模块 4：参考视频分析”。

前置条件：

- 模块 3 已通过。
- Episode 中至少有一个参考视频 Fixture。

目标：

生成可供 Agent 理解的确定性参考分析材料，以及结构化 reference-recipe.json。

必须实现：

1. src/avs/reference/
   - audio.py
   - shots.py
   - keyframes.py
   - contact_sheet.py
   - transcription.py
   - recipe.py

2. CLI：
   - python -m avs reference analyze EP-0001
   - python -m avs reference validate EP-0001

3. 确定性输出：
   - 提取音频；
   - 镜头边界；
   - 每个镜头关键帧；
   - 联系表；
   - 原始时长、比例、fps；
   - 有无音轨；
   - 可选转写。

4. 转写 Provider：
   - 统一接口；
   - `auto`、`manual`、`disabled`；
   - Provider 缺失时不让流程崩溃；
   - 输出 transcript.json。

5. 创建 `skills-src/analyze-reference/SKILL.md`：
   - Agent 读取联系表、关键帧、镜头数据和 transcript；
   - 输出 reference-report.md 和 reference-recipe.json；
   - 标注事实、推测和 confidence；
   - 区分可迁移结构与不可复制内容。

6. Recipe 必须包含：
   - 镜头起止；
   - 镜头类型；
   - 文案片段；
   - 开头、主体和结尾；
   - 信息密度；
   - 可迁移节奏；
   - 缺失分析项；
   - 置信度。

禁止：

- OCR 失败时伪造字幕位置；
- 将音乐节拍和剪辑意图当作确定事实；
- 自动下载第三方平台视频。

测试：

- 有音轨视频；
- 无音轨视频；
- 单镜头视频；
- 快速切镜视频；
- 无转写 Provider；
- 中文 Unicode 路径。

验收：

- 镜头切分可重复；
- 关键帧和联系表实际存在；
- Recipe 通过 Schema；
- 无音轨和无 Provider 均可降级；
- Episode 状态转为 REFERENCE_READY；
- Skill 可被至少一个 Agent 实际调用并产生报告。

完成后提交：

`feat: add reference video analysis pipeline`
```

---

# Prompt 5：内容简报、脚本与分镜

```text
[粘贴通用前缀]

本次只执行“模块 5：内容简报、脚本与分镜”。

前置条件：

- 模块 4 已通过，或当前 Episode 明确无参考视频。
- 输入中有 idea、notes、links 或现成稿件。

目标：

使用项目 Skills 将原始内容转化为可追溯的 brief、script 和 storyboard。

必须实现：

1. 项目 Skills：
   - skills-src/write-video-script/SKILL.md
   - skills-src/create-storyboard/SKILL.md
   - 如有必要增加内部共享 references，但不要复制 AGENTS.md。

2. Agent 工作流：
   - 清点输入；
   - 提取事实和用户观点；
   - 有参考视频时使用 Recipe；
   - 无参考视频时选择 generic 或 screen-explainer 模板；
   - 输出 brief.md；
   - 输出 script.json 和 script.md；
   - 输出 storyboard.json 和 storyboard.md；
   - 输出 missing-assets.md。

3. CLI 只负责：
   - 初始化内容输出目录；
   - Schema 校验；
   - 状态推进；
   - 不在程序内硬编码大模型文案。

4. Script 要求：
   - 每段有 purpose；
   - 每段有 target_duration；
   - 每段有 visual_hint；
   - 每段引用输入来源；
   - 不虚构事实；
   - REFERENCE_ADAPT 必须替换原视频内容。

5. Storyboard 要求：
   - 每个 Scene 映射 Script Segment；
   - 标注用户素材、动效或占位；
   - 标注缺失素材；
   - 推荐的镜头类型；
   - 不直接选择不存在的素材。

6. 人工审核：
   - config 中可开启 script review；
   - 未审核时状态可进入 WAITING_FOR_REVIEW；
   - 用户确认后进入 CONTENT_READY。

测试：

- 有参考视频；
- 无参考视频；
- 只提供一句想法；
- 提供完整文章；
- 缺少真实素材；
- REFERENCE_CLONE；
- 事实来源为空的断言。

验收：

- 两个 JSON 均通过 Schema；
- 每个 Scene 可追溯到 Script；
- 不存在未声明的素材路径；
- missing-assets 完整；
- Agent 实际执行一次 Fixture；
- Episode 状态正确。

完成后提交：

`feat: add agent-driven brief script and storyboard workflow`
```

---

# Prompt 6：时间线与 FFmpeg 粗剪

```text
[粘贴通用前缀]

本次只执行“模块 6：时间线与 FFmpeg 粗剪”。

前置条件：

- 模块 5 已通过。
- 有可用 Storyboard 和至少一部分素材。

目标：

不依赖 HyperFrames，使用 timeline.json 和 FFmpeg 生成基础粗剪。

必须实现：

1. src/avs/timeline/
   - builder.py
   - models.py
   - validate.py
   - csv_export.py

2. src/avs/render/
   - ffmpeg.py
   - filters.py
   - audio.py
   - captions.py
   - layouts.py

3. CLI：
   - python -m avs timeline build EP-0001
   - python -m avs timeline validate EP-0001
   - python -m avs subtitles build EP-0001
   - python -m avs render rough EP-0001

4. Timeline 支持：
   - 视频；
   - 图片；
   - 占位卡；
   - captions；
   - voice；
   - music；
   - overlay；
   - 简单切换；
   - contain/cover；
   - 局部放大元数据。

5. 字幕：
   - SRT 必须；
   - ASS 可选；
   - 时间不得越界；
   - 默认安全区；
   - 无旁白时可根据脚本生成草稿字幕。

6. 音频：
   - 旁白优先；
   - BGM ducking；
   - 无音轨正常处理；
   - 防止明显削波。

7. 输出：
   - timeline.json
   - timeline.csv
   - captions.srt
   - preview-clean.mp4
   - preview-with-captions.mp4

8. 缺失素材：
   - 使用明确占位卡；
   - 写入 timeline 和 edit-notes 草稿；
   - 不使用无关素材。

测试：

- 图片＋录屏；
- 无音轨视频；
- 横屏；
- 空白占位；
- 字幕越界；
- 音量混合；
- FFmpeg 失败；
- 重复渲染缓存。

验收：

- 两个 MP4 可通过 FFprobe 解码；
- 1080×1920、30fps；
- 时间线通过 Schema；
- 不存在未引用文件；
- 不依赖 HyperFrames；
- Episode 状态转为 ROUGH_CUT_READY 前先经过 TIMELINE_READY；
- 实际生成一个 Demo MP4。

完成后提交：

`feat: add timeline engine and ffmpeg rough cut`
```

---

# Prompt 7：HyperFrames 动效集成

```text
[粘贴通用前缀]

本次只执行“模块 7：HyperFrames 动效集成”。

前置条件：

- 模块 6 已通过。
- FFmpeg 基础粗剪已可独立生成。
- HyperFrames 官方 Skills 已安装。

目标：

增加可复用动效，但不得让核心流程依赖 HyperFrames 成功。

必须实现：

1. 验证官方命令：
   - npx hyperframes doctor
   - npx hyperframes lint
   - npx hyperframes render

2. renderers/hyperframes/：
   - components/HookTitle
   - components/InfoCard
   - components/EndCard
   - compositions/demo
   - templates/
   - README.md

3. 动效数据输入：
   - 从 timeline.json 或独立 motion manifest 读取；
   - 不直接读取聊天上下文；
   - 不管理 Episode 状态。

4. 渲染：
   - 输出独立 MP4 或带透明通道的可合成素材，按框架能力选择稳定方式；
   - FFmpeg 合成到基础粗剪；
   - 输出 motion-graphics/。

5. 降级：
   - HyperFrames 未安装；
   - lint 失败；
   - render 失败；
   - 超时；
   - 均应回退至 FFmpeg 静态卡片并记录 warning。

6. Skill：
   - 使用官方 `/hyperframes`、`/hyperframes-cli` 和需要的动画 Skill；
   - 项目 Skill 只规定组件输入输出，不复制官方框架文档。

测试：

- 三个组件；
- 中文字体；
- 9:16；
- 无网络；
- HyperFrames 故意失败；
- 合成后视频可解码。

验收：

- 三个组件实际出现在 Demo；
- doctor、lint、render 有真实日志；
- 生成真实 MP4；
- 失败时基础粗剪仍然存在；
- HyperFrames 代码与业务状态解耦。

完成后提交：

`feat: integrate hyperframes motion graphics`
```

---

# Prompt 8：QA、交付包与平台文案

```text
[粘贴通用前缀]

本次只执行“模块 8：QA、交付包与平台文案”。

前置条件：

- 模块 7 已通过，或已验证 HyperFrames 降级。
- 有完整粗剪。

目标：

对粗剪执行确定性和 Agent 视觉 QA，并生成用户可继续编辑的交付包。

必须实现：

1. src/avs/qa/
   - decode.py
   - metadata.py
   - black_frames.py
   - silence.py
   - audio_levels.py
   - timeline_checks.py
   - subtitle_checks.py
   - contact_sheet.py
   - report.py

2. src/avs/delivery/
   - manifest.py
   - package.py
   - paths.py

3. CLI：
   - python -m avs qa EP-0001
   - python -m avs deliver EP-0001

4. 确定性 QA：
   - 可解码；
   - 尺寸；
   - fps；
   - 时长；
   - 黑帧；
   - 长静音；
   - 音频峰值和削波；
   - 缺失素材；
   - 时间线冲突；
   - 字幕越界；
   - 空文件；
   - 未完成占位。

5. 视觉 QA：
   - 从成片抽取联系表；
   - 创建 skills-src/quality-review/SKILL.md；
   - 输出可读性、画面匹配、节奏和人工修改建议；
   - 不将主观判断伪装成确定性错误。

6. 交付：
   - preview-with-captions.mp4
   - preview-clean.mp4
   - captions.srt
   - timeline.json
   - timeline.csv
   - narration.wav（如存在）
   - assets-used/
   - motion-graphics/
   - edit-notes.md
   - qa-report.md
   - delivery-manifest.json

7. 平台文案：
   - skills-src/create-publish-pack/SKILL.md；
   - publish/douyin.md；
   - publish/xiaohongshu.md；
   - 不自动发布；
   - REFERENCE_CLONE 不生成可发布标记。

8. 所有交付路径必须相对化。

测试：

- 故意黑帧；
- 故意长静音；
- 字幕越界；
- 缺失素材；
- 低分辨率；
- 削波；
- 绝对路径；
- publishable=false。

验收：

- 故意错误均被发现；
- QA 区分 error、warning、suggestion；
- 失败时不进入 QA_PASSED；
- Delivery Manifest 可校验；
- 用户可按 edit-notes 找到每个需修改位置；
- 不触发发布动作。

完成后提交：

`feat: add deterministic qa and editable delivery package`
```

---

# Prompt 9：双 Demo、端到端测试与最终硬化

```text
[粘贴通用前缀]

本次只执行“模块 9：双 Demo、端到端测试与最终硬化”。

前置条件：

- 模块 1—8 均已独立通过。

目标：

证明整个系统在真实最小输入上可重复运行，而不是只有单元模块。

必须完成：

1. 两个 Fixture：
   - fixtures/reference-adapt-demo/
   - fixtures/screen-explainer-demo/

2. 每个 Fixture 包含：
   - idea.md；
   - 图片；
   - 短录屏；
   - 参考视频或模板配置；
   - 可选音频；
   - 预期元数据。

3. 一键命令：
   - npm run demo
   - npm run demo:reference
   - npm run demo:screen
   - npm run verify

4. E2E：
   - 创建 Episode；
   - ingest；
   - reference；
   - content；
   - assets；
   - timeline；
   - render；
   - HyperFrames；
   - QA；
   - delivery。

5. 恢复测试：
   - 在 reference 后中断；
   - 在 render 中断；
   - 恢复后不重复处理已完成阶段。

6. 降级测试：
   - 无转写 Provider；
   - HyperFrames 失败；
   - 无音轨；
   - 缺失素材。

7. 兼容性：
   - 记录 Windows、Node、Python、FFmpeg、HyperFrames 版本；
   - 验证至少一个主 Agent；
   - 检查另外两个 Agent 的项目配置和 Skill 路径；
   - 不虚构实际未运行的 Agent 测试。

8. 文档：
   - README.md；
   - docs/getting-started.md；
   - docs/input-guide.md；
   - docs/editing-guide.md；
   - docs/troubleshooting.md；
   - docs/compatibility.md。

9. 最终报告：
   - 两个交付包路径；
   - FFprobe 摘要；
   - 测试摘要；
   - 失败恢复证据；
   - 降级证据；
   - 已知限制；
   - P1 建议。

验收：

- 两个 Demo 都生成可播放 MP4；
- 交付包完整；
- 无绝对路径；
- 重复执行幂等；
- 中断可恢复；
- 基础粗剪不依赖 HyperFrames；
- `npm run verify` 返回 0；
- 没有 TODO、TBD、空实现和跳过测试。

完成后提交：

`test: add end to end demos and harden v1 pipeline`
```

---

# 每模块审计 Prompt

由另一个 Agent 在模块完成后执行。审计 Agent 默认只读，除非用户明确要求修复。

```text
请以独立审计者身份审查当前模块。

规则：

1. 阅读 AGENTS.md、项目规范、当前模块 Prompt 和 Git diff。
2. 不相信实现 Agent 的完成声明。
3. 重新运行本模块测试和验收命令。
4. 检查是否提前实现后续模块。
5. 检查是否存在空函数、伪实现、硬编码通过、跳过测试、绝对路径、静默失败或未捕获退出码。
6. 检查 Schema、状态、接口与前置模块是否一致。
7. 检查原始媒体是否被修改。
8. 检查 README 或报告中的成功声明是否有真实证据。
9. 不修改文件，先输出审计报告。

报告格式：

# 审计结论
PASS / PASS WITH CONDITIONS / FAIL

# 阻断问题
按严重度排序，包含文件和行号。

# 非阻断问题

# 重新执行的命令
包含返回码和关键输出。

# 验收清单
逐项标记。

# 范围检查
是否存在超范围实现。

# 建议
只有审计结论为 PASS 才允许进入下一模块。
```

---

# 最终全项目审计 Prompt

```text
请以从未参与开发的高级工程审计者身份，对 Agent Video Studio V1 做最终只读审计。

必须：

1. 从干净环境或尽可能接近干净环境开始。
2. 阅读 AGENTS.md、项目规范、ADR 和所有模块 Prompt。
3. 运行：
   - npm run bootstrap
   - npm run doctor
   - npm run skills:check
   - npm run demo:reference
   - npm run demo:screen
   - npm run verify
4. 检查两个 Demo 的：
   - 可播放性；
   - FFprobe；
   - 字幕；
   - 时间线；
   - QA；
   - Delivery Manifest；
   - 相对路径；
   - edit-notes。
5. 故意制造并验证：
   - 损坏视频；
   - 无音轨；
   - 缺失素材；
   - 字幕越界；
   - HyperFrames 失败；
   - 中途退出。
6. 检查：
   - Codex 插件是否被错误设为硬依赖；
   - Skills 是否有单一来源；
   - Claude/Cursor/Codex 配置是否自洽；
   - 是否存在第二套 CLI；
   - 是否包含 V1 之外的大量未测试功能；
   - 是否修改原始素材；
   - 是否有密钥或 Cookie。
7. 不接受“理论上可以”或“代码看起来正确”。

最终输出：

- 总结
- PASS / FAIL
- 阻断问题
- 复现步骤
- 所有命令和返回码
- 两个 Demo 路径和媒体元数据
- V1 验收清单
- 安全与隐私检查
- 依赖与版本检查
- 可维护性检查
- 建议的 P1 工作

只有实际生成两个可播放 MP4 且 npm run verify 返回 0 时，才能给出 PASS。
```

---

# 日常创建一期视频 Prompt

项目完成后，每次可以使用：

```text
请使用 Agent Video Studio 为我创建一期新视频。

任务 ID：
EP-XXXX

输入目录：
episodes/inbox/EP-XXXX/input/

模式：
REFERENCE_ADAPT

目标平台：
抖音、小红书

要求：

1. 阅读 AGENTS.md 和项目配置。
2. 创建 Episode 并清点输入。
3. 不移动或覆盖原始素材。
4. 有参考视频时生成参考分析和 Recipe。
5. 根据我的输入生成 brief、script 和 storyboard。
6. 明确列出缺失素材。
7. 生成 timeline、字幕、clean 粗稿和带字幕粗稿。
8. 必要时使用 HyperFrames 制作标题、信息卡和结尾卡。
9. 运行 QA。
10. 生成完整可编辑交付包和平台文案。
11. 不自动发布。
12. 如遇缺失输入，能使用占位卡则继续；无法继续则进入 WAITING_FOR_INPUT 并准确说明原因。
13. 完成时给出：
    - 当前状态；
    - 产物路径；
    - QA 结果；
    - 人工修改清单；
    - 尚未解决的问题。
```
