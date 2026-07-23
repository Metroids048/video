# ADR-0002：timeline.json 为渲染器共享中间协议

- **状态**：已接受（Accepted）
- **日期**：2026-07-20
- **模块**：0（设计冻结）

---

## 背景

项目使用两个渲染器：FFmpeg（基础粗剪）和 HyperFrames（动效片段）。如果每个渲染器维护各自独立的时间线格式，会导致：数据重复、两个渲染器之间状态不同步、难以添加第三方渲染器（如未来的 Remotion）、Agent 无法统一理解时间线内容。

---

## 决策

**`timeline.json` 是所有渲染器的共享中间协议，是项目时间线的唯一真相来源。**

### 标准结构

```json
{
  "version": "1.0",
  "canvas": {
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "duration": 60.0,
  "tracks": {
    "video": [],
    "overlay": [],
    "captions": [],
    "voice": [],
    "music": [],
    "effects": []
  }
}
```

### Clip 必须字段

每个 Clip 无论所属渲染器，均必须包含：

| 字段 | 说明 |
|------|------|
| `clip_id` | 全局唯一标识 |
| `start` | 轨道起始时间（秒） |
| `duration` | 片段时长（秒） |
| `source` | 素材引用（相对路径或 renderer 标识） |
| `source_in` | 素材起始点（秒） |
| `source_out` | 素材结束点（秒） |
| `layout` | `contain` / `cover` / `absolute` |
| `volume` | 音量系数（0.0–2.0） |
| `transition` | 转场类型（`cut` / `fade` / `none`） |
| `renderer` | `ffmpeg` / `hyperframes` / `auto` |
| `missing` | 素材是否缺失（boolean） |
| `placeholder_label` | 缺失时显示的占位文字 |

### 渲染器职责边界

```
timeline.json
    ├── renderer: "ffmpeg"       → src/avs/render/ffmpeg.py 处理
    ├── renderer: "hyperframes"  → renderers/hyperframes/ 处理
    └── renderer: "auto"         → doctor 探测，优先 ffmpeg
```

HyperFrames 读取 `timeline.json` 中标记为 `"renderer": "hyperframes"` 的条目，渲染为独立片段后交还 FFmpeg 合成。HyperFrames 不持有或修改 `timeline.json`。

---

## 原因

- 统一格式使 Agent（Skill）可读取时间线并给出有意义的编辑建议，不需要了解具体渲染器
- 相同的 `timeline.json` 支持未来增加 Remotion 等渲染器，仅需新增 `renderer` 值
- Schema 校验在 `python -m avs timeline validate` 中统一执行，渲染器无需各自校验
- 消除"渲染器自维护状态"的反模式，符合单一真相来源原则

---

## 后果

**正面：**
- 跨渲染器一致性，避免状态分叉
- 可测试：只需单元测试 `timeline.json` 结构，无需 mock 两套渲染器
- 未来扩展路径清晰（增加 renderer 值即可）

**需注意：**
- HyperFrames 组件开发者须从 `timeline.json` 读取参数，不得从聊天上下文直接获取
- 时间线构建器（`src/avs/timeline/builder.py`）负责确保所有 Clip 字段完整，渲染器不负责补全缺失字段

---

## 合规检测

若发现任何渲染器维护独立时间线结构（与 `timeline.json` 不同步），视为违反本 ADR，需立即合并。
