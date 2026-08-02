# 剪映操作详解

本文档列出 cut.skill 对剪映的所有操作，每个操作的参数、返回值、示例。

所有操作都通过以下方式调用：
- CLI: `python -m cut.cli <command> --backend jianying --project <name> [options]`
- MCP: `cut.<command>` tool_call
- HTTP: `POST /call/cut.<command>` 或便捷端点
- Python: `from cut.jianying import <module>; <module>.<func>(draft, ...)`

## 通用参数

| 参数 | 说明 |
|---|---|
| `--backend jianying` 或 `capcut` | 选择后端 |
| `--project NAME` | 项目名（自动从 drafts_dir 查找） |
| `--dir PATH` | 项目目录绝对路径（优先于 --project） |
| `--dry-run` | 仅打印将要做的操作，不实际写文件 |
| `--json` | 输出 JSON（agent 友好） |

## 时间格式

所有时间参数支持三种格式：
- **微秒整数**：`1500000`（=1.5s）
- **带后缀**：`1.5s` / `1500ms` / `1500000us`
- **HH:MM:SS.mmm**：`00:00:01.500`

---

## 1. detect — 环境检测

```bash
python -m cut.cli detect
```

返回本机剪映/CapCut/Premiere 安装情况与版本。

## 2. list-drafts — 列出剪映项目

```bash
python -m cut.cli list-drafts --app jianying
```

返回所有剪映项目（按修改时间倒序）。

## 3. get-state — 读取项目状态

```bash
python -m cut.cli get-state --backend jianying --project my_vlog
```

返回：
```json
{
  "backend": "jianying",
  "project_name": "my_vlog",
  "duration_us": 18000000,
  "duration_hms": "00:00:18.000",
  "canvas": {"width": 1920, "height": 1080},
  "tracks": [
    {"id": "...", "type": "video", "segments_count": 5, "first_start_us": 0, "last_end_us": 18000000}
  ],
  "materials": {"videos": 5, "audios": 1, "images": 0, "texts": 3, ...}
}
```

**修改前必先调用**，了解当前项目结构。

## 4. list-materials — 列出素材

```bash
python -m cut.cli list-materials --backend jianying --project my_vlog --type video
```

`--type` 可选：video/audio/image/sticker/text/effect。不指定则返回全部。

## 5. get-timeline — 读取时间轴

```bash
python -m cut.cli get-timeline --backend jianying --project my_vlog
```

返回完整时间轴结构（所有 track 与 segment 的扁平数组）。

## 6. import — 导入素材

```bash
python -m cut.cli import --backend jianying --project my_vlog \
    --type video --path /path/to/clip.mp4 --alias "片头"
```

`--type` 必填：video/audio/image。
图片需要额外指定 `--duration`（默认 5s）。

返回 `material_id`。注意：导入后素材在素材池，**还没放到时间轴**。
要放到时间轴用 `add-segment`。

## 7. add-segment — 把素材加到时间轴

```bash
python -m cut.cli add-segment --backend jianying --project my_vlog \
    --material-id abc123 --track-type video --start 0 --duration 5000000
```

参数：
- `--material-id`：import 返回的 ID
- `--track-type`：video/audio
- `--track`：track ID（不指定自动选/创建）
- `--start`：时间轴起点
- `--source-in`：素材内部入点（默认 0）
- `--duration`：片段时长（不指定用素材全时长）

## 8. split — 切分片段

```bash
# 在第 0 个轨道的 5s 处切分
python -m cut.cli split --backend jianying --project my_vlog \
    --track 0 --at 00:00:05.000

# 在第 0 个轨道的第 2 个 clip 的 5s 处切分（仅切这一个 clip）
python -m cut.cli split --backend jianying --project my_vlog \
    --track 0 --clip 2 --at 5000000
```

不指定 `--clip` 时切分所有跨过该时间点的 segment。

## 9. trim — 调整入出点

```bash
python -m cut.cli trim --backend jianying --project my_vlog \
    --track 0 --clip 0 --new-start 1000000 --new-end 6000000
```

`--new-start` / `--new-end` 是时间轴绝对坐标。Source 入点会同步调整。

## 10. add-text — 添加文字

```bash
python -m cut.cli add-text --backend jianying --project my_vlog \
    --content "Hello World" --start 0 --duration 3000000 \
    --preset subtitle --style '{"text_color":"#FF0000"}'
```

`--preset`：
- `subtitle`（默认）：屏幕底部，半透明黑底，小字
- `title`：屏幕中上方，大字

`--style` 是 JSON 字符串，可覆盖预设样式：
```json
{
  "text_color": "#FF0000",
  "text_size": 60,
  "background_alpha": 0.8,
  "position_x": 0.0,
  "position_y": -0.3
}
```

## 11. add-transition — 添加转场

```bash
python -m cut.cli add-transition --backend jianying --project my_vlog \
    --track 0 --clip 0 --preset fade --duration 500000
```

`--clip` 指定在 clip 0 与 clip 1 之间加转场。

`--preset` 可选值见 `cut.jianying.effects.TRANSITION_PRESETS`：
- `fade`（淡入淡出，最常用）
- `slide_left/right/up/down`
- `zoom_in/out`
- `rotate` / `blur` / `flash` / `glitch` / `whip_pan`

## 12. add-effect — 添加特效

```bash
python -m cut.cli add-effect --backend jianying --project my_vlog \
    --track 0 --clip 1 --preset vignette --intensity 0.8
```

`--preset` 可选值见 `cut.jianying.effects.EFFECT_PRESETS`：
- `vignette`（暗角）
- `sharpen`（锐化）
- `blur` / `glow` / `noise` / `mirror`
- `vhs` / `film_grain` / `color_correction`

`--intensity` 0-1+，默认 1.0。

## 13. set-audio — 音频操作

```bash
# 设置音量
python -m cut.cli set-audio --backend jianying --project my_vlog \
    --track 1 --clip 0 --action volume --value 0.5

# 淡入
python -m cut.cli set-audio --backend jianying --project my_vlog \
    --track 1 --clip 0 --action fade_in --duration 500000

# 应用降噪
python -m cut.cli set-audio --backend jianying --project my_vlog \
    --track 1 --clip 0 --action effect --preset denoise
```

`--action`：
- `volume`：调音量，`--value 0-1+`（0=静音，1=原音，2=双倍）
- `fade_in` / `fade_out`：淡入淡出，`--duration` 默认 0.5s
- `effect`：应用音频特效，`--preset` 见下

`--preset` 可选值见 `cut.jianying.audio.AUDIO_EFFECT_PRESETS`：
- `denoise` / `denoise_strong`
- `reverb_room/hall/church`
- `pitch_up/down`
- `compressor` / `equalizer`
- `vocal_remove`（人声消除）

## 14. export — 导出渲染

```bash
# 用 ffmpeg 直接合成（仅简单场景，无特效/字幕）
python -m cut.cli export --backend jianying --project my_vlog \
    --output /path/to/out.mp4 --method ffmpeg

# 用 UI 自动化（需剪映打开，支持所有特效）
python -m cut.cli export --backend jianying --project my_vlog \
    --output /path/to/out.mp4 --method ui
```

`--method`：
- `ffmpeg`（默认）：直接根据 draft 合成，仅支持单轨简单拼接，**不支持转场/特效/字幕**
- `ui`：通过 pyautogui 点击剪映导出按钮，需剪映已打开，**支持所有特性但脆弱**

> 剪映没有命令行导出 API。复杂项目建议用 `ui` 方法或让用户在剪映中手动导出。

## 15. plan — 一句话生成专业剪辑计划

```bash
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音，节奏轻快" \
    --backend jianying --project my_vlog \
    --asset /path/to/clip.mp4 \
    --asset /path/to/bgm.mp3
```

返回 `format`、`target_platform`、`target_duration_us`、`style`、`story_structure` 与 `steps`。
agent 应先读计划，再执行具体的 import/split/text/audio/effect/export 动作。

MCP：

```json
{"tool": "cut.create_plan", "input": {
  "backend": "jianying",
  "project": "my_vlog",
  "brief": "自动做一个60秒旅行vlog，适合抖音"
}}
```

## 16. qa — 导出后质量验收

```bash
python -m cut.cli qa --output /path/to/out.mp4 --expected-duration 60s
```

MCP：

```json
{"tool": "cut.quality_check", "input": {
  "output": "/path/to/out.mp4",
  "expected_duration_us": 60000000
}}
```

QA 会检查 ffprobe 可读性、时长、码率、视频/音频流、分辨率和帧率。

## 17. Python 直接调用

```python
from cut.jianying.draft import Draft
from cut.jianying import materials, segments, text, effects, audio, export

# 打开项目（自动备份）
draft = Draft.open(project_name="my_vlog")

# 读取状态
print(draft.to_summary())

# 导入视频
mid = materials.import_video(draft, "/path/to/clip.mp4")

# 加到时间轴
sid = materials.add_video_segment(draft, mid, start_us=0, duration_us=5_000_000)

# 在 2.5s 处切分
seg = draft.video_tracks[0].segments[0]
left, right = segments.split_segment(draft, seg, at_us=2_500_000)

# 加字幕
text.add_subtitle(draft, "Hello World", start_us=0, duration_us=3_000_000)

# 在前两段间加转场
effects.add_transition_simple(draft, draft.video_tracks[0].id, 0, preset="fade")

# 给第一个视频加暗角
effects.add_video_effect(draft, draft.video_tracks[0].segments[0].id, preset="vignette")

# 保存
draft.save()
print("完成。请在剪映中重新打开项目查看。")
```

## 18. 错误处理

| 错误 | 原因 | 解决 |
|---|---|---|
| `FileNotFoundError` | 项目不存在 | 检查 `--project` 名或用 `list-drafts` 查看 |
| `DraftError` | draft 文件解析失败 | 用 `.bak` 恢复，或检查 JSON 合法性 |
| `UnsupportedSchemaError` | 剪映版本不兼容 | 升级 skill 或固定剪映版本 |
| `KeyError: material_id` | 引用了不存在的素材 | 检查 `import` 返回的 ID |
| `IndexError: track_index` | 轨道索引越界 | 先 `get-state` 查看轨道数 |
| `ValueError: 切点不在片段内` | `--at` 不在 segment 范围 | 先 `get-timeline` 查看片段范围 |

## 19. 最佳实践

1. **修改前先 get-state**：了解项目当前结构
2. **用 --dry-run 预览**：复杂操作先看会不会改坏
3. **批量操作合并 save**：每次 `draft.save()` 都会写盘，多操作应一次性做完再 save
4. **保留 .bak**：skill 默认会备份，但重要项目建议手动多备一份
5. **修改后重启剪映**：剪映不热加载，需要关闭项目重新打开
6. **避免空 track**：剪映对空 track 容错差，没用的 track 应删掉
