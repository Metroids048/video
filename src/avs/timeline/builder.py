"""src/avs/timeline/builder.py — 从 storyboard/asset-manifest 构建 timeline.json。

构建策略：
1. 读取 storyboard.json → 镜头序列
2. 读取 asset-manifest.json → 每个 asset_ref 的工作路径
3. 按镜头顺序拼接 video track；缺失素材生成占位卡
4. 若有 narration.wav → 加入 audio track (voice)
5. 若有 bgm → 加入 audio track (music)
6. 若有脚本文字 → 生成 caption track (SRT 草稿)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from avs.timeline.models import Canvas, Clip, Timeline, Track
from avs.timeline.shot_expander import expand_shot

logger = logging.getLogger(__name__)

# 默认每镜头时长（无 duration_estimate 时使用）
_DEFAULT_SHOT_DURATION = 3.0
# 占位卡最短时长
_MIN_PLACEHOLDER_DURATION = 2.0


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _prepared_working_path(ep_dir: Path, value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    normalized = path.as_posix()
    if not normalized.startswith("work/prepared/"):
        return None
    return normalized if (ep_dir / path).is_file() else None


def _resolve_asset(
    ep_dir: Path, asset_ref: str | None, manifest: dict,
) -> tuple[str | None, bool, str]:
    """返回 (相对工作路径, is_missing, layout)。"""
    if not asset_ref:
        return None, True, "contain"
    for a in manifest.get("assets", []):
        if a["asset_id"] == asset_ref or a["source_path"].endswith(asset_ref):
            working_path = _prepared_working_path(ep_dir, a.get("working_path"))
            if a["status"] == "ok" and working_path:
                return working_path, False, a.get("layout") or "contain"
            return None, True, "contain"
    return None, True, "contain"


def build_timeline(
    ep_dir: Path,
    episode_id: str,
    *,
    force: bool = False,
) -> Timeline:
    """从 episode 目录中的 storyboard + asset-manifest 构建 Timeline。

    幂等：若 timeline.json 已存在且 force=False，直接加载并返回。
    force=True 时无论如何重新构建。
    """
    from avs.timeline.models import Timeline as TL
    timeline_path = ep_dir / "work" / "timeline.json"

    if timeline_path.exists() and not force:
        logger.info("timeline.json 已存在，跳过（use --force 重建）")
        return TL.load(timeline_path)

    # ── 加载前置产物 ──────────────────────────────────────────────────────

    storyboard_path = ep_dir / "work" / "content" / "storyboard.json"
    manifest_path = ep_dir / "work" / "asset-manifest.json"
    input_manifest_path = ep_dir / "work" / "input-manifest.json"

    # 尝试从多个候选路径加载
    storyboard: dict | None = None
    for p in [storyboard_path, ep_dir / "work" / "storyboard.json"]:
        if p.exists():
            storyboard = _load_json(p)
            break

    manifest: dict = {"assets": []}
    manifest_is_legacy = not input_manifest_path.is_file()
    for p in [input_manifest_path, manifest_path, ep_dir / "work" / "prepared" / "asset-manifest.json"]:
        if p.exists():
            manifest = _load_json(p)
            break

    script: dict = {"segments": []}
    script_path = ep_dir / "work" / "content" / "script.json"
    if script_path.exists():
        script = _load_json(script_path)
    script_text = {
        segment["segment_id"]: segment.get("text", "")
        for segment in script.get("segments", [])
    }

    # ── 构建视频轨 ────────────────────────────────────────────────────────

    video_clips: list[Clip] = []
    caption_clips: list[Clip] = []
    current_t = 0.0

    if storyboard:
        shots: list[dict[str, Any]] = []
        for source_shot in storyboard.get("shots", []):
            refs = source_shot.get("asset_refs") or source_shot.get("asset_ids") or []
            normalized = dict(source_shot)
            normalized["asset_refs"] = refs
            normalized["duration_seconds"] = float(
                source_shot.get("duration")
                or source_shot.get("duration_estimate")
                or _DEFAULT_SHOT_DURATION
            )
            atomic, _ = expand_shot(normalized)
            shots.extend(atomic)
        for index, shot in enumerate(shots):
            scene_id = shot.get("scene_id") or shot.get("shot_id") or f"scene{index + 1:03d}"
            dur = float(shot.get("duration_seconds") or shot.get("duration") or shot.get("duration_estimate") or _DEFAULT_SHOT_DURATION)
            dur = max(dur, 0.4)

            asset_refs = shot.get("asset_refs") or []
            first_ref = asset_refs[0] if asset_refs else shot.get("asset_ref")
            asset_id = first_ref.get("asset_id") if isinstance(first_ref, dict) else first_ref
            region_id = first_ref.get("region_id") if isinstance(first_ref, dict) else None
            working_path, is_missing, layout = _resolve_asset(ep_dir, asset_id, manifest)
            primitive = shot.get("primitive") or ("screenshot_focus" if working_path else "kinetic_text")
            generated_visual = primitive in {"kinetic_text", "metric_card"}
            if generated_visual:
                is_missing = False

            transform: dict | None = None
            if working_path:
                # 检测横屏素材（简单启发：宽>高）→ 使用 contain
                # 在实际 render 时 ffprobe 会做精确判断
                region = first_ref.get("region") if isinstance(first_ref, dict) else None
                redactions = first_ref.get("redactions") if isinstance(first_ref, dict) else None
                transform = {
                    "layout": layout, "zoom_meta": None,
                    "region": region, "redactions": redactions,
                }

            segment_ids = shot.get("script_segment_ids") or []
            caption_text = " ".join(script_text.get(item, "") for item in segment_ids).strip()
            caption_text = caption_text or shot.get("caption") or shot.get("description") or ""
            placeholder_text = (
                "; ".join(shot.get("missing_assets") or [])
                or shot.get("gap_note")
                or caption_text
                or "[待补充视频素材]"
            )

            clip = Clip(
                clip_id=f"v-{scene_id}",
                start=current_t,
                duration=dur,
                asset_ref=working_path,
                in_point=0.0,
                out_point=dur,
                transform=transform,
                text=placeholder_text if is_missing else None,
                style={"placeholder": True} if is_missing else None,
                primitive=primitive,
                asset_id=asset_id,
                region_id=region_id,
                segment_id=segment_ids[0] if segment_ids else shot.get("segment_id"),
                evidence_id=shot.get("evidence_id"),
                reference_pattern_ids=shot.get("reference_pattern_ids"),
                keyframes=shot.get("keyframes"),
            )
            video_clips.append(clip)

            # 字幕草稿（来自分镜描述，无旁白时使用）
            cap_text = caption_text
            if cap_text:
                caption_clips.append(Clip(
                    clip_id=f"cap-{scene_id}",
                    start=current_t,
                    duration=dur,
                    text=cap_text,
                    style={"source": "storyboard_draft"},
                ))

            current_t += dur
    else:
        # 无分镜：生成单个占位卡
        logger.warning("未找到 storyboard.json，生成单占位卡时间线")
        video_clips.append(Clip(
            clip_id="v-placeholder-001",
            start=0.0,
            duration=5.0,
            text="[待补充视频素材]",
            style={"placeholder": True},
        ))
        current_t = 5.0

    # ── 音频轨 ────────────────────────────────────────────────────────────

    voice_clips: list[Clip] = []
    music_clips: list[Clip] = []

    # 旁白和 BGM 只从 Manifest 的工作副本选择。
    audio_assets = [
        asset for asset in manifest.get("assets", [])
        if (asset.get("kind") == "audio" or asset.get("source_type") == "audio") and asset.get("status") == "ok"
        and _prepared_working_path(ep_dir, asset.get("working_path"))
    ]
    for asset in audio_assets:
        source_name = Path(asset["source_path"]).name.lower()
        role = asset.get("audio_role")
        if role in {"narration", "original_voice"} or (
            manifest_is_legacy and source_name.startswith(("narration", "voice"))
        ):
            working_path = _prepared_working_path(ep_dir, asset.get("working_path"))
            assert working_path is not None
            voice_clips.append(Clip(
                clip_id="voice-narration",
                start=0.0,
                duration=current_t,
                asset_ref=working_path,
                style={"volume": 1.0, "role": "voice"},
            ))
            break

    for asset in audio_assets:
        source_name = Path(asset["source_path"]).name.lower()
        role = asset.get("audio_role")
        if role == "bgm" or (manifest_is_legacy and source_name.startswith(("bgm", "music"))):
            working_path = _prepared_working_path(ep_dir, asset.get("working_path"))
            assert working_path is not None
            music_clips.append(Clip(
                clip_id="music-bgm", start=0.0, duration=current_t,
                asset_ref=working_path,
                style={"volume": 0.3, "ducking": True, "role": "bgm"},
            ))
            break

    # ── 组装 Timeline ────────────────────────────────────────────────────

    tracks: list[Track] = [
        Track(track_id="video-main", kind="video", clips=video_clips),
    ]
    if voice_clips:
        tracks.append(Track(track_id="audio-voice", kind="audio", clips=voice_clips, audio_role="voice"))
    if music_clips:
        tracks.append(Track(track_id="audio-music", kind="audio", clips=music_clips, audio_role="bgm"))
    if caption_clips:
        tracks.append(Track(track_id="captions-main", kind="caption", clips=caption_clips))

    total_duration = current_t
    graphic_clips: list[Clip] = []
    graphic_t = 0.0
    for index, shot in enumerate(storyboard.get("shots", []) if storyboard else []):
        duration = max(
            float(shot.get("duration") or shot.get("duration_estimate") or _DEFAULT_SHOT_DURATION),
            _MIN_PLACEHOLDER_DURATION,
        )
        template = shot.get("motion_template")
        if template:
            scene_id = shot.get("scene_id") or shot.get("shot_id") or f"scene{index + 1:03d}"
            graphic_clips.append(Clip(
                clip_id=f"graphic-{scene_id}", start=graphic_t, duration=duration,
                text=shot.get("caption") or shot.get("description"),
                style={"motion_template": template},
            ))
        graphic_t += duration
    if graphic_clips:
        tracks.append(Track(track_id="graphics-main", kind="graphic", clips=graphic_clips))

    timeline = Timeline(
        episode_id=episode_id,
        canvas=Canvas(width=1080, height=1920, fps=30.0),
        tracks=tracks,
        version="1.1",
    )
    timeline.total_duration = total_duration

    # 确保目录存在
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline.save(timeline_path)
    missing = [clip for clip in video_clips if (clip.style or {}).get("placeholder")]
    notes_path = ep_dir / "work" / "edit-notes-draft.md"
    notes_path.write_text(
        "# Edit Notes Draft\n\n" + "\n".join(
            f"- {clip.clip_id}: {clip.text or 'missing asset'}" for clip in missing
        ) + "\n",
        encoding="utf-8",
    )
    logger.info("timeline.json 已生成: %s  总时长 %.1fs  %d 轨 %d clips",
                timeline_path, total_duration, len(tracks),
                sum(len(t.clips) for t in tracks))
    return timeline
