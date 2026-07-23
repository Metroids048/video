---
trigger: "Episode 已有 Storyboard 和素材，需要生成 FFmpeg 基础粗剪"
inputs:
  - "episodes/active/<ID>/work/content/storyboard.json"
  - "episodes/active/<ID>/work/asset-manifest.json"
  - "episodes/active/<ID>/work/timeline.json（由 timeline build 命令生成）"
read_only:
  - "AGENTS.md"
  - "schemas/timeline.schema.json"
  - "config/visual.yaml"
  - "config/audio.yaml"
outputs:
  - "episodes/active/<ID>/work/timeline.json"
  - "episodes/active/<ID>/work/timeline.csv"
  - "episodes/active/<ID>/delivery/captions.srt"
  - "episodes/active/<ID>/renders/preview-clean.mp4"
  - "episodes/active/<ID>/renders/preview-with-captions.mp4"
run: |
  python -m avs timeline build <ID>
  python -m avs timeline validate <ID>
  python -m avs subtitles build <ID>
  python -m avs render rough <ID>
verify: |
  ffprobe -v error -show_entries format=duration,size \
    -of default=noprint_wrappers=1 \
    episodes/active/<ID>/renders/preview-clean.mp4
  python -m avs episode status <ID>
stop_when: |
  两个 MP4 存在且通过 FFprobe 解码，
  时间线通过 Schema 校验，
  Episode 状态为 ROUGH_CUT_READY
on_missing_input: |
  缺少素材时生成明确占位卡（不使用无关内容），
  在 timeline.json 中标记 missing: true，
  并写入 delivery/edit-notes.md 草稿
report_format: |
  - FFprobe 摘要（分辨率、帧率、时长、音轨）
  - 时间线轨道统计（视频/字幕/音频片段数）
  - 占位卡数量
  - 命令与返回码
  - Episode 状态
---

# create-rough-cut Skill

使用 `timeline.json` 和 FFmpeg 生成不依赖 HyperFrames 的基础视频粗剪。

## 约束

- 画布：1080×1920，30fps，H.264/AAC/yuv420p
- 输出路径使用相对路径
- 不依赖 HyperFrames（此步骤是 HyperFrames 的降级基础）
- 缺少素材使用占位卡，不使用无关内容
- 字幕默认在安全区（距边缘至少 80px）
- 音量：旁白优先，BGM ducking，防止削波
- 重复执行：`--force` 才覆盖已渲染产物
