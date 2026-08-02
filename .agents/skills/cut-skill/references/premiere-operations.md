# Premiere Pro 操作详解（pymiere）

本文档列出 cut.skill 对 Premiere Pro 的所有操作。

## 前置要求

1. **Premiere Pro 已运行**：pymiere 通过 CEP WebSocket 与 Premiere 通信
2. **已打开项目与序列**：所有操作都基于"当前活动序列"
3. **pymiere 已安装**：`pip install pymiere`
4. **首次连接慢**：第一次调用会有 2-3 秒延迟

## 调用方式

```bash
# CLI
python -m cut.cli get-state --backend premiere
python -m cut.cli import --backend premiere --type video --path /path/to.mp4

# MCP
{"tool": "cut.get_state", "input": {"backend": "premiere"}}

# HTTP
curl http://127.0.0.1:8765/state?backend=premiere

# Python
from cut.premiere import state, materials, timeline, text, effects, audio, export
```

## 1. get-state — 读取状态

```bash
python -m cut.cli get-state --backend premiere
```

返回：
```json
{
  "backend": "premiere",
  "app_version": "24.0",
  "project": {"name": "My Project", "path": "/path/to.prproj"},
  "active_sequence": {
    "name": "Sequence 01",
    "duration_us": 18000000,
    "video_tracks_count": 3,
    "audio_tracks_count": 4
  }
}
```

## 2. list-materials — 列出项目面板素材

```bash
python -m cut.cli list-materials --backend premiere
```

返回项目面板所有素材的列表（含 media_path、duration）。

## 3. get-timeline — 读取时间轴

```bash
python -m cut.cli get-timeline --backend premiere
```

返回当前序列所有视频轨与音频轨的 clip 结构。

## 4. import — 导入素材

```bash
python -m cut.cli import --backend premiere --type video --path /path/to.mp4 --bin "我的素材"
```

- `--bin`：项目面板 bin 名（不存在会创建）
- `--alias`：素材显示名

返回 `project_item_id`，用于后续 `add-segment`（实际 Premiere 直接通过 import + insertClip 完成）。

## 5. add-clip-to-timeline — 加到时间轴

Premiere 中 import 与加到时间轴是分离的。Python 调用：

```python
from cut.premiere import materials
result = materials.import_file("/path/to.mp4")
materials.add_clip_to_timeline(
    project_item_id=result["project_item_id"],
    track_index=0,
    track_type="video",
    start_us=0,
    in_us=0,
    out_us=5_000_000,
    overwrite=True,
)
```

CLI 不直接支持，需用 MCP 或 HTTP：

```bash
curl -X POST http://127.0.0.1:8765/call/cut.import_media \
  -H "Content-Type: application/json" \
  -d '{"backend":"premiere","path":"/path/to.mp4","mtype":"video"}'
```

## 6. split — 切分片段

```bash
python -m cut.cli split --backend premiere \
    --track 0 --track-type video --clip 2 --at 5000000
```

`--track` 是轨道索引，`--clip` 是该轨上 clip 的索引，`--at` 是切点。

注意：Premiere 的 `seq.razor()` 会在**所有轨道**的该时间点切分。如果只想切某一轨，
需要用 QE DOM。

## 7. trim — 调整入出点

```bash
python -m cut.cli trim --backend premiere \
    --track 0 --track-type video --clip 0 \
    --new-start 1000000 --new-end 6000000
```

通过 QE DOM 的 `setInPoint/setOutPoint` 实现。

## 8. add-text — 添加文字

```bash
python -m cut.cli add-text --backend premiere \
    --content "Hello World" --start 0 --duration 3000000 --preset subtitle
```

通过 QE DOM 的 `seq.addText` 创建 Essential Graphics 文字层。

> **限制**：pymiere 对文字样式控制有限，复杂排版请在 Premiere UI 中手动调整。

## 9. add-transition — 添加转场

```bash
python -m cut.cli add-transition --backend premiere \
    --track 0 --clip 0 --preset "Cross Dissolve" --duration 500000
```

`--preset` 必须是 Premiere 内置转场名（英文）：
- `Cross Dissolve`（最常用，对应剪映的 fade）
- `Dip to Black` / `Dip to White`
- `Wipe` / `Slide` / `Push`
- `Zoom` / `Cube Spin` / `Spin`
- `Iris` 系列

用 `cut.premiere.effects.list_transitions()` 查看完整列表。

## 10. add-effect — 添加特效

```bash
python -m cut.cli add-effect --backend premiere \
    --track 0 --clip 0 --preset "Gaussian Blur"
```

`--preset` 是 Premiere 内置特效名，常用：
- `Gaussian Blur`（高斯模糊）
- `Sharpen`（锐化）
- `Black & White`
- `Lumetri Color`（调色，最强大）
- `VR Blur` / `VR Sharpen`
- `Color Balance (RGB)`
- `Brightness & Contrast`
- `Tint`
- `Invert`

用 `cut.premiere.effects.list_video_effects()` 查看完整列表。

## 11. set-audio — 音频操作

```bash
# 设置音量（dB 单位，0=原音量，-6=一半，+6=双倍）
python -m cut.cli set-audio --backend premiere \
    --track 1 --track-type audio --clip 0 --action volume --value -6

# 应用降噪
python -m cut.cli set-audio --backend premiere \
    --track 1 --track-type audio --clip 0 --action effect --preset "DeNoise"
```

常用音频特效：
- `DeNoise`（降噪）
- `Reverb`（混响）
- `Parametric Equalizer`（EQ）
- `Dynamics`（压缩器）
- `Stereo Widener`
- `Bass` / `Treble`
- `Pitch Shifter`

## 12. export — 导出渲染

```bash
python -m cut.cli export --backend premiere \
    --output /path/to/out.mp4 --preset h264_1080p
```

`--preset` 可选值见 `cut.premiere.export.EXPORT_PRESETS`：
- `h264_1080p` / `h264_720p` / `h264_4k`
- `h264_youtube`（YouTube 1080p 预设）
- `h264_match_source`（匹配源）
- `prores_422` / `prores_422_hq`（ProRes）
- `mp3_320` / `wav`

实际导出通过 Adobe Media Encoder 队列渲染。**需 AME 已启动**。

## 13. get-selection — 读取选中

仅 Premiere 支持：

```python
from cut.premiere.state import get_selection
sel = get_selection()
# {"selected_clips": [...], "count": 1}
```

剪映 draft 文件不记录选中状态。

## 14. Python 直接调用

```python
from cut.premiere import state, materials, timeline, effects, audio, export

# 检查连接
state.ensure_connected()

# 读取状态
print(state.get_state())

# 导入并加到时间轴
result = materials.import_file("/path/to/clip.mp4")
materials.add_clip_to_timeline(
    project_item_id=result["project_item_id"],
    track_index=0, track_type="video",
    start_us=0, overwrite=True,
)

# 切分
timeline.split_clip(0, "video", 0, 5_000_000)

# 加转场
effects.add_transition(0, 0, "Cross Dissolve", 500_000)

# 加特效
effects.add_video_effect(0, 0, "Lumetri Color")

# 导出
export.export_to_file("/path/to/out.mp4", preset="h264_1080p")
```

## 14. plan — 一句话生成专业剪辑计划

```bash
python -m cut.cli plan "剪成30分钟影视解说长视频，沉稳电影感" \
    --backend premiere
```

MCP：

```json
{"tool": "cut.create_plan", "input": {
  "backend": "premiere",
  "brief": "剪成30分钟影视解说长视频，沉稳电影感"
}}
```

## 15. qa — 导出后质量验收

```bash
python -m cut.cli qa --output /path/to/out.mp4 --expected-duration 30min
```

MCP：

```json
{"tool": "cut.quality_check", "input": {
  "output": "/path/to/out.mp4",
  "expected_duration_us": 1800000000
}}
```

## 15. 常见问题

### pymiere 连接失败

1. 确认 Premiere 已启动
2. 确认已打开项目（不只是欢迎界面）
3. 确认已打开一个序列（时间轴不为空）
4. macOS 可能需要在"系统设置 → 隐私与安全 → 自动化"中允许 Python 控制 Premiere
5. 检查 pymiere 版本：`pip show pymiere`，建议 ≥ 0.2.0

### QE DOM 不可用

某些操作（如 razor、setInPoint）需要 QE DOM。第一次调用会自动 `app.enableQE()`，
但某些 Premiere 版本可能禁用了 QE。手动启用：
- 编辑 → 首选项 → 常规 → 启用 QE

### 转场/特效名不匹配

Premiere 内置特效名因语言版本而异（中文版用中文名）。
用 `cut.premiere.effects.list_video_effects()` 查询实际可用名。

### 导出超时

长视频渲染超过 1 小时，CLI 可能超时。建议：
- 用 HTTP API（异步）
- 或直接在 AME 中查看队列进度
