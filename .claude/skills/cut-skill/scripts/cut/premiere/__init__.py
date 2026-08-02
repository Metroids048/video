"""cut.premiere — Premiere Pro 操控子包（基于 pymiere）。

核心模块：
- wrapper: 连接管理 + 数据结构转换
- materials: 素材导入
- timeline: 裁切/移动
- text: 文字
- effects: 特效
- audio: 音频
- export: 导出
- state: 反向读取
"""
from .wrapper import (
    ensure_connected, get_app, get_project, get_active_sequence,
    PremiereError, PremiereNotRunningError, HAS_PYMIERE,
)
from . import materials, timeline, text, effects, audio, export, state

__all__ = [
    "ensure_connected", "get_app", "get_project", "get_active_sequence",
    "PremiereError", "PremiereNotRunningError", "HAS_PYMIERE",
    "materials", "timeline", "text", "effects", "audio", "export", "state",
]
