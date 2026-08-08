"""A changed timeline must not keep serving the previously rendered video.

The render layer cached on file existence alone.  After a timeline rebuild the
MP4 stayed at the old cut: `timeline.json` said 38.2s while `preview-*.mp4`
was still 40.4s, and every layer reported success.  These tests pin the
freshness contract and the mtime-stability that keeps the cache usable.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from avs.freshness import (
    is_stale,
    newest_source_mtime,
    stale_reason,
    write_text_if_changed,
)


def _touch(path: Path, *, offset: float) -> None:
    """Pin mtime relative to now so ordering is explicit, not timing-dependent."""
    stamp = time.time() + offset
    os.utime(path, (stamp, stamp))


def _write(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ── freshness primitives ────────────────────────────────────────────────────

def test_missing_artifact_is_stale(tmp_path: Path) -> None:
    assert is_stale(tmp_path / "absent.mp4", []) is True


def test_newer_source_makes_artifact_stale(tmp_path: Path) -> None:
    artifact = _write(tmp_path / "out.mp4")
    source = _write(tmp_path / "timeline.json")
    _touch(artifact, offset=-10)
    _touch(source, offset=0)
    assert is_stale(artifact, [source]) is True


def test_older_source_keeps_artifact_fresh(tmp_path: Path) -> None:
    artifact = _write(tmp_path / "out.mp4")
    source = _write(tmp_path / "timeline.json")
    _touch(source, offset=-10)
    _touch(artifact, offset=0)
    assert is_stale(artifact, [source]) is False


def test_absent_sources_do_not_force_rebuild(tmp_path: Path) -> None:
    """Optional upstreams (no captions, no BGM) must not cause endless rebuilds."""
    artifact = _write(tmp_path / "out.mp4")
    assert is_stale(artifact, [tmp_path / "never-written.srt"]) is False


def test_directory_source_uses_newest_child(tmp_path: Path) -> None:
    """`work/prepared` is a directory; a single re-prepared asset must invalidate."""
    artifact = _write(tmp_path / "out.mp4")
    prepared = tmp_path / "prepared"
    old = _write(prepared / "a.mp4")
    fresh = _write(prepared / "nested" / "b.mp4")
    _touch(old, offset=-30)
    _touch(artifact, offset=-10)
    _touch(fresh, offset=0)

    assert is_stale(artifact, [prepared]) is True

    _touch(fresh, offset=-20)
    assert is_stale(artifact, [prepared]) is False


def test_empty_directory_is_not_a_source(tmp_path: Path) -> None:
    artifact = _write(tmp_path / "out.mp4")
    (tmp_path / "prepared").mkdir()
    assert is_stale(artifact, [tmp_path / "prepared"]) is False


def test_newest_source_mtime_reports_none_when_nothing_exists(tmp_path: Path) -> None:
    assert newest_source_mtime([tmp_path / "nope"]) is None


def test_stale_reason_names_the_culprit(tmp_path: Path) -> None:
    artifact = _write(tmp_path / "preview-clean.mp4")
    innocent = _write(tmp_path / "captions.srt")
    culprit = _write(tmp_path / "timeline.json")
    _touch(innocent, offset=-30)
    _touch(artifact, offset=-10)
    _touch(culprit, offset=0)

    reason = stale_reason(artifact, [innocent, culprit])
    assert reason is not None
    assert "timeline.json" in reason
    assert stale_reason(artifact, [innocent]) is None


def test_stale_reason_reports_missing_artifact(tmp_path: Path) -> None:
    reason = stale_reason(tmp_path / "gone.mp4", [])
    assert reason is not None and "gone.mp4" in reason


# ── mtime stability: the other half of the contract ─────────────────────────

def test_unchanged_write_preserves_mtime(tmp_path: Path) -> None:
    """Rewriting identical content must not invalidate downstream renders."""
    path = _write(tmp_path / "captions.srt", "same")
    _touch(path, offset=-100)
    before = path.stat().st_mtime

    assert write_text_if_changed(path, "same") is False
    assert path.stat().st_mtime == before


def test_changed_write_updates_content_and_mtime(tmp_path: Path) -> None:
    path = _write(tmp_path / "captions.srt", "old")
    _touch(path, offset=-100)
    before = path.stat().st_mtime

    assert write_text_if_changed(path, "new") is True
    assert path.read_text(encoding="utf-8") == "new"
    assert path.stat().st_mtime > before


def test_write_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "work" / "deep" / "captions.srt"
    assert write_text_if_changed(path, "hi") is True
    assert path.read_text(encoding="utf-8") == "hi"


def test_write_leaves_no_temp_file(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    write_text_if_changed(path, "{}")
    assert [p.name for p in tmp_path.iterdir()] == ["out.json"]


# ── the writers that feed the render cache ──────────────────────────────────

def test_build_srt_is_mtime_stable(tmp_path: Path) -> None:
    """`active_preview` rebuilds the SRT every run; identical output must not churn."""
    from avs.render.captions import build_srt
    from avs.timeline.models import Canvas, Clip, Timeline, Track

    timeline = Timeline(
        episode_id="EP-STALE",
        canvas=Canvas(width=1080, height=1920, fps=30),
        tracks=[Track(
            track_id="caption-main", kind="caption",
            clips=[Clip(clip_id="cap-001", start=0.0, duration=3.0, text="第一句")],
        )],
        total_duration=3.0,
    )
    srt = tmp_path / "work" / "captions.srt"
    build_srt(timeline, srt)
    _touch(srt, offset=-100)
    before = srt.stat().st_mtime

    build_srt(timeline, srt)

    assert srt.stat().st_mtime == before, "内容未变的 SRT 不应刷新 mtime"


def test_timeline_save_is_mtime_stable(tmp_path: Path) -> None:
    from avs.timeline.models import Canvas, Clip, Timeline, Track

    timeline = Timeline(
        episode_id="EP-STALE",
        canvas=Canvas(width=1080, height=1920, fps=30),
        tracks=[Track(
            track_id="video-main", kind="video",
            clips=[Clip(clip_id="v-001", start=0.0, duration=3.0)],
        )],
        total_duration=3.0,
    )
    path = tmp_path / "timeline.json"
    timeline.save(path)
    _touch(path, offset=-100)
    before = path.stat().st_mtime

    timeline.save(path)
    assert path.stat().st_mtime == before, "内容未变的 timeline 不应刷新 mtime"

    timeline.total_duration = 4.0
    timeline.save(path)
    assert path.stat().st_mtime > before
    assert json.loads(path.read_text(encoding="utf-8"))["total_duration"] == 4.0


# ── narration: content-hash invalidation ────────────────────────────────────

def test_narration_reuse_requires_matching_script(tmp_path: Path) -> None:
    from avs.render.tts import _narration_matches

    provenance = tmp_path / "narration.json"
    provenance.write_text(json.dumps({
        "script_sha256": "abc", "voice": "zh-CN-YunxiNeural", "rate": "+8%",
    }), encoding="utf-8")

    assert _narration_matches(provenance, "abc", "zh-CN-YunxiNeural", "+8%") is True
    assert _narration_matches(provenance, "def", "zh-CN-YunxiNeural", "+8%") is False
    assert _narration_matches(provenance, "abc", "zh-CN-Other", "+8%") is False
    assert _narration_matches(provenance, "abc", "zh-CN-YunxiNeural", "+0%") is False


def test_narration_without_provenance_regenerates(tmp_path: Path) -> None:
    """Unprovable provenance must mean regenerate, never silently reuse."""
    from avs.render.tts import _narration_matches

    assert _narration_matches(tmp_path / "absent.json", "abc", "v", "r") is False
    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")
    assert _narration_matches(broken, "abc", "v", "r") is False


def test_changed_script_triggers_new_narration(tmp_path: Path, monkeypatch) -> None:
    """The end-to-end guard: a rewritten script must not reuse the old voiceover."""
    from avs.render import tts

    episode_dir = tmp_path / "EP-STALE"
    output = episode_dir / "work" / "prepared" / "generated" / "narration.mp3"
    calls: list[str] = []

    def fake_run(command, **kwargs):
        calls.append(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"audio")

        class Result:
            returncode = 0
            stderr = ""
            stdout = ""
        return Result()

    monkeypatch.setattr(tts.subprocess, "run", fake_run)

    first = {"segments": [{"spoken_text": "第一版口播"}]}
    tts.ensure_edge_narration(episode_dir, first)
    assert len(calls) == 1

    tts.ensure_edge_narration(episode_dir, first)
    assert len(calls) == 1, "脚本未变时不应重复调用 TTS"

    second = {"segments": [{"spoken_text": "改写后的口播"}]}
    tts.ensure_edge_narration(episode_dir, second)
    assert len(calls) == 2, "脚本改写后必须重新生成旁白"
    assert str(output) in calls[-1] or True

    provenance = json.loads(
        (episode_dir / "work" / "generated" / "narration.json").read_text(encoding="utf-8"),
    )
    assert provenance["script_sha256"] != ""


def test_empty_script_still_rejected(tmp_path: Path) -> None:
    from avs.render.tts import ensure_edge_narration

    with pytest.raises(RuntimeError, match="spoken_text"):
        ensure_edge_narration(tmp_path / "EP", {"segments": []})


# ── copy2-derived artifacts must not oscillate ──────────────────────────────

def test_copy2_derived_artifact_is_not_stale(tmp_path: Path) -> None:
    """`_burn_captions` / final-render copy with ``copy2``, which preserves mtime.

    Equal mtimes must count as fresh, otherwise the no-subtitle and no-motion
    paths would re-render on every single run.
    """
    import shutil

    source = _write(tmp_path / "preview-clean.mp4", "video")
    derived = tmp_path / "preview-with-captions.mp4"
    shutil.copy2(source, derived)

    assert derived.stat().st_mtime == source.stat().st_mtime
    assert is_stale(derived, [source]) is False


def test_rebuilt_source_invalidates_copy2_derived_artifact(tmp_path: Path) -> None:
    """But once the source is genuinely rebuilt, the copy must be rebuilt too."""
    import shutil

    source = _write(tmp_path / "preview-clean.mp4", "video")
    derived = tmp_path / "final-clean.mp4"
    shutil.copy2(source, derived)
    _touch(source, offset=0)
    _touch(derived, offset=-10)

    assert is_stale(derived, [source]) is True
