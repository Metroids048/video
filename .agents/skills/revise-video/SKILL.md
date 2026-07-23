---
trigger: "用户需要对已交付的视频进行局部修改"
inputs:
  - "episodes/active/<ID>/delivery/delivery-manifest.json"
  - "episodes/active/<ID>/work/timeline.json"
  - "用户的修改说明（自然语言）"
read_only:
  - "AGENTS.md"
  - "episodes/active/<ID>/input/（只读）"
  - "episodes/active/<ID>/renders/（参考用）"
outputs:
  - "episodes/active/<ID>/work/timeline.json（更新版）"
  - "episodes/active/<ID>/delivery/edit-notes.md（更新）"
  - "重新渲染的产物（如需要）"
run: |
  python -m avs timeline validate <ID>
  python -m avs render rough <ID> --force
  python -m avs qa <ID>
verify: |
  python -m avs episode status <ID>
stop_when: |
  用户确认修改符合预期，
  QA 重新通过，
  edit-notes.md 更新完整
on_missing_input: |
  修改说明不够具体时，提问用户确认后再执行；
  无法在 timeline.json 中表达的修改，写入 edit-notes.md 供人工处理
report_format: |
  - 修改内容摘要
  - 修改的时间线片段列表
  - 需要人工完成的剩余修改
  - 重新渲染命令与返回码
  - QA 结果
---

# revise-video Skill

根据用户反馈对已完成的视频进行局部修改。

## 流程

1. 解析用户修改说明（自然语言）
2. 确认可在 `timeline.json` 中表达的修改范围
3. 超出程序能力的修改写入 `edit-notes.md` 供人工处理
4. 用 `--force` 重新渲染受影响的片段
5. 重新运行 QA
6. 报告修改结果

## 约束

- 只修改当前 Episode 的工作文件，不影响其他 Episode
- 原始输入文件不可修改
- 修改说明模糊时必须先询问用户，不能自行假设
- V1 主要支持时间线级别的修改；复杂的视觉调整记录到 edit-notes.md
