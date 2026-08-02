# Claude Code 最后一次视频质量收口重构 Prompt

你现在是本项目的资深软件架构师、视频工程负责人、测试负责人和最终交付 Reviewer。

请在当前 Git 仓库中完成一次**允许修改代码的最终收口重构**。这不是继续寻找更多问题，也不是重新设计整个系统。你的唯一目标是：修复已经被证据确认的全部问题，使 Agent Video Studio 能够稳定产出“结构和视听已经成立、只需要最后 10%～30% 人工精修”的竖屏短视频粗稿，并确保明显不可看的视频不能再被标记为完成或可交付。

本轮属于最终收口任务。完成已确认问题并通过验收后必须停止，不得继续增加模板、功能、框架或无关优化。

---

## 一、开始前必须读取

按顺序完整读取：

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/Agent-Video-Studio-V1.md`
4. `docs/reference-research/douyin-codex-short-video-study.md`
5. `skills.lock.json`
6. `config/*.yaml`
7. `schemas/*.json`
8. `src/avs/qa/`
9. `src/avs/timeline/`
10. `src/avs/render/`
11. `src/avs/hyperframes/`
12. `src/avs/content/`
13. `src/avs/reference/`
14. `src/avs/delivery/`
15. `scripts/run_e2e_demo.py`
16. `scripts/run_acceptance.py`
17. `scripts/install_skills.mjs`
18. `scripts/sync_skills.py`
19. 与上述模块相关的全部测试。

开始前执行并记录：

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -8 --oneline
python -m avs doctor
python -m pytest -q
```

规则：

- 不得 reset、checkout、clean、stash、覆盖或删除用户现有改动。
- 如果工作区已有改动，先记录并避开，不得擅自清理。
- 当前 HEAD 是实际执行基线；若与历史审计 Commit `e75447b8ea021f548da58e3f40294a41898fcaee` 不同，只记录差异，不得回退。
- 先复现问题，再修改代码。
- 不得声称某条测试通过，除非本轮实际执行并得到 exit code 0。
- 不要只输出计划后停止。完成基线检查后直接按本 Prompt 逐项实施，除非遇到真实不可解除的权限、网络或依赖阻塞。

---

## 二、本轮冻结的问题基线

只处理以下 5 个确认问题：

### P1-01：QA 和状态机存在严重假阳性

当前系统允许全程静音、存在占位卡、字幕超限、画面构图不可用、未经人工视觉复核的视频进入：

- `QA_PASSED`
- `DELIVERY_READY`
- `publishable: true`

### P1-02：参考链接和 Skills 没有进入机器可验证的数据链

仓库已有 18 条抖音参考研究，但主要停留在 Markdown。脚本、分镜和 QA 无法证明具体学习了哪些结构、节奏、字幕、声音和镜头规则。

### P1-03：默认 timeline/render 策略天然产出测试视频感

已确认问题包括：

- 横屏录屏默认 `contain + black pad`；
- 完整长句直接成为整段字幕；
- 字幕缺少语义分句、行数、每屏字数和阅读速度控制；
- 音频依赖文件名前缀识别；
- 少量长 Scene 承载整段内容；
- 缺素材占位卡仍可进入可发布链路；
- 没有明确的前三秒 Hook、画面变化频率和录屏焦点区域约束。

### P1-04：HyperFrames 依赖和中文字体降级不闭环

HyperFrames 不可用时等待时间过长；静态 fallback 只可靠识别 Windows 微软雅黑路径，其他环境可能出现中文方框，但仍可能被当成成功。

### P2-01：完整 `python -m pytest -q` 存在卡住现象

拆分测试可通过，但 canonical 全量测试不能稳定结束，导致最终验收不可信。

本轮禁止新增其他待办。新发现的问题只有在以下条件之一成立时才允许进入本轮：

1. 直接阻塞上述 5 个问题的修复；
2. 本轮修改直接引入的回归；
3. 有可复现证据且会造成数据、状态、交付或安全错误。

其他内容全部进入观察清单，不得继续修改。

---

## 三、固定架构决策

不要再讨论或比较替代架构，直接按以下方案实施。

### 决策 1：不新增第二套状态机

继续使用现有状态：

- `ROUGH_CUT_READY`
- `WAITING_FOR_REVIEW`
- `QA_PASSED`
- `DELIVERY_READY`

规则：

- 技术检查或发布质量规则未通过：QA 返回非零，不进入 `QA_PASSED`。
- 技术检查已通过，但缺少人工视觉批准：状态进入或保持 `WAITING_FOR_REVIEW`，不得 delivery。
- 人工批准与当前最终视频哈希一致，并且全部发布质量规则通过：才进入 `QA_PASSED`。
- `avs run` 遇到人工视觉 Gate 必须停止，不得自动批准或继续 delivery。

### 决策 2：技术 QA、发布质量 Gate、人工视觉批准三层分离

`qa-report.json` 必须同时表达：

```json
{
  "technical_passed": true,
  "publishability_passed": false,
  "human_approved": false,
  "passed": false,
  "blocking_reasons": [],
  "input_fingerprint": "sha256..."
}
```

定义：

- `technical_passed`：编码、解码、尺寸、帧率、时长、Schema、黑帧等确定性检查。
- `publishability_passed`：声音、占位、字幕、横屏布局、节奏和动效降级等最低可看性检查。
- `human_approved`：人工完整播放并批准当前视频，且批准文件中的视频 SHA-256 与当前最终视频完全一致。
- `passed`：
  - `publishable=true` 时，三者全部为 true；
  - `publishable=false` 时，至少要求 technical 通过，不生成公开发布包。

已有 QA 报告不得被无条件复用。必须基于以下输入计算 `input_fingerprint`：

- 当前最终视频 SHA-256；
- `timeline.json` SHA-256；
- `captions.srt` 或实际烧录字幕文件 SHA-256；
- `creative-profile.json` SHA-256；
- `visual-approval.json` SHA-256（不存在时使用明确空值）；
- `config/quality.yaml` SHA-256；
- Episode 的 `publishable` 值。

只有 fingerprint 完全一致时才能复用旧报告，否则自动重跑，无需用户记得传 `--force`。

### 决策 3：人工批准必须与视频内容寻址绑定

新增：

- `schemas/visual-approval.schema.json`
- `src/avs/qa/approval.py`
- CLI：`python -m avs review approve <ID> --reviewer <NAME> --confirm-current-render`
- 产物：`episodes/active/<ID>/delivery/visual-approval.json`

批准文件至少包含：

```json
{
  "episode_id": "EP-XXX",
  "approved": true,
  "reviewer": "human name",
  "video_path": "renders/preview-with-motion.mp4",
  "video_sha256": "...",
  "reviewed_at": "带时区 ISO 8601",
  "checklist": {
    "hook_clear_within_3s": true,
    "captions_readable": true,
    "composition_acceptable": true,
    "audio_acceptable": true,
    "no_placeholders": true,
    "facts_and_rights_checked": true
  },
  "notes": "..."
}
```

要求：

- 命令必须计算当前最终视频哈希，不接受用户手填哈希。
- 任一 checklist 为 false 时不得 approved。
- 最终视频重新渲染后，旧批准自动失效。
- `run_delivery()` 必须再次验证视频哈希与批准文件，不能只相信 `qa-report.passed`。
- Claude Code 不得为真实 Episode 自动执行人工批准；自动测试可以使用明确标记为 `acceptance-fixture` 的测试批准。

### 决策 4：增加机器可读的参考知识库和 Episode 级创意约束

已有 18 条参考链接和学习结论必须从纯 Markdown 转为项目内可验证数据，但不得自动下载、复制或存储第三方视频。

新增：

```text
knowledge/references/catalog.yaml
knowledge/references/patterns.yaml
schemas/reference-library.schema.json
src/avs/reference/library.py
scripts/validate_reference_library.py
schemas/creative-profile.schema.json
src/avs/content/creative_profile.py
skills-src/build-creative-profile/SKILL.md
```

`catalog.yaml` 必须完整保存 `docs/reference-research/douyin-codex-short-video-study.md` 中的 18 条记录，至少包含：

- `source_id`
- 作者/类型
- 原始长链接
- 页面可验证要点
- 可迁移内容
- 禁止复制内容
- 证据等级
- 是否具有本地授权视频
- 研究日期

`patterns.yaml` 只保存抽象、可复用规则，不复制原文案、观点、封面和素材。至少沉淀现有研究中的这些模式：

- 先音频、后时间线；
- 前三秒明确收益或冲突；
- 内容必须落到用户问题和业务结果；
- 对标内容蒸馏为结构规则，而不是照抄；
- 多角色协作但共享单一 Episode 状态；
- 镜头卡、节奏和声音设计；
- 风格板 → 分镜 → 素材/动画；
- 章节化制作与 QA；
- 短冲突、快速反转、明确结尾；
- 安装检查、脚本、分镜、录屏、字幕、归档、复盘的完整 Skill 链。

每个 pattern 至少包含：

- `pattern_id`
- `category`
- `rule`
- `when_to_use`
- `when_not_to_use`
- `source_ids`
- `confidence`
- `machine_constraints`

新增 Episode 产物：

```text
episodes/active/<ID>/work/content/creative-profile.json
```

其 Schema 至少要求：

- 目标观众；
- 观众痛点；
- 本条内容承诺的具体收益；
- 内容形式；
- 前三秒 Hook；
- 节奏规则；
- 镜头变化规则；
- 字幕规则；
- 声音规则；
- 横屏录屏重构规则；
- 选中的 `source_id` 和 `pattern_id`；
- 明确禁止复制的内容；
- `draft/reviewed/approved` 状态。

`content init` 必须生成 creative profile 模板；工作流在进入脚本生成前必须要求该文件存在。

更新：

- `schemas/script.schema.json`
- `schemas/storyboard.schema.json`
- `src/avs/content/schema.py`
- `src/avs/content/models.py`
- `skills-src/write-video-script/SKILL.md`
- `skills-src/create-storyboard/SKILL.md`
- `skills-src/analyze-reference/SKILL.md`
- `skills-src/orchestrate-video-production/SKILL.md`

具体要求：

- Script 顶层必须引用 `creative-profile.json`；
- 每个 Script segment 必须有 `constraint_refs`，指向 profile/pattern；
- Storyboard 顶层必须引用 `creative-profile.json`；
- 每个 shot 必须有 `constraint_refs`、`layout`、`visual_change`；
- `screen_recording` shot 必须有明确 `screen_focus` 或 `screen_stack` 策略，不能静默退回 `contain`；
- 对横屏录屏使用 `screen_focus` 时必须有归一化 `focus_region`：`x/y/width/height` 均在 0～1；
- `validate_content_bundle()` 必须校验所有 pattern、segment、shot 和素材引用真实存在。

### 决策 5：最低可看性规则配置化

新增 `config/quality.yaml`，并将其加入 `Config._REQUIRED_FILES`。

默认规则如下，除非现有项目证据证明需要更严格，不得随意放宽：

```yaml
quality:
  publishable:
    require_non_silent_audio: true
    audio_peak_min_dbfs: -45.0
    max_total_silence_ratio: 0.40
    max_leading_silence_seconds: 1.0
    allow_placeholders: false
    require_human_visual_approval: true

  hook:
    must_be_clear_within_seconds: 3.0
    first_visual_change_within_seconds: 2.5

  pacing:
    max_static_clip_seconds: 5.0
    screen_recording_max_static_seconds: 4.0
    min_visual_changes_per_10_seconds: 2

  captions:
    max_lines: 2
    max_chars_per_line_cjk: 14
    max_chars_per_cue_cjk: 24
    min_cue_seconds: 0.8
    max_cue_seconds: 3.5
    max_cjk_chars_per_second: 12.0
    bottom_margin_px: 260

  composition:
    landscape_publishable_layouts:
      - screen_focus
      - screen_stack
      - cover
    reject_landscape_contain: true
    min_median_active_frame_ratio: 0.55
    min_sample_active_frame_ratio: 0.40

  motion:
    preflight_timeout_seconds: 15
    render_timeout_seconds: 120
    allow_readable_static_fallback: true
    require_cjk_font: true
```

不得把这些规则散落硬编码到多个模块。核心检查从 `config/quality.yaml` 读取。

---

## 四、具体代码任务

必须按以下顺序实施。每个任务都遵循：失败测试 → 最小实现 → 针对性测试 → 必要回归 → 小提交。

### Task 1：固定失败样例并重构 QA/人工批准 Gate

修改：

- `schemas/qa-report.schema.json`
- `src/avs/qa/report.py`
- `src/avs/qa/timeline_checks.py`
- `src/avs/qa/subtitle_checks.py`
- `src/avs/cli_timeline.py`
- `src/avs/delivery/package.py`
- `src/avs/workflow.py`
- `tests/test_qa.py`
- `tests/test_delivery.py`
- `tests/test_workflow.py`

新增：

- `schemas/visual-approval.schema.json`
- `src/avs/qa/approval.py`
- `tests/test_visual_approval.py`
- `tests/test_publishability_gate.py`

必须先写以下失败测试：

1. `publishable=true + planned_audio=false/实际静音` → `passed=false`；
2. `publishable=true + placeholder_count>0` → error，不再是 warning；
3. 字幕超过配置限制 → error；
4. 缺少视觉批准 → `technical_passed=true`、`human_approved=false`、整体不通过；
5. 批准文件视频哈希与当前视频不一致 → 不通过；
6. QA 未通过时 delivery 拒绝；
7. QA 报告 fingerprint 过期时自动重跑；
8. `avs run` 在人工批准缺失时停在 `WAITING_FOR_REVIEW`，不得执行 deliver；
9. `publishable=false` 不生成公开发布文案，但仍执行技术 QA。

CLI 行为必须明确：

- QA 有技术/发布 blocker：exit code 1；
- 只缺人工视觉批准：写报告、状态转为 `WAITING_FOR_REVIEW`、exit code 2；
- 全部通过：状态转为 `QA_PASSED`、exit code 0；
- delivery 只有在状态、QA fingerprint、视频哈希和批准文件全部有效时才能执行。

### Task 2：把 18 条参考资料转为本地机器知识库

新增并填充：

- `knowledge/references/catalog.yaml`
- `knowledge/references/patterns.yaml`
- `schemas/reference-library.schema.json`
- `src/avs/reference/library.py`
- `scripts/validate_reference_library.py`
- `tests/test_reference_library.py`

要求：

- 完整迁移已有 18 条记录，不能丢链接或丢研究结论；
- URL 唯一；
- `source_id` 唯一；
- 每个 pattern 的 `source_ids` 必须存在；
- 机器规则必须是可执行/可校验的字段，不得只写“节奏要好”“字幕要好看”；
- 保留 `docs/reference-research/douyin-codex-short-video-study.md` 作为人类可读说明，但明确 YAML 是单一事实来源；
- 可以增加生成 Markdown 的脚本，也可以手工保持同步，但 `scripts/verify.mjs` 必须能发现不同步；
- 不下载第三方视频，不保存 Cookie、Token，不复制参考文案和素材。

验证命令：

```bash
python scripts/validate_reference_library.py
python -m pytest -q tests/test_reference_library.py
```

### Task 3：增加 creative profile 并强制脚本/分镜可追溯

新增：

- `schemas/creative-profile.schema.json`
- `src/avs/content/creative_profile.py`
- `skills-src/build-creative-profile/SKILL.md`
- `tests/test_creative_profile.py`

修改：

- `src/avs/content/__init__.py`
- `src/avs/content/schema.py`
- `src/avs/content/models.py`
- `src/avs/cli.py`
- `src/avs/workflow.py`
- `schemas/script.schema.json`
- `schemas/storyboard.schema.json`
- 相关 fixture、Demo 和 tests。

必须实现：

```python
load_creative_profile(ep_dir: Path) -> dict[str, Any]
validate_creative_profile(ep_dir: Path, project_root: Path) -> None
validate_constraint_refs(profile: dict, script: dict, storyboard: dict, library: dict) -> None
```

内容验证至少拒绝：

- 缺少 creative profile；
- profile 没有明确观众、痛点、收益或 Hook；
- 选中的 source/pattern 不存在；
- script segment 没有 constraint refs；
- storyboard shot 没有 constraint refs；
- 横屏 `screen_recording` 使用 `contain`；
- `screen_focus` 没有有效 focus region；
- Hook segment/shot 超过前三秒才出现；
- 单个 screen recording 静态 shot 超过配置上限且没有 change points。

更新项目 Skills，使 Claude 在生成内容时必须依次读取：

1. `creative-profile.json`
2. `knowledge/references/patterns.yaml`
3. 本 Episode 的 `reference-recipe.json`（存在时）
4. 用户真实输入和素材清单。

### Task 4：修复 timeline、横屏录屏、字幕和声音策略

新增：

- `src/avs/render/caption_layout.py`
- `src/avs/qa/composition.py`
- `tests/test_caption_layout.py`
- `tests/test_composition.py`

修改：

- `src/avs/timeline/builder.py`
- `src/avs/timeline/models.py`
- `src/avs/timeline/validate.py`
- `src/avs/render/layouts.py`
- `src/avs/render/captions.py`
- `src/avs/render/ffmpeg.py`
- `src/avs/qa/report.py`
- `src/avs/qa/timeline_checks.py`
- `src/avs/qa/subtitle_checks.py`
- `schemas/timeline.schema.json`（只在需要明确 transform 合同时修改）
- `config/visual.yaml`
- `config/audio.yaml`
- 相关测试。

#### 4.1 字幕

实现一个纯函数，名称可以调整，但职责必须明确：

```python
split_caption_cues(
    text: str,
    start: float,
    duration: float,
    rules: CaptionRules,
) -> list[CaptionCue]
```

要求：

- 优先按中文标点和语义停顿拆分；
- 每 cue 最多 24 个中文字符；
- 每行最多 14 个中文字符；
- 最多 2 行；
- cue 时长按字符权重分配；
- 每 cue 0.8～3.5 秒；
- 阅读速度不超过 12 中文字符/秒；
- 不再把完整 Script segment 原样塞进一个 Scene 的整个时长；
- 继续输出 SRT；
- 烧录时使用稳定的 ASS/字幕样式或等价方案，底部安全区至少 260px；
- 保留带字幕和无字幕两个 MP4；
- 如实现关键词高亮，不得破坏 SRT 交付；高亮不是本轮必须项，不能因此扩项。

#### 4.2 横屏录屏布局

`src/avs/render/layouts.py` 至少新增：

```python
screen_focus_filter(focus_region: dict[str, float], ...) -> str
screen_stack_filter(...) -> str
```

要求：

- `screen_focus`：按归一化 focus region 裁切关键操作区域并放大到竖屏可读区域；
- `screen_stack`：使用模糊/暗化的满屏背景加清晰前景，禁止纯黑大边；
- `cover` 保留；
- `contain` 仅允许非公开内部预览或明确的非横屏场景；
- 不拉伸变形；
- filter 字符串必须有单元测试；
- publishable 横屏素材静默回退 contain 必须视为错误。

`src/avs/qa/composition.py` 使用 FFmpeg 可复现地抽样检查有效画面占比。优先使用 `cropdetect` 或等价确定性方式，输出：

```python
{
  "sample_count": 5,
  "median_active_ratio": 0.72,
  "min_active_ratio": 0.58
}
```

需要测试：

- 黑边 contain 合成样例失败；
- 满屏/blur background 样例通过；
- 分析失败时对 publishable Episode 不能默认为通过。

#### 4.3 声音

不再只靠文件名前缀决定音频角色。

修改 asset manifest 或 creative profile 映射，使音频角色显式为：

- `voice`
- `bgm`
- `sfx`
- `intentional_silence`

兼容旧文件名前缀只能作为降级识别，并产生 warning。

publishable 默认要求实际音轨非静音：

- `max_volume` 必须存在且高于 `-45 dBFS`；
- 总长静音占比不得超过配置；
- 开头静音不得超过 1 秒；
- 如果 profile 明确 `intentional_silence`，仍必须由人工批准，且不允许系统自动推断。

#### 4.4 节奏

Timeline QA 至少计算：

- 第一处视觉变化时间；
- 最长静态 video clip；
- 每 10 秒视觉变化数量；
- screen recording 最长连续时长。

publishable 不满足 `config/quality.yaml` 时阻塞 QA。不要开发新的剪辑引擎，只基于现有 shot/clip/graphic 信息判断和构建。

### Task 5：HyperFrames 快速预检和跨平台中文字体

新增：

- `src/avs/hyperframes/fonts.py`
- `tests/test_font_resolution.py`

修改：

- `src/avs/hyperframes/render.py`
- `src/avs/doctor.py`
- `schemas/motion-manifest.schema.json`
- `tests/test_hyperframes.py`
- `config/visual.yaml` 或 `config/quality.yaml`。

实现：

```python
resolve_cjk_font(config: dict[str, Any]) -> Path | None
hyperframes_preflight(project_root: Path, timeout: int) -> PreflightResult
```

字体解析顺序：

1. 配置中的显式路径；
2. Windows 常见中文字体；
3. macOS PingFang/Heiti 常见路径；
4. Linux 使用 `fc-match` 查找 `Noto Sans CJK SC`、`Source Han Sans SC` 等；
5. 找不到中文字体时：publishable fallback 必须失败并给出明确安装说明，不能生成方框后继续通过。

HyperFrames：

- 每次 motion 任务只做一次 preflight；
- CLI/browser 不可用时在 15 秒内决定 fallback；
- 不得每个 clip 都等待完整超时；
- motion manifest 记录：`renderer`、`status`、`fallback_reason`、`font_family/font_path`；
- 可读的静态 fallback 可以继续作为粗稿，但必须进入人工视觉批准；
- `avs doctor` 必须区分“核心链可用”和“HyperFrames 增强可用”：当 FFmpeg fallback 与中文字体均可用时，HyperFrames browser 缺失只能是明确 warning，doctor 仍可 exit 0；如果 fallback 或中文字体也不可用，doctor 必须失败；
- 不替换 HyperFrames，不引入云渲染或 Remotion 主链。

### Task 6：把第三方 Skills 真正下载并固定到项目本地

Claude Code 的项目 Skills 必须最终存在于仓库的 `.claude/skills/<name>/SKILL.md`，不得只依赖用户主目录的全局安装。

修改：

- `scripts/install_skills.mjs`
- `scripts/sync_skills.py`
- `skills.lock.json`
- `scripts/verify.mjs`
- `CLAUDE.md`
- `AGENTS.md`
- `docs/getting-started.md`
- `docs/compatibility.md`
- `tests/test_config.py` 或新增 `tests/test_skills_local.py`。

规则：

1. 项目自有 Skills：
   - `skills-src/` 仍是唯一编辑源；
   - 同步到 `.claude/skills/` 和 `.agents/skills/`；
   - 新增的 `build-creative-profile` 必须纳入同步和 lock。

2. HyperFrames：
   - 固定现有审计版本 `0.7.68`，除非 package lock 已经明确更新且兼容；
   - 从锁定 npm 包的 `dist/skills` 复制完整、可运行的 Skill 支持文件到项目 `.claude/skills/hyperframes*`；
   - 不写入 `~/.claude`、`~/.codex`、`~/.cursor`；
   - 记录来源、版本、许可证/来源说明、tree hash 和项目内目标路径。

3. video-shotcraft：
   - 固定 commit `d4915443232e89527fdc9d7e79f132ba411fc440`；
   - 下载并复制该 Skill 实际需要的最小自包含目录及 LICENSE/来源说明到项目本地；
   - 目标至少包含 `.claude/skills/video-shotcraft/`；
   - 只作为镜头语法、节奏、声音设计知识参考；
   - 不将 Remotion 变成主渲染器。

4. 安装脚本：
   - 支持首次联网安装；
   - 支持 `--check` 离线校验；
   - 重复执行幂等；
   - 下载失败时明确失败，不伪造 installed；
   - lock 中的 hash 与项目文件不一致时 verify 必须失败。

不得安装来源、许可或版本不可审计的社交平台“主页领取”Skill。

验证：

```bash
node scripts/install_skills.mjs --check
python scripts/sync_skills.py --check
```

### Task 7：修复全量测试卡住并建立最终双样例验收

先系统定位，不得直接通过拆分命令掩盖。

执行：

```bash
python -m pytest -vv --durations=30
python -m pytest -vv tests/test_render.py -x --durations=30
```

检查：

- 未设置 timeout 的 FFmpeg/FFprobe/subprocess；
- 子进程 stdout/stderr 管道未读取；
- 临时文件或文件句柄未释放；
- 测试 monkeypatch 泄漏；
- 测试顺序共享状态；
- Windows 文件锁；
- 已生成媒体被重复读取或覆盖；
- HyperFrames/browser 进程未终止。

必须修根因。允许把昂贵集成测试放到独立 subprocess，但最终 canonical 命令 `python -m pytest -q` 必须稳定结束并返回 0，不能只修改文档说“请拆分运行”。

更新 `scripts/run_acceptance.py`，加入两个固定场景：

#### 负样例：不可发布视频

包含以下至少 4 项：

- 静音；
- 横屏 contain 黑边；
- 超长字幕；
- 占位卡；
- 无人工批准。

预期：

- technical 可以部分通过；
- publishability 失败；
- 状态不能进入 `QA_PASSED`；
- deliver 必须失败；
- 报告明确列出 blocker。

#### 正样例：最低合格粗稿

至少满足：

- 非静音音轨；
- 无占位卡；
- 横屏画面使用 screen focus/stack，无大面积纯黑边；
- 字幕满足行数、字数、时长和安全区；
- 前三秒 Hook 与视觉变化合规；
- HyperFrames 不可用时 fallback 中文可读；
- 生成当前视频哈希对应的 `acceptance-fixture` 视觉批准；
- QA 通过；
- delivery 成功；
- 带字幕/无字幕视频均可完整解码。

不要把 Mock 成功当作全部验收。单元测试可以 Mock，但最终两个场景必须实际调用 FFmpeg 生成媒体并执行真实 QA。

---

## 五、必须采用的测试策略

每个根因先写失败测试，再写实现。

最低测试矩阵：

| 场景 | 预期 |
|---|---|
| publishable 静音 | QA FAIL |
| publishable 有占位卡 | QA FAIL |
| 字幕超过 2 行/24 字/阅读速度 | QA FAIL |
| 横屏 contain | QA FAIL |
| screen_focus focus region 非法 | content/timeline validate FAIL |
| 缺人工批准 | WAITING_FOR_REVIEW，deliver FAIL |
| 批准哈希过期 | QA/deliver FAIL |
| 重新渲染后旧 QA fingerprint | 自动重跑，不复用 |
| 合规声音/字幕/布局/批准 | QA PASS，deliver PASS |
| 无 HyperFrames | 15 秒内 fallback 或明确失败 |
| 无中文字体 | 不生成乱码成功结果 |
| reference source/pattern 引用不存在 | validate FAIL |
| 18 条参考目录完整且唯一 | PASS |
| 本地 Skills hash 与 lock 不一致 | verify FAIL |
| 全量 pytest | 一次完成、0 failed |

不要追求百分之百覆盖率；只补足能够证明上述根因被关闭的测试。

---

## 六、必须执行的最终验收命令

结束前必须从当前 HEAD 新鲜执行，不能引用之前的结果：

```bash
python -m avs doctor
python scripts/validate_reference_library.py
python scripts/sync_skills.py --check
node scripts/install_skills.mjs --check
python -m pytest -q
node scripts/verify.mjs
python scripts/run_acceptance.py
```

如果仓库的 Windows 标准入口不同，再额外执行项目原有 Windows 包装命令，但不能替代以上核心验收。

媒体验收还必须执行：

```bash
ffprobe <正样例无字幕视频>
ffprobe <正样例带字幕视频>
ffmpeg -v error -i <正样例无字幕视频> -f null -
ffmpeg -v error -i <正样例带字幕视频> -f null -
```

并记录：

- 分辨率；
- fps；
- 编码；
- 时长；
- 音轨；
- QA blocker 数量；
- 视觉批准视频 SHA-256；
- delivery manifest 中对应 SHA-256。

任何一条命令失败，本任务都不得标记完成。

---

## 七、提交与回滚规则

建议按以下原子提交组织，提交名称可调整但不得混成一次大提交：

1. `test: lock failing publishability cases`
2. `feat: enforce publishability and visual approval gate`
3. `feat: persist reference patterns and creative profiles`
4. `feat: improve captions screen layouts and audio validation`
5. `fix: make hyperframes fallback portable and readable`
6. `build: vendor and verify project-local skills`
7. `test: stabilize full suite and final acceptance`

每个提交前运行对应针对性测试。

不得：

- `git push --force`；
- 重写历史；
- 删除用户分支；
- 提交密钥、Cookie、Token、第三方视频或受版权保护素材；
- 把生成媒体大文件无边界加入 Git；
- 为提高评分进行无关重构。

如果用户没有明确要求推送，只提交到当前本地分支，不主动 push。

---

## 八、失败处理与自动尝试上限

同一个根因最多自动尝试 3 次。

连续 3 次仍失败时：

1. 停止继续叠加修改；
2. 保留失败现场；
3. 报告精确命令、错误、已尝试方案和当前 diff；
4. 标记为 BLOCKED；
5. 不得通过更换技术栈或大规模重构掩盖失败。

网络下载第三方 Skills 失败时，不能把状态写成 installed。已经存在项目本地的合法锁定副本时，可以使用离线副本并验证 hash。

---

## 九、明确不做事项

本轮禁止：

- 替换 Python、FFmpeg 或 HyperFrames 主技术栈；
- 引入 Remotion 作为主渲染器；
- 自动下载抖音视频；
- 自动发布、登录、评论或私信；
- 数字人、声音克隆、云渲染、剪映草稿逆向；
- 新增大量模板；
- 建设独立 Agent 状态系统；
- 全局目录重组；
- 全面代码美化、命名统一、无关类型重构；
- 将参考原文案、素材、观点或封面复制进项目；
- 用“最终还需要人工精修”掩盖声音、字幕、构图和节奏根本未完成；
- 在全部验收通过后继续“顺便优化”。

---

## 十、停止条件

只有同时满足以下条件才能停止并声明完成：

1. P1-01、P1-02、P1-03、P1-04、P2-01 全部有代码和测试证据关闭；
2. 负样例稳定被阻止；
3. 正样例稳定通过；
4. `avs run` 不再绕过人工视觉 Gate；
5. delivery 能验证最新视频、最新 QA、最新人工批准三者哈希一致；
6. 18 条历史参考链接和学习结论已进入项目本地机器知识库；
7. HyperFrames 和 video-shotcraft 相关 Skills 已固定到项目 `.claude/skills/`，不依赖全局目录；
8. 无 HyperFrames 时能快速降级，中文字体不可用时不会生成乱码成功产物；
9. `python -m pytest -q` 一次执行完成且 0 failed；
10. 所有最终验收命令 exit code 0；
11. 没有新引入的主线回归；
12. 剩余内容仅为非阻塞观察项。

达到条件后必须停止，不得继续找新问题。

---

## 十一、最终报告格式

最终只输出以下内容：

### 1. 执行结论

- 是否完成；
- 当前 Commit；
- 是否可作为可靠短视频粗稿系统交付；
- 是否仍有阻塞项。

### 2. 问题关闭表

| 问题 | 根因 | 修改文件 | 测试证据 | 状态 |
|---|---|---|---|---|

只列本轮 5 个问题。

### 3. 关键设计结果

说明：

- QA 三层 Gate；
- visual approval 哈希绑定；
- reference library/creative profile；
- 横屏录屏和字幕策略；
- HyperFrames fallback；
- 项目本地 Skills。

### 4. 修改文件

按新增、修改、删除分类。原则上不应有无关删除。

### 5. 实际执行的验证

逐条列出：

- 命令；
- exit code；
- 通过/失败数量；
- 关键输出。

### 6. 负样例结果

明确证明不可发布样例不能进入 `QA_PASSED/DELIVERY_READY`。

### 7. 正样例结果

列出视频路径、ffprobe、QA、批准哈希和 delivery manifest 结果。

### 8. Git 信息

- 基线 Commit；
- 最终 Commit；
- 提交列表；
- 工作区是否干净；
- 是否 push。

### 9. 剩余观察项

只允许非阻塞项；没有则写“无”。

### 10. 唯一下一步动作

只能选择：

> 当前验收已经通过，下一步是不再修改代码，使用真实素材创建一个 Episode，人工完成最终视觉批准后交付。

如果任务 BLOCKED，则唯一下一步必须是解除一个具体 blocker，不得给多个并行建议。
