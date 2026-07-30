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
    assert skill["remotion_primary_renderer"] is False
