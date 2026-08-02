"""cut.jianying — 剪映 draft 文件操控子包。

核心模块：
- draft: Draft 类，文件读写与三层结构解析
- materials: 素材导入
- segments: 片段裁切
- text: 字幕与文本（基础）
- effects: 转场与特效（基础）
- audio: 音频混音
- export: 导出
- state: 反向读取时间轴状态

专业模块（基于剪映大神工作流调研）：
- pro_effects: 专业特效（不透明度转场/闪白闪黑/推拉/动态模糊/文字蒙版）
- pro_text: 花字预设/顺序入场/ASR自动字幕/浮空滤色文字
- pro_color: 调色 LUT 生成器（青橙/赛博朋克/日系/小清新/黑金/复古/莫兰迪）
- viral_templates: 8种爆款模板
- audio_beat: 节拍识别 + 卡点对齐
- auto_edit: 一键成片 + 模仿爆款
"""
from .draft import Draft, Segment, Track, Material, TimeRange, DraftError, UnsupportedSchemaError
from . import materials, segments, text, effects, audio, export, state
from . import pro_effects, pro_text, pro_color, viral_templates, audio_beat, auto_edit

__all__ = [
    "Draft", "Segment", "Track", "Material", "TimeRange",
    "DraftError", "UnsupportedSchemaError",
    "materials", "segments", "text", "effects", "audio", "export", "state",
    "pro_effects", "pro_text", "pro_color", "viral_templates", "audio_beat", "auto_edit",
]
