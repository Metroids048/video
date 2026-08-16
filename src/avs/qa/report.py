"""Deterministic media QA and human visual-review artifacts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema

from avs.qa.approval import verify_approval_current
from avs.qa.audio_levels import audio_is_publishable, detect_audio_levels
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


def _final_video_path(ep_dir: Path) -> Path:
    candidates = (
        ep_dir / "renders" / "final-with-captions.mp4",
        ep_dir / "renders" / "preview-with-motion.mp4",
        ep_dir / "renders" / "preview-with-captions.mp4",
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    if not path.is_file():
        return ""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_quality_config(ep_dir: Path) -> dict[str, Any]:
    """Load quality.yaml config from project root."""
    for candidate in (ep_dir, *ep_dir.parents):
        config_path = candidate / "config" / "quality.yaml"
        if config_path.is_file():
            import yaml
            return yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return {}


def _compute_input_fingerprint(
    ep_dir: Path,
    final_video: Path,
    publishable: bool,
) -> str:
    """Compute fingerprint of all QA inputs to detect staleness."""
    parts = [
        _sha256_file(final_video),
        _sha256_file(ep_dir / "work" / "timeline.json"),
        _sha256_file(ep_dir / "work" / "captions.srt"),
        _sha256_file(ep_dir / "work" / "content" / "creative-profile.json"),
        _sha256_file(ep_dir / "delivery" / "visual-approval.json"),
    ]

    for candidate in (ep_dir, *ep_dir.parents):
        config_path = candidate / "config" / "quality.yaml"
        if config_path.is_file():
            parts.append(_sha256_file(config_path))
            break

    parts.append("publishable=true" if publishable else "publishable=false")

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


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


def run_qa(ep_dir: Path, episode_id: str, *, publishable: bool = True, force: bool = False, require_human_approval: bool = True) -> dict[str, Any]:
    """Run deterministic QA with three-layer gate logic and fingerprint checking."""
    delivery_dir = ep_dir / "delivery"
    report_path = delivery_dir / "qa-report.json"

    final_video = _final_video_path(ep_dir)
    current_fingerprint = _compute_input_fingerprint(ep_dir, final_video, publishable)

    if report_path.exists() and not force:
        existing_report = json.loads(report_path.read_text(encoding="utf-8"))
        existing_fingerprint = existing_report.get("input_fingerprint", "")
        if existing_fingerprint == current_fingerprint:
            _validate_report(ep_dir, existing_report)
            return existing_report

    delivery_dir.mkdir(parents=True, exist_ok=True)
    timeline = inspect_timeline(ep_dir / "work" / "timeline.json")
    total_duration = float(timeline.get("total_duration") or 0)
    quality_config = _load_quality_config(ep_dir)

    checks: list[QACheck] = []
    blocking_reasons: list[str] = []

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

    clean_video = ep_dir / "renders" / "final-clean.mp4"
    if not clean_video.is_file():
        clean_video = ep_dir / "renders" / "preview-clean.mp4"
    caption_video = ep_dir / "renders" / "final-with-captions.mp4"
    if not caption_video.is_file():
        caption_video = ep_dir / "renders" / "preview-with-captions.mp4"
    media_specs = (
        (clean_video, "无字幕 MP4", "clean"),
        (caption_video, "带字幕 MP4", "captions"),
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
    if publishable:
        placeholder_severity = "error"
        placeholder_passed = placeholder_count == 0
        placeholder_message = (
            f"{placeholder_count} 个占位卡，publishable=true 时不允许"
            if placeholder_count > 0 else None
        )
        if not placeholder_passed:
            blocking_reasons.append(f"存在 {placeholder_count} 个占位卡")
    else:
        placeholder_severity = "warning"
        placeholder_passed = placeholder_count == 0
        placeholder_message = (
            f"{placeholder_count} 个占位卡需人工补充素材"
            if placeholder_count > 0 else None
        )

    checks.append(QACheck(
        "placeholder_assets",
        "无待补素材占位卡" if publishable else "占位卡记录",
        placeholder_passed,
        placeholder_severity,
        placeholder_message,
        placeholder_count,
    ))

    final_video = _final_video_path(ep_dir)
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

        levels, levels_error = _safe_call(detect_audio_levels, final_video)
        mean_db, peak = levels if isinstance(levels, tuple) else (None, None)
        has_audio = bool(final_meta.get("audio_codec"))
        audible_ok = levels_error is None and audio_is_publishable(
            has_audio=has_audio, mean_db=mean_db, max_db=peak
        )
        checks.append(QACheck(
            "audio_audible", "音频实际可听而非仅存在音轨", audible_ok,
            message=levels_error or (
                f"平均响度 {mean_db} dBFS / 峰值 {peak} dBFS，音轨存在但实际不可听"
                if not audible_ok else None
            ),
            value={"mean_db": mean_db, "max_db": peak},
        ))
        peak_ok = levels_error is None and peak is not None and float(peak) <= -1.0
        checks.append(QACheck(
            "audio_peak", "音频峰值不高于 -1 dBFS", peak_ok,
            message=levels_error or (f"峰值 {peak} dBFS，可能削波或无可测音频" if not peak_ok else None), value=peak,
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
            QACheck("audio_audible", "音频实际可听而非仅存在音轨", False, message="无可检查的最终视频"),
            QACheck("audio_peak", "音频峰值不高于 -1 dBFS", False, message="无可检查的最终视频"),
            QACheck("visual_contact_sheet", "生成视觉联系表", False, "warning", "无可检查的最终视频"),
        ])

    input_manifest_path = ep_dir / "work" / "input-manifest.json"
    evidence_path = ep_dir / "work" / "content" / "evidence-map.json"
    shot_plan_path = ep_dir / "work" / "content" / "shot-plan.json"
    visual_review_path = ep_dir / "work" / "qa" / "visual-review.json"
    reference_selection_path = ep_dir / "work" / "content" / "reference-selection.json"
    if all(path.is_file() for path in (input_manifest_path, evidence_path, shot_plan_path)):
        from avs.qa.evidence_coverage import check_evidence_coverage
        from avs.qa.input_coverage import check_input_coverage
        from avs.qa.pacing import check_pacing

        active_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
        evidence_map = json.loads(evidence_path.read_text(encoding="utf-8"))
        shot_plan = json.loads(shot_plan_path.read_text(encoding="utf-8"))
        used_asset_ids = {
            ref.get("asset_id")
            for shot in shot_plan.get("shots", [])
            for ref in shot.get("asset_refs", [])
            if ref.get("asset_id")
        }
        used_asset_ids.update(shot_plan.get("analysis_asset_ids", []))
        exclusions = {
            item.get("asset_id") for item in shot_plan.get("excluded_assets", [])
            if item.get("excluded") and item.get("asset_id")
        }
        input_coverage = check_input_coverage(active_manifest, used_asset_ids, approved_exclusions=exclusions)
        evidence_coverage = check_evidence_coverage(evidence_map, active_manifest)
        pacing = check_pacing(shot_plan, platform="douyin")
        checks.extend([
            QACheck("active_input_coverage", "must-use 素材覆盖", input_coverage["passed"], value=input_coverage,
                    message=None if input_coverage["passed"] else f"未使用: {input_coverage['missing_asset_ids']}"),
            QACheck("active_evidence_coverage", "旁白事实证据覆盖", evidence_coverage["passed"], value=evidence_coverage,
                    message=None if evidence_coverage["passed"] else "存在未绑定真实素材的事实"),
            QACheck("active_pacing", "平台节奏与产品画面占比", pacing["passed"], value=pacing,
                    message=None if pacing["passed"] else "前 10 秒变化、静态时长或产品画面占比不合格"),
        ])
        visual_review = json.loads(visual_review_path.read_text(encoding="utf-8")) if visual_review_path.is_file() else {"passed": False, "blocked": True}
        visual_passed = bool(visual_review.get("passed")) and not bool(visual_review.get("blocked"))
        checks.append(QACheck(
            "active_visual_review", "视觉语义审核", visual_passed,
            message=None if visual_passed else "视觉审核未通过或已阻塞", value=visual_review,
        ))
        if reference_selection_path.is_file():
            selected = json.loads(reference_selection_path.read_text(encoding="utf-8"))
            selected_ids = {item.get("pattern_id") for item in selected.get("selections", [])}
            shot_ids = {
                pattern for shot in shot_plan.get("shots", [])
                for pattern in shot.get("reference_pattern_ids", [])
            }
            reference_passed = bool(selected_ids) and selected_ids.issubset(shot_ids)
        else:
            reference_passed = False
            selected_ids = set()
        checks.append(QACheck(
            "active_reference_trace", "Reference Pattern 进入 Shot Plan", reference_passed,
            message=None if reference_passed else "缺少具体 pattern_id 或未进入 Shot Plan",
            value=sorted(selected_ids),
        ))

    errors = [check for check in checks if not check.passed and check.severity == "error"]
    warnings = [check for check in checks if not check.passed and check.severity == "warning"]
    for check in errors:
        if check.check_id.startswith("active_") and check.name not in blocking_reasons:
            blocking_reasons.append(check.name)

    technical_passed = not errors
    publishability_passed = True

    if publishable:
        if placeholder_count > 0:
            publishability_passed = False

        planned_audio = bool(timeline.get("planned_audio"))
        if planned_audio and quality_config.get("quality", {}).get("publishable", {}).get("require_non_silent_audio", True):
            silence_check = next((c for c in checks if c.check_id == "planned_audio_silence"), None)
            if silence_check and not silence_check.passed:
                publishability_passed = False
                if "静音" not in "".join(blocking_reasons):
                    blocking_reasons.append("音频静音或异常长静音")
            audible_check = next((c for c in checks if c.check_id == "audio_audible"), None)
            if audible_check and not audible_check.passed:
                publishability_passed = False
                blocking_reasons.append("音轨存在但实际响度不可听")

    human_approved = not require_human_approval
    approval_message = None
    if publishable and require_human_approval and quality_config.get("quality", {}).get("publishable", {}).get("require_human_visual_approval", True):
        is_valid, error = verify_approval_current(ep_dir, final_video)
        human_approved = is_valid
        if not is_valid:
            approval_message = error
            blocking_reasons.append(f"人工批准: {error}")
    elif not publishable:
        human_approved = True
        approval_message = "publishable=false，无需人工批准"

    checks.append(QACheck(
        "human_visual_approval",
        "人工视觉批准有效" if publishable else "人工批准（非必需）",
        human_approved,
        "error" if publishable and require_human_approval else "info",
        approval_message,
        None,
    ))

    if publishable:
        passed = technical_passed and publishability_passed and human_approved
    else:
        passed = technical_passed

    report: dict[str, Any] = {
        "episode_id": episode_id,
        "passed": passed,
        "technical_passed": technical_passed,
        "publishability_passed": publishability_passed,
        "human_approved": human_approved,
        "blocking_reasons": blocking_reasons,
        "input_fingerprint": current_fingerprint,
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
