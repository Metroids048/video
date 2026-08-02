# 上下文感知与反向读取

cut.skill 的核心设计原则之一：**修改前必先读取状态**。

agent 在做任何修改前，应该先调用 `get_state` / `get_timeline` / `list_materials`
了解当前项目结构，避免盲目修改导致 draft 损坏。

## 1. 三个层级的只读接口

### 1.1 项目概要：`get_state`

最快的状态读取，返回项目的高层摘要。

```python
from cut.context import get_project_state

state = get_project_state(backend="jianying", project_name="my_vlog")
# 或
state = get_project_state(backend="premiere")
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
    {"id": "...", "type": "video", "segments_count": 5},
    {"id": "...", "type": "audio", "segments_count": 1},
    {"id": "...", "type": "text", "segments_count": 3}
  ],
  "materials": {"videos": 5, "audios": 1, "texts": 3}
}
```

**用途**：决定下一步该做什么。比如看到 `duration_hms: 00:00:00.500` 就知道项目几乎空，
应该先 import 素材。

### 1.2 素材池：`list_materials`

列出所有导入的素材。

```python
from cut.context import list_materials

materials = list_materials(backend="jianying", project_name="my_vlog", mtype="video")
```

返回每个素材的 id/type/path/duration/width/height。

**用途**：决定要不要再导入新素材，或复用已有素材。

### 1.3 完整时间轴：`get_timeline`

最详细的读取，返回所有 track 与 segment 的扁平结构。

```python
from cut.context import get_timeline

tl = get_timeline(backend="jianying", project_name="my_vlog")
```

返回：
```json
{
  "backend": "jianying",
  "project_name": "my_vlog",
  "duration_us": 18000000,
  "tracks": [
    {
      "id": "...",
      "type": "video",
      "segments_count": 5,
      "segments": [
        {
          "id": "...",
          "material_id": "...",
          "material_path": "/path/to/clip1.mp4",
          "start_us": 0,
          "end_us": 5000000,
          "duration_us": 5000000,
          "start_hms": "00:00:00.000",
          "end_hms": "00:00:05.000",
          "source_start_us": 0,
          "source_duration_us": 5000000,
          "speed": 1.0,
          "volume": 1.0
        }
      ]
    }
  ]
}
```

**用途**：精确定位要修改的片段。比如"在第 2 个视频的 3.5s 处切分"。

## 2. 决策树：什么时候调什么

```
用户提需求
   ↓
是只读需求吗？(读取/查看/分析)
   ├─ 是 → get_state + get_timeline，回答用户
   └─ 否 → 修改需求
            ↓
        get_state（必调）
            ↓
        需要操作具体片段吗？
            ├─ 是 → get_timeline（精确定位）
            └─ 否 → 只需导入新素材
                     ↓
                 list_materials（看是否已存在）
```

## 3. 实用辅助函数

### 3.1 找出某时间点的所有片段

```python
from cut.jianying.state import get_timeline, get_segments_at

tl = get_timeline(project_name="my_vlog")
segs_at_5s = get_segments_at(tl, at_us=5_000_000)
# 返回 5s 处所有轨道的 segment 列表
```

### 3.2 找出轨道空隙

```python
from cut.jianying.state import get_timeline, find_gaps

tl = get_timeline(project_name="my_vlog")
gaps = find_gaps(tl)
# 返回所有 video/audio 轨的空隙段
# 常用于：自动用转场/素材填补空隙
```

### 3.3 读取 Premiere 选中状态

仅 Premiere 支持：

```python
from cut.premiere.state import get_selection

sel = get_selection()
# {"selected_clips": [...], "count": 1}
```

剪映 draft 文件不记录选中状态，无法读取。

## 4. Agent 决策示例

### 场景 A：用户说"帮我把第 2 个视频切两半"

```python
# 1. 读状态
state = get_project_state(backend="jianying", project_name="my_vlog")

# 2. 读时间轴找第 2 个视频
tl = get_timeline(backend="jianying", project_name="my_vlog")
video_track = next(t for t in tl["tracks"] if t["type"] == "video")
if len(video_track["segments"]) < 2:
    print("没有第 2 个视频")
else:
    seg = video_track["segments"][1]
    mid = (seg["start_us"] + seg["end_us"]) // 2
    
    # 3. 执行切分
    from cut.jianying.draft import Draft
    from cut.jianying import segments as S
    draft = Draft.open(project_name="my_vlog")
    target = draft.get_segment_raw(seg["id"])
    parsed_seg = next(s for s in draft.video_tracks[0].segments if s.id == seg["id"])
    S.split_segment(draft, parsed_seg, at_us=mid)
    draft.save()
```

### 场景 B：用户说"给所有视频加水印字幕"

```python
state = get_project_state(backend="jianying", project_name="my_vlog")
tl = get_timeline(backend="jianying", project_name="my_vlog")

draft = Draft.open(project_name="my_vlog")
from cut.jianying import text as TX

for t in tl["tracks"]:
    if t["type"] != "video":
        continue
    for seg in t["segments"]:
        # 给每个视频段加水印
        TX.add_text(
            draft, "@ My Channel",
            start_us=seg["start_us"],
            duration_us=seg["duration_us"],
            preset="subtitle",
            style_overrides={"position_y": -0.4, "text_size": 24},
        )
draft.save()
```

### 场景 C：用户说"读取一下我剪映里有什么"

```python
state = get_project_state(backend="jianying")  # 自动找最近项目
print(f"项目: {state['project_name']}")
print(f"时长: {state['duration_hms']}")
print(f"画布: {state['canvas']['width']}x{state['canvas']['height']}")
for t in state["tracks"]:
    print(f"  {t['type']} 轨: {t['segments_count']} 段")
print(f"素材: {state['materials']}")
```

## 5. 反向读取的限制

### 剪映

- **不能读取选中状态**：draft 文件不记录 UI 选中
- **不能读取播放头位置**：同上
- **不能实时反映 UI 改动**：用户在剪映 UI 改了东西没保存的话，draft 还是旧的
- **修改后需重启**：剪映不热加载 draft

### Premiere

- **可以读取选中**：`get_selection()`
- **可以读取播放头**：`seq.getPlayheadPosition()`
- **实时反映**：所有改动立即可见
- **限制**：必须 Premiere 运行中

## 6. 上下文感知最佳实践

1. **每次会话开始先 detect**：了解环境
2. **每次修改前先 get_state**：了解项目
3. **批量操作前先 get_timeline**：精确定位
4. **导出前先 get_state 确认时长**：避免导出空项目
5. **错误后重新 get_state**：可能是上次操作改坏了
