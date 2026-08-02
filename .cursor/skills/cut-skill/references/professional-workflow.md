# 专业剪辑工作流

本参考用于用户只给一句话、但期望 agent 自动完成长视频或短视频剪辑时。

## 标准流程

1. `detect`：确认本机可用后端。
2. `get-state`：读取项目当前状态，任何写操作前必做。
3. `plan` / `cut.create_plan`：把一句话需求转成剪辑计划。
4. 执行计划中的剪辑动作：导入素材、粗剪、字幕、转场、混音、调色。
5. `export`：用目标后端导出。
6. `qa` / `cut.quality_check`：验收导出文件。

## 计划层职责

`cut.director.create_edit_plan()` 会识别：

| 字段 | 说明 |
|---|---|
| `format` | `short_form` 或 `long_form` |
| `target_platform` | douyin/tiktok/xiaohongshu/kuaishou/youtube/bilibili/generic |
| `target_duration_us` | 目标时长 |
| `style` | 节奏、转场策略、调色、字幕和混音策略 |
| `story_structure` | hook/setup/development/turning_point/payoff |
| `steps` | 具体执行步骤 |

计划层是确定性剪辑助理，不做真正视觉理解。若要达到更高质量，应先用 ASR、镜头检测、节拍检测或人工标签给素材增加元数据，再把这些资产信息传入 `assets`。

## CLI 示例

```bash
python -m cut.cli plan "自动做一个60秒旅行vlog，适合抖音，节奏轻快" \
  --backend jianying --project my_vlog \
  --asset D:\footage\a.mp4 \
  --asset D:\music\bgm.mp3
```

## MCP 示例

```json
{
  "tool": "cut.create_plan",
  "input": {
    "backend": "jianying",
    "project": "my_vlog",
    "brief": "剪成30分钟影视解说长视频，沉稳电影感",
    "assets": [
      {"path": "a.mp4", "duration_us": 600000000, "type": "video"},
      {"path": "voice.wav", "duration_us": 1800000000, "type": "audio", "role": "voice"}
    ]
  }
}
```

## 导出 QA

QA 检查项：

- 文件是否能被 ffprobe 读取
- 时长是否接近期望值
- 视频流是否存在
- 音频流是否存在
- 码率是否低于阈值
- 分辨率与帧率是否有效

```bash
python -m cut.cli qa --output out.mp4 --expected-duration 60s --min-video-bitrate 1000000
```

`success=false` 表示自动流程不应宣称交付完成，应把 findings 报给用户或回到导出设置修正。
