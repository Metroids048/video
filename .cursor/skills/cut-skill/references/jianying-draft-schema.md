# 剪映 draft_content.json Schema 详解

本文档是修改剪映工程文件的权威参考。剪映的 `draft_content.json` 是 JSON 格式，
包含项目的所有信息：素材池、轨道、片段、特效、动画、关键帧。

> **版本说明**：本 schema 基于 剪映专业版 5.x。4.x 与 5.x 有差异，但 5.x 是当前主流。
> 如果 `draft_version` 字段以 `4.` 开头，部分字段可能不存在。

## 1. 顶层结构

```json
{
  "version": "5.9.0",
  "draft_version": "5.9.0",
  "duration": 18000000,
  "canvas_config": {"width": 1920, "height": 1080, "ratio": "original"},
  "materials": {...},
  "tracks": [...],
  "id": "global-uuid",
  "create_time": 1700000000,
  "platform": {"os": "mac", "app_id": "..."},
  "home_template_type": 0,
  "fps": 30,
  "display_aspect_ratio": {"width": 1920, "height": 1080}
}
```

### 关键字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `duration` | int (μs) | 项目总时长，微秒。`draft.extend_duration()` 会重算 |
| `canvas_config` | object | 画布尺寸。`width/height` 是像素，`ratio` 是预设名 |
| `materials` | object | 素材池，详见第 2 节 |
| `tracks` | array | 轨道数组，详见第 3 节 |
| `fps` | int | 项目帧率（30/60） |

## 2. materials 素材池

`materials` 是对象，每个子字段是一个数组：

```json
{
  "materials": {
    "videos": [...],      // 视频与图片（图片 type=photo）
    "audios": [...],      // 音频
    "images": [],         // 旧版本字段，5.x 通常空
    "stickers": [...],    // 贴纸
    "texts": [...],       // 文本
    "effects": [...],     // 视频特效资源
    "audio_effects": [...], // 音频特效资源
    "material_animations": [...], // 入场/出场/循环动画
    "material_color": [...],      // 纯色背景
    "digital_humans": [],
    "log_color": [],
    "log_color_curves": [],
    "multi_language_refs": [],
    "placeholders": [],
    "sounds": [...],      // 音效
    "space_paths": [],
    "stickers_v2": [],
    "text_effects": [],
    "text_templates": [],
    "video_effects": [...],
    "material_labels": []
  }
}
```

### 2.1 video material

```json
{
  "id": "abc123...",
  "type": "video",  // 或 "photo" 表示图片
  "path": "/Users/me/Movies/clip.mp4",
  "duration": 18000000,
  "width": 1920,
  "height": 1080,
  "fps": 30.0,
  "has_audio": true,
  "material_name": "clip",
  "local_material_id": "abc123...",
  "stable_material_id": "abc123...",
  "md5": "",
  "is_proxy": false,
  "is_copyright": false,
  "is_ai_generate": false,
  "is_recycle": false,
  "is_valid": true,
  "is_placeholder": false,
  "fursuer_effect": [],
  "team_id": "",
  "source_platform": 0,
  "request_id": "",
  "import_time": 0,
  "intensifies_audio_path": "",
  "intensifies_path": "",
  "mask_info": {"mask_id": "", "mask_name": "", "mask_path": ""},
  "category_id": "",
  "category_name": "",
  "extra_material_id": ""
}
```

### 2.2 audio material

```json
{
  "id": "...",
  "type": "audio",
  "path": "/path/to.mp3",
  "duration": 60000000,
  "material_name": "bgm",
  "name": "bgm.mp3",
  "local_material_id": "...",
  "stable_material_id": "...",
  "is_valid": true,
  "is_copyright": false,
  "is_ai_generate": false,
  "category_id": "",
  "category_name": "",
  "intensifies_audio_path": "",
  "import_time": 0,
  "app_id": "",
  "business_id": 0,
  "fursuer_effect": []
}
```

### 2.3 text material

文本素材字段较多，关键：

```json
{
  "id": "...",
  "type": "subtitle",  // 或 "title"
  "text": "Hello world",
  "content": "Hello world",
  "base_content": "Hello world",
  "text_size": 40,
  "text_color": "#FFFFFF",
  "text_alpha": 1.0,
  "background_color": "#000000",
  "background_alpha": 0.5,
  "font_path": "",
  "font_resource_id": "",
  "font_id": "",
  "font_size": 40,
  "alignment": 1,  // 0=左 1=中 2=右
  "text_stroke_color": "#000000",
  "text_stroke_width": 1,
  "text_shadow_color": "#000000",
  "text_shadow_alpha": 0.5,
  "text_shadow_point": {"x": 0.0, "y": 0.06},
  "text_shadow_radius": 1.0,
  "transform": {"x": 0.0, "y": 0.4},  // 位置，-1~1 屏幕比例
  "scale": {"x": 1.0, "y": 1.0},
  "text_styles": [{
    "text": "Hello world",
    "style": {...}
  }],
  "text_type": "subtitle",
  "paragraphs": [],
  "sort_words": [],
  "wave_form": [],
  "create_segment": true,
  "is_rich_text": false,
  "language": "",
  "multi_language_current": ""
}
```

### 2.4 effect material

```json
{
  "id": "...",
  "type": "effect",
  "resource_id": "effect.vignette",  // 内置特效 ID
  "name": "vignette",
  "category_name": "video_effect",
  "is_affect_video": true,
  "is_affect_audio": false,
  "is_valid": true,
  "platform": "",
  "path": "",  // 自定义特效才有
  "stable_material_id": "..."
}
```

## 3. tracks 轨道

```json
{
  "id": "track-uuid",
  "type": "video",  // video/audio/text/sticker/effect
  "segments": [...],
  "attribute": 0,
  "flag": 0,
  "volume": 1.0,
  "visible": true,
  "enabled": true,
  "collapsed": false,
  "is_selected": false,
  "default_segment": null,
  "extra_material_refs": [],
  "common_keyframes": [],
  "type_source": 0,
  "fursuer_effect": [],
  "supported_mix_types": [],
  "polylines": [],
  "polyline_indices": [],
  "captions": [],
  "is_locked": false,
  "is_hidden": false,
  "transitions": [],  // video 轨道才有
  "play_back_rate": 1.0,
  "speed": 1.0,
  "render_index": 0
}
```

### 3.1 segment

```json
{
  "id": "seg-uuid",
  "material_id": "abc123...",
  "track_id": "track-uuid",
  "source_timerange": {
    "start": 0,        // 素材内部入点（μs）
    "duration": 5000000  // 素材内部时长
  },
  "target_timerange": {
    "start": 1200000,  // 时间轴起点（μs）
    "duration": 5000000 // 时间轴时长
  },
  "source_in_speed": 1.0,
  "speed": 1.0,
  "volume": 1.0,
  "visible": true,
  "enabled": true,
  "is_placeholder": false,
  "render_index": 0,
  "clip": {
    "alpha": 1.0,
    "flip": {"horizontal": false, "vertical": false},
    "rotation": 0,
    "scale": {"x": 1.0, "y": 1.0},
    "transform": {"x": 0.0, "y": 0.0}
  },
  "common_keyframes": [...],
  "material_animations": [...],  // 入场/出场动画 ID
  "extra_material_refs": [...],  // 关联的特效/LUT ID
  "fursuer_effect": [],
  "reverse": false,
  "source": 0,
  "stage_width": 0,
  "stage_height": 0,
  "responsive_layout": {...},
  "hole_info": {"holes": []}
}
```

### 3.2 transition

video track 的 `transitions` 数组：

```json
{
  "id": "trans-uuid",
  "type": "transition",
  "duration": 500000,
  "left_segment_id": "seg-1-uuid",
  "right_segment_id": "seg-2-uuid",
  "transition": {
    "resource_id": "transition.fade_in_out",
    "name": "fade",
    "category_name": "basic",
    "duration": 500000,
    "overlap": true,
    "render_index": 0,
    "direction": 0,
    "apply_id": 0,
    "params": []
  }
}
```

## 4. 关键帧

`common_keyframes` 数组：

```json
{
  "id": "kf-uuid",
  "field": "alpha",  // alpha/scale/scale_x/scale_y/rotation/position_x/position_y/volume
  "time": 1500000,   // 时间轴坐标（μs）
  "value": 0.5,
  "easing": "linear",  // linear/ease_in/ease_out/ease_in_out
  "curve_type": 0,
  "default": false
}
```

## 5. 入场/出场动画

`material_animations` 数组：

```json
{
  "id": "anim-uuid",
  "animations": [{
    "id": "anim-uuid",
    "type": "in",  // in/out/loop
    "duration": 500000,
    "resource_id": "animation.fade_in",
    "name": "Fade In",
    "category_id": "in",
    "request_id": "",
    "platform": ""
  }]
}
```

## 6. 常见修改场景

### 6.1 添加新视频片段

1. 向 `materials.videos` 添加 video material
2. 找到目标 video track（没有就新建）
3. 向 track.segments 添加 segment，引用 material_id
4. 调 `draft.extend_duration()` 重算项目时长

### 6.2 切分片段

1. 找到目标 segment
2. 计算 source/target 切分点（按 speed 调整比例）
3. 修改原 segment 的 timerange 为左半段
4. 深拷贝原 segment，修改 ID 与 timerange 为右半段，插入到原 segment 后

### 6.3 添加转场

1. 找到 video track
2. 找到相邻两个 segment
3. 向 `track.transitions` 添加 transition，关联两个 segment id

### 6.4 修改字幕内容

1. 找到 text segment → 取 material_id
2. 找到对应 text material
3. 修改 `text`、`content`、`base_content`、`text_styles[0].text`

## 7. 注意事项

1. **ID 唯一性**：所有 id 必须全局唯一。用 `_new_id()` 生成。
2. **timerange 单位**：微秒（μs），不是毫秒。
3. **修改后必须重启剪映**：剪映不会热加载 draft。需要用户关闭项目重新打开。
4. **不要改 draft_meta_info.json**：那是项目列表索引文件，改了会导致列表错乱。
5. **备份优先**：`Draft.save()` 默认会备份到 `.bak.<timestamp>`。
6. **JSON 合法性**：保存前会序列化校验，失败抛 `DraftError`。
7. **scale 是相对值**：1.0 = 原大小，0.5 = 一半，2.0 = 双倍。不是像素。
8. **transform 是归一化坐标**：x/y ∈ [-1, 1]，0.0 = 居中，0.5 = 偏右下。

## 8. 调试技巧

1. **对比 draft**：在剪映中手动做一次操作（如加字幕），保存前后 diff draft 文件，能看到字段差异。
2. **JSON 格式化**：剪映默认紧凑无缩进，用 `python -m json.tool draft_content.json` 美化。
3. **字段缺失容错**：5.x 各小版本字段会有增减，代码用 `.get()` 取，不要硬下标。

## 9. 与 CapCut 国际版的差异

CapCut 国际版与剪映 draft schema **完全一致**，只是：
- 默认路径不同（见 `references/cross-platform.md`）
- 部分内置特效/转场/字体 ID 因地区而异
- 字段名都是英文

代码层面无需区分，`Draft.open(app="capcut")` 会自动找对应路径。
