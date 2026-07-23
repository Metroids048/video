# CLAUDE.md — Agent Video Studio

> Claude Code 入口。本文件引用项目总规则，不重复规则内容。

## 规则与规范

完整规则见 [AGENTS.md](AGENTS.md)，完整规范见 [docs/Agent-Video-Studio-V1.md](docs/Agent-Video-Studio-V1.md)。

**开始任何任务前必须读取：**
1. `AGENTS.md` — 项目总规则（核心约束、状态机、媒体规则、完成报告格式）
2. `docs/Agent-Video-Studio-V1.md` — 项目规范快速参考
3. `tools-manifest.yaml` — 工具版本约束
4. 当前模块的 Prompt（见 `docx/Agent_Video_Studio_V1_逐模块开发_Prompts.md`）

## 业务 CLI

```bash
python -m avs doctor              # 环境诊断
python -m avs episode create <ID> # 创建 Episode
python -m avs episode status <ID>
python -m avs ingest <ID>
python -m avs reference analyze <ID>
python -m avs timeline build <ID>
python -m avs render rough <ID>
python -m avs qa <ID>
python -m avs deliver <ID>
python -m avs run <ID>            # 全流程
```

npm 命令是薄包装，所有业务逻辑在 Python CLI 中实现。

## Subagents

- `content-worker` — 内容生成（脚本、分镜、发布文案）
- `media-worker` — 媒体操作（素材准备、渲染、QA）
- `reviewer` — 只读审计（验证模块交付结果）

## 核心约束（摘要）

1. 原始素材不可变（`input/` 只读）
2. 状态机不可跳过，不可伪造
3. 未运行验证命令，不得声称完成
4. 不自动发布，不存储密钥
5. HyperFrames 失败时必须有 FFmpeg 降级路径
6. 只有 `--force` 可重新生成可再生成产物
