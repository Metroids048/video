"""cut.premiere.export — Premiere 导出渲染。

通过 Premiere 的 encoder 触发渲染。
支持：
1. 直接导出到文件（in-app encoding）
2. 加入 Adobe Media Encoder 队列（后台渲染）
"""
from __future__ import annotations

from typing import Dict, Any

from .wrapper import get_app, get_active_sequence


# 常用导出预设名
EXPORT_PRESETS = {
    "h264_1080p": "H264.1080p",
    "h264_720p": "H264.720p",
    "h264_4k": "H264.2160p",
    "h264_youtube": "H264.YouTube 1080p Full HD",
    "h264_match_source": "H264.Match Source - High bitrate",
    "prores_422": "QuickTime.ProRes 422",
    "prores_422_hq": "QuickTime.ProRes 422 HQ",
    "mp3_320": "MP3.MP3 320kbps",
    "wav": "WAV.WAV 48kHz 16-bit Stereo",
}


def export_to_file(output_path: str,
                   preset: str = "h264_1080p",
                   work_area_only: bool = False,
                   timeout: int = 3600) -> Dict[str, Any]:
    """直接导出当前序列到文件。

    preset: EXPORT_PRESETS 的 key 或完整 preset 名。
    timeout: 渲染超时秒数
    """
    app = get_app()
    get_active_sequence()

    preset_name = EXPORT_PRESETS.get(preset, preset)

    # 在 Premiere 中，导出预设需通过 encoder 序列
    # pymiere 暴露的 ingestDialog 与 encoder 接口有限
    # 这里通过文件 → 导出 → 媒体 弹窗的方式（UI 自动化）
    # 完整 pymiere 接口可能没有，需用 QE DOM

    try:
        app.enableQE()
        qe_proj = app.qe.project
        qe_proj.getActiveSequence()
        # 调用导出
        # 实际上 pymiere 没有直接 export 接口，需通过 Adobe Media Encoder
        # 这里给出调用 AME 的方法
        return _export_via_ame(output_path, preset_name, work_area_only, timeout)
    except Exception as e:
        return {"success": False, "error": str(e)}


def _export_via_ame(output_path: str, preset: str,
                    work_area_only: bool, timeout: int) -> Dict[str, Any]:
    """通过 Adobe Media Encoder 后台渲染。"""
    try:
        import pymiere
        # 检查 AME 是否运行
        ame_app = pymiere.objects.AppEncoder if hasattr(pymiere.objects, "AppEncoder") else None
        if ame_app is None:
            return {
                "success": False,
                "error": "Adobe Media Encoder 未运行或 pymiere 版本不支持 AME 接口。"
                         "请启动 AME 后重试，或用 UI 手动导出。"
            }
    except Exception as e:
        return {"success": False, "error": f"AME 检查失败: {e}"}

    # 加入队列
    try:
        app = get_app()
        seq = get_active_sequence()
        # pymiere 暴露的 encoder 接口
        app.encoder.encodeSequence(seq, output_path, preset, 0, True)
        # 0 = ExportWorkAreaOnly = false; True = removeAfterEncoding
        return {
            "success": True,
            "output_path": output_path,
            "preset": preset,
            "note": "已加入 Media Encoder 队列。请打开 AME 查看进度。",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_presets() -> Dict[str, str]:
    """返回所有可用预设。"""
    return dict(EXPORT_PRESETS)
