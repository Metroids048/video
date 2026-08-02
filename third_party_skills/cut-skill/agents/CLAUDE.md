# Claude Code 入口

把本文件内容复制到 `.claude/skills/cut/SKILL.md`，或把整个 `cut/` 目录软链到 `.claude/skills/cut/`。

## Skill: cut — 视频剪辑操控

让 Claude 通过 CLI、MCP 或直接 Python 调用操控剪映与 Premiere Pro。

### 触发条件

用户提到以下任一关键词时使用本 skill：
- 剪映、CapCut、JianYing
- Premiere、Pr、视频剪辑
- 字幕、转场、特效、调色
- 渲染、导出、mp4

### 推荐调用方式

#### 1. MCP（首选）

如果已配置 MCP server，Claude 会自动 `tool_call`：

```json
{"tool": "cut.get_state", "input": {"backend": "jianying", "project": "my_vlog"}}
```

完整工具列表见 `SKILL.md` 第 7 节。

#### 2. CLI

```bash
python -m cut.cli detect
python -m cut.cli get-state --backend jianying --project my_vlog
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音" --backend jianying --project my_vlog
python -m cut.cli split --backend jianying --project my_vlog --track 0 --at 5s
python -m cut.cli qa --output out.mp4 --expected-duration 60s
```

#### 3. Python 直接调用

复杂批量操作时：
```python
from cut.jianying.draft import Draft
from cut.jianying import segments, text
draft = Draft.open(project_name="my_vlog")
# ...
draft.save()
```

### 关键规则

1. **修改前先 get_state**：了解项目结构
2. **使用 --dry-run 预览**：复杂操作先看影响
3. **告诉用户重启剪映**：draft 修改后需重新打开项目
4. **备份默认开启**：`Draft.save()` 自动备份 .bak

### 完整文档

- 主文档：`SKILL.md`
- 剪映 draft schema：`references/jianying-draft-schema.md`
- 剪映操作详解：`references/jianying-operations.md`
- Premiere 操作详解：`references/premiere-operations.md`
- 上下文感知：`references/context-awareness.md`
- 跨平台：`references/cross-platform.md`
- 示例：`examples/*.py`
