"""tests/test_reference.py — 模块4验收测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from avs.reference import run_reference_analyze
from avs.reference.audio import extract_audio
from avs.reference.keyframes import extract_keyframes
from avs.reference.recipe import load_recipe, recipe_path
from avs.reference.shots import Shot, detect_shots


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
        # 无 ffmpeg 或文件损坏 → None（不抛异常）
        assert result is None or not out.exists()


class TestKeyframes:
    def test_extract_keyframes_no_ffmpeg(self, tmp_path: Path) -> None:
        """FFmpeg 不可用时返回空字典。"""
        video = tmp_path / "fake.mp4"
        video.write_bytes(b"not a real video")
        shots = [Shot("s001", 0.0, 5.0)]
        result = extract_keyframes(video, shots, tmp_path / "kf")
        assert isinstance(result, dict)
        # 无 ffmpeg 或损坏文件 → 空字典


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
        # 空 manifest
        save_manifest(ep_dir, "EP-TEST-REF", [])
        recipes = run_reference_analyze(ep_dir, "EP-TEST-REF")
        assert recipes == []
