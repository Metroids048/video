# 输入说明

每期输入均在 `episodes/active/<ID>/input/` 下。原始输入只读保留，系统只在 `work/prepared/` 创建工作副本。

| 输入 | 目录/文件 | 用途 |
|---|---|---|
| 创意、事实来源、口播要点 | `idea.md` 或其他 `.md/.txt` | 内容简报和脚本的可追溯来源 |
| 本地授权参考视频 | `reference/` | 生成镜头、关键帧与 `reference-recipe.json` |
| 录屏 | `screen/` | 录屏讲解主画面 |
| 图片 | `images/` | 分镜视觉素材和封面候选 |
| 配音、BGM、音效 | `audio/` | 音频时间基准与混音 |
| 链接 | `links.txt` | 来源、权利和待研究记录，不会被自动下载 |

先执行 `python -m avs ingest <ID>` 或 `python -m avs workflow resume <ID>`。损坏文件会被标记，不会进入渲染；横屏素材必须在分镜中明确选择 contain、cover 或布局模板。

`REFERENCE_ADAPT` 只能借鉴结构、节奏和镜头语法，必须替换原文案、素材、案例、数据、标题和封面。无法核实的内容写为“需确认”，不要补造事实。
