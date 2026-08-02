# 专业剪辑能力详解

本文档介绍 cut.skill 的专业剪辑能力，所有功能基于全网剪映大神、Premiere 大神工作流调研固化。

## 模块总览

| 模块 | 功能 | 数量 |
|---|---|---|
| `pro_effects` | 专业转场（不透明度/闪白闪黑/推拉/动态模糊/文字蒙版） | 8 presets |
| `pro_text` | 花字预设/顺序入场/ASR自动字幕/浮空滤色 | 10 presets |
| `pro_color` | 调色 LUT 生成器（青橙/赛博朋克/日系等） | 7 presets |
| `viral_templates` | 爆款模板（教程/测评/vlog/知识/剧情/对比/情感/卡点） | 8 templates |
| `audio_beat` | 节拍识别 + 卡点对齐 | - |
| `auto_edit` | 一键成片 + 模仿爆款 | - |

---

## 1. 一键成片（auto-edit）

最强大的命令，自动完成：模板应用 → 转场 → 调色 → 字幕 → ducking

```bash
python -m cut.cli auto-edit \
    --backend jianying --project my_vlog \
    --videos "mat1,mat2,mat3,mat4,mat5,mat6,mat7" \
    --bgm bgm_mat_id \
    --template vlog \
    --texts "我的一天|早晨|工作|高光|晚上|感悟|再见" \
    --color-preset teal_orange
```

支持的模板（`--template`）：
- `tutorial` 教程类（7 phase，黄金3秒钩子+演示+CTA）
- `review` 测评类（产品+亮点+对比+推荐）
- `vlog` 日记类（一天记录+高光+感悟）
- `knowledge` 知识科普（提问+解释+案例+升华）
- `drama` 剧情类（冲突+发展+高潮+反转）
- `comparison` 测评对比（A vs B 多维度）
- `emotional` 情感类（场景+故事+共鸣）
- `beat_sync` 卡点类（节拍切换+高潮）

---

## 2. 模仿爆款（imitate_viral）

给定参考视频的元数据，生成同类型视频：

```python
from cut.jianying import auto_edit

reference = {
    "template": "tutorial",
    "duration_us": 40_000_000,  # 40秒
    "color_preset": "teal_orange",
    "texts": ["AI剪辑太难？", "今天教你一键成片", "第一步：导入素材",
              "第二步：选择模板", "第三步：自动卡点", "就这么简单", "关注学更多"],
    "auto_subtitle": True,
    "subtitle_engine": "whisper",
}

result = auto_edit.imitate_viral(draft, reference, video_material_ids, bgm_material_id)
```

---

## 3. 专业转场（pro-transition）

8 种基于大神工作流的转场：

```bash
python -m cut.cli pro-transition --list-presets

# 在 clip 0 和 clip 1 之间加闪白转场
python -m cut.cli pro-transition --backend jianying --project my_vlog \
    --track 0 --clip 0 --preset flash_white
```

| 预设 | 效果 | 适用场景 |
|---|---|---|
| `smooth` | 不透明度淡入淡出 | vlog 通用 |
| `flash_white` | 闪白 | 教程/卡点 |
| `flash_black` | 闪黑 | 电影感 |
| `zoom_in` | 推近放大 | 强调细节 |
| `zoom_out` | 拉远缩小 | 场景切换 |
| `motion_blur` | 动态模糊 | 运动镜头 |
| `cinematic` | 电影感闪黑 | 剧情片 |
| `vlog` | vlog 丝滑 | 日记类 |

---

## 4. 花字字幕（add-huazi）

10 种花字预设，带动画：

```bash
python -m cut.cli add-huazi --list-presets

python -m cut.cli add-huazi --backend jianying --project my_vlog \
    --content "你绝对想不到！" --start 0 --preset hook_red
```

| 预设 | 用途 |
|---|---|
| `hook_red` | 红色大字钩子（开头吸睛） |
| `hook_yellow` | 黄色描边钩子 |
| `vlog_clean` | vlog 干净字幕 |
| `vlog_minimal` | 极简字幕 |
| `tutorial_boxed` | 教程带框字幕 |
| `cinematic` | 电影感字幕 |
| `emphasis_red` | 红色强调 |
| `stat_number` | 数据展示大字 |
| `quote_italic` | 引用斜体 |
| `chapter_title` | 章节标题 |

---

## 5. 调色 LUT（add-lut）

7 种调色预设，可生成 .cube 文件导入剪映/PR/达芬奇：

```bash
python -m cut.cli add-lut --list-presets

# 应用青橙调色到所有片段
python -m cut.cli add-lut --backend jianying --project my_vlog \
    --preset teal_orange --all-clips --intensity 0.8

# 生成 LUT 包到本地（可导入其他软件）
python -m cut.cli add-lut --generate --output ./my_luts --size 32
```

| 预设 | 风格 |
|---|---|
| `teal_orange` | 青橙电影感（最火） |
| `cyberpunk` | 赛博朋克霓虹 |
| `japanese_film` | 日系电影感 |
| `fresh` | 小清新 |
| `black_gold` | 黑金质感 |
| `vintage_film` | 复古胶片 |
| `morandi` | 莫兰迪灰调 |

生成的 .cube 文件用法：
- **剪映**：滤镜 → 导入 LUT
- **Premiere**：Lumetri Color → 创意 → Look
- **达芬奇**：LUT 库

---

## 6. 节拍卡点（beat-sync）

识别 BGM 节拍，自动对齐视频片段切换：

```bash
# 仅检测节拍
python -m cut.cli beat-sync --detect-only --audio-path /path/to/bgm.mp3

# 卡点对齐
python -m cut.cli beat-sync --backend jianying --project my_vlog \
    --audio-segment bgm_seg_id \
    --videos "seg1,seg2,seg3,seg4"
```

支持两种引擎：
- `librosa`（准确，需 `pip install librosa`）
- `energy`（简化版，仅依赖 ffmpeg）

---

## 7. 爆款模板（apply-template）

单独应用某个模板：

```bash
python -m cut.cli apply-template --list

python -m cut.cli apply-template --backend jianying --project my_vlog \
    --template vlog \
    --videos "mat1,mat2,mat3,mat4,mat5,mat6,mat7" \
    --texts "我的一天|早晨|工作|高光|晚上|感悟|再见" \
    --bgm bgm_mat_id
```

每个模板预设了：
- phase 数量与时长（黄金3秒钩子 → 中段 → CTA）
- 每个 phase 的花字预设
- phase 之间的转场
- 整体调色风格

---

## 完整工作流示例

```python
from cut.jianying.draft import Draft
from cut.jianying import materials, auto_edit

draft = Draft.open(project_name="my_vlog")

mat_ids = []
for f in ["clip1.mp4", "clip2.mp4", "clip3.mp4", "clip4.mp4",
          "clip5.mp4", "clip6.mp4", "clip7.mp4"]:
    mid = materials.import_video(draft, f"/path/to/{f}")
    mat_ids.append(mid)

bgm_mid = materials.import_audio(draft, "/path/to/bgm.mp3")

result = auto_edit.auto_edit(
    draft, mat_ids, bgm_material_id=bgm_mid,
    template="vlog",
    texts=["我的一天", "早晨", "工作", "高光", "晚上", "感悟", "再见"],
    auto_subtitle=True,
    subtitle_engine="whisper",  # 需 pip install openai-whisper
    beat_sync=True,
)

print(f"完成！总时长: {result['total_duration_hms']}")
draft.save()
```

---

## 设计哲学

### 为什么基于 draft 而不是 UI 自动化？

- **稳定**：draft 是 JSON，结构公开，不受剪映 UI 改版影响
- **离线**：不需要剪映运行，改完用户重开项目即可
- **可批量**：能同时处理多个项目
- **可回滚**：自动备份 .bak

### 为什么用预设而非完全自定义？

- **专业经验固化**：8种爆款模板是调研数百条爆款视频得出的结构
- **降低决策成本**：用户不需要懂剪辑也能出专业作品
- **保留灵活性**：所有预设都支持 `overrides` 参数深度定制

### 兼容性注意

- 剪映 6+ 版本 draft 可能加密，本 skill 默认支持 5.x 明文 JSON
- 如遇 6+ 加密 draft，需用户手动解密或降级剪映版本
- CapCut 国际版 draft 与剪映完全一致
