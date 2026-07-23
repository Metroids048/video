"""Run the two V1 demos through the canonical ``python -m avs`` CLI."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = {
    "reference": ROOT / "fixtures" / "reference-adapt-demo",
    "screen": ROOT / "fixtures" / "screen-explainer-demo",
}


@dataclass(frozen=True)
class DemoSpec:
    name: str
    fixture_dir: Path
    data: dict[str, Any]

    @property
    def episode_id(self) -> str:
        return str(self.data["episode_id"])

    @property
    def episode_dir(self) -> Path:
        return ROOT / "episodes" / "active" / self.episode_id


def load_spec(name: str) -> DemoSpec:
    fixture_dir = FIXTURES[name]
    data = json.loads((fixture_dir / "fixture.json").read_text(encoding="utf-8"))
    return DemoSpec(name, fixture_dir, data)


def run_cli(args: list[str], label: str, *, extra_env: dict[str, str] | None = None) -> None:
    command = [sys.executable, "-m", "avs", *args]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    if extra_env:
        env.update(extra_env)
    print(f"\n[{label}] {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"{label} 失败 (exit {result.returncode})")


def _episode_data(spec: DemoSpec) -> dict[str, Any]:
    return json.loads((spec.episode_dir / "episode.json").read_text(encoding="utf-8"))


def _stage_done(spec: DemoSpec, stage: str) -> bool:
    return stage in _episode_data(spec).get("completed_stages", [])


def _remove_generated_episode(spec: DemoSpec) -> None:
    active_root = (ROOT / "episodes" / "active").resolve()
    target = spec.episode_dir.resolve()
    target.relative_to(active_root)
    if not spec.episode_id.startswith("EP-DEMO-"):
        raise ValueError(f"拒绝清理非 Demo Episode: {spec.episode_id}")
    if target.is_dir():
        shutil.rmtree(target)


def _create_episode(spec: DemoSpec, *, force: bool) -> None:
    if force:
        _remove_generated_episode(spec)
    if spec.episode_dir.is_dir():
        return
    platforms = ",".join(spec.data["platforms"])
    run_cli(
        ["episode", "create", spec.episode_id, "--mode", spec.data["mode"], "--platforms", platforms],
        f"{spec.name}: create",
    )
    shutil.copytree(spec.fixture_dir / "input", spec.episode_dir / "input", dirs_exist_ok=True)


def _asset_ids(spec: DemoSpec) -> dict[str, str]:
    manifest = json.loads((spec.episode_dir / "work" / "asset-manifest.json").read_text(encoding="utf-8"))
    return {
        str(asset["source_path"]): str(asset["asset_id"])
        for asset in manifest["assets"]
        if asset["status"] == "ok"
    }


def materialize_content(spec: DemoSpec) -> None:
    """Materialize static fixture content as canonical Script/Storyboard files."""
    generated_at = datetime.now(timezone.utc).isoformat()
    content_dir = spec.episode_dir / "work" / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    asset_ids = _asset_ids(spec)

    script_config = deepcopy(spec.data["script"])
    script = {
        "episode_id": spec.episode_id,
        "total_duration_estimate": script_config["total_duration_estimate"],
        "segments": [],
        "generated_at": generated_at,
    }
    for configured in script_config["segments"]:
        segment = deepcopy(configured)
        segment.update({"status": "draft", "notes": None})
        script["segments"].append(segment)

    storyboard_config = deepcopy(spec.data["storyboard"])
    shots: list[dict[str, Any]] = []
    for configured in storyboard_config["shots"]:
        shot = deepcopy(configured)
        sources = shot.pop("asset_sources")
        missing_sources = [source for source in sources if source not in asset_ids]
        if missing_sources:
            raise ValueError(f"Fixture 素材未进入 Manifest: {', '.join(missing_sources)}")
        shot["asset_ids"] = [asset_ids[source] for source in sources]
        shots.append(shot)
    gaps = [shot["scene_id"] for shot in shots if shot["missing_assets"]]
    storyboard = {
        "episode_id": spec.episode_id,
        "shots": shots,
        "asset_gaps": gaps,
        "generated_at": generated_at,
    }

    (content_dir / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    (content_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    (content_dir / "brief.md").write_text(
        f"# 内容简报\n\nEpisode: {spec.episode_id}\n\n事实来源: `input/idea.md`\n",
        encoding="utf-8",
    )
    (content_dir / "script.md").write_text(
        "# 视频脚本\n\n" + "\n\n".join(f"## {item['segment_id']}\n\n{item['text']}" for item in script["segments"]) + "\n",
        encoding="utf-8",
    )
    (content_dir / "storyboard.md").write_text(
        "# 分镜\n\n" + "\n".join(f"- {item['scene_id']}: {item['caption']}" for item in shots) + "\n",
        encoding="utf-8",
    )
    missing_lines = [f"- {item['scene_id']}: {', '.join(item['missing_assets'])}" for item in shots if item["missing_assets"]]
    (content_dir / "missing-assets.md").write_text(
        "# 缺失素材\n\n" + ("\n".join(missing_lines) if missing_lines else "- 无") + "\n",
        encoding="utf-8",
    )


def _run_preproduction(spec: DemoSpec, *, stop_after: str | None) -> bool:
    if not _stage_done(spec, "ingest"):
        run_cli(["ingest", spec.episode_id], f"{spec.name}: ingest")

    has_reference = any((spec.fixture_dir / "input" / "reference").glob("*.mp4"))
    if has_reference and not _stage_done(spec, "reference"):
        run_cli(
            ["reference", "analyze", spec.episode_id, "--transcription", spec.data["transcription"]],
            f"{spec.name}: reference",
        )
    if stop_after == "reference":
        print(f"\n[STOP] {spec.name} 在 reference 后按要求中断")
        return False

    if not _stage_done(spec, "content"):
        run_cli(["content", "init", spec.episode_id], f"{spec.name}: content init")
        materialize_content(spec)
        run_cli(["content", "validate", spec.episode_id], f"{spec.name}: content validate")
        run_cli(["content", "approve", spec.episode_id], f"{spec.name}: content approve")
    if not _stage_done(spec, "assets"):
        run_cli(["assets", "validate", spec.episode_id], f"{spec.name}: assets validate")
        run_cli(["assets", "approve", spec.episode_id], f"{spec.name}: assets approve")
    return True


def _run_postproduction(spec: DemoSpec, *, stop_after: str | None, force_motion_fallback: bool) -> bool:
    if not _stage_done(spec, "timeline"):
        run_cli(["timeline", "build", spec.episode_id], f"{spec.name}: timeline")
        run_cli(["timeline", "validate", spec.episode_id], f"{spec.name}: timeline validate")
    if not _stage_done(spec, "rough_cut"):
        run_cli(["subtitles", "build", spec.episode_id], f"{spec.name}: subtitles")
        run_cli(["render", "rough", spec.episode_id], f"{spec.name}: rough cut")
    if stop_after == "render":
        print(f"\n[STOP] {spec.name} 在 render 后按要求中断")
        return False

    if not _stage_done(spec, "qa"):
        motion_env = None
        if force_motion_fallback:
            motion_env = {"HYPERFRAMES_BROWSER_PATH": str(ROOT / "fixtures" / "missing-browser.exe")}
        run_cli(["motion", "render", spec.episode_id], f"{spec.name}: motion", extra_env=motion_env)
        run_cli(["qa", spec.episode_id], f"{spec.name}: qa")
    if not _stage_done(spec, "delivery"):
        run_cli(["deliver", spec.episode_id], f"{spec.name}: delivery")
    return True


def verify_demo(spec: DemoSpec) -> dict[str, Any]:
    from avs.delivery.manifest import validate_manifest
    from avs.qa.decode import decode_error
    from avs.qa.metadata import probe_media

    episode = _episode_data(spec)
    if episode["status"] != "DELIVERY_READY":
        raise ValueError(f"最终状态错误: {episode['status']}")
    manifest_path = spec.episode_dir / "delivery" / "delivery-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(spec.episode_dir, manifest)
    if any(Path(item["path"]).is_absolute() or not item["path"].startswith("delivery/") for item in manifest["files"]):
        raise ValueError("交付清单包含绝对路径或非 delivery 路径")

    final_video = spec.episode_dir / "renders" / "preview-with-motion.mp4"
    if not final_video.is_file():
        final_video = spec.episode_dir / "renders" / "preview-with-captions.mp4"
    metadata = probe_media(final_video)
    expected = json.loads((spec.fixture_dir / "expected-metadata.json").read_text(encoding="utf-8"))
    canvas = expected["canvas"]
    if (metadata.get("width"), metadata.get("height")) != (canvas["width"], canvas["height"]):
        raise ValueError(f"输出尺寸错误: {metadata}")
    if metadata.get("video_codec") != expected["video_codec"] or metadata.get("audio_codec") != expected["audio_codec"]:
        raise ValueError(f"输出编码错误: {metadata}")
    decode_message = decode_error(final_video)
    if decode_message:
        raise ValueError(f"最终视频完整解码失败: {decode_message}")
    return {
        "episode_id": spec.episode_id,
        "status": episode["status"],
        "delivery": manifest_path.relative_to(ROOT).as_posix(),
        "video": final_video.relative_to(ROOT).as_posix(),
        "metadata": metadata,
        "files": len(manifest["files"]),
    }


def run_demo(spec: DemoSpec, *, force: bool, stop_after: str | None, force_motion_fallback: bool) -> dict[str, Any] | None:
    print(f"\n{'=' * 72}\nDemo: {spec.name} ({spec.episode_id})\n{'=' * 72}")
    _create_episode(spec, force=force)
    if not _run_preproduction(spec, stop_after=stop_after):
        return None
    if not _run_postproduction(spec, stop_after=stop_after, force_motion_fallback=force_motion_fallback):
        return None
    result = verify_demo(spec)
    print(f"\n[PASS] {spec.name}: {result['video']} -> {result['delivery']}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent Video Studio V1 E2E demos")
    parser.add_argument("--mode", choices=["reference", "screen"], help="只运行一个 Demo")
    parser.add_argument("--all", action="store_true", help="运行两个 Demo")
    parser.add_argument("--force", action="store_true", help="删除并重建明确命名的 Demo Episode")
    parser.add_argument("--stop-after", choices=["reference", "render"], help="模拟中断")
    parser.add_argument("--force-motion-fallback", action="store_true", help="用不存在的浏览器验证 FFmpeg 动效降级")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = ["reference", "screen"] if args.all or not args.mode else [args.mode]
    results: list[dict[str, Any]] = []
    try:
        for name in names:
            result = run_demo(
                load_spec(name), force=args.force, stop_after=args.stop_after,
                force_motion_fallback=args.force_motion_fallback,
            )
            if result:
                results.append(result)
    except Exception as exc:
        print(f"\n[FAIL] E2E Demo: {exc}", file=sys.stderr)
        return 1
    print(f"\n完成 Demo: {len(results)}/{len(names)}；中断场景不计失败")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
