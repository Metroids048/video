"""src/avs/reference/__init__.py — 模块4主入口：run_reference_analyze()。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from avs.ingest.manifest import load_manifest
from avs.ingest.probe import probe_media
from avs.reference.audio import extract_audio
from avs.reference.contact_sheet import make_contact_sheet
from avs.reference.keyframes import extract_keyframes
from avs.reference.recipe import build_recipe, save_recipe
from avs.reference.shots import detect_shots
from avs.reference.transcription import run_transcription

log = logging.getLogger(__name__)


def run_reference_analyze(
    episode_dir: Path,
    episode_id: str,
    *,
    transcription_provider: str = "auto",
    force: bool = False,
) -> list[dict[str, Any]]:
    """分析 episode 中所有参考视频，生成 reference-recipe.json。

    返回生成的 recipe 列表（每个参考视频一个）。
    无参考视频时返回空列表（不报错）。
    """
    # 加载 asset-manifest 找出参考视频
    manifest = load_manifest(episode_dir)
    ref_assets = [
        a for a in manifest["assets"]
        if a["kind"] == "video"
        and a["status"] == "ok"
        and "reference" in a["source_path"]
    ]

    if not ref_assets:
        log.info("未找到参考视频（kind=video, source_path 含 reference），跳过分析")
        return []

    work_ref_dir = episode_dir / "work" / "reference"
    work_ref_dir.mkdir(parents=True, exist_ok=True)

    recipes: list[dict[str, Any]] = []

    for asset in ref_assets:
        asset_id = asset["asset_id"]
        video_path = episode_dir / asset["working_path"]
        if not video_path.exists():
            video_path = episode_dir / asset["source_path"]
        if not video_path.exists():
            log.warning("参考视频文件不存在: %s", asset["source_path"])
            continue

        log.info("分析参考视频: %s (%s)", asset_id, video_path.name)

        asset_work_dir = work_ref_dir / asset_id
        asset_work_dir.mkdir(parents=True, exist_ok=True)

        # 1. FFprobe 探测（已在 ingest 阶段做过，但 recipe 需要 duration/fps）
        probe = probe_media(video_path)
        duration = probe.get("duration") or 0.0
        if duration <= 0:
            log.warning("无法获取视频时长，使用 0（可能无 ffprobe）")
            duration = 0.001

        # 2. 提取音频
        audio_out = asset_work_dir / "audio.wav"
        audio_path = extract_audio(video_path, audio_out) if (not audio_out.exists() or force) else audio_out

        # 3. 镜头检测
        shots = detect_shots(video_path, duration)
        log.info("检测到 %d 个镜头", len(shots))

        # 4. 关键帧提取
        kf_dir = asset_work_dir / "keyframes"
        keyframe_paths = extract_keyframes(video_path, shots, kf_dir)

        # 5. 联系表
        contact_out = asset_work_dir / "contact_sheet.jpg"
        if not contact_out.exists() or force:
            make_contact_sheet(keyframe_paths, contact_out)

        # 6. 转写
        transcript_out = asset_work_dir / "transcript.json"
        tr_result = run_transcription(
            audio_path=audio_path,
            episode_dir=episode_dir,
            output_path=transcript_out,
            provider=transcription_provider,
        )
        transcript_text = tr_result.text if tr_result else None

        # 7. 生成 recipe（相对路径 keyframe_paths）
        recipe = build_recipe(
            episode_id=episode_id,
            source_asset_id=asset_id,
            probe=probe,
            shots=shots,
            keyframe_paths=keyframe_paths,
            episode_dir=episode_dir,
            transcript_text=transcript_text,
        )

        out_path = save_recipe(episode_dir, recipe)
        log.info("Recipe 保存: %s", out_path)
        recipes.append(recipe)

    return recipes
