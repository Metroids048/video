---
trigger: "SCREEN_DOCUMENTARY 需要在完整片前制作三个真实开场 Pilot"
inputs:
  - "episodes/active/<ID>/work/director/short-video-brief.json"
  - "episodes/active/<ID>/work/director/证据镜头索引.json"
read_only:
  - "config/production-types.yaml"
outputs:
  - "episodes/active/<ID>/renders/pilots/pilot-A-result.mp4"
  - "episodes/active/<ID>/renders/pilots/pilot-B-reversal.mp4"
  - "episodes/active/<ID>/renders/pilots/pilot-C-project.mp4"
run: "python -m avs pilot <ID>"
verify: "python -m avs pilot <ID>"
stop_when: "A/B/C 均为 8-10 秒、真实录屏开场且附带 SRT、ROI 时间线、密集帧和联系表"
on_missing_input: "缺少 director brief 时停止，不从旧 V1 timeline 派生。"
report_format: "- 变体名称\n- Hook 文案\n- 时长\n- 事实来源\n- 输出路径"
---

# hook-variant-generator

A 是结果型，B 是谨慎反转型，C 是项目型。无标题卡、无网格背景、无关 B-roll 或整页缩放。
