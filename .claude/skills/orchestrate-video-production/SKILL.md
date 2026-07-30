---
trigger: "需要从输入素材、参考视频或创意启动/续跑 Agent Video Studio 全流程；需要了解某一期视频下一步该做什么"
inputs:
  - "Episode ID，或创建 Episode 所需的 ID、模式和目标平台"
  - "episodes/active/<ID>/input/ 下的文本、图片、录屏、音频、本地参考视频或 links.txt（按实际情况提供）"
read_only:
  - "AGENTS.md"
  - "episode.json"
  - "work/asset-manifest.json"
  - "work/reference/reference-recipe.json（如存在）"
  - "work/content/"
outputs:
  - "不创建第二套工作流状态；所有状态仍写入 episode.json"
  - "由既有 CLI 生成的素材清单、参考配方、内容产物、timeline.json、MP4、SRT、QA 和 delivery/"
run: |
  python -m avs workflow resume <ID>
verify: |
  python -m avs workflow status <ID> --json
stop_when: |
  workflow status 的 next_action.kind 为 agent、human、input、recovery 或 complete。
  不得绕过任何人工审核关口。
on_missing_input: |
  没有素材时停在 WAITING_FOR_INPUT；补充 input/ 后执行 python -m avs ingest <ID>。
  没有本地参考视频时不分析远程链接，直接进入原创/改编内容工作区。
report_format: |
  - Episode ID 与当前状态
  - 本次实际执行的确定性命令及返回码
  - 当前 next_action（类型、原因、所需产物）
  - 需要 Agent 或人工完成的工作
  - QA/交付状态与已知限制
---

# Orchestrate Video Production

使用项目内的 `workflow` 命令协调现有 CLI；它只能续跑确定性步骤，不能伪造内容审核、素材批准或发布。

## 标准运行

```bash
# 创建一期（若尚未创建）
python -m avs episode create EP-20260730-01 --mode REFERENCE_ADAPT

# 将用户输入放入 episodes/active/EP-20260730-01/input/ 后续跑
python -m avs workflow resume EP-20260730-01

# 随时查询机器可读的下一步
python -m avs workflow next EP-20260730-01 --json
```

`resume` 只会依次执行以下已存在的确定性命令：

1. `ingest`；
2. 当 `input/reference/` 有本地视频时执行 `reference analyze`；
3. `content init`；
4. 在素材已人工确认后调用既有 `run`，完成时间线、字幕、FFmpeg、HyperFrames、QA 和交付。

## Agent 内容关口

当 `next_action.kind=agent` 时，依次使用 `write-video-script` 与
`create-storyboard` Skill。读取 `brief.md`、本地 `reference-recipe.json` 和
`input/`，生成全部内容产物后运行：

```bash
python -m avs content validate <ID>
python -m avs content approve <ID>
```

不得把参考原文案、案例、标题或封面复制进 `REFERENCE_ADAPT` 成片。无法核实的事实必须标记为待确认。

## 人工关口

当 `next_action.kind=human` 时，先完整检查页面提示的所需产物。

- `assets`：确认缺口、版式、使用权和占位声明，再执行 `avs assets approve <ID>`。
- `review`：完成内容或成片复核，使用相应的审核/QA 命令。
- `complete`：交付包已生成；仍需在剪映等编辑器中人工调整并手工发布。

## 远程参考链接

把 URL 放入 `input/links.txt` 仅作为来源和权利记录。不要让项目自动下载、转写或复制第三方平台视频。若需要结构分析，取得有权使用的本地副本后放入 `input/reference/`，再续跑工作流。
