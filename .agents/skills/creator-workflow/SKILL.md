---
trigger: "需要把一个项目想法、真实项目进展或参考视频变成有变现假设的内容；需要续跑账号级视频生产流程"
inputs:
  - "一个具体问题、冲突或项目节点"
  - "至少一个可核实事实来源和公开边界"
  - "可选：本地授权参考视频、录屏、截图、语音、链接或发布数据"
read_only:
  - "AGENTS.md"
  - "config/creator-workflow.yaml"
  - "docs/creator-video-workflow.md"
  - "docs/video-plugin-routing.md"
  - "episode.json"
  - "episodes/active/<ID>/input/"
outputs:
  - "不创建第二套状态；账号规则来自 config/creator-workflow.yaml"
  - "每条内容回挂 Episode 的 content、timeline、qa、delivery 和 publish 产物"
  - "选题契约、事实边界、变现假设、脚本、分镜、素材清单、MP4、SRT、QA 和复盘记录"
run: |
  python -m avs workflow resume <ID>
verify: |
  python -m avs workflow status <ID> --json
  python -m avs content validate <ID>
stop_when: |
  workflow status 的 next_action.kind 为 agent、human、input、recovery 或 complete。
  没有真实事实来源、公开边界、必要素材或人工批准时不得宣称完成。
on_missing_input: |
  缺少问题或事实时停在 WAITING_FOR_INPUT；缺少授权本地参考片时只能做原创或结构级研究。
  缺少配音、音乐授权、视觉 Provider 或用户批准时标记 BLOCKED，并列出可行替代方案。
report_format: |
  - 账号定位与本条内容主行为
  - 输入证据等级与事实边界
  - 选用的第三方 Skill 及原因
  - Episode ID、当前状态、下一步和所需产物
  - QA、人工批准、交付和变现假设

# creator-workflow

这是账号级入口，不替代 `episode.json` 状态机，也不直接剪辑。

## 执行顺序

1. 读取 `config/creator-workflow.yaml`，把本条内容写成一个选题契约：问题、主行为、赌注、成功信号和下一步承诺。
2. 如果用户给了本地参考视频，先调用 `analyze-reference`，读取 `reference-recipe.json`、联系表、关键帧和转写；`video-shotcraft` 只作镜头/节奏/声音参考，标注置信度。
3. 如果只有参考链接，只记录来源和页面可见线索；禁止声称完整看过、下载或逐帧复刻。
4. 调用 `ip-strategist` 选择系列角度和变现假设，但不让它替代事实核验或后期剪辑。
5. 依次使用 `write-video-script`、`create-storyboard`、`prepare-assets`，生成 brief、脚本、分镜和缺口清单；每段脚本必须有 `source_refs`。
6. 按 `docs/video-plugin-routing.md` 选择渲染能力：默认 `ffmpeg` + `hyperframes`；Remotion、CapCut、JianyingEditor、ChatCut、OpenMontage、MoneyPrinterTurbo、Pixelle-Video 只能在场景匹配且产物回挂 Episode 时启用。
7. 使用 `quality-review` 完成确定性 QA、语义视觉审核和事实边界检查。失败时回到最上游问题修正，不用无关动画遮盖内容缺口。
8. 用户完整播放并批准后，再调用 `create-publish-pack`；发布必须人工完成，数据回传后由 `ip-strategist` 只做有证据的批次复盘。

## 输入质量优先级

最少但有效的输入是：一个具体问题 + 一个事实来源 + 一个公开边界。输入越接近真实项目证据，输出越能做成“项目过程”而不是泛泛 AI 资讯。没有证据时必须把内容降级为观点/实验假设，不能伪造案例。
