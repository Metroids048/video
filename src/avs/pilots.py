"""SCREEN_DOCUMENTARY mining, Pilot rendering, and fail-closed visual gate.

All durable artifacts live below the Episode directory.  The VCI package and
the original capture are read-only inputs; no code here mutates either of them.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from avs.qa.creative_sampling import build_contact_sheets, extract_frames, extract_uniform_frames
from avs.render.captions import build_srt_from_words
from avs.render.layouts import choose_layout, is_landscape


PILOT_IDS = ("primary",)
CORE_DIMENSIONS = (
    "first_frame", "hook", "mobile_readability", "real_evidence",
    "caption_intrusion", "visual_density", "pacing", "ppt_feel",
    "cheap_ai_feel", "continue_watching",
)
MAX_REPAIR_ROUNDS = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def screen_documentary_rules() -> dict[str, Any]:
    payload = yaml.safe_load((_root() / "config" / "production-types.yaml").read_text(encoding="utf-8"))
    raw = dict(payload["production_types"]["SCREEN_DOCUMENTARY"])
    # Normalize the product contract's names to the renderer's internal gate keys.
    pilot_seconds = raw.get("pilot_seconds", [20, 30])
    raw.setdefault("pilot_duration_seconds", {"min": float(pilot_seconds[0]), "max": float(pilot_seconds[1])})
    raw.setdefault("real_screen_footage_ratio_min", raw.get("real_screen_footage_min_ratio", 0.7))
    raw.setdefault("generated_card_count_max", raw.get("generated_fullscreen_cards_max", 2))
    raw.setdefault("generated_motion_total_seconds_max", raw.get("generated_fullscreen_cards_total_seconds_max", 5))
    return raw


def _source_recording(ep_dir: Path) -> Path:
    """Resolve the one explicitly selected recording from this Episode only."""
    manifest_path = ep_dir / "work" / "input-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("SCREEN_DOCUMENTARY 缺少当前 Episode 的 input-manifest.json")
    manifest = _read(manifest_path)
    recordings = [
        asset for asset in manifest.get("assets", [])
        if asset.get("source_type") in {"recording", "video"}
        and asset.get("status", "ok") == "ok"
        and asset.get("working_path")
    ]
    selected = [asset for asset in recordings if asset.get("must_use") is True]
    if len(selected) != 1:
        raise RuntimeError(
            "SCREEN_DOCUMENTARY 必须明确唯一 must_use 主录屏；"
            f"当前可用录屏 {len(recordings)} 个，must_use 主录屏 {len(selected)} 个"
        )
    working_path = Path(str(selected[0]["working_path"]))
    if working_path.is_absolute() or ".." in working_path.parts or not working_path.as_posix().startswith("work/prepared/"):
        raise RuntimeError("SCREEN_DOCUMENTARY 主录屏必须引用 Episode 内的 work/prepared 工作副本")
    source = (ep_dir / working_path).resolve()
    try:
        source.relative_to((ep_dir / "work" / "prepared").resolve())
    except ValueError as exc:
        raise RuntimeError("SCREEN_DOCUMENTARY 主录屏路径越过 Episode 工作副本边界") from exc
    if not source.is_file():
        raise RuntimeError(f"SCREEN_DOCUMENTARY 主录屏工作副本不存在: {working_path.as_posix()}")
    return source


def _prepared_source(ep_dir: Path) -> Path:
    # Ingest already created this Episode-local immutable working copy.
    return _source_recording(ep_dir)


def mine_story(ep_dir: Path) -> dict[str, Path]:
    """Mine a screen story from the current Episode's analyzed artifacts."""
    source = _prepared_source(ep_dir)
    manifest_path = ep_dir / "work" / "input-manifest.json"
    recording_analysis_path = ep_dir / "work" / "analysis" / "recording-analysis.json"
    intelligence_path = ep_dir / "work" / "analysis" / "asset-intelligence.json"
    for required in (manifest_path, recording_analysis_path, intelligence_path):
        if not required.is_file():
            raise RuntimeError(f"SCREEN_DOCUMENTARY 缺少当前 Episode 分析产物: {required.relative_to(ep_dir).as_posix()}")
    manifest = _read(manifest_path)
    analysis = _read(recording_analysis_path)
    intelligence = _read(intelligence_path)
    if analysis.get("episode_id") != ep_dir.name or intelligence.get("episode_id") != ep_dir.name:
        raise RuntimeError("SCREEN_DOCUMENTARY 分析产物 episode_id 与当前 Episode 不一致")
    recording_assets = [
        asset for asset in manifest.get("assets", [])
        if asset.get("source_type") in {"recording", "video"} and asset.get("must_use") is True
    ]
    if len(recording_assets) != 1:
        raise RuntimeError("SCREEN_DOCUMENTARY 必须从当前 Episode 唯一主录屏建立故事")
    asset_id = str(recording_assets[0]["asset_id"])
    analyzed = next((item for item in analysis.get("recordings", []) if item.get("asset_id") == asset_id), None)
    if not isinstance(analyzed, dict):
        raise RuntimeError(f"当前 Episode 没有主录屏分析结果: {asset_id}")
    dimensions = (recording_assets[0].get("original_width"), recording_assets[0].get("original_height"))
    landscape = is_landscape(*dimensions)
    intelligence_item = next((item for item in intelligence.get("assets", []) if item.get("asset_id") == asset_id), {})
    regions = intelligence_item.get("regions", []) if isinstance(intelligence_item, dict) else []
    usable = analyzed.get("usable_segments", [])
    if not usable:
        raise RuntimeError("当前 Episode 主录屏没有可用 source timeline")
    scenes: list[dict[str, Any]] = []
    for index, segment in enumerate(usable, start=1):
        start, end = float(segment.get("start", 0.0)), float(segment.get("end", 0.0))
        if end <= start:
            continue
        scenes.append({
            "id": f"{asset_id}-segment-{index:03d}",
            "source_start": start,
            "source_end": end,
            "label": str(intelligence_item.get("summary") or f"screen segment {index}"),
            "target": str(regions[0].get("meaning") if regions and isinstance(regions[0], dict) else "full page context"),
            "region": [0.0, 0.0, 1.0, 1.0],
            "layout": "fit_full_frame",
            "landscape": landscape,
            "evidence": "SOURCE_ANALYZED",
        })
    validate_source_order(scenes)
    validate_context_first(scenes)
    output = ep_dir / "work" / "director"
    screen_index = {
        "episode_id": ep_dir.name,
        "source_asset_id": asset_id,
        "source_recording": source.relative_to(ep_dir).as_posix(),
        "source_sha256": _sha256(source),
        "source_dimensions": {"width": dimensions[0], "height": dimensions[1]},
        "scenes": scenes,
        "context_first": True,
        "source_order": "monotonic_after_optional_cold_open",
        "generated_at": _now(),
    }
    evidence_index = {
        "episode_id": ep_dir.name,
        "source_asset_id": asset_id,
        "facts": intelligence_item.get("visible_facts", []) if isinstance(intelligence_item, dict) else [],
        "scenes": scenes,
    }
    _write(output / "录屏内容索引.json", screen_index)
    _write(output / "证据镜头索引.json", evidence_index)
    (output / "推荐片段.md").write_text(
        "# 推荐片段\n\n" + "\n".join(
            f"- {scene['source_start']:.3f}-{scene['source_end']:.3f}s：{scene['target']}（先保留完整页面上下文）。"
            for scene in scenes
        ) + "\n",
        encoding="utf-8",
    )
    (output / "禁止使用片段.md").write_text(
        "# 禁止使用片段\n\n- 未经分析的录屏区间。\n- 未建立完整页面上下文就进入局部 ROI。\n- 为制造变化而添加人工镜头运动。\n",
        encoding="utf-8",
    )
    return {"screen_index": output / "录屏内容索引.json", "evidence_index": output / "证据镜头索引.json", "recommended": output / "推荐片段.md", "forbidden": output / "禁止使用片段.md"}


def direct_story(ep_dir: Path) -> Path:
    index_path = ep_dir / "work" / "director" / "录屏内容索引.json"
    evidence_path = ep_dir / "work" / "director" / "证据镜头索引.json"
    if not index_path.is_file() or not evidence_path.is_file():
        raise RuntimeError("请先完成当前 Episode 的 story-mine")
    index, evidence = _read(index_path), _read(evidence_path)
    scenes = index.get("scenes", [])
    if not scenes:
        raise RuntimeError("当前 Episode 没有可用于 direct 的真实录屏镜头")
    payload = {
        "episode_id": ep_dir.name,
        "production_type": "SCREEN_DOCUMENTARY",
        "source_asset_id": index.get("source_asset_id"),
        "core_story": str(evidence.get("facts", [])[0] if evidence.get("facts") else "从真实录屏过程解释一个可验证的问题"),
        "fact_boundary": [str(fact) for fact in evidence.get("facts", [])],
        "target_duration_seconds": {"min": 25, "max": 60},
        "excluded": ["未出现在当前 Episode 分析中的事实", "未经授权的局部裁切", "人工镜头运动"],
        "structure": [scene.get("target", "full page context") for scene in scenes],
        "generated_at": _now(),
    }
    return _write(ep_dir / "work" / "director" / "short-video-brief.json", payload)


def validate_source_order(clips: list[dict[str, Any]], *, cold_open_max_seconds: float = 4.0) -> None:
    """Reject source-time teleportation while allowing one short cold open.

    ``source_start``/``source_end`` describe offsets in the original recording,
    while ``start``/``duration`` describe output time.  The first clip may be an
    explicitly marked cold open up to four seconds; all following source clips
    must move forward (or continue at the same offset) in source time.
    """
    if not isinstance(clips, list) or not clips:
        raise ValueError("source timeline 不能为空")
    previous_end: float | None = None
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError(f"source timeline 第 {index + 1} 项无效")
        try:
            start = float(clip["source_start"])
            end = float(clip["source_end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"source timeline 第 {index + 1} 项缺少 source_start/source_end") from exc
        if start < 0 or end <= start:
            raise ValueError(f"source timeline 第 {index + 1} 项区间无效")
        if index == 0 and bool(clip.get("cold_open")):
            output_duration = float(clip.get("duration", end - start))
            if output_duration > cold_open_max_seconds:
                raise ValueError(f"cold open 不得超过 {cold_open_max_seconds:g} 秒")
        elif previous_end is not None and start < previous_end:
            raise ValueError(
                "source timeline 必须 monotonic："
                f"第 {index + 1} 镜 source_start={start:g} < 前镜 source_end={previous_end:g}"
            )
        previous_end = end


def validate_context_first(clips: list[dict[str, Any]]) -> None:
    """Require full-page context before any landscape destructive ROI crop."""
    if not isinstance(clips, list) or not clips:
        raise ValueError("screen timeline 不能为空")
    context_seen = False
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError(f"screen timeline 第 {index + 1} 项无效")
        landscape = bool(clip.get("landscape"))
        layout = str(clip.get("layout") or "fit_full_frame")
        destructive = layout in {"screen_focus", "roi_crop", "cover", "screen_stack"}
        authorized = clip.get("allow_destructive_crop") is True and clip.get("roi_authorized") is True
        is_full_frame = layout in {"fit_full_frame", "contain", "full_frame", "context"} or not destructive
        if landscape and destructive:
            if not context_seen:
                raise ValueError("landscape ROI 必须先建立完整页面 context")
            if not authorized:
                raise ValueError("landscape ROI 必须显式授权 allow_destructive_crop=true 且 roi_authorized=true")
        if landscape and is_full_frame:
            context_seen = True


def _pilot_filter(spec: dict[str, Any], source_width: int | None, source_height: int | None) -> tuple[str, dict[str, Any]]:
    """Build a context-preserving filter and normalized clip metadata."""
    landscape = is_landscape(source_width, source_height)
    requested_layout = str(spec.get("layout") or ("fit_full_frame" if landscape else "contain"))
    transform = {
        "layout": requested_layout,
        "region": spec.get("region"),
        "allow_destructive_crop": spec.get("allow_destructive_crop") is True,
    }
    if spec.get("roi_authorized") is True:
        transform["roi_authorized"] = True
    vf = choose_layout(transform, source_width, source_height)
    # For a landscape source, choose_layout safely falls back to full-frame when
    # authorization/context is absent.  The contract validator catches an ROI
    # requested as the first shot before FFmpeg is invoked.
    return vf, transform


def _pilot_spec(ep_dir: Path, variant: str) -> list[dict[str, Any]]:
    """Load episode-specific shots from the locked Creative/Shot Plan."""
    plan_path = ep_dir / "work" / "content" / "pilot-shot-plan.json"
    if not plan_path.is_file():
        raise RuntimeError("缺少数据驱动的 pilot-shot-plan.json；Pilot 不得从 runtime 硬编码 EP 文案")
    payload = _read(plan_path)
    variants = payload.get("variants", payload)
    specs = variants.get(variant)
    if not isinstance(specs, list) or not specs:
        raise RuntimeError(f"pilot-shot-plan.json 缺少 variant={variant}")
    required = {"start", "duration", "in", "target", "spoken"}
    source_index_path = ep_dir / "work" / "director" / "录屏内容索引.json"
    if not source_index_path.is_file():
        raise RuntimeError("缺少当前 Episode 的录屏内容索引")
    source_index = _read(source_index_path)
    source_asset_id = source_index.get("source_asset_id")
    source_dimensions = source_index.get("source_dimensions", {})
    normalized: list[dict[str, Any]] = []
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict) or not required.issubset(spec):
            missing = sorted(required - set(spec)) if isinstance(spec, dict) else sorted(required)
            raise RuntimeError(f"pilot-shot-plan.json 第 {index + 1} 镜缺少字段: {missing}")
        item = dict(spec)
        item["source_start"] = float(item["in"])
        item["source_end"] = float(item["in"]) + float(item["duration"])
        item.setdefault("source_asset_id", source_asset_id)
        item.setdefault(
            "landscape",
            is_landscape(source_dimensions.get("width"), source_dimensions.get("height")),
        )
        item.setdefault("layout", "fit_full_frame" if item["landscape"] else "contain")
        item.setdefault("region", [0.0, 0.0, 1.0, 1.0])
        normalized.append(item)
    if any(item.get("source_asset_id") != source_asset_id for item in normalized):
        raise RuntimeError("pilot-shot-plan.json 引用了当前 Episode 主录屏之外的素材")
    validate_source_order(normalized)
    validate_context_first(normalized)
    return normalized


def _srt_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds_int, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds_int:02},{milliseconds:03}"


def _subtitles_filter(path: Path) -> str:
    filename = path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
    # Restrained single-line captions: no black outline, a translucent backing,
    # and enough bottom margin to avoid the primary ROI.
    style = "FontName=Microsoft YaHei,FontSize=16,PrimaryColour=&H00FFFFFF,BackColour=&H70000000,BorderStyle=3,Outline=0,Shadow=0,Alignment=2,MarginV=120,MarginL=72,MarginR=72"
    return f"subtitles='{filename}':force_style='{style}'"


def _run(command: list[str], *, timeout: int, error: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{error}: {(result.stderr or result.stdout)[-600:]}")


def _ensure_narration(work: Path, specs: list[dict[str, Any]], *, force: bool) -> Path:
    output = work / "narration.mp3"
    provenance = work / "narration.json"
    words = work / "narration.words.json"
    if not output.is_file() or not words.is_file() or not provenance.is_file():
        raise RuntimeError("Pilot 需要已经锁定的旁白、voice-profile 和词级强制对齐；禁止使用 Edge TTS 自动补旁白")
    metadata = _read(provenance)
    if metadata.get("provider") == "edge_tts" or not metadata.get("voice_profile"):
        raise RuntimeError("Edge TTS 只能作为开发 fallback，不能进入 Pilot 或 READY_TO_PUBLISH")
    return output


def _adjust_region(region: list[float], zoom: float) -> list[float]:
    if zoom <= 1:
        return region
    x, y, w, h = region
    width, height = w / zoom, h / zoom
    return [max(0.0, min(1 - width, x + (w - width) / 2)), max(0.0, min(1 - height, y + (h - height) / 2)), width, height]


def _render_pilot(ep_dir: Path, variant: str, specs: list[dict[str, Any]], *, force: bool) -> dict[str, Path]:
    source, work, renders = _prepared_source(ep_dir), ep_dir / "work" / "pilots" / variant, ep_dir / "renders" / "pilots"
    output, srt, timeline_path = renders / f"pilot-{variant}.mp4", work / "captions.srt", work / "timeline.json"
    if output.is_file() and srt.is_file() and timeline_path.is_file() and not force:
        return {"video": output, "srt": srt, "timeline": timeline_path}
    work.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)
    screen_index = _read(ep_dir / "work" / "director" / "录屏内容索引.json")
    dimensions = screen_index.get("source_dimensions", {})
    source_width, source_height = dimensions.get("width"), dimensions.get("height")
    validate_source_order(specs)
    validate_context_first(specs)
    segments: list[Path] = []
    clips: list[dict[str, Any]] = []
    for index, spec in enumerate(specs):
        segment = work / f"segment-{index:02}.mp4"
        vf, transform = _pilot_filter(spec, source_width, source_height)
        _run(["ffmpeg", "-y", "-ss", str(spec["in"]), "-i", str(source), "-t", str(spec["duration"]), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", str(segment)], timeout=180, error=f"Pilot {variant} 镜头渲染失败")
        segments.append(segment)
        clips.append({
            "source_asset_id": screen_index.get("source_asset_id"),
            "source_start": float(spec["in"]),
            "source_end": float(spec["in"]) + float(spec["duration"]),
            "target": spec["target"],
            "layout": transform["layout"],
            "region": spec.get("region", [0.0, 0.0, 1.0, 1.0]),
            "landscape": is_landscape(source_width, source_height),
            "allow_destructive_crop": transform.get("allow_destructive_crop") is True,
            "roi_authorized": transform.get("roi_authorized") is True,
            "zoom": 1.0,
            "pan": None,
            "caption_safe_zone": "bottom",
            "minimum_mobile_readability": True,
        })
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{part.resolve().as_posix()}'\n" for part in segments), encoding="utf-8")
    narration = _ensure_narration(work, specs, force=force)
    total = sum(float(item["duration"]) for item in specs)
    build_srt_from_words(work / "narration.words.json", srt, total_duration=total)
    # apad preserves the visual duration when narration ends before the last shot.
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(narration), "-filter_complex", "[1:a]apad=pad_dur=12[a]", "-map", "0:v:0", "-map", "[a]", "-vf", _subtitles_filter(srt), "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-pix_fmt", "yuv420p", str(output)], timeout=240, error=f"Pilot {variant} 合并、字幕或旁白失败")
    _run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(output)], timeout=30, error=f"Pilot {variant} 解码验证失败")
    timeline = {
        "episode_id": ep_dir.name,
        "variant": variant,
        "production_type": "SCREEN_DOCUMENTARY",
        "total_duration": total,
        "real_screen_footage_ratio": 1.0,
        "generated_card_count": 0,
        "generated_motion_seconds": 0.0,
        "spoken_lines": [item["spoken"] for item in specs],
        "clips": clips,
        "source_asset_id": screen_index.get("source_asset_id"),
        "source_recording": source.relative_to(ep_dir).as_posix(),
        "source_sha256": _sha256(source),
        "generated_at": _now(),
    }
    _write(timeline_path, timeline)
    return {"video": output, "srt": srt, "timeline": timeline_path}


def _validate_pilot_timeline(timeline: dict[str, Any]) -> None:
    rules = screen_documentary_rules()
    pilot_rules = rules.get("pilot_duration_seconds", {"min": 20, "max": 30})
    if not float(pilot_rules["min"]) <= float(timeline["total_duration"]) <= float(pilot_rules["max"]):
        raise RuntimeError(
            f"Pilot 时长必须在 {pilot_rules['min']}-{pilot_rules['max']} 秒，"
            "并由真实口播字幕驱动"
        )
    if float(timeline["real_screen_footage_ratio"]) < float(rules["real_screen_footage_ratio_min"]):
        raise RuntimeError("Pilot 真实录屏占比不足")
    if timeline["generated_card_count"] > rules["generated_card_count_max"] or timeline["generated_motion_seconds"] > rules["generated_motion_total_seconds_max"]:
        raise RuntimeError("Pilot 生成包装超出 SCREEN_DOCUMENTARY 限制")
    try:
        validate_source_order(timeline["clips"])
        validate_context_first(timeline["clips"])
    except ValueError as exc:
        raise RuntimeError(f"Pilot source contract 失败: {exc}") from exc
    first = timeline["clips"][0] if timeline["clips"] else {}
    if first.get("landscape") and first.get("layout") not in {"fit_full_frame", "contain", "full_frame", "context"}:
        raise RuntimeError("Pilot 第一帧必须先建立完整页面 context")


def render_pilots(ep_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if not (ep_dir / "work" / "director" / "short-video-brief.json").is_file():
        raise RuntimeError("请先完成 story-mine 与 direct")
    result: dict[str, Any] = {"episode_id": ep_dir.name, "pilots": {}}
    for variant in PILOT_IDS:
        output = _render_pilot(ep_dir, variant, _pilot_spec(ep_dir, variant), force=force)
        timeline = _read(output["timeline"])
        _validate_pilot_timeline(timeline)
        video, qa_root = output["video"], ep_dir / "work" / "qa" / "pilots" / variant
        total = float(_read(output["timeline"])["total_duration"])
        dense_stamps = [round(total * index / 10, 2) for index in range(11)]
        dense = extract_frames(video, dense_stamps, qa_root / "dense", force=force)
        uniform = extract_uniform_frames(video, qa_root / "uniform", step_seconds=1.0, force=force)
        sheets = build_contact_sheets(uniform or dense, qa_root / "contact-sheets", label=f"pilot-{variant}")
        mobile = qa_root / "mobile-preview"
        mobile.mkdir(parents=True, exist_ok=True)
        from PIL import Image
        for stamp, frame in dense.items():
            with Image.open(frame) as image:
                image.resize((360, 640)).save(mobile / f"t{stamp:05.2f}.jpg")
        result["pilots"][variant] = {"video": video.relative_to(ep_dir).as_posix(), "timeline": output["timeline"].relative_to(ep_dir).as_posix(), "srt": output["srt"].relative_to(ep_dir).as_posix(), "dense_frames": len(dense), "uniform_frames": len(uniform), "contact_sheets": sheets, "facts": "work/director/证据镜头索引.json"}
    _write(ep_dir / "work" / "qa" / "pilots" / "pilot-manifest.json", result)
    return result


def _validate_variant_review(item: dict[str, Any], variant: str) -> dict[str, Any]:
    scores = item.get("scores")
    if not isinstance(scores, dict):
        raise ValueError(f"{variant} 缺失实际看片的 numeric scores")
    normalized: dict[str, float] = {}
    for dimension in CORE_DIMENSIONS:
        value = scores.get(dimension)
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 10:
            raise ValueError(f"{variant} Reviewer 维度无效: {dimension}")
        normalized[dimension] = float(value)
    overall = scores.get("overall")
    if not isinstance(overall, (int, float)) or not 0 <= float(overall) <= 10:
        raise ValueError(f"{variant} Reviewer 缺少有效 overall")
    findings = item.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError(f"{variant} findings 必须为数组")
    return {"scores": {**normalized, "overall": float(overall)}, "findings": findings}


def _validate_reviewer_payload(raw: dict[str, Any]) -> dict[str, Any]:
    reviewer_id, reviewer_kind = raw.get("reviewer_id"), raw.get("reviewer_kind")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise ValueError("Reviewer 必须提供 reviewer_id")
    if reviewer_kind not in {"agent", "provider"}:
        raise ValueError("Reviewer 必须标记 reviewer_kind=agent 或 provider")
    reviewed_artifacts = raw.get("reviewed_artifacts", [])
    if not isinstance(reviewed_artifacts, list) or not reviewed_artifacts or not all(
        isinstance(item, str) and item.strip() for item in reviewed_artifacts
    ):
        raise ValueError("Reviewer 必须列出实际查看过的 MP4、联系表或关键帧")
    variants = raw.get("variants")
    if not isinstance(variants, dict) or set(variants) != set(PILOT_IDS):
        raise ValueError(f"每个独立 Reviewer 必须对 {', '.join(PILOT_IDS)} 全部评分")
    return {"reviewer_id": reviewer_id, "reviewer_kind": reviewer_kind, "reviewed_artifacts": reviewed_artifacts, "variants": {variant: _validate_variant_review(dict(variants[variant]), variant) for variant in PILOT_IDS}}


def review_pilots(ep_dir: Path, reviewer_payloads: list[dict[str, Any]] | None = None, *, force: bool = False) -> dict[str, Any]:
    manifest = ep_dir / "work" / "qa" / "pilots" / "pilot-manifest.json"
    if not manifest.is_file():
        raise RuntimeError("请先运行 pilot 生成真实 Pilot")
    output_dir, existing = ep_dir / "work" / "qa" / "pilots", ep_dir / "work" / "qa" / "pilots" / "pilot-review.json"
    if existing.is_file() and not force and reviewer_payloads is None:
        return _read(existing)
    previous_round = 0
    if existing.is_file():
        try:
            previous_round = int(_read(existing).get("repair_round", 0) or 0)
        except (OSError, ValueError):
            previous_round = 0
    if reviewer_payloads is None:
        report: dict[str, Any] = {"episode_id": ep_dir.name, "decision": "BLOCKED", "winner": None, "reviewers": [], "reviews": {}, "findings": [{"repair_target": "visual-critic", "observation": "缺少两份真实看片的独立 Reviewer 评分；无 Vision Provider 时必须 fail closed。"}], "repair_round": previous_round, "generated_at": _now()}
        _write(existing, report)
        return report
    if len(reviewer_payloads) not in {1, 2}:
        raise ValueError("Pilot Gate 必须提供至少一份独立、真实看片的 Reviewer 结果")
    reviewers = [_validate_reviewer_payload(dict(item)) for item in reviewer_payloads]
    if len(reviewers) == 2 and reviewers[0]["reviewer_id"] == reviewers[1]["reviewer_id"]:
        raise ValueError("两个 Reviewer 必须为独立身份")
    for reviewer in reviewers:
        _write(output_dir / f"reviewer-{reviewer['reviewer_id']}.json", reviewer)
    reviews: dict[str, Any] = {}
    aggregate_findings: list[dict[str, Any]] = []
    for variant in PILOT_IDS:
        scores = {dimension: round(sum(reviewer["variants"][variant]["scores"][dimension] for reviewer in reviewers) / len(reviewers), 2) for dimension in (*CORE_DIMENSIONS, "overall")}
        findings = [finding for reviewer in reviewers for finding in reviewer["variants"][variant]["findings"]]
        reviews[variant] = {"scores": scores, "findings": findings, "reviewer_ids": [reviewer["reviewer_id"] for reviewer in reviewers]}
        aggregate_findings.extend({"variant": variant, **finding} for finding in findings if isinstance(finding, dict))
    passing = [variant for variant, data in reviews.items() if data["scores"]["overall"] >= 8.5 and all(data["scores"][dimension] >= 8 for dimension in CORE_DIMENSIONS)]
    winner = max(passing, key=lambda item: reviews[item]["scores"]["overall"]) if passing else None
    if winner is None and not aggregate_findings:
        aggregate_findings = [{"repair_target": "mobile-screen-director", "observation": "没有 Pilot 达到任一核心项 8 / Overall 8.5 门槛"}]
    report = {"episode_id": ep_dir.name, "decision": "PASS" if winner else "REJECT", "winner": winner, "reviewers": reviewers, "reviews": reviews, "findings": aggregate_findings, "repair_round": previous_round, "generated_at": _now()}
    _write(existing, report)
    return report


def revise_pilots(ep_dir: Path, *, force: bool = False) -> dict[str, Any]:
    """Apply only deterministic, local fixes derived from explicit findings."""
    review_path = ep_dir / "work" / "qa" / "pilots" / "pilot-review.json"
    if not review_path.is_file():
        raise RuntimeError("请先运行 pilot-review")
    review = _read(review_path)
    round_number = int(review.get("repair_round", 0)) + 1
    if round_number > MAX_REPAIR_ROUNDS:
        return {"decision": "BLOCKED", "repair_round": round_number, "reason": "Pilot 已完成两轮自动返修，禁止第三轮渲染"}
    overrides: dict[str, dict[str, float]] = {}
    for finding in review.get("findings", []):
        target = finding.get("repair_target") if isinstance(finding, dict) else None
        variant = str(finding.get("variant") or "") if isinstance(finding, dict) else ""
        if target == "mobile-screen-director":
            targets = (variant,) if variant in PILOT_IDS else PILOT_IDS
            for item in targets:
                overrides[item] = {"zoom": 1.16}
    if not overrides:
        return {"decision": "BLOCKED", "repair_round": round_number, "reason": "findings 没有可自动执行的最小 repair_target"}
    _write(ep_dir / "work" / "pilots" / "pilot-overrides.json", overrides)
    review["repair_round"] = round_number
    _write(review_path, review)
    return {"decision": "RENDER_REQUIRED", "repair_round": round_number, "overrides": overrides}


def pilot_gate_passed(ep_dir: Path) -> bool:
    path = ep_dir / "work" / "qa" / "pilots" / "pilot-review.json"
    return path.is_file() and _read(path).get("decision") == "PASS"


def assert_screen_documentary_pilot_gate(ep_dir: Path, model: Any) -> None:
    """Shared fail-closed guard for every SCREEN_DOCUMENTARY render path."""
    if getattr(model, "production_type", "STANDARD") != "SCREEN_DOCUMENTARY":
        return
    downstream_statuses = {"PILOT_APPROVED", "ROUGH_CUT_READY", "QA_PASSED", "DELIVERY_READY"}
    if getattr(model, "status", None) not in downstream_statuses or not pilot_gate_passed(ep_dir):
        raise RuntimeError(
            "SCREEN_DOCUMENTARY 必须先通过字幕驱动的 20-30 秒 Pilot Gate；"
            "没有匹配录屏不是阻塞条件，但没有真实看片记录不能完整渲染"
        )
