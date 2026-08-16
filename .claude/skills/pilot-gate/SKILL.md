---
trigger: "至少一位 visual-critic 已实际查看 Pilot 并提交带素材路径的评分，需要仲裁是否允许完整渲染"
inputs:
  - "episodes/active/<ID>/work/qa/pilots/pilot-manifest.json"
  - "episodes/active/<ID>/work/qa/pilots/reviewer-*.json"
read_only:
  - "config/production-types.yaml"
outputs:
  - "episodes/active/<ID>/work/qa/pilots/pilot-review.json"
run: "python -m avs pilot-review <ID> --reviewers <two-reviewer-json>"
verify: "python -m avs workflow next <ID> --json"
stop_when: "唯一赢家的任一核心维度均 >=8 且 overall >=8.5；否则 REJECT 或 BLOCKED"
on_missing_input: "没有任何实际看片记录或评分未列出 reviewed_artifacts 时 BLOCKED；不因缺第二个 Reviewer 身份而阻塞。"
report_format: "- 仲裁结论\n- winner\n- 聚合分数\n- 原始 Reviewer 路径\n- repair_round\n- findings"
---

# pilot-gate

任何低于门槛的核心项都拒绝。Pilot 未通过前，`final-render`、交付包和 `DELIVERY_READY` 都被禁止。录屏专题的 Pilot 使用真人口播与 20-30 秒 SRT 主时钟，不使用 AI 配音占位。
