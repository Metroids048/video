---
trigger: "粗剪完成，需要对视频进行 QA 审查"
inputs:
  - "episodes/active/<ID>/renders/preview-clean.mp4"
  - "episodes/active/<ID>/renders/preview-with-captions.mp4"
  - "episodes/active/<ID>/work/timeline.json"
  - "episodes/active/<ID>/delivery/captions.srt"
read_only:
  - "AGENTS.md"
  - "schemas/qa-report.schema.json"
  - "episodes/active/<ID>/renders/（只读）"
outputs:
  - "episodes/active/<ID>/delivery/qa-report.md"
  - "episodes/active/<ID>/delivery/qa-report.json"
  - "episodes/active/<ID>/work/reference/contact-sheet-final.jpg"
run: |
  python -m avs qa <ID>
verify: |
  python -m avs episode status <ID>
stop_when: |
  确定性 QA 全部通过（无 FAIL 级别错误），
  Agent 视觉 QA 报告已生成，
  Episode 状态为 QA_PASSED
on_missing_input: |
  MP4 不存在时报错并停止；
  SRT 不存在时跳过字幕越界检查并在报告中注明
report_format: |
  # 确定性 QA
  - 可解码性：PASS/FAIL
  - 分辨率：<actual> vs 1080x1920
  - 帧率：<actual> vs 30fps
  - 时长：<value>s
  - 黑帧：<count>（连续>1s 为 FAIL）
  - 长静音：<count>（连续>3s 为 WARN）
  - 音频峰值：<dBFS>（>-1dBFS 为 FAIL）
  - 字幕越界：<count>
  - 缺失素材占位：<count>
  # Agent 视觉 QA
  - 字幕可读性
  - 画面与口播匹配度
  - 节奏评估
  - 人工修改建议清单
---

# quality-review Skill

对粗剪视频执行确定性 QA 检测，并通过联系表执行 Agent 视觉 QA。

## 确定性 QA 检查项

| 检查项 | FAIL 条件 | WARN 条件 |
|--------|-----------|-----------|
| 可解码性 | 无法解码 | - |
| 分辨率 | ≠ 1080×1920 | - |
| 帧率 | < 28fps | - |
| 黑帧 | 连续 > 1s | > 0.5s |
| 长静音 | 连续 > 3s（仅音轨） | > 1.5s |
| 音频峰值 | > -1 dBFS | > -3 dBFS |
| 字幕越界 | 任何越界 | - |
| 缺失素材占位 | - | > 0 |

## Agent 视觉 QA

读取从成片抽取的联系表（非凭空判断），评估：
- 字幕可读性
- 画面与口播匹配度
- 录屏文字是否过小
- 节奏是否明显拖沓
- 人工修改优先级列表

## 约束

- 视觉 QA 不将主观判断伪装成确定性错误
- QA_FAIL 不进入 QA_PASSED 状态
- 输出路径使用相对路径
