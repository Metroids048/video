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

logger = logging.getLogger(__name__)

# 默认每镜头时长（无 duration_estimate 时使用）
_DEFAULT_SHOT_DURATION = 3.0
# 占位卡最短时长
_MIN_PLACEHOLDER_DURATION = 2.0


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_asset(ep_dir: Path, asset_ref: str | None, manifest: dict) -> tuple[str | None, bool]:
    """返回 (相对工作路径, is_missing)。"""
    if not asset_ref:
        return None, True
    for a in manifest.get("assets", []):
        if a["asset_id"] == asset_ref or a["source_path"].endswith(asset_ref):
            if a["status"] == "ok":
                return a["working_path"], False
            else:
                return None, True
    return None, True


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

    # 尝试从多个候选路径加载
    storyboard: dict | None = None
    for p in [storyboard_path, ep_dir / "work" / "storyboard.json"]:
        if p.exists():
            storyboard = _load_json(p)
            break

    manifest: dict = {"assets": []}
    for p in [manifest_path, ep_dir / "work" / "prepared" / "asset-manifest.json"]:
        if p.exists():
            manifest = _load_json(p)
            break

    # ── 构建视频轨 ────────────────────────────────────────────────────────

    video_clips: list[Clip] = []
    caption_clips: list[Clip] = []
    current_t = 0.0

    if storyboard:
        shots = sorted(storyboard.get("shots", []), key=lambda s: s.get("order", 0))
        for shot in shots:
            dur = float(shot.get("duration_estimate") or _DEFAULT_SHOT_DURATION)
            dur = max(dur, _MIN_PLACEHOLDER_DURATION)

            asset_ref = shot.get("asset_ref")
            working_path, is_missing = _resolve_asset(ep_dir, asset_ref, manifest)

            transform: dict | None = None
            if working_path:
                # 检测横屏素材（简单启发：宽>高）→ 使用 contain
                # 在实际 render 时 ffprobe 会做精确判断
                transform = {"layout": "contain", "zoom_meta": None}

            clip = Clip(
                clip_id=f"v-{shot['shot_id']}",
                start=current_t,
                duration=dur,
                asset_ref=working_path,
                in_point=0.0,
                out_point=dur,
                transform=transform,
                text=shot.get("description") if is_missing else None,
                style={"placeholder": True} if is_missing else None,
            )
            video_clips.append(clip)

            # 字幕草稿（来自分镜描述，无旁白时使用）
            cap_text = shot.get("description") or shot.get("gap_note") or ""
            if cap_text:
                caption_clips.append(Clip(
                    clip_id=f"cap-{shot['shot_id']}",
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

    # 旁白
    narration_candidates = [
        ep_dir / "work" / "prepared" / "narration.wav",
        ep_dir / "input" / "audio" / "narration.wav",
        ep_dir / "work" / "content" / "narration.wav",
    ]
    for nc in narration_candidates:
        if nc.exists():
            voice_clips.append(Clip(
                clip_id="voice-narration",
                start=0.0,
                duration=current_t,
                asset_ref=str(nc.relative_to(ep_dir)),
                style={"volume": 1.0, "role": "voice"},
            ))
            break

    # BGM
    bgm_candidates = list((ep_dir / "input" / "audio").glob("bgm*")) + \
                     list((ep_dir / "input" / "audio").glob("music*"))
    if bgm_candidates:
        bgm = bgm_candidates[0]
        music_clips.append(Clip(
            clip_id="music-bgm",
            start=0.0,
            duration=current_t,
            asset_ref=str(bgm.relative_to(ep_dir)),
            style={"volume": 0.3, "ducking": True, "role": "bgm"},
        ))

    # ── 组装 Timeline ────────────────────────────────────────────────────

    tracks: list[Track] = [
        Track(track_id="video-main", kind="video", clips=video_clips),
    ]
    if voice_clips:
        tracks.append(Track(track_id="audio-voice", kind="audio", clips=voice_clips))
    if music_clips:
        tracks.append(Track(track_id="audio-music", kind="audio", clips=music_clips))
    if caption_clips:
        tracks.append(Track(track_id="captions-main", kind="caption", clips=caption_clips))

    timeline = Timeline(
        episode_id=episode_id,
        canvas=Canvas(width=1080, height=1920, fps=30.0),
        tracks=tracks,
    )
    timeline.total_duration = current_t

    # 确保目录存在
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline.save(timeline_path)
    logger.info("timeline.json 已生成: %s  总时长 %.1fs  %d 轨 %d clips",
                timeline_path, current_t, len(tracks),
                sum(len(t.clips) for t in tracks))
    return timeline
