---
trigger: "需要分析参考视频，生成结构报告和 reference-recipe.json"
inputs:
  - "episodes/active/<ID>/input/reference/*.{mp4,mov,mkv,webm}（至少一个）"
  - "episodes/active/<ID>/work/asset-manifest.json（必须先完成 ingest）"
read_only:
  - "AGENTS.md"
  - "schemas/reference-recipe.schema.json"
  - "episodes/active/<ID>/input/reference/（只读）"
outputs:
  - "episodes/active/<ID>/work/reference/transcript.json（可选，取决于 Provider）"
  - "episodes/active/<ID>/work/reference/shots.json"
  - "episodes/active/<ID>/work/reference/keyframes/"
  - "episodes/active/<ID>/work/reference/contact-sheet.jpg"
  - "episodes/active/<ID>/work/reference/reference-report.md"
  - "episodes/active/<ID>/work/reference/reference-recipe.json"
run: |
  python -m avs reference analyze <ID>
verify: |
  python -m avs reference validate <ID>
stop_when: |
  reference-recipe.json 存在且通过 Schema 校验，
  Episode 状态为 REFERENCE_READY
on_missing_input: |
  无参考视频时跳过此 Skill，Episode 从 INGESTED 直接进入 CONTENT_READY 流程，
  使用 generic 或 screen-explainer 模板
report_format: |
  - 参考视频时长、比例、帧率
  - 检测到的镜头数量
  - 关键帧数量
  - 转写状态（成功/降级/禁用）
  - recipe 包含的结构要素
  - 置信度标注
  - 命令与返回码
---

# analyze-reference Skill

分析参考视频，生成可机器读取的结构配方（reference-recipe.json）。

## 步骤（确定性）

1. `python -m avs reference analyze <ID>` 提取：
   - 原始时长、比例、fps、音轨存在性
   - 镜头边界（基于帧差）
   - 每个镜头的关键帧
   - 联系表（contact-sheet.jpg）
   - 可选转写（通过 Provider 适配器）

## Agent 步骤（生成式）

读取确定性输出后，Agent 执行风格解释：

- 阅读联系表、关键帧、shots.json 和 transcript.json（如有）
- 分析开头钩子、叙事段落、结尾方式
- 标注可迁移的结构规则
- 标注不应复制的原始内容
- 标注每项的置信度（`high/medium/low`）

## 约束

- 字幕位置、转场意图、音乐节拍必须使用 `confidence`，不得假装确定
- 不自动下载第三方平台视频
- 转写 Provider 缺失时降级为 `manual` 模式
- 无音轨视频正常处理（跳过转写步骤）
- REFERENCE_CLONE 必须设 publishable=false，禁止生成发布包

## Agent 输出要求（reference-report.md）

```markdown
# Reference Analysis Report

## 基本参数
| 项 | 值 |
|----|---|
| 时长 | X.Xs |
| 镜头数 | N |
| 转写 | ✓/✗ |

## 开头Hook（0-15s）
[描述开头吸引力手法，标注 confidence]

## 主体结构
[分段描述叙事逻辑，标注可迁移元素]

## 结尾
[描述CTA或总结方式]

## 镜头清单
| ID | 时段 | 类型 | 内容 | Confidence |
|----|------|------|------|------------|
| s001 | 0-3.2s | 标题卡 | ... | 0.9 |

## 可迁移规律
- 快节奏剪辑（每镜<5s）
- 文字主导+配音
- [Agent补充]

## 禁止复制（Mandatory）
- 原视频文案、观点、案例
- 原视频标题、封面

## 数据缺口
- [仅在真正缺失时填写]
```

## 验收

```bash
python -m avs reference validate <ID>
# 期望：reference-recipe.json 通过 Schema
# 期望：状态 = REFERENCE_READY
```
