from __future__ import annotations

import json
from pathlib import Path

from avs.active import active_voice_audition, active_voice_lock
from avs.models.episode import EpisodeModel
from avs.workflow import action_for_episode


def _episode(tmp_path: Path, *, production_type: str = "STANDARD") -> tuple[Path, EpisodeModel]:
    ep = tmp_path / "episodes" / "active" / "EP-VOICE"
    (ep / "work" / "analysis").mkdir(parents=True)
    (ep / "work" / "content").mkdir(parents=True)
    (ep / "work" / "prepared").mkdir(parents=True)
    (ep / "work" / "input-manifest.json").write_text(
        json.dumps({"episode_id": ep.name, "assets": []}), encoding="utf-8"
    )
    model = EpisodeModel.create(ep.name, production_type=production_type)
    for status in ("INGESTED", "CONTENT_READY"):
        model.transition(status)
    model.complete_stage("ingest")
    model.complete_stage("analyze")
    model.complete_stage("plan")
    model.save(ep / "episode.json")
    return ep, model


def test_missing_voice_returns_explicit_audition_action(tmp_path: Path) -> None:
    ep, model = _episode(tmp_path)
    action = action_for_episode(ep, model)
    assert action.stage == "voice-audition"
    assert action.kind == "human"
    assert action.command is None


def test_approved_voice_audition_unlocks_voice_lock(tmp_path: Path) -> None:
    ep, model = _episode(tmp_path)
    sample = tmp_path / "user-voice.wav"
    sample.write_bytes(b"voice")
    active_voice_audition(ep, model, sample, provider="azure_speech", voice_profile="profile-1")
    reloaded = EpisodeModel.load(ep / "episode.json")
    assert "voice-lock" in reloaded.completed_stages
    assert (ep / "work" / "final-narration.mp3").is_file()
    assert action_for_episode(ep, reloaded).stage == "preview"


def test_edge_tts_is_not_publishable_voice(tmp_path: Path) -> None:
    ep, _model = _episode(tmp_path)
    (ep / "work" / "final-narration.mp3").write_bytes(b"edge")
    (ep / "work" / "voice-lock.json").write_text(
        json.dumps({"approved": True, "voice_profile": "edge", "provider": "edge_tts"}),
        encoding="utf-8",
    )
    ready_model = EpisodeModel.load(ep / "episode.json")
    action = action_for_episode(ep, ready_model)
    assert action.stage == "voice-audition"
    assert "Edge TTS" in action.summary


def test_voice_lock_is_idempotent_and_copies_current_audio(tmp_path: Path) -> None:
    ep, model = _episode(tmp_path)
    source = ep / "work" / "source.wav"
    source.write_bytes(b"approved")
    (ep / "work" / "voice-lock.json").write_text(
        json.dumps({"approved": True, "voice_profile": "profile-1", "provider": "user_audio"}),
        encoding="utf-8",
    )
    (ep / "work" / "input-manifest.json").write_text(
        json.dumps({"episode_id": ep.name, "assets": [{"source_type": "audio", "audio_role": "narration", "working_path": "work/source.wav"}]}),
        encoding="utf-8",
    )
    result = active_voice_lock(ep, model)
    assert result["provider"] == "user_audio"
    assert (ep / "work" / "final-narration.mp3").read_bytes() == b"approved"


def test_user_manifest_voice_can_be_locked_without_edge_or_hidden_fallback(tmp_path: Path) -> None:
    ep, model = _episode(tmp_path)
    source = ep / "work" / "user.wav"
    source.write_bytes(b"user-voice")
    (ep / "work" / "input-manifest.json").write_text(
        json.dumps({"episode_id": ep.name, "assets": [{"source_type": "audio", "audio_role": "original_voice", "working_path": "work/user.wav", "status": "ok"}]}),
        encoding="utf-8",
    )
    assert action_for_episode(ep, model).stage == "voice-lock"
    active_voice_lock(ep, model)
    assert json.loads((ep / "work" / "voice-lock.json").read_text(encoding="utf-8"))["provider"] == "user_audio"


def test_release_order_requires_approve_before_qa(tmp_path: Path) -> None:
    ep, model = _episode(tmp_path)
    model.complete_stage("voice-lock")
    model.complete_stage("preview")
    model.complete_stage("visual-review")
    model.complete_stage("final-render")
    model.save(ep / "episode.json")
    assert action_for_episode(ep, model).stage == "release-review"
