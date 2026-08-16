---
trigger: "Pilot Gate REJECT 且 findings 指向可自动执行的最小责任层"
inputs:
  - "episodes/active/<ID>/work/qa/pilots/pilot-review.json"
  - "episodes/active/<ID>/work/pilots/*/timeline.json"
read_only:
  - "config/production-types.yaml"
outputs:
  - "episodes/active/<ID>/work/pilots/pilot-overrides.json"
  - "episodes/active/<ID>/renders/pilots/*.mp4（局部重渲染）"
run: "python -m avs pilot-revise <ID>"
verify: "python -m avs pilot-review <ID> --reviewers <two-reviewer-json> --force"
stop_when: "最多两轮，并且仅修改 finding 指向的 ROI、字幕、节奏或文案"
on_missing_input: "无可执行 repair_target、已两轮或审核 BLOCKED 时保持阻塞，不整体重做。"
report_format: "- repair_round\n- finding\n- 最小修改\n- 重渲染的 Pilot\n- 复审结果"
---

# auto-video-reviser

不改旧 V1，不制作完整 V2。第三次返修请求直接阻塞。
