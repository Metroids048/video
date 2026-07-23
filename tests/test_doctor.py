"""tests/test_doctor.py — doctor 模块单元测试。

测试策略：
- 版本解析逻辑：纯函数，无 mock
- 外部命令检查：mock subprocess，测试各种失败场景
- Windows 路径：测试相对/绝对路径下的 venv 检测
- 不测试真实系统状态（避免环境依赖）
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 将 src/ 加入路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from avs.doctor import (
    CheckResult,
    DoctorReport,
    _parse_semver,
    _version_ok,
    check_disk_space,
    check_ffmpeg,
    check_ffprobe,
    check_git,
    check_git_lfs,
    check_node,
    check_project_dirs,
    check_python,
    check_skills,
    check_venv,
    run_doctor,
)


# ── _parse_semver ──────────────────────────────────────────────────────
class TestParseSemver:
    def test_standard_version(self):
        assert _parse_semver("1.2.3") == (1, 2, 3)

    def test_git_output(self):
        assert _parse_semver("git version 2.41.0") == (2, 41, 0)

    def test_node_output(self):
        assert _parse_semver("v22.0.0") == (22, 0, 0)

    def test_ffmpeg_output(self):
        result = _parse_semver("ffmpeg version 6.1.1 Copyright")
        assert result == (6, 1, 1)

    def test_no_version_returns_none(self):
        assert _parse_semver("command not found") is None

    def test_two_part_version(self):
        # 只有 major.minor（无 patch）
        result = _parse_semver("2.41")
        assert result == (2, 41, 0)


# ── _version_ok ────────────────────────────────────────────────────────
class TestVersionOk:
    def test_meets_minimum(self):
        assert _version_ok("22.1.0", (22, 0, 0)) is True

    def test_exactly_minimum(self):
        assert _version_ok("22.0.0", (22, 0, 0)) is True

    def test_below_minimum(self):
        assert _version_ok("20.0.0", (22, 0, 0)) is False

    def test_unparseable_version(self):
        assert _version_ok("unknown", (22, 0, 0)) is False


# ── check_python ───────────────────────────────────────────────────────
class TestCheckPython:
    def test_current_python_passes(self):
        # 当前运行测试的 Python 版本应满足 3.11+
        result = check_python()
        assert result.required is True
        assert result.version is not None
        # 在 CI 中如果 Python < 3.11，测试本身就无法运行

    def test_result_has_version(self):
        result = check_python()
        assert "." in (result.version or "")


# ── check_git ──────────────────────────────────────────────────────────
class TestCheckGit:
    def test_git_not_found(self):
        with patch("avs.doctor._run", return_value=(127, "command not found: git")):
            result = check_git()
        assert result.passed is False
        assert result.required is True
        assert "git" in result.message.lower()

    def test_git_old_version(self):
        with patch("avs.doctor._run", return_value=(0, "git version 2.30.0")):
            result = check_git()
        assert result.passed is False

    def test_git_meets_minimum(self):
        with patch("avs.doctor._run", return_value=(0, "git version 2.45.0")):
            result = check_git()
        assert result.passed is True
        assert result.version == "2.45.0"


# ── check_node ─────────────────────────────────────────────────────────
class TestCheckNode:
    def test_node_not_found(self):
        with patch("avs.doctor._run", return_value=(127, "command not found: node")):
            result = check_node()
        assert result.passed is False
        assert result.required is True

    def test_node_old_version(self):
        with patch("avs.doctor._run", return_value=(0, "v18.0.0")):
            result = check_node()
        assert result.passed is False

    def test_node_22_passes(self):
        with patch("avs.doctor._run", return_value=(0, "v22.1.0")):
            result = check_node()
        assert result.passed is True
        assert result.version == "22.1.0"


# ── check_ffmpeg ───────────────────────────────────────────────────────
class TestCheckFfmpeg:
    def test_ffmpeg_not_found(self):
        with patch("avs.doctor._run", return_value=(127, "command not found: ffmpeg")):
            result = check_ffmpeg()
        assert result.passed is False
        assert result.required is True
        assert "ffmpeg.org" in result.message

    def test_ffmpeg_old_version(self):
        with patch("avs.doctor._run", return_value=(0, "ffmpeg version 5.1.0")):
            result = check_ffmpeg()
        assert result.passed is False

    def test_ffmpeg_6_passes(self):
        with patch("avs.doctor._run", return_value=(0, "ffmpeg version 6.1.0")):
            result = check_ffmpeg()
        assert result.passed is True


# ── check_ffprobe ──────────────────────────────────────────────────────
class TestCheckFfprobe:
    def test_ffprobe_not_found(self):
        with patch("avs.doctor._run", return_value=(127, "command not found: ffprobe")):
            result = check_ffprobe()
        assert result.passed is False

    def test_ffprobe_found(self):
        with patch("avs.doctor._run", return_value=(0, "ffprobe version 6.1.0")):
            result = check_ffprobe()
        assert result.passed is True


# ── check_git_lfs ──────────────────────────────────────────────────────
class TestCheckGitLfs:
    def test_lfs_not_installed(self):
        with patch("avs.doctor._run", return_value=(1, "git: 'lfs' is not a git command")):
            result = check_git_lfs()
        assert result.required is False  # 可选项
        assert result.passed is False

    def test_lfs_installed(self):
        with patch("avs.doctor._run", return_value=(0, "git-lfs/3.4.0")):
            result = check_git_lfs()
        assert result.passed is True


# ── check_venv ─────────────────────────────────────────────────────────
class TestCheckVenv:
    def test_no_venv(self, tmp_path):
        result = check_venv(tmp_path)
        assert result.required is False
        assert result.passed is False
        assert "bootstrap" in result.message.lower()

    def test_venv_exists_unix(self, tmp_path):
        (tmp_path / ".venv" / "bin").mkdir(parents=True)
        (tmp_path / ".venv" / "bin" / "python").touch()
        result = check_venv(tmp_path)
        assert result.passed is True

    def test_venv_exists_windows(self, tmp_path):
        (tmp_path / ".venv" / "Scripts").mkdir(parents=True)
        (tmp_path / ".venv" / "Scripts" / "python.exe").touch()
        result = check_venv(tmp_path)
        assert result.passed is True


# ── check_project_dirs ─────────────────────────────────────────────────
class TestCheckProjectDirs:
    def test_missing_dirs(self, tmp_path):
        result = check_project_dirs(tmp_path)
        assert result.passed is False
        assert "config" in result.message

    def test_all_dirs_present(self, tmp_path):
        for d in ["config", "schemas", "src/avs", "skills-src",
                  "episodes/inbox", "episodes/active"]:
            (tmp_path / d).mkdir(parents=True)
        result = check_project_dirs(tmp_path)
        assert result.passed is True


# ── check_skills ───────────────────────────────────────────────────────
class TestCheckSkills:
    def test_no_skills_dir(self, tmp_path):
        result = check_skills(tmp_path)
        assert result.passed is False

    def test_skill_missing_skill_md(self, tmp_path):
        skills_dir = tmp_path / "skills-src"
        (skills_dir / "create-episode").mkdir(parents=True)
        result = check_skills(tmp_path)
        assert result.passed is False
        assert "create-episode" in result.message

    def test_all_skills_have_skill_md(self, tmp_path):
        skills_dir = tmp_path / "skills-src"
        for name in ["create-episode", "write-video-script"]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("# skill")
        result = check_skills(tmp_path)
        assert result.passed is True


# ── DoctorReport ───────────────────────────────────────────────────────
class TestDoctorReport:
    def test_all_required_passed(self):
        report = DoctorReport()
        report.add(CheckResult("A", required=True, passed=True))
        report.add(CheckResult("B", required=True, passed=True))
        assert report.all_required_passed is True

    def test_required_fail_blocks(self):
        report = DoctorReport()
        report.add(CheckResult("A", required=True, passed=True))
        report.add(CheckResult("B", required=True, passed=False))
        assert report.all_required_passed is False

    def test_optional_fail_does_not_block(self):
        report = DoctorReport()
        report.add(CheckResult("A", required=True, passed=True))
        report.add(CheckResult("B", required=False, passed=False))
        assert report.all_required_passed is True

    def test_status_label(self):
        assert CheckResult("X", required=True, passed=True).status_label == "OK"
        assert CheckResult("X", required=True, passed=False).status_label == "FAIL"
        assert CheckResult("X", required=False, passed=False).status_label == "WARN"


# ── run_doctor integration ─────────────────────────────────────────────
class TestRunDoctor:
    def test_returns_report(self, tmp_path):
        """run_doctor 返回 DoctorReport 且包含所有检查项。"""
        with patch("avs.doctor._run", return_value=(127, "not found")):
            with patch("avs.doctor.check_python",
                       return_value=CheckResult("Python", True, True, "3.11.0")):
                report = run_doctor(tmp_path)
        assert isinstance(report, DoctorReport)
        assert len(report.results) > 0

    def test_missing_ffmpeg_fails_required(self, tmp_path):
        """FFmpeg 缺失时，all_required_passed 应为 False。"""
        with patch("avs.doctor._run") as mock_run:
            def side_effect(cmd):
                if "ffmpeg" in cmd:
                    return (127, "not found")
                if "ffprobe" in cmd:
                    return (127, "not found")
                if "hyperframes" in cmd:
                    return (127, "not found")
                return (0, "ok 99.0.0")
            mock_run.side_effect = side_effect
            report = run_doctor(tmp_path)
        assert report.all_required_passed is False
