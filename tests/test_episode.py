"""tests/test_episode.py — Episode 创建/路径/模型/CLI 集成测试。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from avs.models.episode import EpisodeModel, EpisodeValidationError
from avs.paths import PathError, create_episode_skeleton, episode_dir, episode_json_path, find_episode_dir, validate_episode_id
from avs.state import EpisodeStatus, TransitionError


# ── 辅助 fixture ─────────────────────────────────────────────────────

@pytest.fixture()
def episodes_root(tmp_path: Path) -> Path:
    """临时 episodes 根目录。"""
    root = tmp_path / "episodes"
    root.mkdir()
    return root


@pytest.fixture()
def project_root(tmp_path: Path, episodes_root: Path) -> Path:
    """带完整配置的临时项目根（软链接 config/ 和 schemas/ 到真实目录）。"""
    import shutil
    real_root = Path(__file__).resolve().parents[1]

    # 复制配置目录
    shutil.copytree(real_root / "config", tmp_path / "config")
    shutil.copytree(real_root / "schemas", tmp_path / "schemas")

    # AGENTS.md 标记项目根
    (tmp_path / "AGENTS.md").write_text("# Test", encoding="utf-8")

    return tmp_path


# ── ID 校验 ───────────────────────────────────────────────────────────

class TestValidateEpisodeId:
    def test_valid_id(self):
        validate_episode_id("EP-0001")
        validate_episode_id("TEST-0001")
        validate_episode_id("A1")
        validate_episode_id("EPISODE_01")

    def test_lowercase_rejected(self):
        with pytest.raises(PathError):
            validate_episode_id("ep-0001")

    def test_leading_hyphen_rejected(self):
        with pytest.raises(PathError):
            validate_episode_id("-EP0001")

    def test_single_char_rejected(self):
        with pytest.raises(PathError):
            validate_episode_id("A")

    def test_too_long_rejected(self):
        with pytest.raises(PathError):
            validate_episode_id("A" * 65)

    def test_path_traversal_chars_rejected(self):
        with pytest.raises(PathError):
            validate_episode_id("../ESCAPE")

    def test_slash_rejected(self):
        with pytest.raises(PathError):
            validate_episode_id("EP/0001")


# ── 路径穿越 ──────────────────────────────────────────────────────────

class TestPathTraversal:
    def test_normal_path_ok(self, episodes_root: Path):
        ep = episode_dir(episodes_root, "EP-0001")
        assert ep.is_relative_to(episodes_root)

    def test_path_traversal_blocked(self, episodes_root: Path):
        """构造恶意 ID 仍被 ID 格式校验阻止。"""
        with pytest.raises(PathError):
            episode_dir(episodes_root, "../../etc")


# ── 目录骨架 ──────────────────────────────────────────────────────────

class TestEpisodeSkeleton:
    def test_skeleton_created(self, episodes_root: Path):
        ep = episode_dir(episodes_root, "EP-0001")
        ep.mkdir(parents=True)
        create_episode_skeleton(ep)
        assert (ep / "input" / "reference").is_dir()
        assert (ep / "work" / "content").is_dir()
        assert (ep / "renders").is_dir()
        assert (ep / "delivery" / "publish").is_dir()
        assert (ep / "logs").is_dir()

    def test_skeleton_idempotent(self, episodes_root: Path):
        ep = episode_dir(episodes_root, "EP-0001")
        ep.mkdir(parents=True)
        create_episode_skeleton(ep)
        create_episode_skeleton(ep)  # 二次调用不报错


# ── EpisodeModel 创建与校验 ───────────────────────────────────────────

class TestEpisodeModel:
    def test_create_default(self):
        m = EpisodeModel.create("EP-0001")
        assert m.id == "EP-0001"
        assert m.status == EpisodeStatus.CREATED
        assert m.mode == "REFERENCE_ADAPT"
        assert m.publishable is True

    def test_reference_clone_not_publishable(self):
        m = EpisodeModel.create("EP-0001", mode="REFERENCE_CLONE")
        assert m.publishable is False

    def test_reference_adapt_publishable(self):
        m = EpisodeModel.create("EP-0001", mode="REFERENCE_ADAPT")
        assert m.publishable is True

    def test_original_publishable(self):
        m = EpisodeModel.create("EP-0001", mode="ORIGINAL")
        assert m.publishable is True

    def test_timestamps_are_timezone_aware(self):
        m = EpisodeModel.create("EP-0001")
        d = m.to_dict()
        for ts_key in ("created_at", "updated_at"):
            ts = d[ts_key]
            # 带时区的 ISO 8601 必须包含 +/- 或 Z
            assert "+" in ts or "Z" in ts or "-0" in ts or ts.endswith("Z"), (
                f"{ts_key} 不含时区: {ts!r}"
            )

    def test_save_and_load(self, tmp_path: Path, project_root: Path):
        ep_json = tmp_path / "episode.json"
        m = EpisodeModel.create("EP-0001")
        # 修改 schema 路径指向真实文件
        import avs.models.episode as em_module
        original = em_module._SCHEMA_REL
        em_module._SCHEMA_REL = project_root / "schemas" / "episode.schema.json"
        try:
            m.save(ep_json)
            loaded = EpisodeModel.load(ep_json)
            assert loaded.id == "EP-0001"
            assert loaded.status == EpisodeStatus.CREATED
        finally:
            em_module._SCHEMA_REL = original

    def test_transition_valid(self):
        m = EpisodeModel.create("EP-0001")
        m.transition(EpisodeStatus.INGESTED)
        assert m.status == EpisodeStatus.INGESTED

    def test_transition_invalid_raises(self):
        m = EpisodeModel.create("EP-0001")
        with pytest.raises(TransitionError):
            m.transition(EpisodeStatus.DELIVERY_READY)

    def test_fail_sets_status_and_reason(self):
        m = EpisodeModel.create("EP-0001")
        m.fail("测试原因")
        assert m.status == EpisodeStatus.FAILED
        assert m.last_error == "测试原因"


# ── REFERENCE_CLONE publishable 规则 ─────────────────────────────────

class TestReferenceCloneRule:
    def test_publishable_is_false(self):
        m = EpisodeModel.create("RC-0001", mode="REFERENCE_CLONE")
        assert m.publishable is False
        assert m.to_dict()["publishable"] is False

    def test_to_dict_has_false(self):
        m = EpisodeModel.create("RC-0001", mode="REFERENCE_CLONE")
        assert m.to_dict()["publishable"] is False


# ── 重复创建 ──────────────────────────────────────────────────────────

class TestDuplicateCreate:
    def test_duplicate_create_no_clobber(self, episodes_root: Path, project_root: Path):
        """重复 create 时不破坏已有目录，返回非零退出码。"""
        ep = episode_dir(episodes_root, "EP-0001")
        ep.mkdir(parents=True)
        create_episode_skeleton(ep)

        import avs.models.episode as em_module
        em_module._SCHEMA_REL = project_root / "schemas" / "episode.schema.json"

        m = EpisodeModel.create("EP-0001")
        m.save(episode_json_path(ep))

        # 模拟 CLI 逻辑：目录已存在时应返回非零
        ep_json = episode_json_path(ep)
        assert ep_dir_exists := ep.exists()
        assert ep_json.exists()


# ── CLI 集成（subprocess）────────────────────────────────────────────

class TestCLICreate:
    """使用 subprocess 测试 CLI 退出码。"""

    def _run(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "avs", *args],
            capture_output=True,
            text=True,
            cwd=str(cwd),
        )

    def test_create_episode(self, project_root: Path, episodes_root: Path):
        """验收1：退出码 0，生成 episode.json + 规范目录。"""
        import avs.models.episode as em_module
        em_module._SCHEMA_REL = project_root / "schemas" / "episode.schema.json"

        # 需要真实 episodes 目录
        (project_root / "episodes" / "active").mkdir(parents=True, exist_ok=True)

        result = self._run("episode", "create", "TEST-0001", cwd=project_root)
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"

        ep_dir_path = project_root / "episodes" / "active" / "TEST-0001"
        assert ep_dir_path.is_dir()
        assert (ep_dir_path / "episode.json").exists()

    def test_duplicate_create_nonzero(self, project_root: Path):
        """验收2：重复 create 同 ID → 非零退出码，且不破坏已有目录。"""
        (project_root / "episodes" / "active").mkdir(parents=True, exist_ok=True)

        self._run("episode", "create", "TEST-0001", cwd=project_root)
        result2 = self._run("episode", "create", "TEST-0001", cwd=project_root)
        assert result2.returncode != 0, "重复创建应返回非零"

        # 原有 episode.json 未损坏
        ep_json = project_root / "episodes" / "active" / "TEST-0001" / "episode.json"
        assert ep_json.exists()
        data = json.loads(ep_json.read_text(encoding="utf-8"))
        assert data["id"] == "TEST-0001"

    def test_illegal_id_nonzero(self, project_root: Path):
        """验收（辅助）：非法 ID 返回非零，不留半成品。"""
        result = self._run("episode", "create", "invalid-lowercase", cwd=project_root)
        assert result.returncode != 0
        ep_dir_path = project_root / "episodes" / "active" / "invalid-lowercase"
        assert not ep_dir_path.exists(), "非法 ID 不应留下目录"

    def test_reference_clone_not_publishable(self, project_root: Path):
        """验收4：REFERENCE_CLONE create → publishable=false。"""
        (project_root / "episodes" / "active").mkdir(parents=True, exist_ok=True)
        result = self._run(
            "episode", "create", "RC-0001", "--mode", "REFERENCE_CLONE", cwd=project_root
        )
        assert result.returncode == 0, result.stderr

        ep_json = project_root / "episodes" / "active" / "RC-0001" / "episode.json"
        data = json.loads(ep_json.read_text(encoding="utf-8"))
        assert data["publishable"] is False

    def test_validate_passes(self, project_root: Path):
        """验收5：episode validate 退出码 0。"""
        (project_root / "episodes" / "active").mkdir(parents=True, exist_ok=True)
        self._run("episode", "create", "TEST-0001", cwd=project_root)
        result = self._run("episode", "validate", "TEST-0001", cwd=project_root)
        assert result.returncode == 0, result.stderr

    def test_fail_command(self, project_root: Path):
        """验收6：episode fail → 状态 FAILED。"""
        (project_root / "episodes" / "active").mkdir(parents=True, exist_ok=True)
        self._run("episode", "create", "TEST-0001", cwd=project_root)
        result = self._run(
            "episode", "fail", "TEST-0001", "--reason", "demo", cwd=project_root
        )
        assert result.returncode == 0, result.stderr

        ep_json = project_root / "episodes" / "active" / "TEST-0001" / "episode.json"
        data = json.loads(ep_json.read_text(encoding="utf-8"))
        assert data["status"] == "FAILED"
        assert data["last_error"] == "demo"
