---
trigger: "QA 通过，需要生成可发布的文案和交付包"
inputs:
  - "episodes/active/<ID>/delivery/qa-report.json（状态必须为 QA_PASSED）"
  - "episodes/active/<ID>/work/content/script.json"
  - "episodes/active/<ID>/work/content/brief.md"
  - "episodes/active/<ID>/episode.json"
read_only:
  - "AGENTS.md"
  - "config/platforms.yaml"
  - "episodes/active/<ID>/input/（只读）"
outputs:
  - "episodes/active/<ID>/delivery/publish/douyin.md"
  - "episodes/active/<ID>/delivery/publish/xiaohongshu.md"
  - "episodes/active/<ID>/delivery/edit-notes.md"
  - "episodes/active/<ID>/delivery/delivery-manifest.json"
run: |
  python -m avs deliver <ID>
verify: |
  python -m avs episode status <ID>
stop_when: |
  delivery-manifest.json 通过 Schema 校验，
  两个平台文案文件存在，
  所有路径为相对路径，
  Episode 状态为 DELIVERY_READY
on_missing_input: |
  QA 未通过时拒绝生成发布文案；
  publishable=false 时不生成可发布标记
report_format: |
  - 交付包文件清单（路径均为相对路径）
  - 抖音文案预览（标题、话题、说明）
  - 小红书文案预览（标题、正文、标签）
  - 人工修改清单摘要
  - publishable 标记
  - 命令与返回码
---

# create-publish-pack Skill

生成可直接使用的平台发布文案和完整编辑交付包。

## 平台文案要求

### 抖音（douyin.md）

- 标题（≤ 30 字，含关键词）
- 话题标签（3–5 个）
- 视频说明（≤ 100 字）
- 封面建议
- 发布时间建议（可选）

### 小红书（xiaohongshu.md）

- 标题（含 emoji，≤ 20 字）
- 正文（结构化，含价值主张）
- 标签（5–10 个）
- 首图文字建议

## 约束

- **不自动发布**（始终等待用户人工操作）
- `REFERENCE_CLONE` 模式不生成可发布标记
- `publishable: false` 时在文案文件顶部添加醒目警告
- 所有交付路径相对化（不含绝对路径）
- 不虚构视频数据或夸大效果
