---
trigger: "需要为 SCREEN_DOCUMENTARY Pilot 生成自然中文旁白"
inputs:
  - "episodes/active/<ID>/work/director/short-video-brief.json"
  - "episodes/active/<ID>/work/director/证据镜头索引.json"
read_only:
  - "config/production-types.yaml"
outputs:
  - "episodes/active/<ID>/work/pilots/<variant>/narration.mp3"
  - "episodes/active/<ID>/work/pilots/<variant>/narration.json"
run: "python -m avs pilot <ID>"
verify: "ffprobe -v error episodes/active/<ID>/work/pilots/<variant>/narration.mp3"
stop_when: "三支 Pilot 使用同一 TTS 声线，旁白不含未经验证的收益承诺"
on_missing_input: "没有可用自然原声时使用 Edge TTS；不得克隆用户声音。"
report_format: "- 旁白文本\n- 声线与语速\n- 事实边界\n- 音频验证"
---

# narration-director

句子保持口语化且通常为 8-22 个汉字。禁止“本系统实现了”式项目汇报腔和播音腔。
