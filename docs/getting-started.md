# Agent Video Studio V1 — Getting Started

## 快速开始

### 1. 环境检查

```bash
python -m avs doctor
```

必需：Python 3.11+, FFmpeg  
可选：ffprobe, HyperFrames (npx)

### 2. 创建 Episode

```bash
python -m avs episode create EP-MY-FIRST --mode REFERENCE_ADAPT
```

### 3. 放入素材

将素材放入 `episodes/active/EP-MY-FIRST/input/`：
- `input/reference/` — 参考视频（可选）
- `input/images/` — 图片素材
- `input/audio/` — 音频素材
- `input/screen/` — 录屏素材

### 4. 运行全流程

```bash
python -m avs run EP-MY-FIRST
```

或分步执行：

```bash
# 清点素材
python -m avs ingest EP-MY-FIRST

# 分析参考（可选）
python -m avs reference analyze EP-MY-FIRST

# 内容生成（Agent 驱动，手动调用 Skills）
python -m avs content init EP-MY-FIRST

# 构建时间线
python -m avs timeline build EP-MY-FIRST

# 生成字幕
python -m avs subtitles build EP-MY-FIRST

# 渲染粗剪
python -m avs render rough EP-MY-FIRST

# QA 检查
python -m avs qa EP-MY-FIRST

# 生成交付包
python -m avs deliver EP-MY-FIRST
```

### 5. 查看产物

```bash
# 查看状态
python -m avs episode status EP-MY-FIRST

# 播放粗剪
ffplay episodes/active/EP-MY-FIRST/renders/preview-with-captions.mp4

# 检查交付包
ls episodes/active/EP-MY-FIRST/delivery/
```

## 常见问题

### Q: FFmpeg 失败
A: 检查 `ffmpeg -version`，确保版本 ≥ 4.0

### Q: HyperFrames 失败
A: 正常，系统会自动降级到 FFmpeg 静态卡片

### Q: 缺失素材
A: 系统会生成占位卡，查看 `delivery/edit-notes.md`

## 下一步

- [输入规范](input-guide.md) — 素材准备
- [编辑指南](editing-guide.md) — 人工修改交付包
- [兼容性](compatibility.md) — 支持的格式与工具版本
