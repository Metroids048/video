"""cut.mcp_server — MCP (Model Context Protocol) Server。

让 Claude Desktop / OpenCode 等 MCP 客户端直接 tool_call 调用 cut 操作。

启动：
    python -m cut.mcp_server

或在 MCP 客户端配置中：
    {
      "mcpServers": {
        "cut": {
          "command": "python",
          "args": ["-m", "cut.mcp_server"]
        }
      }
    }

本实现使用 stdio 传输（最通用）。
依赖：mcp 包 (pip install mcp)
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    # 提供 shim 类，让模块在未安装 mcp 包时仍可 import（HTTP API 依赖本模块的 TOOLS/dispatch_tool）
    class Server:  # type: ignore
        def __init__(self, *args, **kwargs): pass
    class Tool:  # type: ignore
        def __init__(self, name, description, inputSchema):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema
    class TextContent:  # type: ignore
        def __init__(self, type="text", text=""):
            self.type = type
            self.text = text
    def stdio_server():  # type: ignore
        raise RuntimeError("mcp 包未安装，无法启动 MCP server。请 pip install mcp")


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="cut.list_backends",
        description="检测本机环境，返回可用的视频剪辑后端（剪映/CapCut/Premiere）及版本。",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="cut.get_state",
        description="读取当前项目状态：项目名、时长、轨道数、素材数。修改前必先调用。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
            },
        },
    ),
    Tool(
        name="cut.list_materials",
        description="列出素材池所有素材。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "mtype": {"type": "string", "enum": ["video", "audio", "image", "sticker", "text", "effect"]},
            },
        },
    ),
    Tool(
        name="cut.get_timeline",
        description="读取完整时间轴：所有轨道与片段的扁平结构。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
            },
        },
    ),
    Tool(
        name="cut.import_media",
        description="导入视频/音频/图片素材到项目。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "path": {"type": "string", "description": "媒体文件绝对路径"},
                "mtype": {"type": "string", "enum": ["video", "audio", "image"]},
                "alias": {"type": "string"},
            },
            "required": ["path", "mtype"],
        },
    ),
    Tool(
        name="cut.split",
        description="在指定时间点切分片段。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "track_index": {"type": "integer", "description": "轨道索引（0=最上）"},
                "track_type": {"type": "string", "enum": ["video", "audio"], "default": "video", "description": "Premiere 必填，剪映忽略"},
                "clip_index": {"type": "integer", "description": "Premiere 必填，剪映不填则切分所有跨过 at_us 的片段"},
                "at_us": {"type": "integer", "description": "切点时间（微秒）"},
            },
            "required": ["track_index", "at_us"],
        },
    ),
    Tool(
        name="cut.trim",
        description="调整片段入点/出点。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "track_index": {"type": "integer"},
                "track_type": {"type": "string", "enum": ["video", "audio"], "default": "video"},
                "clip_index": {"type": "integer"},
                "new_start_us": {"type": "integer"},
                "new_end_us": {"type": "integer"},
            },
            "required": ["track_index", "clip_index"],
        },
    ),
    Tool(
        name="cut.add_text",
        description="添加文字/字幕/标题。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "content": {"type": "string"},
                "start_us": {"type": "integer"},
                "duration_us": {"type": "integer", "default": 3000000},
                "preset": {"type": "string", "enum": ["subtitle", "title"], "default": "subtitle"},
            },
            "required": ["content", "start_us"],
        },
    ),
    Tool(
        name="cut.add_transition",
        description="在两段之间加转场。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "track_index": {"type": "integer"},
                "clip_index": {"type": "integer", "description": "在该 clip 与下个 clip 之间加"},
                "preset": {"type": "string", "default": "fade"},
                "duration_us": {"type": "integer", "default": 500000},
            },
            "required": ["track_index", "clip_index"],
        },
    ),
    Tool(
        name="cut.add_effect",
        description="应用视频特效。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "track_index": {"type": "integer"},
                "clip_index": {"type": "integer"},
                "preset": {"type": "string", "default": "vignette"},
                "intensity": {"type": "number", "default": 1.0},
            },
            "required": ["track_index", "clip_index"],
        },
    ),
    Tool(
        name="cut.set_audio",
        description="音频操作（音量/淡入/淡出/特效）。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "track_index": {"type": "integer"},
                "clip_index": {"type": "integer"},
                "action": {"type": "string", "enum": ["volume", "fade_in", "fade_out", "effect"]},
                "value": {"type": "number", "description": "volume (0-1+)"},
                "preset": {"type": "string"},
                "duration_us": {"type": "integer", "default": 500000},
            },
            "required": ["track_index", "clip_index", "action"],
        },
    ),
    Tool(
        name="cut.export",
        description="导出渲染。剪映用 method=ui/ffmpeg，Premiere 用 preset。",
        inputSchema={
            "type": "object",
            "properties": {
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "剪映项目名（与 project_dir 二选一）"},
                "project_dir": {"type": "string", "description": "项目目录绝对路径（优先于 project）"},
                "output": {"type": "string"},
                "method": {"type": "string", "enum": ["ui", "ffmpeg"], "default": "ffmpeg"},
                "preset": {"type": "string", "default": "h264_1080p"},
            },
            "required": ["output"],
        },
    ),
    Tool(
        name="cut.create_plan",
        description="从一句话需求生成专业剪辑执行计划，覆盖长视频/短视频、节奏、字幕、混音、调色、导出和 QA。",
        inputSchema={
            "type": "object",
            "properties": {
                "brief": {"type": "string", "description": "用户的一句话剪辑需求"},
                "backend": {"type": "string", "enum": ["jianying", "capcut", "premiere"], "default": "jianying"},
                "project": {"type": "string", "description": "项目名"},
                "assets": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "素材列表，可包含 path/duration_us/type/role",
                },
            },
            "required": ["brief"],
        },
    ),
    Tool(
        name="cut.quality_check",
        description="导出后成片质量验收，检查时长、码率、视频/音频流、分辨率和帧率。",
        inputSchema={
            "type": "object",
            "properties": {
                "output": {"type": "string", "description": "导出文件路径"},
                "expected_duration_us": {"type": "integer"},
                "min_video_bitrate": {"type": "integer", "default": 1000000},
            },
            "required": ["output"],
        },
    ),
]


# ---------------------------------------------------------------------------
# 工具分发
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """根据工具名分发到对应实现。"""
    from . import context
    backend = args.get("backend", "jianying")
    project = args.get("project")
    project_dir = args.get("project_dir")

    if name == "cut.list_backends":
        return context.detect_environment()

    elif name == "cut.get_state":
        return context.get_project_state(backend=backend, project_name=project, project_dir=project_dir)

    elif name == "cut.list_materials":
        return context.list_materials(backend=backend, project_name=project, project_dir=project_dir, mtype=args.get("mtype"))

    elif name == "cut.get_timeline":
        return context.get_timeline(backend=backend, project_name=project, project_dir=project_dir)

    elif name == "cut.import_media":
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import materials as M
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            if args["mtype"] == "video":
                mid = M.import_video(draft, args["path"], alias=args.get("alias"))
            elif args["mtype"] == "audio":
                mid = M.import_audio(draft, args["path"], alias=args.get("alias"))
            else:
                mid = M.import_image(draft, args["path"], alias=args.get("alias"))
            draft.save()
            return {"success": True, "material_id": mid}
        elif backend == "premiere":
            from .premiere import materials as M
            return M.import_file(args["path"], alias=args.get("alias"))

    elif name == "cut.split":
        at = int(args["at_us"])
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import segments as S
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            track = draft.all_tracks()[int(args["track_index"])]
            results = []
            for seg in track.segments:
                if seg.start_us < at < seg.end_us:
                    l, r = S.split_segment(draft, seg, at)
                    results.append({"left": l, "right": r})
            draft.save()
            return {"success": True, "splits": results}
        elif backend == "premiere":
            from .premiere import timeline as T
            track_type = args.get("track_type", "video")
            clip_index = args.get("clip_index")
            if clip_index is None:
                return {"success": False, "error": "Premiere 后端必须提供 clip_index"}
            return T.split_clip(int(args["track_index"]), track_type, int(clip_index), at)

    elif name == "cut.trim":
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import segments as S
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            track = draft.all_tracks()[int(args["track_index"])]
            seg = track.segments[int(args["clip_index"])]
            S.trim_segment(draft, seg,
                            new_start_us=args.get("new_start_us"),
                            new_end_us=args.get("new_end_us"))
            draft.save()
            return {"success": True}
        elif backend == "premiere":
            from .premiere import timeline as T
            track_type = args.get("track_type", "video")
            return T.trim_clip(int(args["track_index"]), track_type, int(args["clip_index"]),
                                args.get("new_start_us"), args.get("new_end_us"))

    elif name == "cut.add_text":
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import text as TX
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            sid = TX.add_text(draft, args["content"], int(args["start_us"]),
                              int(args.get("duration_us", 3_000_000)),
                              preset=args.get("preset", "subtitle"))
            draft.save()
            return {"success": True, "segment_id": sid}
        elif backend == "premiere":
            from .premiere import text as TX
            return TX.add_text(args["content"], int(args["start_us"]),
                               int(args.get("duration_us", 3_000_000)))

    elif name == "cut.add_transition":
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import effects as E
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            track = draft.all_tracks()[int(args["track_index"])]
            tid = E.add_transition_simple(draft, track.id, int(args["clip_index"]),
                                          preset=args.get("preset", "fade"),
                                          duration_us=int(args.get("duration_us", 500_000)))
            draft.save()
            return {"success": True, "transition_id": tid}
        elif backend == "premiere":
            from .premiere import effects as E
            return E.add_transition(int(args["track_index"]), int(args["clip_index"]),
                                    args.get("preset", "Cross Dissolve"),
                                    int(args.get("duration_us", 500_000)))

    elif name == "cut.add_effect":
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import effects as E
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            track = draft.all_tracks()[int(args["track_index"])]
            seg = track.segments[int(args["clip_index"])]
            sid = E.add_video_effect(draft, seg.id, preset=args.get("preset", "vignette"),
                                     intensity=float(args.get("intensity", 1.0)))
            draft.save()
            return {"success": True, "effect_segment_id": sid}
        elif backend == "premiere":
            from .premiere import effects as E
            return E.add_video_effect(int(args["track_index"]), int(args["clip_index"]),
                                      args.get("preset", "Gaussian Blur"))

    elif name == "cut.set_audio":
        action = args["action"]
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import audio as A
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            track = draft.all_tracks()[int(args["track_index"])]
            seg = track.segments[int(args["clip_index"])]
            if action == "volume":
                A.set_volume(draft, seg.id, float(args["value"]))
            elif action == "fade_in":
                A.add_audio_fade_in(draft, seg.id, int(args.get("duration_us", 500_000)))
            elif action == "fade_out":
                A.add_audio_fade_out(draft, seg.id, int(args.get("duration_us", 500_000)))
            elif action == "effect":
                A.apply_audio_effect(draft, seg.id, preset=args.get("preset", "denoise"))
            draft.save()
            return {"success": True}
        elif backend == "premiere":
            from .premiere import audio as A
            if action == "volume":
                return A.set_volume(int(args["track_index"]), int(args["clip_index"]), float(args["value"]))
            elif action == "fade_in":
                return A.add_fade_in(int(args["track_index"]), int(args["clip_index"]),
                                     int(args.get("duration_us", 500_000)))
            elif action == "fade_out":
                return A.add_fade_out(int(args["track_index"]), int(args["clip_index"]),
                                      int(args.get("duration_us", 500_000)))
            elif action == "effect":
                return A.apply_audio_effect(int(args["track_index"]), int(args["clip_index"]),
                                            args.get("preset", "DeNoise"))

    elif name == "cut.export":
        if backend in ("jianying", "capcut"):
            from .jianying.draft import Draft
            from .jianying import export as E
            draft = Draft.open(project_name=project, project_dir=project_dir, app=backend)
            return E.export(draft, args["output"], method=args.get("method", "ffmpeg"))
        elif backend == "premiere":
            from .premiere import export as E
            return E.export_to_file(args["output"], preset=args.get("preset", "h264_1080p"))

    elif name == "cut.create_plan":
        from .director import create_edit_plan
        return create_edit_plan(
            args["brief"],
            args.get("assets") or [],
            backend=backend,
            project=args.get("project"),
        )

    elif name == "cut.quality_check":
        from .quality import analyze_export
        return analyze_export(
            args["output"],
            expected_duration_us=args.get("expected_duration_us"),
            min_video_bitrate=int(args.get("min_video_bitrate", 1_000_000)),
        )

    return {"error": f"未知工具: {name}"}


# ---------------------------------------------------------------------------
# MCP Server 启动
# ---------------------------------------------------------------------------

async def serve():  # pragma: no cover
    """启动 MCP stdio server。"""
    if not HAS_MCP:
        print("mcp 包未安装。请运行: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = Server("cut")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        try:
            result = dispatch_tool(name, arguments or {})
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(serve())


if __name__ == "__main__":
    main()
