"""Active multimodal workflow stages.

All artifacts are attached to the existing Episode directory; ``episode.json``
remains the only state store.  Legacy timeline/render commands can still be
used for internal filter tests, but these helpers are the publishable route.
"""
from __future__ import annotations

import json
import hashlib
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
    """Use an already verified VCI package; never invoke ingest/transcription."""
    if model.production_type != "SCREEN_DOCUMENTARY":
        raise RuntimeError("story-mine 只适用于 SCREEN_DOCUMENTARY")
    from avs.pilots import mine_story
    if model.status == "CREATED":
        model.ensure_stage("ingest", "INGESTED")
        model.complete_stage("ingest")
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
    _write(ep_dir / "work" / "content" / "evidence-map.json", evidence)
    _write(ep_dir / "work" / "content" / "shot-plan.json", shot_plan)
    if model.status == "INGESTED":
        model.ensure_stage("content", "CONTENT_READY")
    model.complete_stage("plan")
    model.save(ep_dir / "episode.json")
    return {"brief": brief, "selection": selection, "script": script, "evidence_map": evidence, "shot_plan": shot_plan}


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
    if model.production_type == "SCREEN_DOCUMENTARY":
        from avs.pilots import assert_screen_documentary_pilot_gate
        assert_screen_documentary_pilot_gate(ep_dir, model)
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
