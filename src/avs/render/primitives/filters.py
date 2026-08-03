"""FFmpeg filter graphs for Timeline 1.1 primitives."""
from __future__ import annotations

from typing import Any

PRIMITIVES = frozenset({
    "screenshot_full", "screenshot_focus", "screenshot_pan", "screenshot_stack",
    "screenshot_compare", "screenshot_scroll", "screenshot_callout",
    "recording_focus_crop", "recording_cursor_follow", "recording_speed_ramp",
    "recording_freeze_callout", "recording_split_view", "kinetic_text",
    "metric_card", "picture_in_picture",
})


def apply_redactions(graph: str, redactions: list[list[float]] | None) -> str:
    """Burn normalized opaque masks after a primitive has produced its canvas."""
    if not redactions:
        return graph
    suffix = ",format=yuv420p"
    base = graph[:-len(suffix)] if graph.endswith(suffix) else graph
    masks: list[str] = []
    for raw in redactions:
        x, y, w, h = _normalized_region(raw, [0.0, 0.0, 1.0, 1.0])
        masks.append(
            f"drawbox=x=iw*{x:g}:y=ih*{y:g}:w=iw*{w:g}:h=ih*{h:g}:color=black@1:t=fill"
        )
    return base + "," + ",".join(masks) + suffix


def _cover(width: int, height: int) -> str:
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"


def _normalized_region(region: list[float] | None, default: list[float]) -> list[float]:
    values = region if isinstance(region, list) and len(region) == 4 else default
    x, y, w, h = (max(0.0, min(1.0, float(value))) for value in values)
    w = max(0.05, min(w, 1.0 - x))
    h = max(0.05, min(h, 1.0 - y))
    return [x, y, w, h]


def _roi(region: list[float] | None, default: list[float]) -> str:
    x, y, w, h = _normalized_region(region, default)
    return f"crop=iw*{w:g}:ih*{h:g}:iw*{x:g}:ih*{y:g}"


def primitive_filter(
    primitive: str,
    *,
    duration: float,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    region: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> str:
    """Build a stable single-input graph for a Timeline primitive."""
    if primitive not in PRIMITIVES:
        raise ValueError(f"未知渲染 Primitive: {primitive}")
    opts = options or {}
    frames = max(1, round(duration * fps))
    cover = _cover(width, height)
    if primitive == "screenshot_full":
        return f"{cover},fps={fps},format=yuv420p"
    if primitive == "screenshot_focus":
        zoom = float(opts.get("zoom", 1.06))
        return (
            f"{_roi(region, [0.12, 0.12, 0.76, 0.76])},{cover},"
            f"zoompan=z='min(zoom+0.0015,{zoom})':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
        )
    if primitive == "screenshot_pan":
        zoom = float(opts.get("zoom", 1.10))
        return f"{cover},zoompan=z='{zoom}':x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
    if primitive == "screenshot_scroll":
        zoom = float(opts.get("zoom", 1.08))
        return f"{cover},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{frames}':d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
    if primitive == "screenshot_stack":
        half = height // 2
        return (
            f"split=2[a][b];[a]scale={width}:{half}:force_original_aspect_ratio=increase,crop={width}:{half}[top];"
            f"[b]scale={width}:{half}:force_original_aspect_ratio=increase,crop={width}:{half},eq=brightness=-0.08[bottom];"
            f"[top][bottom]vstack=inputs=2,fps={fps},format=yuv420p"
        )
    if primitive == "screenshot_compare":
        half = width // 2
        return (
            f"split=2[a][b];[a]scale={half}:{height}:force_original_aspect_ratio=increase,crop={half}:{height}[left];"
            f"[b]scale={half}:{height}:force_original_aspect_ratio=increase,crop={half}:{height},eq=saturation=0.65[right];"
            f"[left][right]hstack=inputs=2,fps={fps},format=yuv420p"
        )
    if primitive == "screenshot_callout":
        x, y, w, h = _normalized_region(region, [0.1, 0.1, 0.8, 0.25])
        return f"{cover},drawbox=x=iw*{x:g}:y=ih*{y:g}:w=iw*{w:g}:h=ih*{h:g}:color=yellow@0.85:t=6,fps={fps},format=yuv420p"
    if primitive == "recording_focus_crop":
        return f"{_roi(region, [0.08, 0.18, 0.84, 0.64])},{cover},fps={fps},format=yuv420p"
    if primitive == "recording_cursor_follow":
        zoom = float(opts.get("zoom", 1.18))
        return f"{cover},zoompan=z='{zoom}':x='(iw-iw/zoom)*(0.5+0.4*sin(on/12))':y='(ih-ih/zoom)*(0.5+0.35*cos(on/15))':d={frames}:s={width}x{height}:fps={fps},format=yuv420p"
    if primitive == "recording_speed_ramp":
        return f"{cover},setpts=0.75*PTS,fps={fps},format=yuv420p"
    if primitive == "recording_freeze_callout":
        x, y, w, h = _normalized_region(region, [0.15, 0.2, 0.7, 0.2])
        return f"{cover},tpad=stop_mode=clone:stop_duration=0.35,drawbox=x=iw*{x:g}:y=ih*{y:g}:w=iw*{w:g}:h=ih*{h:g}:color=#ff4d4f@0.9:t=8,fps={fps},format=yuv420p"
    if primitive == "recording_split_view":
        half = height // 2
        return (
            f"split=2[a][b];[a]scale={width}:{half}:force_original_aspect_ratio=increase,crop={width}:{half}[top];"
            f"[b]{_roi(region, [0.1, 0.1, 0.8, 0.8])},scale={width}:{half}:force_original_aspect_ratio=increase,crop={width}:{half}[detail];"
            f"[top][detail]vstack=inputs=2,fps={fps},format=yuv420p"
        )
    if primitive == "picture_in_picture":
        pip_w, pip_h = int(width * 0.38), int(height * 0.28)
        return (
            f"split=2[base][pip];[base]{cover}[bg];"
            f"[pip]scale={pip_w}:{pip_h}:force_original_aspect_ratio=decrease,pad={pip_w}:{pip_h}:(ow-iw)/2:(oh-ih)/2:black[inset];"
            f"[bg][inset]overlay=W-w-54:H-h-120:format=auto,fps={fps},format=yuv420p"
        )
    if primitive == "kinetic_text":
        return f"{cover},drawbox=x=0:y=ih*0.38:w=iw:h=ih*0.24:color=black@0.52:t=fill,fps={fps},format=yuv420p"
    if primitive == "metric_card":
        return f"{cover},drawbox=x=iw*0.08:y=ih*0.28:w=iw*0.84:h=ih*0.44:color=white@0.88:t=fill,fps={fps},format=yuv420p"
    raise AssertionError(primitive)
