---
trigger: "SCREEN_DOCUMENTARY 已完成 story-mine，需要选择唯一故事和事实边界"
inputs:
  - "episodes/active/<ID>/work/director/录屏内容索引.json"
  - "episodes/active/<ID>/work/director/证据镜头索引.json"
read_only:
  - "config/production-types.yaml"
outputs:
  - "episodes/active/<ID>/work/director/short-video-brief.json"
run: "python -m avs direct <ID>"
verify: "python -m avs episode validate <ID>"
stop_when: "只保留一个主问题、一个主结果和一个下一集钩子，时长目标 45-55 秒"
on_missing_input: "缺少证据索引时先运行 story-mine。"
report_format: "- 核心故事\n- 事实边界\n- 删除清单\n- 结构与目标时长"
---

# short-video-director

EP01 的固定故事是阶段账户变化作为钩子，Agent 构建真实 Binance Demo 系统作为证据，且不把阶段变化说成策略收益。
