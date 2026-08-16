---
trigger: "SCREEN_DOCUMENTARY 为每句话规划手机端可读的录屏镜头"
inputs:
  - "episodes/active/<ID>/work/director/证据镜头索引.json"
  - "episodes/active/<ID>/work/director/short-video-brief.json"
read_only:
  - "config/production-types.yaml"
outputs:
  - "episodes/active/<ID>/work/pilots/<variant>/timeline.json"
run: "python -m avs pilot <ID>"
verify: "python -m avs pilot <ID>"
stop_when: "每个录屏镜头包含 region、target、caption_safe_zone 与 minimum_mobile_readability"
on_missing_input: "缺少导演简报时先运行 direct。"
report_format: "- source_start/end\n- ROI region/zoom/pan\n- 目标 UI\n- 字幕安全区"
---

# mobile-screen-director

禁止完整横屏缩成竖屏邮票。关键 UI 必须通过 360x640 预览，返修仅可按明确 finding 调整 ROI。
