# 更新日志 | Changelog

本项目的所有重要变更记录于此文件。

All notable changes to this project will be documented in this file.

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [1.2.0] - 2026-07-09

### 新增 | Added

- `cut.director`：从一句话生成专业剪辑执行计划，覆盖长视频/短视频、平台、目标时长、节奏、字幕、混音、调色、导出和 QA。
- `cut.quality`：导出后质量验收，检查 ffprobe 可读性、时长、码率、视频/音频流、分辨率和帧率。
- CLI 新增 `plan` 与 `qa` 命令；MCP 新增 `cut.create_plan` 与 `cut.quality_check`。
- `references/professional-workflow.md`：专业剪辑计划与导出 QA 参考。
- `agents/openai.yaml`：Codex/OpenAI skill UI 元数据。
- `tests/test_agent_compat.py` 与 `tests/test_professional_workflow.py`，测试套件扩展到 9 组，并兼容远程 main 的专业功能测试。

### 修复 | Fixed

- Windows 上 `tests/run_all.py` 统一使用 UTF-8 子进程输出，避免 GBK 终端因 `✓/✗` 崩溃。
- `npm test` 修正为从仓库根目录运行 `tests/run_all.py`。
- `SKILL.md` frontmatter 移除非便携 `compatibility` key，兼容严格 skill 加载器。
- OpenCode 安装路径改为用户级 `~/.config/opencode/skills/cut` 与项目级 `.opencode/skill/cut`。
- Qwen 安装方式改为 skill 目录扫描，不再写入非标准 `skills.json`。
- Agent 文档统一使用真实 MCP 工具名 `cut.list_backends`。

## [1.1.0] - 2026-07-07

### 修复 | Fixed

- **[CRITICAL]** `draft.save()` 改为原子写入（临时文件 + os.replace），写入失败不再破坏原文件
- **[CRITICAL]** `mcp_server` 未安装 mcp 包时仍可 import（提供 Tool/TextContent shim 类），HTTP API 不再受牵连
- **[CRITICAL]** `segments.move_segment` 跨轨道移动后更新 `raw["track_id"]` 字段
- **[CRITICAL]** `segments.remove_segment` ripple 模式：只移动真正在删除段之后的片段，同步移动关键帧时间，避免负数 start
- **[CRITICAL]** `premiere.audio.add_fade_in/add_fade_out` 不再用 `setGain(0)` 把整段静音，改为通过 Volume 组件关键帧 API（不支持时返回 success=False 而非假装成功）
- **[CRITICAL]** `effects.add_video_effect` 不再把 segment_id 错放进 `extra_material_refs`，改为在目标 segment 上引用 effect material_id（与 LUT 模式一致）
- **[CRITICAL]** `text._make_text_material` 修复字段名前导空格 typo（`" recognize_type"` → `"recognize_type"`）

- **[HIGH]** `segments.split_segment` 防御 source_duration 不足导致负数（clamp 到 0）
- **[HIGH]** `segments.split_segment` 关键帧按切点分配到左右段，右段关键帧重新生成 ID 避免重复；`extra_material_refs` 不复制到右段
- **[HIGH]** `materials.add_video_segment` 删除重复的 `clip` 和 `is_placeholder` dict key
- **[HIGH]** `text` 删除重复的 `text_alpha` 和 `text_size` dict key
- **[HIGH]** `draft.recalc_duration()` 新方法：删除片段后收缩项目时长（原 `extend_duration` 只增不减）
- **[HIGH]** `text.update_text_content` 设置 `_modified` 标记
- **[HIGH]** `export.export_via_ui` 不再无脑返回 success=True，改为轮询输出文件大小稳定后返回，超时返回 False
- **[HIGH]** `export.export_via_ffmpeg` 用 list 形式构造命令（不再 `shell=True`），消除命令注入风险
- **[HIGH]** `mcp_server` split/trim 工具支持 `track_type` 参数（不再硬编码 "video"）
- **[HIGH]** `mcp_server` split 工具 Premiere 后端校验 `clip_index` 必填
- **[HIGH]** `cli` split 命令 Premiere 后端校验 `--clip` 必填
- **[HIGH]** `premiere.audio.set_volume` 移除无限递归风险
- **[HIGH]** `draft._us` 修复时间语义不一致：裸数字字符串现在按 unit（默认 μs）处理，与 CLI `_parse_time` 一致
- **[HIGH]** `audio.apply_ducking` 修复 `is_ducked` 死代码，起始处补充原音量关键帧

### 变更 | Changed

- 清理所有未使用 import（autoflake）
- 修复所有 f-string 无占位符警告（pyflakes 完全干净）

### 新增 | Added

- `tests/test_regression.py` — 13 项 Bug 修复回归测试
- `LICENSE` — MIT 许可证
- `CONTRIBUTING.md` — 贡献指南
- `CHANGELOG.md` — 本文件
- 中英文双语 README

## [1.0.0] - 2026-07-07

### 首次发布 | Initial Release

- 剪映 draft 文件操控（导入/裁切/字幕/转场/特效/混音/导出）
- Premiere pymiere 封装
- 4 种集成形态：CLI / MCP Server / HTTP API / 纯文档
- 6 家 agent 适配：Codex / Claude / OpenCode / Kimi / Qwen / GLM
- 跨平台支持（Windows + macOS）
- 上下文感知与反向读取接口
- 3 个端到端示例：批量裁切 / ASR 自动字幕 / 双轨混剪
- 5 个测试套件（58 项断言）
