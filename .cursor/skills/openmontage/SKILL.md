---
name: openmontage
description: >
  【开放蒙太奇】OpenMontage agentic video production entry skill.
  Use for multi-pipeline documentary montage, explainer, and stock-footage workflows.
  Read AGENT_GUIDE.md in the vendored repo before driving pipelines.
trigger: 多管线 Agent 制片、纪录片蒙太奇、OpenMontage pipeline
inputs: []
read_only:
  - input/
outputs: []
run: "参阅 vendor/repos/openmontage/AGENT_GUIDE.md 与 pipeline_defs/"
verify: "确认最终 MP4 与 Episode 工作目录产物已挂载"
stop_when: "用户要求停止或 pipeline 自检失败"
on_missing_input: "列出缺口并停止，不伪造素材"
report_format: "命令、退出码、产物路径、已知限制"
---

# OpenMontage（开放蒙太奇）入口

Full sparse checkout at `vendor/repos/openmontage`.

上游：https://github.com/calesthio/OpenMontage

## 必读

1. `vendor/repos/openmontage/AGENT_GUIDE.md`（若已 vendor）
2. `vendor/repos/openmontage/PROJECT_CONTEXT.md`
3. `vendor/repos/openmontage/pipeline_defs/`

## 与 AVS 的关系

- Episode 状态机仍由 `python -m avs` 管理。
- OpenMontage 产出必须落到对应 Episode 的 `work/` 或 `output/`。
- 不得跳过状态机或伪造 `QA_PASSED`。

## AGPL 注意

OpenMontage 为 AGPL-3.0。用于正式交付前确认合规。
