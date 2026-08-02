# OpenCode 入口

OpenCode 通过用户级 `~/.config/opencode/skills/` 或项目级 `.opencode/skills/` 加载 skill，也可配置 MCP server。

## 配置

### 方式 1：Skill 目录

在 `opencode.json` 中：

```json
{
  "skills": ["/path/to/cut"]
}
```

或软链到 `~/.config/opencode/skills/cut`：

```bash
mkdir -p ~/.config/opencode/skills
ln -s /path/to/cut ~/.config/opencode/skills/cut
```

### 方式 2：MCP Server（推荐）

```json
{
  "mcp": {
    "servers": {
      "cut": {
        "command": "python",
        "args": ["-m", "cut.mcp_server"],
        "env": {
          "PYTHONPATH": "/path/to/cut/skill/scripts"
        }
      }
    }
  }
}
```

## 使用

OpenCode 会自动检测 skill 与 MCP，对话中直接说：

```
> 检测一下我电脑上有什么视频剪辑软件
> 自动做一个 60 秒旅行 vlog，适合抖音
> 帮我在剪映 my_vlog 项目第 5 秒切一刀
> 给视频加个淡入转场
> 导出后帮我做质量检查
```

OpenCode 会自动调用 `cut.list_backends` / `cut.split` / `cut.add_transition`。

## 关键说明

1. **修改前先 get_state**：OpenCode 应该先读取项目状态
2. **--dry-run 预览**：复杂操作先预览
3. **draft 修改后需重启剪映**：用户需在剪映中重新打开项目

## 完整文档

- 主文档：`SKILL.md`
- 剪映 draft schema：`references/jianying-draft-schema.md`
- 剪映操作详解：`references/jianying-operations.md`
- Premiere 操作详解：`references/premiere-operations.md`
- 上下文感知：`references/context-awareness.md`
- 跨平台：`references/cross-platform.md`
- 示例：`examples/*.py`
