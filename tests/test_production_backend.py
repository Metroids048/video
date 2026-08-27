from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from avs.production_backend import (
    ProductionBackendError,
    build_mpt_command,
    build_mpt_request,
    run_mpt,
)


def _episode(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    ep = root / "episodes" / "active" / "EP-MPT"
    (root / "config").mkdir(parents=True)
    (root / "config" / "production-backends.yaml").write_text(
        "production_backends:\n  moneyprinterturbo:\n    version: '1.2.7'\n    runtime: '.runtime/moneyprinterturbo'\n",
        encoding="utf-8",
    )
    (root / ".runtime" / "moneyprinterturbo").mkdir(parents=True)
    (root / ".runtime" / "moneyprinterturbo" / "cli.py").write_text("# pinned runtime\n", encoding="utf-8")
    (ep / "work" / "content").mkdir(parents=True)
    (ep / "work" / "content" / "script.md").write_text("approved script", encoding="utf-8")
    (ep / "work" / "prepared").mkdir(parents=True)
    (ep / "work" / "prepared" / "material.png").write_bytes(b"material")
    (ep / "work" / "final-narration.mp3").write_bytes(b"locked-audio")
    return ep


def test_standard_route_uses_pinned_mpt_contract(tmp_path: Path) -> None:
    request = build_mpt_request(_episode(tmp_path))
    command = build_mpt_command(request)
    assert "--video-script" in command
    assert "--video-source" in command and "local" in command
    assert "--video-materials" in command
    assert "--custom-audio-file" in command
    assert command[-4:] == ["--video-aspect", "9:16", "--stop-at", "video"]


def test_locked_audio_is_required(tmp_path: Path) -> None:
    ep = _episode(tmp_path)
    (ep / "work" / "final-narration.mp3").unlink()
    with pytest.raises(ProductionBackendError, match="custom audio"):
        build_mpt_request(ep)


def test_mpt_candidate_is_copied_to_canonical_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ep = _episode(tmp_path)
    candidate = tmp_path / "mpt" / "final.mp4"
    candidate.parent.mkdir()
    candidate.write_bytes(b"mpt-video")

    monkeypatch.setattr(
        "avs.production_backend.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=f"MPT_RESULT\nVIDEO_FILE={candidate}\n", stderr=""),
    )
    result = run_mpt(ep)
    assert result == ep / "renders" / "final-with-captions.mp4"
    assert result.read_bytes() == b"mpt-video"


def test_mpt_failure_does_not_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ep = _episode(tmp_path)
    monkeypatch.setattr(
        "avs.production_backend.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="backend failed"),
    )
    with pytest.raises(ProductionBackendError, match="生产失败"):
        run_mpt(ep)
    assert not (ep / "renders" / "final-with-captions.mp4").exists()
