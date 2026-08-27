"""Active multimodal workflow stages.

All artifacts are attached to the existing Episode directory; ``episode.json``
remains the only state store.  Legacy timeline/render commands can still be
used for internal filter tests, but these helpers are the publishable route.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from avs.analysis import analyze_assets, analyze_documents, analyze_recordings, transcribe_audio_assets
from avs.creative import (
    assert_agent_script,
    build_creative_brief,
    build_evidence_map,
    load_agent_script,
    plan_script,
    plan_shots,
    select_reference_patterns,
)
from avs.creative.brief import HOOKS, save_creative_brief
from avs.creative.reference_matcher import save_reference_selection
from avs.models.episode import EpisodeModel
from avs.render.captions import build_srt
from avs.timeline import build_timeline
from avs.timeline.models import Timeline


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_analyze(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> dict[str, Any]:
    manifest = _read(ep_dir / "work" / "input-manifest.json")
    retry_force = force or model.blocked_stage == "analyze"
    # screenshot_intro 只允许依据用户明确备注生成“待 Provider 复核”的预览
    # 分析；最终 visual-review 仍会要求真实 Vision Provider。
    intelligence = analyze_assets(
        ep_dir,
        manifest=manifest,
        require_provider=model.input_mode != "screenshot_intro",
        allow_manual_notes=model.input_mode == "screenshot_intro",
        force=retry_force,
    )
    recording = analyze_recordings(ep_dir, manifest=manifest, force=retry_force)
    documents = analyze_documents(ep_dir, manifest)
    transcription = transcribe_audio_assets(ep_dir, manifest)
    model.to_dict().setdefault("artifacts", {})
    reasons = [
        str(item.get("blocking_reason") or "分析被阻塞")
        for item in (intelligence, transcription)
        if item.get("blocked")
    ]
    if documents.get("blocked"):
        reasons.append("必须使用的文档无法提取")
    if reasons:
        model.block("; ".join(reasons), stage="analyze")
        model.save(ep_dir / "episode.json")
        return {"asset_intelligence": intelligence, "recording_analysis": recording, "document_analysis": documents, "transcription": transcription}
    model.clear_block(stage="analyze")
    model.complete_stage("analyze")
    model.save(ep_dir / "episode.json")
    return {"asset_intelligence": intelligence, "recording_analysis": recording, "document_analysis": documents, "transcription": transcription}


def active_story_mine(ep_dir: Path, model: EpisodeModel) -> dict[str, str]:
    """Mine the current Episode after real ingest/analyze stages have completed."""
    if model.production_type != "SCREEN_DOCUMENTARY":
        raise RuntimeError("story-mine 只适用于 SCREEN_DOCUMENTARY")
    required = (
        ep_dir / "work" / "input-manifest.json",
        ep_dir / "work" / "analysis" / "recording-analysis.json",
        ep_dir / "work" / "analysis" / "asset-intelligence.json",
    )
    missing = [path.relative_to(ep_dir).as_posix() for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(
            "SCREEN_DOCUMENTARY 必须先完成当前 Episode 的 ingest/analyze；缺少: "
            + ", ".join(missing)
        )
    if "ingest" not in model.completed_stages or "analyze" not in model.completed_stages:
        raise RuntimeError("SCREEN_DOCUMENTARY 不得在未完成真实 ingest/analyze 时进入 story-mine")
    from avs.pilots import mine_story
    output = mine_story(ep_dir)
    model.clear_block(stage="story-mine")
    model.complete_stage("story-mine")
    model.save(ep_dir / "episode.json")
    return {name: path.relative_to(ep_dir).as_posix() for name, path in output.items()}


def active_direct(ep_dir: Path, model: EpisodeModel) -> str:
    if model.production_type != "SCREEN_DOCUMENTARY":
        raise RuntimeError("direct 只适用于 SCREEN_DOCUMENTARY")
    if not (ep_dir / "work" / "director" / "录屏内容索引.json").is_file():
        raise RuntimeError("请先完成 story-mine")
    from avs.pilots import direct_story
    path = direct_story(ep_dir)
    if model.status == "INGESTED":
        model.ensure_stage("content", "CONTENT_READY")
    model.clear_block(stage="direct")
    model.complete_stage("direct")
    model.complete_stage("screen-plan")
    model.save(ep_dir / "episode.json")
    return path.relative_to(ep_dir).as_posix()


def active_pilot(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> dict[str, Any]:
    if model.production_type != "SCREEN_DOCUMENTARY":
        raise RuntimeError("pilot 只适用于 SCREEN_DOCUMENTARY")
    from avs.pilots import render_pilots
    result = render_pilots(ep_dir, force=force)
    if model.status == "CONTENT_READY":
        model.ensure_stage("assets", "ASSETS_READY")
        model.ensure_stage("timeline", "TIMELINE_READY")
    model.clear_block(stage="pilot")
    model.complete_stage("pilot")
    model.save(ep_dir / "episode.json")
    return result


def active_pilot_review(
    ep_dir: Path, model: EpisodeModel, reviewer_payloads: list[dict[str, Any]] | None = None, *, force: bool = False,
) -> dict[str, Any]:
    if model.production_type != "SCREEN_DOCUMENTARY":
        raise RuntimeError("pilot-review 只适用于 SCREEN_DOCUMENTARY")
    from avs.pilots import review_pilots
    report = review_pilots(ep_dir, reviewer_payloads, force=force)
    if report["decision"] == "PASS":
        model.clear_block(stage="pilot-review")
        model.ensure_stage("pilot-review", "PILOT_APPROVED")
        model.complete_stage("pilot-review")
    else:
        reason = "Pilot 视觉审核未通过" if report["decision"] == "REJECT" else "Pilot 视觉审核被阻塞"
        model.block(reason, stage="pilot-review")
    model.save(ep_dir / "episode.json")
    return report


def active_pilot_revise(ep_dir: Path, model: EpisodeModel) -> dict[str, Any]:
    """Apply a bounded, finding-targeted Pilot repair and rerender only Pilots."""
    if model.production_type != "SCREEN_DOCUMENTARY":
        raise RuntimeError("pilot-revise 只适用于 SCREEN_DOCUMENTARY")
    if model.blocked_stage != "pilot-review":
        raise RuntimeError("pilot-revise 只能处理被 Pilot Gate 拒绝的 Episode")

    from avs.pilots import revise_pilots, render_pilots

    revision = revise_pilots(ep_dir)
    if revision["decision"] != "RENDER_REQUIRED":
        model.block(str(revision.get("reason", "Pilot 自动返修不可执行")), stage="pilot-review")
        model.save(ep_dir / "episode.json")
        return revision

    # Repair has an explicit target; clear only the matching block, rerender
    # the pilot artifacts, then require two fresh independent reviews.
    model.clear_block(stage="pilot-review")
    model.complete_stage("pilot-revise")
    render_pilots(ep_dir, force=True)
    model.save(ep_dir / "episode.json")
    return revision


def active_plan(
    ep_dir: Path,
    model: EpisodeModel,
    *,
    platform: str = "douyin",
    hook_variant: str = "conflict",
    pattern_ids: list[str] | None = None,
    regenerate_script: bool = False,
) -> dict[str, Any]:
    intelligence = _read(ep_dir / "work" / "analysis" / "asset-intelligence.json")
    if intelligence.get("blocked"):
        raise RuntimeError(str(intelligence.get("blocking_reason") or "asset intelligence blocked"))
    manifest = _read(ep_dir / "work" / "input-manifest.json")
    must_use = [asset["asset_id"] for asset in manifest.get("assets", []) if asset.get("must_use")]
    selection = select_reference_patterns(model.id, platform=platform, pattern_ids=pattern_ids)

    # An Agent-authored script is the publishable route; the deterministic planner
    # is the fallback.  Overwriting a validated Agent script would silently trade
    # real writing for a fact-join, which is exactly how good content got lost
    # before: the Agent wrote it, then `plan` regenerated over the top of it.
    agent_script = None if regenerate_script else load_agent_script(ep_dir)
    if agent_script is not None:
        assert_agent_script(
            agent_script, manifest=manifest, intelligence=intelligence, episode_id=model.id,
        )
        script = agent_script
        script["reference_pattern_ids"] = [
            item["pattern_id"] for item in selection.get("selections", [])
        ] or script.get("reference_pattern_ids", [])
        hook_variant = str(script.get("hook_variant") or hook_variant)
        brief = build_creative_brief(
            model.id, platform=platform, must_use_asset_ids=must_use,
            hook_variant=hook_variant if hook_variant in HOOKS else "conflict",
        )
        if script.get("angle"):
            brief["angle"] = str(script["angle"])
        if script.get("audience"):
            brief["target_audience"] = str(script["audience"])
        brief["hook"] = str(script["segments"][0].get("spoken_text") or brief["hook"])
    else:
        brief = build_creative_brief(
            model.id, platform=platform, must_use_asset_ids=must_use, hook_variant=hook_variant,
        )
        script = plan_script(brief, intelligence, selection, hook_variant=hook_variant)
    referenced = {
        ref.get("asset_id")
        for segment in script.get("segments", [])
        for ref in segment.get("asset_refs", [])
    }
    visual_asset_ids = {
        asset["asset_id"] for asset in manifest.get("assets", [])
        if asset.get("source_type") in {"screenshot", "recording", "video"}
    }
    missing_evidence = [
        asset_id for asset_id in must_use
        if asset_id in visual_asset_ids and asset_id not in referenced
    ]
    if missing_evidence:
        raise RuntimeError(
            "must-use 素材尚未形成可验证事实: " + ", ".join(missing_evidence)
        )
    evidence = build_evidence_map(model.id, script, intelligence=intelligence)
    regions = {
        (asset.get("asset_id"), region.get("region_id")): region.get("box")
        for asset in intelligence.get("assets", [])
        for region in asset.get("regions", [])
    }
    for segment in evidence.get("segments", []):
        for ref in segment.get("asset_refs", []):
            box = regions.get((ref.get("asset_id"), ref.get("region_id")))
            if box:
                ref["region"] = box
    shot_plan = plan_shots(model.id, evidence, selection=selection)
    shot_plan["excluded_assets"] = [
        {
            "asset_id": asset["asset_id"],
            "excluded": True,
            "reason": "未匹配到新的可见产品事实",
        }
        for asset in manifest.get("assets", [])
        if asset.get("asset_id") not in referenced and not asset.get("must_use")
    ]
    shot_plan["analysis_asset_ids"] = [
        asset["asset_id"] for asset in manifest.get("assets", [])
        if asset.get("must_use")
        and asset.get("source_type") in {"document", "text", "link", "audio"}
        and asset.get("status") == "ok"
    ]
    save_creative_brief(ep_dir, brief)
    save_reference_selection(ep_dir, selection)
    _write(ep_dir / "work" / "content" / "hook-selection.json", {
        "episode_id": model.id,
        "selected": hook_variant,
        "hook": brief["hook"],
        "confirmed_by": (
            f"agent:{script.get('author_id') or 'unknown'}"
            if agent_script is not None
            else "cli-user"
        ),
    })
    _write(ep_dir / "work" / "content" / "script.json", script)
    approved_script = "\n\n".join(
        f"## {index}. {segment.get('narrative_beat') or segment.get('segment_id') or 'Segment'}\n\n"
        f"{segment.get('spoken_text', '').strip()}"
        for index, segment in enumerate(script.get("segments", []), start=1)
    ).strip() + "\n"
    (ep_dir / "work" / "content" / "approved-script.md").write_text(approved_script, encoding="utf-8")
    _write(ep_dir / "work" / "content" / "evidence-map.json", evidence)
    _write(ep_dir / "work" / "content" / "shot-plan.json", shot_plan)
    if model.status == "INGESTED":
        model.ensure_stage("content", "CONTENT_READY")
    model.complete_stage("plan")
    model.save(ep_dir / "episode.json")
    return {"brief": brief, "selection": selection, "script": script, "evidence_map": evidence, "shot_plan": shot_plan}


def _voice_metadata_paths(ep_dir: Path) -> tuple[Path, ...]:
    return (
        ep_dir / "work" / "voice-lock.json",
        ep_dir / "work" / "narration.json",
        ep_dir / "work" / "generated" / "narration.json",
    )


def _voice_audio_path(ep_dir: Path) -> Path | None:
    manifest_path = ep_dir / "work" / "input-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = _read(manifest_path)
        except (OSError, ValueError):
            manifest = {}
        for asset in manifest.get("assets", []):
            if asset.get("source_type") != "audio" or asset.get("audio_role") not in {"narration", "original_voice"}:
                continue
            rel = asset.get("working_path") or asset.get("source_path")
            if not rel:
                continue
            candidate = (ep_dir / str(rel)).resolve()
            try:
                candidate.relative_to(ep_dir.resolve())
            except ValueError:
                continue
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
    for path in (
        ep_dir / "work" / "final-narration.mp3",
        ep_dir / "work" / "narration.mp3",
        ep_dir / "work" / "audio" / "final-narration.mp3",
    ):
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def _has_manifest_voice_asset(ep_dir: Path) -> bool:
    manifest_path = ep_dir / "work" / "input-manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = _read(manifest_path)
    except (OSError, ValueError):
        return False
    return any(
        asset.get("source_type") == "audio"
        and asset.get("audio_role") in {"narration", "original_voice"}
        and asset.get("status", "ok") == "ok"
        for asset in manifest.get("assets", [])
    )


def voice_lock_state(ep_dir: Path, *, publishable: bool = True) -> tuple[bool, str]:
    """Return whether this Episode has current, approved, non-Edge locked audio."""
    audio = _voice_audio_path(ep_dir)
    if audio is None:
        return False, "缺少当前 Episode 的 narration/original_voice 音频"
    metadata: dict[str, Any] | None = None
    for path in _voice_metadata_paths(ep_dir):
        if path.is_file():
            try:
                candidate = _read(path)
            except (OSError, ValueError):
                continue
            if isinstance(candidate, dict):
                metadata = candidate
                break
    if metadata is None:
        if _has_manifest_voice_asset(ep_dir):
            return True, "user_audio"
        return False, "缺少 voice-lock.json/narration.json；需要一次 voice audition 批准"
    provider = str(metadata.get("provider") or "").lower()
    if publishable and provider == "edge_tts":
        return False, "Edge TTS 仅允许 development，publishable Episode 必须使用批准声音"
    if metadata.get("approved") is not True or not metadata.get("voice_profile"):
        return False, "声音尚未由 voice audition 批准并锁定 voice_profile"
    recorded_sha = metadata.get("audio_sha256")
    if recorded_sha and recorded_sha != hashlib.sha256(audio.read_bytes()).hexdigest():
        return False, "锁定旁白已变化；必须重新试听或重新锁定当前音频"
    return True, "locked"


def active_voice_lock(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> dict[str, str]:
    """Materialize the approved narration into the canonical Episode paths."""
    ready, reason = voice_lock_state(ep_dir, publishable=model.publishable)
    if not ready:
        model.block(reason, stage="voice-lock")
        model.save(ep_dir / "episode.json")
        raise RuntimeError(reason)
    source = _voice_audio_path(ep_dir)
    assert source is not None
    work = ep_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    target = work / "final-narration.mp3"
    if source.resolve() != target.resolve() and (force or not target.exists()):
        shutil.copy2(source, target)
    metadata_path = next((p for p in _voice_metadata_paths(ep_dir) if p.is_file()), work / "voice-lock.json")
    metadata = _read(metadata_path) if metadata_path.is_file() else {}
    metadata.setdefault("provider", "user_audio")
    metadata.setdefault("voice_profile", "user-audio")
    metadata.update({"approved": True, "locked": True, "locked_audio": target.relative_to(ep_dir).as_posix()})
    metadata.setdefault("audio_sha256", hashlib.sha256(target.read_bytes()).hexdigest())
    _write(work / "voice-lock.json", metadata)
    narration = work / "narration.mp3"
    if force or not narration.exists():
        shutil.copy2(target, narration)
    _write(work / "narration.json", metadata)
    words = work / "final-narration.words.json"
    if words.is_file() and (force or not (work / "narration.words.json").is_file()):
        shutil.copy2(words, work / "narration.words.json")
    model.clear_block(stage="voice-lock")
    model.complete_stage("voice-lock")
    model.save(ep_dir / "episode.json")
    return {"audio": target.relative_to(ep_dir).as_posix(), "provider": str(metadata.get("provider") or "user_audio")}


def active_voice_audition(
    ep_dir: Path,
    model: EpisodeModel,
    audio: Path,
    *,
    provider: str = "approved_voice_profile",
    voice_profile: str = "audition-approved",
) -> dict[str, str]:
    """Persist a user-approved audition result; no synthesis or silent fallback."""
    if not audio.is_file() or audio.stat().st_size == 0:
        raise RuntimeError(f"试听音频不存在或为空: {audio}")
    if model.publishable and provider.lower() == "edge_tts":
        raise RuntimeError("Edge TTS 仅允许 development，不能批准为 publishable voice")
    work = ep_dir / "work"
    work.mkdir(parents=True, exist_ok=True)
    target = work / "final-narration.mp3"
    shutil.copy2(audio, target)
    metadata = {
        "version": "2.0",
        "provider": provider,
        "voice_profile": voice_profile,
        "approved": True,
        "locked": True,
        "locked_audio": target.relative_to(ep_dir).as_posix(),
        "audio_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    _write(work / "voice-lock.json", metadata)
    model.clear_block(stage="voice-audition")
    model.complete_stage("voice-audition")
    model.complete_stage("voice-lock")
    model.save(ep_dir / "episode.json")
    return {"audio": target.relative_to(ep_dir).as_posix(), "provider": provider}


def active_preview(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> Timeline:
    plan = _read(ep_dir / "work" / "content" / "shot-plan.json")
    script = _read(ep_dir / "work" / "content" / "script.json")
    by_segment = {item["segment_id"]: item for item in script.get("segments", [])}
    storyboard_shots: list[dict[str, Any]] = []
    shots = plan.get("shots", [])
    for index, shot in enumerate(shots):
        segment = by_segment.get(shot.get("segment_id"), {})
        refs = [ref.get("asset_id") for ref in shot.get("asset_refs", []) if ref.get("asset_id")]
        if index == 0:
            motion_template = "HookTitle"
        elif index == len(shots) - 1:
            motion_template = "EndCard"
        elif not refs:
            motion_template = "InfoCard"
        else:
            motion_template = None
        storyboard_shots.append({
            "scene_id": shot["shot_id"],
            "script_segment_ids": [shot.get("segment_id")],
            "duration": shot["duration_seconds"],
            "visual_type": "image" if refs else "motion_graphic",
            "asset_ids": refs,
            "asset_refs": shot.get("asset_refs", []),
            "caption": segment.get("spoken_text", ""),
            "motion_template": motion_template,
            "missing_assets": [],
            "notes": shot.get("primitive"),
            "primitive": shot.get("primitive"),
            "reference_pattern_ids": shot.get("reference_pattern_ids", []),
            "keyframes": shot.get("keyframes", []),
        })
    script_path = ep_dir / "work" / "content" / "script.json"
    brief_path = ep_dir / "work" / "content" / "creative-brief.json"
    storyboard = {
        "episode_id": model.id,
        "shots": storyboard_shots,
        "asset_gaps": [],
        "traceability": {"script_sha256": _sha256(script_path), "creative_profile_sha256": _sha256(brief_path)},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "storyboard.schema.json"
    jsonschema.Draft7Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(storyboard)
    _write(ep_dir / "work" / "content" / "storyboard.json", storyboard)
    if model.status == "CONTENT_READY":
        model.ensure_stage("assets", "ASSETS_READY")
    timeline = build_timeline(ep_dir, model.id, force=force)
    voice_track = next((track for track in timeline.tracks if track.kind == "audio" and track.audio_role == "voice"), None)
    if voice_track is None:
        raise RuntimeError(
            "V2 预览需要已经锁定的最终旁白音轨；请先完成 voice audition、voice-profile 和 forced alignment。"
        )
    if model.status == "ASSETS_READY":
        model.ensure_stage("timeline", "TIMELINE_READY")
    build_srt(
        timeline,
        ep_dir / "work" / "captions.srt",
        words_path=ep_dir / "work" / "final-narration.words.json",
    )
    from avs.render import render_rough_cut
    render_rough_cut(ep_dir, timeline, force=force)
    from avs.hyperframes import render_motion_graphics
    render_motion_graphics(Path(__file__).resolve().parents[2], ep_dir, timeline, force=force)
    model.complete_stage("preview")
    model.save(ep_dir / "episode.json")
    return timeline


def active_final_render(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> dict[str, Any]:
    if model.publishable and model.production_type in {"STANDARD", "VISUAL_EXPLAINER"}:
        ready, reason = voice_lock_state(ep_dir, publishable=True)
        if not ready:
            raise RuntimeError("publishable final-render 必须先通过 voice-lock: " + reason)

    # A new final render invalidates every downstream approval/review artifact.
    # Keep episode.json as the sole state source while removing stale stage marks.
    stale_stages = {"approve", "qa", "delivery", "export"}
    model.retain_completed_stages(set(model.completed_stages) - stale_stages)
    for relative in (
        "work/qa/video-release-review.json",
        "delivery/visual-approval.json",
        "delivery/qa-report.json",
        "delivery/qa-report.md",
    ):
        (ep_dir / relative).unlink(missing_ok=True)
    if model.production_type in {"STANDARD", "VISUAL_EXPLAINER"}:
        from avs.production_backend import produce_publishable_video
        result = produce_publishable_video(ep_dir, model.production_type, force=force)
        if model.status in {"TIMELINE_READY", "PILOT_APPROVED"}:
            model.ensure_stage("rough_cut", "ROUGH_CUT_READY")
        model.complete_stage("final-render")
        model.save(ep_dir / "episode.json")
        return result
    if model.production_type == "SCREEN_DOCUMENTARY":
        from avs.pilots import assert_screen_documentary_pilot_gate, validate_context_first, validate_source_order
        assert_screen_documentary_pilot_gate(ep_dir, model)
        if model.publishable:
            ready, reason = voice_lock_state(ep_dir, publishable=True)
            if not ready:
                raise RuntimeError("publishable final-render 必须先通过 voice-lock: " + reason)
        index_path = ep_dir / "work" / "director" / "录屏内容索引.json"
        if not index_path.is_file():
            raise RuntimeError("SCREEN_DOCUMENTARY final-render 缺少当前 Episode 录屏索引")
        index = _read(index_path)
        source_asset_id = index.get("source_asset_id")
        timeline_path = ep_dir / "work" / "timeline.json"
        if timeline_path.is_file():
            current_timeline = _read(timeline_path)
            screen_clips = [
                clip for track in current_timeline.get("tracks", [])
                for clip in track.get("clips", [])
                if track.get("kind") == "video" and clip.get("asset_id")
            ]
            if screen_clips:
                if any(clip.get("asset_id") != source_asset_id for clip in screen_clips):
                    raise RuntimeError("SCREEN_DOCUMENTARY timeline 引用了当前主录屏之外的素材")
                source_clips = [
                    {
                        "source_start": clip.get("in_point", 0.0),
                        "source_end": clip.get("out_point", clip.get("in_point", 0.0) + clip.get("duration", 0.0)),
                        **(clip.get("transform") or {}),
                    }
                    for clip in screen_clips
                ]
                validate_source_order(source_clips)
                validate_context_first(source_clips)
    review_path = ep_dir / "work" / "qa" / "visual-review.json"
    if not review_path.is_file():
        raise RuntimeError("final-render 必须先完成 visual-review")
    review = _read(review_path)
    if not review.get("passed") or review.get("blocked"):
        raise RuntimeError("visual-review 未通过，禁止进入 final-render")
    timeline = Timeline.load(ep_dir / "work" / "timeline.json")
    build_srt(
        timeline,
        ep_dir / "work" / "captions.srt",
        words_path=ep_dir / "work" / "final-narration.words.json",
    )
    from avs.render import render_rough_cut
    rough = render_rough_cut(ep_dir, timeline, force=force)
    renders = ep_dir / "renders"
    final_clean = renders / "final-clean.mp4"
    final_captions = renders / "final-with-captions.mp4"
    from avs.hyperframes import render_motion_graphics
    project_root = Path(__file__).resolve().parents[2]
    clean_motion = render_motion_graphics(
        project_root, ep_dir, timeline, force=force,
        base_video=rough["preview_clean"], output_path=final_clean,
        write_manifest=False,
    )
    caption_motion = render_motion_graphics(
        project_root, ep_dir, timeline, force=force,
        base_video=rough["preview_with_captions"], output_path=final_captions,
    )
    if clean_motion.output_path is None:
        import shutil
        shutil.copy2(rough["preview_clean"], final_clean)
    if caption_motion.output_path is None:
        import shutil
        shutil.copy2(rough["preview_with_captions"], final_captions)
    result = {
        "final_clean": final_clean,
        "final_with_captions": final_captions,
        "preview_clean": rough["preview_clean"],
        "preview_with_captions": rough["preview_with_captions"],
    }
    if model.status in {"TIMELINE_READY", "PILOT_APPROVED"}:
        model.ensure_stage("rough_cut", "ROUGH_CUT_READY")
    model.complete_stage("final-render")
    model.save(ep_dir / "episode.json")
    return result
