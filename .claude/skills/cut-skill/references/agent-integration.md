# Agent 集成指南

cut.skill 设计为通用兼容，支持所有主流 agent 工具：
- **Codex CLI** (OpenAI)
- **Claude Code** (Anthropic)
- **OpenCode** (开源)
- **Kimi Code** (Moonshot)
- **Qwen Code** (阿里通义)
- **GLM Code** (智谱)
- **任何支持 MCP 或 shell 的 agent**

每家 agent 的 skill 加载机制不同，本文档给出最小配置示例。

---

## 通用准备

不论用哪家 agent，都需要：

```bash
# 1. 安装 Python 依赖
cd /path/to/cut/skill/scripts
pip install -r requirements.txt

# 2. 把 cut 包放到 Python 路径
# 方式 A：pip install -e .  （如果有 setup.py）
# 方式 B：export PYTHONPATH=/path/to/cut/skill/scripts
# 方式 C：把 scripts/ 目录加到 site-packages

# 3. 验证
python -m cut.cli detect
```

---

## 1. Codex CLI

Codex 读取项目级 `.agents/skills/<name>/SKILL.md` 或用户级 `~/.agents/skills/<name>/SKILL.md`，并可使用 `agents/openai.yaml` 元数据。

### 配置

在项目根目录创建 `AGENTS.md`：

```markdown
# Agents

## 可用 Skills

### cut — 视频剪辑操控

读取 `/path/to/cut/SKILL.md` 获取完整说明。

#### 何时使用
当用户提到剪映、CapCut、Premiere、视频剪辑、字幕、转场、特效、
导出渲染等需求时。

#### 如何使用
优先用 CLI：
```bash
python -m cut.cli detect
python -m cut.cli get-state --backend jianying --project <name>
python -m cut.cli split --backend jianying --project <name> --track 0 --at <time>
```

复杂场景用 Python 直接调用：
```python
from cut.jianying.draft import Draft
from cut.jianying import segments
draft = Draft.open(project_name="<name>")
# ...
draft.save()
```
```

或者把 `cut/SKILL.md` 软链到 `.agents/skills/cut/SKILL.md`：

```bash
mkdir -p .agents/skills
ln -s /path/to/cut .agents/skills/cut
```

### 使用

在 Codex CLI 中直接对话：
```
> 帮我把剪映里的 my_vlog 项目第 2 个视频切两半
```
Codex 会读 `AGENTS.md` → 找到 cut skill → 调用 CLI 完成。

---

## 2. Claude Code

Claude Code 读取 `.claude/skills/<name>/SKILL.md`。

### 配置

```bash
mkdir -p .claude/skills
cp -r /path/to/cut .claude/skills/cut
# 或软链
ln -s /path/to/cut .claude/skills/cut
```

`.claude/skills/cut/SKILL.md` 即本 skill 主文档。

### 使用 MCP（推荐）

Claude Desktop / Claude Code 原生支持 MCP。在配置文件中添加：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cut": {
      "command": "python",
      "args": ["-m", "cut.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/cut/skill/scripts"
      }
    }
  }
}
```

重启 Claude Desktop 后，可在对话中直接说：
> "用 cut 工具读取我的剪映项目状态"

Claude 会自动 `tool_call` `cut.get_state`。

---

## 3. OpenCode

OpenCode 是开源终端 agent，支持 skill 与 MCP。

### 配置 skill

在 `opencode.json` 中：

```json
{
  "skills": [
    "/path/to/cut"
  ]
}
```

或把 `cut/` 目录放到用户级 `~/.config/opencode/skills/`，或项目级 `.opencode/skills/`。

### 配置 MCP

```json
{
  "mcp": {
    "servers": {
      "cut": {
        "command": "python",
        "args": ["-m", "cut.mcp_server"],
        "env": {"PYTHONPATH": "/path/to/cut/skill/scripts"}
      }
    }
  }
}
```

### 使用

OpenCode 会自动检测 skill 与 MCP，对话中直接说：
> "用剪映把这段视频剪一下"

---

## 4. Kimi Code

Kimi Code (Moonshot) 可使用 `~/.kimi/skills.yaml` 配置。

### 配置

在 `~/.kimi/skills.yaml` 中：

```yaml
skills:
  - name: cut
    path: /path/to/cut
    description: 视频剪辑操控（剪映 + Premiere）
    triggers:
      - 剪映
      - CapCut
      - Premiere
      - 视频剪辑
      - 字幕
      - 转场
      - 特效
      - 渲染导出
    entry: SKILL.md
```

### MCP 配置

Kimi Code 也支持 MCP：

```yaml
mcp_servers:
  - name: cut
    command: python
    args: ["-m", "cut.mcp_server"]
    env:
      PYTHONPATH: /path/to/cut/skill/scripts
```

---

## 5. Qwen Code

Qwen Code (阿里通义) 可扫描 `~/.qwen/skills/` 或项目级 `.qwen/skills/`。

### 配置

创建目录或软链：

```bash
mkdir -p ~/.qwen/skills
ln -s /path/to/cut ~/.qwen/skills/cut
```

### MCP 配置

```json
{
  "mcp_servers": {
    "cut": {
      "command": "python",
      "args": ["-m", "cut.mcp_server"],
      "env": {"PYTHONPATH": "/path/to/cut/skill/scripts"}
    }
  }
}
```

---

## 6. GLM Code

GLM Code (智谱) 原生支持 skill 系统，`cut.skill` 可直接作为 skill 包加载。

### 配置

把 `cut/` 目录放到：
- 项目级：`./skills/cut/`
- 用户级：`~/.glm/skills/cut/`

或软链：
```bash
ln -s /path/to/cut ~/.glm/skills/cut
```

GLM 会自动扫描 `skills/` 目录，读 `SKILL.md` 的 frontmatter 触发。

### 使用

直接对话：
> "帮我在剪映里给视频加字幕"

GLM 会根据 `cut.skill` 的 description 自动触发。

---

## 7. 通用兼容方案

如果你的 agent 不在上述列表中，但支持以下任一方式，都可以用 cut.skill：

### 方案 A：shell 调用

把 `cut/SKILL.md` 内容作为 system prompt 注入，agent 通过 shell 调用 CLI。

### 方案 B：MCP

任何支持 MCP 的 agent 都可以连接：

```json
{
  "mcpServers": {
    "cut": {
      "command": "python",
      "args": ["-m", "cut.mcp_server"],
      "env": {"PYTHONPATH": "/path/to/cut/skill/scripts"}
    }
  }
}
```

### 方案 C：HTTP API

启动 HTTP 服务：
```bash
python -m cut.http_api --port 8765
```

agent 通过 HTTP 调用：
```
GET  http://127.0.0.1:8765/state?backend=jianying&project=my_vlog
POST http://127.0.0.1:8765/split  {"backend":"jianying","project":"my_vlog","track":0,"at_us":5000000}
```

---

## 8. 安装路径建议

把 cut.skill 放在固定位置，方便多家 agent 共享：

```bash
# 推荐：放在用户目录
mkdir -p ~/.skills
cp -r cut ~/.skills/cut

# 然后各家 agent 配置中引用
# Codex:    ln -s ~/.skills/cut .agents/skills/cut
# Claude:   ln -s ~/.skills/cut .claude/skills/cut
# GLM:      ln -s ~/.skills/cut ~/.glm/skills/cut
# Kimi:     path: ~/.skills/cut
# Qwen:     path: ~/.skills/cut
# OpenCode: skills: ["~/.skills/cut"]
```

---

## 9. 验证安装

每家 agent 配置完后，用同一句话测试：

> "检测一下我电脑上有什么视频剪辑软件"

正确响应：调用 CLI `detect` 或 MCP `cut.list_backends`，返回剪映/Premiere 安装情况。

如果 agent 没有触发 cut skill：
1. 检查 skill 路径是否正确
2. 检查 `SKILL.md` 的 `description` 是否包含触发词
3. 检查 PYTHONPATH 是否能 `import cut`
4. 手动验证：`python -m cut.cli detect`

---

## 10. 调试

### skill 未触发

各家的触发机制不同：
- **Codex/Claude/OpenCode**：靠 description 关键词匹配
- **GLM**：靠 description + 路径扫描
- **Kimi/Qwen**：靠 `triggers` 字段

确认 description 包含足够多的触发词。本 skill 的 description 已包含：
"剪映、CapCut、JianYing、Premiere、Pr、视频剪辑、时间轴、轨道、片段、字幕、转场、调色、混音、渲染导出"

### MCP 连接失败

```bash
# 手动测试 MCP server
python -m cut.mcp_server
# 应该等待 stdio 输入，不报错
```

### CLI 找不到 cut 模块

```bash
# 检查 PYTHONPATH
echo $PYTHONPATH

# 或安装为可执行
cd /path/to/cut/skill/scripts
pip install -e .
# 之后可直接 cut-cli detect
```

---

## 11. 一键安装脚本

```bash
#!/bin/bash
# install.sh — 一键配置多家 agent

CUT_SKILL_DIR="${1:-$HOME/.skills/cut}"

# 1. 复制 skill
mkdir -p ~/.skills
cp -r . "$CUT_SKILL_DIR"

# 2. 安装 Python 依赖
cd "$CUT_SKILL_DIR/scripts"
pip install -r requirements.txt

# 3. 配置各家 agent
# Codex
mkdir -p .agents/skills && ln -sf "$CUT_SKILL_DIR" .agents/skills/cut

# Claude Code
mkdir -p .claude/skills && ln -sf "$CUT_SKILL_DIR" .claude/skills/cut

# GLM
mkdir -p ~/.glm/skills && ln -sf "$CUT_SKILL_DIR" ~/.glm/skills/cut

# Kimi
mkdir -p ~/.kimi
cat >> ~/.kimi/skills.yaml <<EOF
skills:
  - name: cut
    path: $CUT_SKILL_DIR
    description: 视频剪辑操控（剪映 + Premiere）
    triggers: [剪映, CapCut, Premiere, 视频剪辑, 字幕, 转场, 特效]
    entry: SKILL.md
EOF

# Qwen
mkdir -p ~/.qwen/skills
ln -sf "$CUT_SKILL_DIR" ~/.qwen/skills/cut

# 4. 验证
PYTHONPATH="$CUT_SKILL_DIR/scripts" python -m cut.cli detect

echo "✓ cut.skill 已配置到所有支持的 agent"
```
