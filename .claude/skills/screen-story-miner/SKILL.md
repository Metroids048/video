---
trigger: "SCREEN_DOCUMENTARY 需要从已验证 VCI 包和录屏工作副本定位真实证据镜头"
inputs:
  - "episodes/active/<ID>/episode.json"
  - "video-content-intelligence/workspace/packages/VID-20260812-FDA0/（只读）"
read_only:
  - "录屏/20260812_131106.mp4"
  - "量化项目仓库（只读事实）"
outputs:
  - "episodes/active/<ID>/work/director/录屏内容索引.json"
  - "episodes/active/<ID>/work/director/证据镜头索引.json"
  - "episodes/active/<ID>/work/director/推荐片段.md"
  - "episodes/active/<ID>/work/director/禁止使用片段.md"
run: "python -m avs story-mine <ID>"
verify: "python -m avs episode validate <ID>"
stop_when: "索引明确标注 Binance、K线、Why No Trade 和无效加载片段，且 reused_vci=true"
on_missing_input: "缺少已验证 VCI 包时阻塞；不得重新 ingest 或转写。"
report_format: "- VCI 包 ID\n- 证据镜头与 ROI\n- 禁止使用片段\n- 命令与返回码"
---

# screen-story-miner

只复用已验证的内容智能包，从真实录屏中定位可证明事实的 UI 片段。不得读取旧 V1 时间线来派生镜头。
