---
trigger: "脚本已完成，需要规划分镜和素材安排"
inputs:
  - "episodes/active/<ID>/work/content/script.json"
  - "episodes/active/<ID>/work/asset-manifest.json"
  - "episodes/active/<ID>/work/reference/reference-recipe.json（可选）"
read_only:
  - "AGENTS.md"
  - "schemas/storyboard.schema.json"
  - "episodes/active/<ID>/input/（只读）"
outputs:
  - "episodes/active/<ID>/work/content/storyboard.json"
  - "episodes/active/<ID>/work/content/storyboard.md"
  - "episodes/active/<ID>/work/content/missing-assets.md"
run: |
  python -m avs episode validate <ID>
verify: |
  python -m avs episode validate <ID>
stop_when: |
  storyboard.json 通过 Schema 校验，
  每个 Scene 映射到 Script Segment，
  missing-assets.md 完整列出缺失素材
on_missing_input: |
  缺少实际素材时：在 storyboard 中标记 missing_assets 字段，
  生成 missing-assets.md；不使用无关素材占位
report_format: |
  - Scene 数量
  - 每 Scene 的视觉类型（用户素材/动效/占位）
  - 缺失素材清单（类型、建议替代方案）
  - HyperFrames 动效需求（如有）
  - Schema 校验结果
---

# create-storyboard Skill

将脚本转化为逐帧分镜，标注素材来源和缺口。

## 生成要求

每个分镜 Scene 必须包含：
- `scene_id`：唯一标识
- `script_segment_ids`：对应的脚本段落
- `duration`：预计时长（秒）
- `visual_type`：screen_recording / image / b_roll / motion_graphic / placeholder
- `asset_ids`：来自 asset-manifest 的素材引用（不存在的不填）
- `caption`：字幕文本
- `motion_template`：HyperFrames 组件名（如 HookTitle / InfoCard）
- `missing_assets`：缺失素材描述清单
- `notes`：给剪辑师的说明

## 约束

- 不直接选择不存在的素材路径
- 缺失素材必须在 `missing_assets` 字段和 `missing-assets.md` 中声明
- 不虚构素材内容

## 输出格式

**storyboard.json**（machine-readable）:
```json
{
  "episode_id": "EP-XXX",
  "shots": [
    {
      "scene_id": "scene001",
      "script_segment_ids": ["seg001"],
      "duration": 3.0,
      "visual_type": "motion_graphic",
      "asset_ids": [],
      "caption": "开场标题卡",
      "motion_template": "HookTitle",
      "missing_assets": ["需要品牌标题卡素材"],
      "notes": "可用 HyperFrames HookTitle 动态生成"
    },
    {
      "scene_id": "scene002",
      "script_segment_ids": ["seg002"],
      "duration": 5.0,
      "visual_type": "image",
      "asset_ids": ["asset_product_screenshot"],
      "caption": "产品截图展示",
      "motion_template": null,
      "missing_assets": [],
      "notes": "contain + zoom"
    }
  ],
  "asset_gaps": ["scene001"],
  "generated_at": "2026-07-20T..."
}
```

**storyboard.md**（human-readable）:
```markdown
# Storyboard — EP-XXX

## shot001 (0-3s)
**描述：** 开场标题卡
**素材：** ❌ 缺失 — 需要品牌标题卡素材
**处理：** HookTitle component

## shot002 (3-8s)
**描述：** 产品截图展示
**素材：** ✅ images_product_screenshot.png
**处理：** contain + zoom

---
**缺失素材总计：** 1 项（见 missing-assets.md）
```

**missing-assets.md**:
```markdown
# Missing Assets — EP-XXX

## shot001 — 品牌标题卡
**类型：** 图片或视频
**用途：** 开场3秒
**替代方案：** 可用 HyperFrames HookTitle 动态生成

---
请补充素材到 input/ 后重新运行 `avs ingest`
```

## CLI 工作流

```bash
# 1. 脚本完成后
python -m avs content validate EP-XXX  # 确认script.json存在

# 2. Agent 生成分镜（此Skill）
# → 读取 script.json, asset-manifest.json
# → 生成 storyboard.json + storyboard.md + missing-assets.md

# 3. 校验
python -m avs content validate EP-XXX

# 4. 人工审核
python -m avs content approve EP-XXX
```

## 验收标准

- ✅ storyboard.json 通过 schemas/storyboard.schema.json
- ✅ 每个shot有order/description/duration_estimate
- ✅ asset_ref仅引用asset-manifest中存在的素材
- ✅ 缺失素材标记gap=true且在asset_gaps列表中
- ✅ missing-assets.md完整列出所有缺口
