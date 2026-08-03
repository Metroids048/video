# Agent Video Studio

Agent Video Studio 将文本、图片、录屏、音频和本地参考视频整理为可人工编辑的竖屏短视频粗稿。输出包含带字幕/无字幕 MP4、SRT、`timeline.json`、素材副本、QA 报告和编辑说明。

它不会自动发布、登录平台、下载第三方视频、生成剪映草稿、克隆声音或伪造内容事实。

## 快速开始

```bash
npm run bootstrap
python -m avs doctor
python -m avs episode create EP-20260730-01 --mode REFERENCE_ADAPT
```

将输入放到 `episodes/active/EP-20260730-01/input/`，再运行：

```bash
python -m avs workflow resume EP-20260730-01
python -m avs workflow next EP-20260730-01 --json
```

工作流会自动执行可确定的步骤，并在内容生成、素材确认和最终编辑处停下。按 `next_action` 的提示完成内容 Skill 和人工审批后再次执行 `workflow resume`。

## 核心命令

```bash
python -m avs workflow status <ID>
python -m avs workflow resume <ID>
python -m avs content validate <ID>
python -m avs content approve <ID>
python -m avs assets approve <ID>
npm run demo
npm run verify
```

详见 [入门指南](docs/getting-started.md)、[输入说明](docs/input-guide.md)、[编辑说明](docs/editing-guide.md)、[排障](docs/troubleshooting.md) 和 [兼容性](docs/compatibility.md)。

账号级内容生产与变现流程见 [AI 产品经理创作者工作流](docs/creator-video-workflow.md)；它支持多个项目共用同一套输入契约、Skill 路由、质量门禁和数据复盘，不把账号绑定在单个量化项目上。
