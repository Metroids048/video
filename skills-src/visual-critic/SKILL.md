---
trigger: "Pilot 已渲染，需要独立上下文对实际 MP4 做视觉审查"
inputs:
  - "episodes/active/<ID>/renders/pilots/*.mp4"
  - "episodes/active/<ID>/work/qa/pilots/*/contact-sheets/*"
  - "episodes/active/<ID>/work/qa/pilots/*/mobile-preview/*"
read_only:
  - "episodes/active/<ID>/work/director/证据镜头索引.json"
outputs:
  - "episodes/active/<ID>/work/qa/pilots/reviewer-<id>.json"
run: "python -m avs pilot-review <ID> --reviewers <two-reviewer-json>"
verify: "python -m avs pilot-review <ID> --reviewers <two-reviewer-json>"
stop_when: "每位 Reviewer 对 Pilot 的核心维度和 overall 均给出基于实际画面的评分、finding 与 reviewed_artifacts"
on_missing_input: "没有可实际查看 MP4、联系表或移动预览的审片人时 BLOCKED，不能基于 JSON 推断评分；单个可追溯审片人足以发起定向返修。"
report_format: "- reviewer_id/kind\n- 已看过的素材\n- 各维度分数\n- 证据帧\n- finding 与 repair_target"
---

# visual-critic

必须真实检查 MP4、解码帧、1fps 联系表和 360x640 预览。不能只读 timeline 或确定性 QA。
