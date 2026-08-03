from __future__ import annotations

import json
from pathlib import Path

from avs.config import Config


def test_project_episodes_root_override(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "project.yaml").write_text(
        "project:\n  episodes_root: custom-episodes\n",
        encoding="utf-8",
    )
    assert Config(tmp_path).episodes_root == tmp_path / "custom-episodes"


def test_video_shotcraft_is_pinned_as_reference_only_skill() -> None:
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "skills.lock.json").read_text(encoding="utf-8"))
    skill = lock["third_party_skills"]["video-shotcraft"]

    assert skill["source_repository"] == "https://github.com/Vincentwei1021/video-shotcraft"
    assert skill["commit"] == "d4915443232e89527fdc9d7e79f132ba411fc440"
    assert skill["license"] == "Apache-2.0"
    assert skill["usage"] == "reference_only"
    # video-shotcraft 自身仍不作主渲染器；Remotion 正式渲染见 remotion 条目 / ADR-0006
    assert skill["remotion_primary_renderer"] is False
    assert skill["status"] == "vendored"
    assert "third_party_skills/video-shotcraft" in skill.get("destinations", [])


def test_remotion_is_vendored_as_production_renderer() -> None:
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "skills.lock.json").read_text(encoding="utf-8"))
    skill = lock["third_party_skills"]["remotion"]

    assert skill["source_repository"] == "https://github.com/remotion-dev/skills"
    assert skill["usage"] == "production_allowed"
    assert skill["remotion_primary_renderer"] is True
    assert skill["status"] == "vendored"
    assert (root / "third_party_skills" / "remotion-best-practices" / "SKILL.md").is_file()


def test_video_third_party_skills_are_vendored() -> None:
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "skills.lock.json").read_text(encoding="utf-8"))
    required = [
        "hyperframes",
        "remotion",
        "video-use",
        "seedance",
        "chatcut",
        "capcut-david",
        "cut-skill",
        "ip-strategist",
        "openmontage",
        "video-shotcraft",
        "seedance-free",
        "jianying-editor",
        "ffmpeg",
        "azure-speech",
        "elevenlabs",
        "ai-video-shot-prompt",
        "ltx-prompt-director",
        "epidemic-sound",
        "moneyprinterturbo",
    ]
    for name in required:
        entry = lock["third_party_skills"][name]
        assert entry["status"] in {
            "vendored",
            "installed",
            "installed_offline_bundle",
            "local",
        }
        assert entry.get("usage") in {"production_allowed", "reference_only", None} or name == "hyperframes"
        skill_dir = root / "third_party_skills" / name
        assert skill_dir.is_dir(), name
        assert any(skill_dir.rglob("SKILL.md")), name
    assert (root / "third_party_skills" / "text-to-speech" / "SKILL.md").is_file()
    assert (root / "docs" / "video-plugin-routing.md").is_file()
    assert (root / "docs" / "decisions" / "0006-video-third-party-renderers.md").is_file()
