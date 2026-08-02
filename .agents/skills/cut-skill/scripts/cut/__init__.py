"""cut — 统一视频剪辑操控包。

支持剪映 (JianYing/CapCut) 与 Adobe Premiere Pro 两种后端，
通过同一组动词 (import/split/trim/text/transition/effect/audio/export) 操控。

子模块：
- platform: 跨平台路径检测
- context: 统一上下文感知接口（只读）
- jianying: 剪映 draft 操控子包
- premiere: Premiere pymiere 封装子包
- cli: cut-cli 命令行入口
- mcp_server: MCP Server
- http_api: Flask HTTP API
"""
from . import platform, context, director, quality
from .jianying import Draft
from .jianying import materials, segments, text, effects, audio, export
from . import premiere

__version__ = "1.2.0"

__all__ = [
    "platform", "context", "director", "quality", "premiere",
    "Draft", "materials", "segments", "text", "effects", "audio", "export",
    "__version__",
]
