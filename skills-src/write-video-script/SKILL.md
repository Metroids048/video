---
trigger: "需要将内容简报和参考配方转化为口播脚本"
inputs:
  - "episodes/active/<ID>/work/content/brief.md（或用户提供的 idea.md）"
  - "episodes/active/<ID>/work/reference/reference-recipe.json（可选）"
  - "episodes/active/<ID>/work/asset-manifest.json"
read_only:
  - "AGENTS.md"
  - "schemas/script.schema.json"
  - "episodes/active/<ID>/input/（只读，引用来源用）"
outputs:
  - "episodes/active/<ID>/work/content/brief.md"
  - "episodes/active/<ID>/work/content/script.json"
  - "episodes/active/<ID>/work/content/script.md"
run: |
  # 此 Skill 由 Agent 执行内容生成，CLI 只负责 Schema 校验和状态推进
  python -m avs episode validate <ID>
verify: |
  # Agent 生成后运行 Schema 校验
  python -m avs episode validate <ID>
stop_when: |
  script.json 通过 Schema 校验，
  每个脚本段落有 purpose / target_duration / source_refs，
  不存在虚构事实
on_missing_input: |
  无参考配方时使用 generic 模板或 screen-explainer 模板；
  用户只提供一句想法时，先生成内容简报请用户确认再写脚本
report_format: |
  - 脚本段落数量和总预估时长
  - 每段的来源引用
  - 无法核实的内容标注
  - REFERENCE_ADAPT 时列出与原内容的差异
  - Schema 校验结果
  - 命令与返回码
---

# write-video-script Skill

将内容简报、参考配方和用户输入转化为可追溯的口播脚本。

## 生成要求

每个脚本段落必须包含：
- `segment_id`：唯一标识
- `text`：口播文案
- `purpose`：段落目的（hook / body / cta 等）
- `target_duration`：预计时长（秒）
- `visual_hint`：视觉方向提示
- `source_refs`：来源引用（指向 input/ 中的实际文件或链接）
- `status`：draft / reviewed / approved

## 约束

- 不虚构事实、数据、产品功能、运行结果或用户经历
- REFERENCE_ADAPT 必须替换原视频文案，不抄录
- REFERENCE_CLONE 设置 `publishable: false`
- 无法核实的内容用「需确认」标注，不假装确定

## 输出格式

**script.json**（machine-readable）:
```json
{
  "episode_id": "EP-XXX",
  "total_duration_estimate": 45.0,
  "segments": [
    {
      "segment_id": "seg001",
      "text": "开场口播...",
      "purpose": "hook",
      "target_duration": 5.0,
      "visual_hint": "标题卡 + 快速剪辑",
      "source_refs": ["input/idea.md"],
      "status": "draft",
      "notes": "源自 reference recipe 的结构，不复制原文案"
    }
  ],
  "generated_at": "2026-07-20T..."
}
```

**script.md**（human-readable）:
```markdown
# Script — EP-XXX

## seg001 (0-5s) — Hook
**口播：** 开场口播...
**视觉：** 标题卡 + 快速剪辑
**来源：** reference shot s001-s003

---
总预估时长：45.0s
```

## CLI 工作流

```bash
# 1. 初始化（CLI创建骨架）
python -m avs content init EP-XXX

# 2. Agent 生成（此Skill）
# → 读取 brief.md, reference-recipe.json, input/
# → 生成 script.json + script.md

# 3. 校验（CLI）
python -m avs content validate EP-XXX

# 4. 人工审核通过
python -m avs content approve EP-XXX
```

## 验收标准

- ✅ script.json 通过 schemas/script.schema.json
- ✅ 每段有 purpose/target_duration/visual_hint
- ✅ 无虚构事实（来源可追溯）
- ✅ REFERENCE_ADAPT 不抄录原文案
- ✅ script.md 可读性良好
