"""Deterministic media QA and human visual-review artifacts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema

from avs.qa.audio_levels import detect_max_volume
from avs.qa.black_frames import detect_black_intervals
from avs.qa.contact_sheet import create_final_contact_sheet
from avs.qa.decode import decode_error
from avs.qa.metadata import probe_media
from avs.qa.silence import detect_silence_intervals
from avs.qa.subtitle_checks import inspect_subtitles
from avs.qa.timeline_checks import inspect_timeline


@dataclass
class QACheck:
    check_id: str
    name: str
    passed: bool
    severity: str = "error"
    message: str | None = None
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "value": self.value,
        }


def _safe_call(function: Callable[[Path], Any], path: Path) -> tuple[Any, str | None]:
    try:
        return function(path), None
    except Exception as exc:
        return None, str(exc)


def _media_checks(path: Path, label: str, prefix: str, expected_duration: float) -> tuple[list[QACheck], dict[str, Any]]:
    checks: list[QACheck] = []
    if not path.is_file() or path.stat().st_size == 0:
        checks.append(QACheck(f"{prefix}_exists", f"{label} 存在且非空", False, message=f"文件不存在或为空: {path.name}"))
        return checks, {"error": "文件不存在或为空"}

    checks.append(QACheck(f"{prefix}_exists", f"{label} 存在且非空", True, value=path.stat().st_size))
    metadata = probe_media(path)
    metadata_error = metadata.get("error")
    checks.append(QACheck(
        f"{prefix}_metadata", f"{label} 元数据可读取", not metadata_error,
        message=str(metadata_error) if metadata_error else None,
        value=None if metadata_error else metadata,
    ))
    if metadata_error:
        return checks, metadata

    decode_message = decode_error(path)
    checks.append(QACheck(
        f"{prefix}_decode", f"{label} 可完整解码", decode_message is None,
        message=decode_message,
    ))

    width, height = metadata.get("width"), metadata.get("height")
    checks.append(QACheck(
        f"{prefix}_canvas", f"{label} 为 1080x1920", width == 1080 and height == 1920,
        message=None if (width, height) == (1080, 1920) else f"实际尺寸: {width}x{height}",
        value={"width": width, "height": height},
    ))
    fps = float(metadata.get("fps") or 0)
    checks.append(QACheck(
        f"{prefix}_fps", f"{label} 为 30fps", 29.0 <= fps <= 31.0,
        message=None if 29.0 <= fps <= 31.0 else f"实际帧率: {fps:.3f}", value=fps,
    ))
    duration = float(metadata.get("duration") or 0)
    duration_ok = expected_duration <= 0 or abs(duration - expected_duration) <= 0.25
    checks.append(QACheck(
        f"{prefix}_duration", f"{label} 时长匹配 timeline", duration_ok,
        message=None if duration_ok else f"视频 {duration:.3f}s，timeline {expected_duration:.3f}s",
        value=duration,
    ))
    video_codec = str(metadata.get("video_codec") or "")
    checks.append(QACheck(
        f"{prefix}_video_codec", f"{label} 使用 H.264", video_codec == "h264",
        message=None if video_codec == "h264" else f"实际视频编码: {video_codec or '无'}", value=video_codec,
    ))
    audio_codec = str(metadata.get("audio_codec") or "")
    checks.append(QACheck(
        f"{prefix}_audio_codec", f"{label} 包含 AAC 音轨", audio_codec == "aac",
        message=None if audio_codec == "aac" else f"实际音频编码: {audio_codec or '无音轨'}", value=audio_codec or None,
    ))
    return checks, metadata


def run_qa(ep_dir: Path, episode_id: str, *, force: bool = False) -> dict[str, Any]:
    """Run deterministic QA and write JSON, Markdown and visual-review artifacts."""
    delivery_dir = ep_dir / "delivery"
    report_path = delivery_dir / "qa-report.json"
    if report_path.exists() and not force:
        existing_report = json.loads(report_path.read_text(encoding="utf-8"))
        _validate_report(ep_dir, existing_report)
        return existing_report

    delivery_dir.mkdir(parents=True, exist_ok=True)
    timeline = inspect_timeline(ep_dir / "work" / "timeline.json")
    total_duration = float(timeline.get("total_duration") or 0)
    checks: list[QACheck] = []

    timeline_errors = list(timeline.get("errors", []))
    timeline_warnings = list(timeline.get("warnings", []))
    checks.append(QACheck(
        "timeline_semantics", "timeline Schema 与语义有效", not timeline_errors,
        message="; ".join(timeline_errors) or None,
        value={"errors": timeline_errors, "warnings": timeline_warnings},
    ))
    checks.append(QACheck(
        "timeline_warnings", "timeline 无非阻断警告", not timeline_warnings, "warning",
        message="; ".join(timeline_warnings) or None, value=timeline_warnings,
    ))

    media_specs = (
        (ep_dir / "renders" / "preview-clean.mp4", "无字幕 MP4", "clean"),
        (ep_dir / "renders" / "preview-with-captions.mp4", "带字幕 MP4", "captions"),
    )
    for path, label, prefix in media_specs:
        media_checks, _ = _media_checks(path, label, prefix, total_duration)
        checks.extend(media_checks)

    subtitle = inspect_subtitles(ep_dir / "work" / "captions.srt", total_duration)
    checks.append(QACheck(
        "subtitle_present", "SRT 字幕存在", not subtitle["missing"],
        message="work/captions.srt 不存在" if subtitle["missing"] else None,
    ))
    checks.append(QACheck(
        "subtitle_overflow", "字幕时间未越界", not subtitle["overflow"],
        message=f"越界字幕编号: {', '.join(subtitle['overflow'])}" if subtitle["overflow"] else None,
        value=subtitle["overflow"],
    ))
    checks.append(QACheck(
        "subtitle_line_length", "字幕单行长度适合竖屏", not subtitle["long_lines"], "warning",
        message=f"{len(subtitle['long_lines'])} 行超过 28 字" if subtitle["long_lines"] else None,
        value=subtitle["long_lines"],
    ))

    placeholder_count = int(timeline.get("placeholder_count") or 0)
    checks.append(QACheck(
        "placeholder_assets", "无待补素材占位卡", placeholder_count == 0, "warning",
        message=f"{placeholder_count} 个占位卡需人工补充素材" if placeholder_count else None,
        value=placeholder_count,
    ))

    final_video = ep_dir / "renders" / "preview-with-motion.mp4"
    if not final_video.is_file():
        final_video = ep_dir / "renders" / "preview-with-captions.mp4"
    final_probe, final_probe_error = _safe_call(probe_media, final_video)
    final_meta = final_probe if final_video.is_file() and isinstance(final_probe, dict) else {
        "error": final_probe_error or "最终视觉视频不存在",
    }
    checks.append(QACheck(
        "final_visual_source", "最终视觉检查源可用", "error" not in final_meta,
        message=str(final_meta.get("error")) if final_meta.get("error") else None,
        value=final_video.relative_to(ep_dir).as_posix() if final_video.is_file() else None,
    ))

    if "error" not in final_meta:
        black_intervals, black_error = _safe_call(detect_black_intervals, final_video)
        long_black = [item for item in (black_intervals or []) if item["duration"] >= 1.0]
        checks.append(QACheck(
            "black_frames", "最终视频无连续 1 秒黑帧", black_error is None and not long_black,
            message=black_error or (f"发现 {len(long_black)} 段连续黑帧" if long_black else None), value=long_black,
        ))

        silence_intervals, silence_error = _safe_call(detect_silence_intervals, final_video)
        planned_audio = bool(timeline.get("planned_audio"))
        long_silence = list(silence_intervals or [])
        silence_passed = silence_error is None and (not planned_audio or not long_silence)
        silence_message = silence_error
        if not silence_message and planned_audio and long_silence:
            silence_message = f"计划音轨存在，检测到 {len(long_silence)} 段长静音"
        elif not planned_audio:
            silence_message = "timeline 未计划音轨；静音 AAC 为正常降级"
        checks.append(QACheck(
            "planned_audio_silence", "计划音轨无异常长静音", silence_passed,
            "error" if planned_audio else "info", silence_message, long_silence,
        ))

        peak, peak_error = _safe_call(detect_max_volume, final_video)
        peak_ok = peak_error is None and (peak is None or float(peak) <= -1.0)
        checks.append(QACheck(
            "audio_peak", "音频峰值不高于 -1 dBFS", peak_ok,
            message=peak_error or (f"峰值 {peak} dBFS，可能削波" if not peak_ok else None), value=peak,
        ))

        contact_path = delivery_dir / "qa-contact-sheet.jpg"
        try:
            contact = create_final_contact_sheet(final_video, contact_path, float(final_meta.get("duration") or 0))
            contact_ok = contact is not None and contact.is_file()
            contact_message = None if contact_ok else "联系表未生成，请人工打开最终视频复核"
        except Exception as exc:
            contact_ok, contact_message = False, str(exc)
        checks.append(QACheck(
            "visual_contact_sheet", "生成视觉联系表", contact_ok, "warning",
            contact_message, "delivery/qa-contact-sheet.jpg" if contact_ok else None,
        ))
    else:
        checks.extend([
            QACheck("black_frames", "最终视频无连续 1 秒黑帧", False, message="无可检查的最终视频"),
            QACheck("planned_audio_silence", "计划音轨无异常长静音", False, message="无可检查的最终视频"),
            QACheck("audio_peak", "音频峰值不高于 -1 dBFS", False, message="无可检查的最终视频"),
            QACheck("visual_contact_sheet", "生成视觉联系表", False, "warning", "无可检查的最终视频"),
        ])

    errors = [check for check in checks if not check.passed and check.severity == "error"]
    warnings = [check for check in checks if not check.passed and check.severity == "warning"]
    report: dict[str, Any] = {
        "episode_id": episode_id,
        "passed": not errors,
        "checks": [check.to_dict() for check in checks],
        "summary": f"{len(checks)} 项检查，{len(errors)} error，{len(warnings)} warning",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _validate_report(ep_dir, report)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qa_markdown(report, delivery_dir / "qa-report.md")
    _write_visual_review(ep_dir, final_video, report, delivery_dir / "visual-review.md")
    return report


def _project_root(ep_dir: Path) -> Path:
    for candidate in (ep_dir, *ep_dir.parents):
        if (candidate / "schemas" / "qa-report.schema.json").is_file():
            return candidate
    raise FileNotFoundError("无法定位 schemas/qa-report.schema.json")


def _validate_report(ep_dir: Path, report: dict[str, Any]) -> None:
    schema = json.loads((_project_root(ep_dir) / "schemas" / "qa-report.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(report)


def _write_qa_markdown(report: dict[str, Any], output: Path) -> None:
    lines = [
        f"# QA 报告 - {report['episode_id']}", "",
        f"生成时间: {report['generated_at']}",
        f"总体结果: {'通过' if report['passed'] else '未通过'}", "", "## 检查项", "",
    ]
    for check in report["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- [{mark}] [{check['severity'].upper()}] {check['name']}")
        if check.get("message"):
            lines.append(f"  - {check['message']}")
    lines.extend(["", f"汇总: {report['summary']}"])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_visual_review(ep_dir: Path, final_video: Path, report: dict[str, Any], output: Path) -> None:
    source = final_video.relative_to(ep_dir).as_posix() if final_video.is_file() else "不可用"
    lines = [
        f"# 视觉复核 - {report['episode_id']}", "",
        f"复核视频: `{source}`", "",
        "联系表: `delivery/qa-contact-sheet.jpg`", "",
        "## 人工复核项", "",
        "- 标题、信息卡和结尾卡是否完整可读",
        "- 字幕是否处于安全区并与语音同步",
        "- 素材裁切、contain/cover 选择是否合理",
        "- 转场、节奏、品牌信息和结尾行动指引是否合适",
        "- 是否仍有占位卡、事实待核验或版权风险",
        "", "确定性 QA 不代表主观视觉验收；发布前仍需人工完整播放。", "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
