from __future__ import annotations

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
