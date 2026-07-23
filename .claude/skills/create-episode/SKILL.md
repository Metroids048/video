---
trigger: "用户要创建新的 Episode，或者执行 python -m avs episode create <ID>"
inputs:
  - "episodes/inbox/<ID>/input/ 或空目录（Episode 可先创建后再放入素材）"
read_only:
  - "AGENTS.md"
  - "config/project.yaml"
  - "config/workflow.yaml"
  - "schemas/episode.schema.json"
outputs:
  - "episodes/active/<ID>/episode.json"
  - "episodes/active/<ID>/input/（空目录占位）"
  - "episodes/active/<ID>/work/（空目录占位）"
  - "episodes/active/<ID>/renders/（空目录占位）"
  - "episodes/active/<ID>/delivery/（空目录占位）"
  - "episodes/active/<ID>/logs/（空目录占位）"
run: |
  python -m avs episode create <ID>
verify: |
  python -m avs episode status <ID>
  python -m avs episode validate <ID>
stop_when: "episode.json 存在且 Schema 校验通过，状态为 CREATED"
on_missing_input: "Episode 可以在没有任何输入文件的情况下创建；用户后续可以向 input/ 放入文件"
report_format: |
  - 完成内容：已创建 Episode <ID>
  - episode.json 路径
  - 初始状态：CREATED
  - 目录结构已创建
  - 命令与返回码
---

# create-episode Skill

创建新的 Episode 目录结构和初始 `episode.json`。

## 步骤

1. 验证 Episode ID 格式（字母数字连字符，如 `EP-0001`）
2. 检查 ID 是否已存在（防止重复创建）
3. 创建目录结构：`episodes/active/<ID>/{input,work,renders,delivery,logs}`
4. 写入 `episode.json`（初始状态 `CREATED`，`publishable: true` 默认）
5. 如模式为 `REFERENCE_CLONE`，自动设置 `publishable: false`

## episode.json 初始结构

```json
{
  "id": "EP-0001",
  "mode": "REFERENCE_ADAPT",
  "publishable": true,
  "status": "CREATED",
  "platforms": ["douyin", "xiaohongshu"],
  "completed_stages": [],
  "last_error": null,
  "artifacts": {},
  "updated_at": "<ISO-8601-with-timezone>"
}
```

## 约束

- 不可手工伪造状态
- 目录一旦创建，原始素材不可移动或删除
- ID 不允许路径穿越（不含 `/`, `\`, `..`）
