# Codex CLI 入口

本文件由 Codex CLI 自动读取，作为项目级 skill 配置。

## 可用 Skill：cut — 视频剪辑操控

完整文档：`/path/to/cut/SKILL.md`（请用 Read 工具加载）

### 何时使用

当用户的请求涉及以下任一关键词时，**必须**先读取 `SKILL.md`：
- 剪映、CapCut、JianYing
- Premiere、Pr
- 视频剪辑、剪辑、混剪
- 时间轴、轨道、片段
- 字幕、文本、标题
- 转场、特效、调色、LUT
- 音频、混音、降噪、淡入淡出
- 渲染、导出、mp4、mov
- vlog、教学视频、产品演示

### 如何使用

#### 检测环境
```bash
python -m cut.cli detect
python -m cut.cli list-drafts --app jianying
```

#### 读取状态（修改前必做）
```bash
python -m cut.cli get-state --backend jianying --project <name>
python -m cut.cli get-timeline --backend jianying --project <name>
python -m cut.cli list-materials --backend jianying --project <name>
```

#### 一句话专业剪辑计划
```bash
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音" --backend jianying --project <name>
```

#### 编辑操作
```bash
python -m cut.cli import --backend jianying --project <name> --type video --path <path>
python -m cut.cli split --backend jianying --project <name> --track 0 --at <time>
python -m cut.cli trim --backend jianying --project <name> --track 0 --clip 0 --new-start <t> --new-end <t>
python -m cut.cli add-text --backend jianying --project <name> --content "Hello" --start 0 --duration 3000000
python -m cut.cli add-transition --backend jianying --project <name> --track 0 --clip 0 --preset fade
python -m cut.cli add-effect --backend jianying --project <name> --track 0 --clip 0 --preset vignette
python -m cut.cli set-audio --backend jianying --project <name> --track 1 --clip 0 --action volume --value 0.5
```

#### 导出
```bash
python -m cut.cli export --backend jianying --project <name> --output out.mp4 --method ffmpeg
python -m cut.cli qa --output out.mp4 --expected-duration 60s
```

### 时间格式

所有时间参数支持：
- 微秒整数：`1500000`
- 带后缀：`1.5s` / `1500ms` / `1500000us`
- HH:MM:SS.mmm：`00:00:01.500`

### 安全规则

1. 修改前先 `get-state` 了解项目结构
2. 重要操作先 `--dry-run` 预览
3. 剪映 draft 修改后需用户在剪映中重新打开项目才生效
4. 永远不要硬编码路径，用 `detect` 找

### 复杂场景

复杂批量操作用 Python 直接调用：
```python
from cut.jianying.draft import Draft
from cut.jianying import materials, segments, text, effects

draft = Draft.open(project_name="<name>")
# 批量操作...
draft.save()
```

完整示例见 `examples/` 目录。

### 参考文档

需要深度了解时按需加载：
- `references/jianying-draft-schema.md` — draft 文件结构
- `references/jianying-operations.md` — 剪映所有操作详解
- `references/premiere-operations.md` — Premiere 操作详解
- `references/context-awareness.md` — 上下文感知
- `references/cross-platform.md` — 跨平台差异
