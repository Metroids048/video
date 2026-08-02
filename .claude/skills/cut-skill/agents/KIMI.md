# Kimi Code 入口

Kimi Code 通过 `~/.kimi/skills.yaml` 加载 skill。

## 配置

### 方式 1：Skill

```yaml
# ~/.kimi/skills.yaml
skills:
  - name: cut
    path: /path/to/cut
    description: 视频剪辑操控（剪映 + Premiere）
    triggers:
      - 剪映
      - CapCut
      - JianYing
      - Premiere
      - Pr
      - 视频剪辑
      - 时间轴
      - 轨道
      - 片段
      - 字幕
      - 转场
      - 特效
      - 调色
      - 混音
      - 渲染导出
      - vlog
      - 教学视频
    entry: SKILL.md
```

### 方式 2：MCP Server

```yaml
mcp_servers:
  - name: cut
    command: python
    args: ["-m", "cut.mcp_server"]
    env:
      PYTHONPATH: /path/to/cut/skill/scripts
```

## 使用

Kimi Code 会根据 triggers 自动触发。对话中：

```
> 帮我把剪映里的项目剪一下
> 给视频加字幕
> 让 Premiere 把这几个素材按顺序排到时间轴上
```

## 调用方式

### CLI（推荐）

```bash
python -m cut.cli detect
python -m cut.cli get-state --backend jianying --project my_vlog
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音" --backend jianying --project my_vlog
python -m cut.cli split --backend jianying --project my_vlog --track 0 --at 5s
python -m cut.cli qa --output out.mp4 --expected-duration 60s
```

### Python

```python
from cut.jianying.draft import Draft
from cut.jianying import segments, text

draft = Draft.open(project_name="my_vlog")
segments.split_segment(draft, draft.video_tracks[0].segments[0], at_us=5_000_000)
draft.save()
```

## 关键规则

1. **修改前先 get_state**
2. **复杂操作用 --dry-run**
3. **告诉用户重启剪映**：draft 修改后需重新打开项目

## 完整文档

- 主文档：`SKILL.md`
- 剪映 draft schema：`references/jianying-draft-schema.md`
- 剪映操作详解：`references/jianying-operations.md`
- Premiere 操作详解：`references/premiere-operations.md`
- 上下文感知：`references/context-awareness.md`
- 跨平台：`references/cross-platform.md`
- 示例：`examples/*.py`
