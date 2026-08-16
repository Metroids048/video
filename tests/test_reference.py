"""tests/test_reference.py — 参考素材分析与 V2 研究规则验收测试。"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from avs.reference import run_reference_analyze
from avs.reference.audio import extract_audio
from avs.reference.keyframes import extract_keyframes
from avs.reference.recipe import load_recipe, recipe_path
from avs.reference.shots import Shot, detect_shots
from avs.ingest import run_ingest
from avs.paths import create_episode_skeleton
from avs.cli import main
from avs.models.episode import EpisodeModel


def test_reference_research_document_is_v2_reusable_rules_not_legacy_ledger() -> None:
    """V2 不再把某一批 18 条历史链接当作生产前置条件。"""
    root = Path(__file__).resolve().parents[1]
    study_path = root / "docs" / "reference-research" / "douyin-codex-short-video-study.md"
    study = study_path.read_text(encoding="utf-8")

    assert "Creator OS V2" in study
    assert "真实结果" in study
    assert "ROI" in study
    assert "Creative Review" in study
    assert "复制文案" in study
    assert "18 条" not in study
    assert not (root / "docs" / "reference-research" / "workbuddy-samples" / "video-workshop").exists()


class TestShots:
    def test_single_shot_fallback(self) -> None:
        """FFprobe 不可用时返回单镜头。"""
        shots = detect_shots(Path("/nonexistent.mp4"), duration=10.0)
        assert len(shots) == 1
        assert shots[0].start == 0.0
        assert shots[0].end == 10.0

    def test_shot_dataclass(self) -> None:
        shot = Shot(shot_id="s001", start=0.0, end=3.5, confidence=0.8)
        d = shot.to_dict()
        assert d["shot_id"] == "s001"
        assert d["start"] == 0.0
        assert d["end"] == 3.5
        assert d["confidence"] == 0.8


class TestAudio:
    def test_extract_audio_no_ffmpeg(self, tmp_path: Path) -> None:
        """FFmpeg 不可用时返回 None 而非崩溃。"""
        video = tmp_path / "fake.mp4"
        video.write_bytes(b"not a real video")
        out = tmp_path / "audio.wav"
        result = extract_audio(video, out)
        assert result is None or not out.exists()


class TestKeyframes:
    def test_extract_keyframes_no_ffmpeg(self, tmp_path: Path) -> None:
        """FFmpeg 不可用时返回空字典。"""
        video = tmp_path / "fake.mp4"
        video.write_bytes(b"not a real video")
        shots = [Shot("s001", 0.0, 5.0)]
        result = extract_keyframes(video, shots, tmp_path / "kf")
        assert isinstance(result, dict)


class TestRecipe:
    def test_recipe_path(self, tmp_path: Path) -> None:
        p = recipe_path(tmp_path)
        assert p == tmp_path / "work" / "reference" / "reference-recipe.json"

    def test_load_recipe_not_exists(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_recipe(tmp_path)


class TestRunReferenceAnalyze:
    def test_no_reference_videos(self, tmp_path: Path) -> None:
        """无参考视频时返回空列表（不崩溃）。"""
        from avs.ingest.manifest import save_manifest
        ep_dir = tmp_path / "EP-TEST-REF"
        ep_dir.mkdir()
        (ep_dir / "work").mkdir()
        save_manifest(ep_dir, "EP-TEST-REF", [])
        recipes = run_reference_analyze(ep_dir, "EP-TEST-REF")
        assert recipes == []

    def test_real_reference_outputs_and_schema(self, tmp_path: Path) -> None:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            pytest.skip("ffmpeg/ffprobe required")
        ep_dir = tmp_path / "EP-TEST-REF"
        ep_dir.mkdir()
        create_episode_skeleton(ep_dir)
        video = ep_dir / "input" / "reference" / "参考.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(video),
        ], check=True, capture_output=True)
        run_ingest(ep_dir, "EP-TEST-REF")

        recipes = run_reference_analyze(
            ep_dir, "EP-TEST-REF", transcription_provider="disabled",
        )
        assert len(recipes) == 1
        recipe = load_recipe(ep_dir)
        assert recipe["width"] == 320
        assert recipe["height"] == 180
        assert recipe["has_audio"] is True
        assert recipe["shots"]
        assert 0 <= recipe["overall_confidence"] <= 1

        asset_id = recipe["source_asset_id"]
        output = ep_dir / "work" / "reference" / asset_id
        assert (output / "shots.json").is_file()
        assert (output / "contact-sheet.jpg").is_file()
        assert list((output / "keyframes").glob("*.jpg"))
        transcript = json.loads((output / "transcript.json").read_text(encoding="utf-8"))
        assert transcript["status"] == "disabled"

    def test_multiple_references_keep_per_asset_recipes(self, tmp_path: Path) -> None:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            pytest.skip("ffmpeg/ffprobe required")
        ep_dir = tmp_path / "EP-MULTI-REF"
        ep_dir.mkdir()
        create_episode_skeleton(ep_dir)
        for index, color in enumerate(("red", "green"), start=1):
            video = ep_dir / "input" / "reference" / f"ref-{index}.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"color=c={color}:s=160x284:d=0.3", "-an", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", str(video),
            ], check=True, capture_output=True)
        run_ingest(ep_dir, "EP-MULTI-REF")
        recipes = run_reference_analyze(
            ep_dir, "EP-MULTI-REF", transcription_provider="disabled",
        )
        assert len(recipes) == 2
        for recipe in recipes:
            path = (
                ep_dir / "work" / "reference" / recipe["source_asset_id"]
                / "reference-recipe.json"
            )
            assert path.is_file()

    def test_reference_cli_updates_episode_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            pytest.skip("ffmpeg/ffprobe required")
        root = tmp_path
        real_root = Path(__file__).resolve().parents[1]
        shutil.copytree(real_root / "config", root / "config")
        (root / "AGENTS.md").write_text("# test", encoding="utf-8")
        ep_dir = root / "episodes" / "active" / "EP-CLI-REF"
        ep_dir.mkdir(parents=True)
        create_episode_skeleton(ep_dir)
        video = ep_dir / "input" / "reference" / "ref.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=160x284:d=0.3",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
        ], check=True, capture_output=True)
        run_ingest(ep_dir, "EP-CLI-REF")
        model = EpisodeModel.create("EP-CLI-REF")
        model.transition("INGESTED")
        model.complete_stage("ingest")
        model.save(ep_dir / "episode.json")
        monkeypatch.setattr("avs.cli._find_project_root", lambda: root)

        result = CliRunner().invoke(
            main, ["reference", "analyze", "EP-CLI-REF", "--transcription", "disabled"],
        )
        assert result.exit_code == 0, result.output
        assert EpisodeModel.load(ep_dir / "episode.json").status == "REFERENCE_READY"
