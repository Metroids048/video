---
name: epidemic-sound
description: >
  【Epidemic Sound】版权音乐 / SFX 素材检索入口。
  官方提供 MCP（无公开 GitHub SKILL.md 仓）。用于短视频 BGM、音效匹配；
  无账号时标记素材缺口，不硬凑无关音频。
trigger: 版权音乐、Epidemic Sound、BGM 检索、配乐素材
inputs: []
read_only:
  - input/
outputs: []
run: "通过官方 MCP 检索曲目；下载到 Episode work/ 工作副本"
verify: "记录曲目 ID/许可范围与本地音频路径"
stop_when: "无账号/MCP 不可用或用户停止"
on_missing_input: "标记音乐缺口并停止，不伪造授权"
report_format: "命令、退出码、产物路径、已知限制"
---

# Epidemic Sound（版权音乐）入口

上游 MCP：https://www.epidemicsound.com/a/mcp-service/mcp

GitHub org（无 Agent Skill 仓）：https://github.com/epidemicsound

## 硬规则

1. 不将 API Key / Cookie / Token 写入仓库；仅用本机 `.env` 或 MCP 登录态。
2. 无账号或 MCP 失败时：在素材缺口清单中标记，**禁止**用明显无关音频硬凑。
3. 下载的音频只进 Episode `work/` 工作副本，不得写入 `input/`。
4. 旁路配乐不得伪造 Episode 状态机完成态。

## 与 AVS 的关系

- Episode 状态机仍由 `python -m avs` 管理。
- 选中曲目路径应可被 `timeline.json` 音频轨引用或在交付说明中标明。
- 默认仍可用本地/免版税平替；Epidemic Sound 为版权曲库升级路径。

## Agent 操作

1. 确认 MCP `epidemic-sound`（或等价）已配置。
2. 按情绪/时长/BPM 检索，记录 track id 与许可范围。
3. 将预览或授权下载落到 `work/audio/`。
