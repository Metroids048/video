# GLM Code 入口

GLM Code（智谱 AI Code）原生支持 skill 系统，`cut.skill` 可直接作为 skill 包加载。

## 配置

### 方式 1：Skill 目录（推荐）

把 `cut/` 目录放到：
- 项目级：`./skills/cut/`
- 用户级：`~/.glm/skills/cut/`

或软链：
```bash
# 用户级
mkdir -p ~/.glm/skills
ln -s /path/to/cut ~/.glm/skills/cut

# 项目级
mkdir -p skills
ln -s /path/to/cut skills/cut
```

GLM 会自动扫描 `skills/` 目录，读 `SKILL.md` 的 frontmatter（`name` + `description`）触发。

### 方式 2：MCP Server

GLM Code 也支持 MCP：

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

### 方式 3：HTTP API（长任务推荐）

```bash
# 启动服务
python -m cut.http_api --port 8765
```

GLM 通过 HTTP 调用：
```
GET  http://127.0.0.1:8765/state?backend=jianying&project=my_vlog
POST http://127.0.0.1:8765/split  {"backend":"jianying","project":"my_vlog","track_index":0,"at_us":5000000}
```

## 触发关键词

GLM 根据 `SKILL.md` 的 `description` 字段自动触发。本 skill 已包含以下触发词：

- 剪映、CapCut、JianYing
- Premiere、Pr、视频剪辑
- 时间轴、轨道、片段
- 字幕、转场、特效、调色
- 混音、渲染导出
- vlog、教学视频

## 使用示例

直接对话：

```
> 检测一下我电脑上有什么视频剪辑软件
> 帮我在剪映里给视频加字幕
> 让 Premiere 把这几个素材按顺序排到时间轴上
> 读取一下我剪映里现在有什么素材
> 自动做个 vlog 混剪
```

GLM 会自动调用 `cut.list_backends` / `cut.get_state` / `cut.add_text` 等工具。

## 推荐工作流

GLM 调用 cut.skill 的标准 4 步流程：

```text
1. detect           → 检测环境与可用后端
2. get_state        → 读取当前项目状态（必做，上下文感知）
3. <编辑动作>        → import / split / trim / text / transition / effect / audio
4. export           → 触发渲染输出
```

**第 2 步是关键**：GLM 在做任何修改前，应先调一次 `cut.get_state` 或对应 CLI，
把当前项目快照读进来，再决定下一步。盲目修改 draft 文件很容易让剪映加载失败。

## 调用方式

### CLI（最常用）

```bash
python -m cut.cli detect
python -m cut.cli get-state --backend jianying --project my_vlog
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音" --backend jianying --project my_vlog
python -m cut.cli split --backend jianying --project my_vlog --track 0 --at 5s
python -m cut.cli add-text --backend jianying --project my_vlog --content "Hello" --start 0 --duration 3000000
python -m cut.cli qa --output out.mp4 --expected-duration 60s
```

### Python 直接调用（复杂批量操作）

```python
from cut.jianying.draft import Draft
from cut.jianying import materials, segments, text, effects, audio

draft = Draft.open(project_name="my_vlog")

# 导入视频
mid = materials.import_video(draft, "/path/to/clip.mp4")
sid = materials.add_video_segment(draft, mid, start_us=0, duration_us=5_000_000)

# 切分
seg = draft.video_tracks[0].segments[0]
segments.split_segment(draft, seg, at_us=2_500_000)

# 加字幕
text.add_subtitle(draft, "Hello World", start_us=0, duration_us=3_000_000)

# 加转场
effects.add_transition_simple(draft, draft.video_tracks[0].id, 0, preset="fade")

# 保存（自动备份 .bak）
draft.save()
print("完成。请在剪映中重新打开项目查看。")
```

## 关键规则

1. **修改前先 get_state**：了解项目当前结构
2. **复杂操作用 --dry-run**：先预览不写文件
3. **告诉用户重启剪映**：draft 修改后需重新打开项目
4. **永远不要硬编码路径**：用 `detect` 找

## 完整文档

- 主文档：`SKILL.md`
- 剪映 draft schema：`references/jianying-draft-schema.md`
- 剪映操作详解：`references/jianying-operations.md`
- Premiere 操作详解：`references/premiere-operations.md`
- 上下文感知：`references/context-awareness.md`
- 跨平台：`references/cross-platform.md`
- Agent 集成（含 GLM 配置）：`references/agent-integration.md`
- 示例：`examples/*.py`
