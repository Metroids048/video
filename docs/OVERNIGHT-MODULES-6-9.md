# Agent Video Studio V1 — 通宵编排 Prompt（模块 6→9）

> **用法**：整份复制到 Claude Code / Cursor Agent（**禁止 @ 附件 md**）。  
> **目标**：从模块 6 做到模块 9，每模块完整落地 → 自动验收 → 通过后自动下一模块。  
> **硬约束**：不得偷工减料；不得在 Bash/安全分类器上死循环烧钱。

---

## 一键粘贴正文（从下一行 `<<<BEGIN` 到 `END>>>`）

```text
<<<BEGIN
你正在通宵执行 Agent Video Studio V1「模块 6 → 7 → 8 → 9」连续交付。
工作目录：c:\Users\Windows11\Desktop\video

══════════════════════════════════════════════════════════════════
0. 最高优先级：反卡死 / 反烧钱（违反即任务失败）
══════════════════════════════════════════════════════════════════

A. 禁止 @ / 拖拽 / document 附件。规范用 Read 读磁盘路径。

B. Shell 安全分类器不可用（含原文）：
   "temporarily unavailable" / "cannot determine the safety of Bash|PowerShell"
   → 同一命令最多再试 **1** 次；第 2 次起 **永久跳过该 shell 动作**。
   → 立刻切换：Write/Edit 写代码；把验收命令追加到
     `logs/overnight-verify-queue.ps1`（UTF-8），继续下一代码任务。
   → **禁止** 等待、空转、重复试 Bash/PowerShell/pip/doctor。

C. 同一错误原文（或同一命令+同一退出码）累计处理 **≤2 次**：
   第 1 次修根因；第 2 次换更小实现/降级；第 3 次起写入
   `logs/overnight-bypass.md` 并继续（降级须仍满足本模块「可演示产物」，
   不得用空函数假装通过）。

D. 每个模块的「完整验收命令套件」最多跑 **2 轮**。第 2 轮仍红：
   - 若可用降级保住核心产物 → 标 PASS_WITH_DEGRADATION，写绕过，进下一模块；
   - 若核心产物不存在 → 标 MODULE_FAILED，写清阻塞，**停止通宵链**（宁停勿烧）。

E. 禁止环境修复循环：
   - 禁止反复 pip install / npm install / bootstrap / doctor 验收。
   - 固定解释器策略（成功即锁死整晚）：
     1) 若存在 `.\.venv\Scripts\python.exe` → 用之
     2) 否则 `py -3.11` 或 `python`
     3) `$env:PYTHONPATH = "c:\Users\Windows11\Desktop\video\src"`
     4) 验证：`& $py -c "import avs; print('OK', avs.__file__)"`
     5) import 成功后 **整晚禁止 pip install -e .**
   - 禁止使用 `C:\Users\Windows11\.agent-reach-venv\...`

F. Token/费用控制：
   - 每个模块开始：只 Read 本模块相关文件 + Prompt 对应节，禁止每次重读全部规范。
   - 禁止重复粘贴大段规范到回复。
   - 禁止为「再确认一次」无改动重跑全仓测试超过 2 轮。
   - 单模块墙钟超过约 90 分钟仍无新产物文件 → 强制走降级或 MODULE_FAILED 并停止。

G. 进度落盘（崩溃可续跑）：
   维护 `logs/overnight-progress.json`：
   {
     "current_module": 6,
     "modules": {
       "6": {"status": "pending|in_progress|passed|passed_with_degradation|failed", "commit": null, "notes": ""},
       "7": {...}, "8": {...}, "9": {...}
     },
     "python": "<锁定路径>",
     "updated_at": "<ISO8601>"
   }
   每完成一个切片或验收，立刻更新该文件。
   若文件显示某模块已 passed → 跳过，从下一个 pending 开始。

H. Git：每模块验收通过后 **自动 commit 一次**（用户已授权通宵任务）。
   若 hook 失败：修一次；再失败则记录，不阻断进入下一模块代码（但报告里标明未提交）。

══════════════════════════════════════════════════════════════════
1. 开工前（只做一次，≤10 分钟）
══════════════════════════════════════════════════════════════════

1. Read：AGENTS.md（快速）、docs/architecture.md §相关、docs/decisions/0002+0003。
2. Read：docs/Agent_Video_Studio_V1_逐模块开发_Prompts.md 中 Prompt 6/7/8/9 全文（本文件已内嵌任务，仍以仓库 Prompt 为准核对，不得删减交付项）。
3. 探测前置：确认已有 episode/ingest/reference/content 相关代码可导入。
   若模块 5 产物缺失：用 fixtures 生成 **最小可用** brief/script/storyboard/asset-manifest
   （真实 JSON 符合 schema），不要重做模块 2–5 的完整工程。
4. 锁定 python + PYTHONPATH；写进 overnight-progress.json。
5. 创建日志目录 logs/（若不存在）。
6. 输出 15 行内通宵计划后 **立即开始模块 6**（不要等用户确认）。

══════════════════════════════════════════════════════════════════
2. 模块间自动状态机（必须遵守）
══════════════════════════════════════════════════════════════════

对 M in [6,7,8,9]:
  1) status=in_progress；写实施计划（短）
  2) TDD：先写本模块失败测试，再实现
  3) 按本模块「必须实现」清单逐项落地（禁止合并偷懒删文件）
  4) 跑本模块最小验收集（见各模块）——最多 2 轮
  5) 写模块完成报告 → 追加到 logs/overnight-module-reports.md
  6) git add 相关文件；commit（message 用各模块指定）
  7) status=passed 或 passed_with_degradation → 自动开始 M+1
  8) status=failed → 停止整链，写 logs/overnight-STOP.md

模块内禁止提前写下一模块业务；但可为下一模块预留空目录 **仅当本模块验收需要**。

自我审计（每个模块验收后、commit 前，用 1 次短检查代替第二 Agent）：
  - 对照本模块「必须实现」文件是否都存在且非空壳
  - 对照「验收」项是否有命令证据（退出码）
  - 若 shell 被拦：以「代码存在 + verify-queue 中有可复现命令」为临时证据，
    并在报告标 SHELL_BLOCKED；核心产物（如 mp4）若无法生成则不能标 passed

══════════════════════════════════════════════════════════════════
3. 模块 6 — 时间线与 FFmpeg 粗剪（完整，不偷工）
══════════════════════════════════════════════════════════════════

【目标】不依赖 HyperFrames，用 timeline.json + FFmpeg 生成基础粗剪。

【必须实现的文件】
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
3. CLI（扩展现有 cli.py，禁止第二套 CLI）：
   - python -m avs timeline build <ID>
   - python -m avs timeline validate <ID>
   - python -m avs subtitles build <ID>
   - python -m avs render rough <ID>
4. skills-src/create-rough-cut/SKILL.md（完整：触发/输入/禁止改/输出/命令/验证/停止条件/缺输入行为/完成报告）

【Timeline 能力必须支持】
视频、图片、占位卡、captions、voice、music、overlay、简单切换、contain/cover、局部放大元数据。

【字幕】
SRT 必须；ASS 可选；时间不越界；默认安全区；无旁白时可由脚本生成草稿字幕。

【音频】
旁白优先；BGM ducking；无音轨正常；防明显削波。

【输出产物】
- work/timeline.json（或规范约定路径，与 schema 一致）
- work/timeline.csv
- delivery 或 work 下 captions.srt（与项目路径约定一致，贯穿后续模块）
- renders/preview-clean.mp4
- renders/preview-with-captions.mp4

【缺失素材】
明确占位卡；写入 timeline + edit-notes 草稿；禁止无关素材硬凑。

【画布】1080×1920、30fps、H.264、AAC。所有外部命令检查退出码。

【测试必须覆盖】
图片+录屏；无音轨；横屏 contain/cover；空白占位；字幕越界检测；音量混合；FFmpeg 失败路径；重复渲染缓存/幂等。

【Demo Episode】
若无现成 CONTENT_READY episode：创建 EP-M6-DEMO，放入最小 fixture（图+短视频+script/storyboard JSON），跑通 build→subtitles→render。

【模块 6 最小验收集】（全过才可 passed）
1. pytest 本模块相关测试通过
2. timeline build + validate 退出码 0；timeline.json 通过 schemas/timeline.schema.json
3. subtitles build 产出 SRT；无越界
4. render rough 产出两个 MP4；ffprobe 可解码；宽高 1080x1920；fps≈30
5. 状态：先 TIMELINE_READY 再 ROUGH_CUT_READY
6. 不依赖 HyperFrames 即可出片
7. 重复 render 不重复无意义重算（或 --force 才重建）

【降级允许】
- ASS 可跳过；
- BGM 缺失则跳过 ducking 但记录 warning；
- 不得降级到「无 MP4」。

【commit】`feat: add timeline engine and ffmpeg rough cut`

══════════════════════════════════════════════════════════════════
4. 模块 7 — HyperFrames 动效集成（完整，不偷工）
══════════════════════════════════════════════════════════════════

【前置】模块 6 passed（或有可播放 preview-clean.mp4）。

【目标】可复用动效；核心流程不得依赖 HyperFrames 成功。

【必须实现】
1. 尝试官方：
   - npx hyperframes doctor
   - npx hyperframes lint
   - npx hyperframes render
   （若 npx/网络/分类器失败：记入 bypass，走 FFmpeg 静态卡片降级，但仍必须创建组件目录与合成管道代码）
2. renderers/hyperframes/
   - components/HookTitle/（完整可渲染源）
   - components/InfoCard/
   - components/EndCard/
   - compositions/demo/
   - templates/
   - README.md
3. 动效输入：只从 timeline.json 或独立 motion manifest 读；不读聊天上下文；不管理 Episode 状态
4. 渲染：输出独立 MP4 或可合成素材 → FFmpeg 合成到粗剪 → delivery/motion-graphics/ 或规范路径
5. 降级必须实现并测试：未安装 / lint 失败 / render 失败 / 超时 → FFmpeg 静态卡片 + warning，且 preview-clean.mp4 仍在
6. 项目侧 Skill 只规定 I/O，不复制官方文档；可引用官方 skill 名

【测试】三组件；中文字体；9:16；无网络或故意失败；合成后可解码。

【模块 7 最小验收集】
1. 三组件文件真实存在且非占位
2. doctor/lint/render 有日志文件落盘到 logs/hyperframes-*.log
   （命令被拦则：至少有一次成功本地降级渲染日志 + 静态卡片合成证据）
3. Demo 成片可解码；失败注入时基础粗剪仍存在
4. 业务状态机不被 HyperFrames 代码直接改写（经 CLI/avs 层）

【commit】`feat: integrate hyperframes motion graphics`

══════════════════════════════════════════════════════════════════
5. 模块 8 — QA、交付包与平台文案（完整，不偷工）
══════════════════════════════════════════════════════════════════

【前置】有完整粗剪；HyperFrames 成功或已验证降级。

【必须实现文件】
1. src/avs/qa/
   decode.py, metadata.py, black_frames.py, silence.py, audio_levels.py,
   timeline_checks.py, subtitle_checks.py, contact_sheet.py, report.py
2. src/avs/delivery/
   manifest.py, package.py, paths.py
3. CLI：
   - python -m avs qa <ID>
   - python -m avs deliver <ID>
4. skills-src/quality-review/SKILL.md（完整）
5. skills-src/create-publish-pack/SKILL.md（完整）

【确定性 QA 必须检测】
可解码、尺寸、fps、时长、黑帧、长静音、峰值/削波、缺失素材、时间线冲突、
字幕越界、空文件、未完成占位。

【视觉 QA】
从成片抽联系表；Skill 输出可读性/匹配/节奏/人工修改建议；
主观项只能是 warning/suggestion，不得伪装成确定性 error。

【交付包必须包含】
preview-with-captions.mp4, preview-clean.mp4, captions.srt,
timeline.json, timeline.csv, narration.wav(如有),
assets-used/, motion-graphics/, edit-notes.md, qa-report.md,
delivery-manifest.json,
publish/douyin.md, publish/xiaohongshu.md
路径全部相对化。不自动发布。REFERENCE_CLONE → 不可发布标记。

【测试必须】
故意黑帧、长静音、字幕越界、缺失素材、低分辨率、削波、绝对路径、publishable=false。

【模块 8 最小验收集】
1. 故意错误 fixture 均被检出
2. QA 分级 error/warning/suggestion；有 error 时不进入 QA_PASSED
3. deliver 后 manifest 通过 schema；无绝对路径
4. edit-notes 可定位修改点
5. 不触发任何发布 API/登录

【commit】`feat: add deterministic qa and editable delivery package`

══════════════════════════════════════════════════════════════════
6. 模块 9 — 双 Demo、E2E、硬化（完整，不偷工）
══════════════════════════════════════════════════════════════════

【前置】模块 6–8 均 passed 或 passed_with_degradation（降级项在报告列出）。

【必须完成】
1. fixtures/reference-adapt-demo/（idea.md、图片、短录屏、参考或模板配置、可选音频、预期元数据）
2. fixtures/screen-explainer-demo/（同上结构）
3. package.json scripts：
   - npm run demo
   - npm run demo:reference
   - npm run demo:screen
   - npm run verify
   （实现须调用同一 python -m avs 链，禁止第二套业务逻辑）
4. E2E 全链路：create→ingest→reference→content→assets→timeline→render→hyperframes→qa→deliver
5. 恢复测试：reference 后中断、render 中断；恢复不重复已完成阶段
6. 降级测试：无转写、HyperFrames 失败、无音轨、缺失素材
7. docs：README.md, getting-started.md, input-guide.md, editing-guide.md,
   troubleshooting.md, compatibility.md（写真实版本与真实命令，禁止假绿）
8. 最终报告：logs/v1-final-report.md
   （两交付包路径、ffprobe 摘要、测试摘要、恢复证据、降级证据、限制、P1 建议）

【模块 9 最小验收集】
1. 两 Demo 均可播放 MP4
2. 交付包完整、相对路径
3. 重复执行幂等
4. 中断可恢复
5. 无 HyperFrames 时仍有基础粗剪
6. npm run verify 退出码 0（若 npm 被拦：等价 python 脚本 verify 退出码 0，并写 queue）
7. 无 TODO/TBD/空实现/无故 skip 测试

【commit】`test: add end to end demos and harden v1 pipeline`

══════════════════════════════════════════════════════════════════
7. 通宵结束条件
══════════════════════════════════════════════════════════════════

成功：模块 9 status=passed（或 degradation 仅限已文档化非核心项）且
      logs/v1-final-report.md 存在。

停止（节省费用）：
- 连续 3 次 shell 分类器全拦且无法用 Write 推进超过 30 分钟；
- 模块核心产物（M6 的 MP4 / M8 的 deliver / M9 的双 demo）无法生成且已 2 次降级失败；
- 出现密钥写入仓库风险。

结束时必须输出：
1. overnight-progress.json 最终状态
2. 各模块 commit hash
3. bypass 清单
4. verify-queue.ps1（若有未跑命令，给用户早上一键跑）
5. 一句话：能否宣布 V1 粗剪链路可用

现在执行：更新 overnight-progress.json → 锁定 python → 开始模块 6。
END>>>
```

---

## 早上一键补跑验收（若夜里 shell 被拦）

若生成了 `logs/overnight-verify-queue.ps1`，早上在项目根执行：

```powershell
cd c:\Users\Windows11\Desktop\video
$env:PYTHONPATH = "c:\Users\Windows11\Desktop\video\src"
powershell -NoProfile -ExecutionPolicy Bypass -File .\logs\overnight-verify-queue.ps1
```

---

## 使用注意

1. **不要 @ 本文件**；在 Claude Code 里粘贴 `<<<BEGIN`…`END>>>` 之间正文即可。  
2. 通宵前先手动确认一次：`PYTHONPATH=src` 下 `python -c "import avs"` 为 OK。  
3. 若官方 Claude 安全分类器大面积挂掉，Agent 应只写代码 + queue，把重命令留给早上 queue——这比空转烧钱正确。  
4. 模块 2–5 已有代码时不要重做；只补模块 6 所需的最小 content/storyboard fixture。
