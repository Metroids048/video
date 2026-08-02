---
name: remotion
description: >
  Remotion entry router. Prefer remotion-best-practices for authoring;
  use remotion-create / remotion-render / remotion-captions / remotion-multimedia as needed.
trigger: React/代码驱动成片、Remotion 模板、可复用动效片
inputs: []
read_only:
  - input/
outputs: []
run: "Read remotion-best-practices first; then remotion-create or remotion-render"
verify: "Rendered media exists under Episode work/output; non-zero exit on failure"
stop_when: "User stops or render fails"
on_missing_input: "List gaps; do not fake frames"
report_format: "commands, exit codes, artifact paths, limits"
---

# Remotion（代码驱动视频）

上游 Skills：https://github.com/remotion-dev/skills  
框架：https://github.com/remotion-dev/remotion  

## 本仓库已 vendor 的相关 Skill

- `remotion-best-practices` — 默认先读
- `remotion-create` / `remotion-render` / `remotion-upgrade`
- `remotion-captions` / `remotion-multimedia` / `remotion-markup`
- `remotion-interactivity` / `remotion-maps` / `remotion-saas` / `remotion-docs`

## 与 AVS

- 按 `docs/video-plugin-routing.md` 启用。
- 产物回挂 Episode `work/` 或 `output/`。
- 不得伪造 `QA_PASSED`。见 ADR-0006。
