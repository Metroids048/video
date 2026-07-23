"""Agent Video Studio — 环境诊断模块。

所有检查均确定性执行，不调用大模型。
返回码：0 = 全部必需项通过；1 = 至少一个必需项失败。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── 版本要求（与 tools-manifest.yaml 保持同步）──────────────────────
MIN_PYTHON = (3, 11)
MIN_NODE   = (22, 0)
MIN_FFMPEG = (6, 0)
MIN_GIT    = (2, 40)


# ── 数据结构 ──────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    name: str
    required: bool
    passed: bool
    version: Optional[str] = None
    message: str = ""

    @property
    def status_label(self) -> str:
        if self.passed:
            return "OK"
        return "FAIL" if self.required else "WARN"


@dataclass
class DoctorReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def all_required_passed(self) -> bool:
        return all(r.passed for r in self.results if r.required)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)


# ── 版本解析工具 ──────────────────────────────────────────────────────
def _run(cmd: list[str]) -> tuple[int, str]:
    """运行命令，返回 (exit_code, stdout+stderr)。"""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout: {cmd[0]}"


def _parse_semver(text: str) -> Optional[tuple[int, ...]]:
    """从字符串中提取第一个 x.y.z 版本号。"""
    import re
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not m:
        return None
    parts = [int(x) for x in m.groups() if x is not None]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _version_ok(text: str, min_ver: tuple[int, ...]) -> bool:
    parsed = _parse_semver(text)
    if parsed is None:
        return False
    return parsed >= min_ver


# ── 各项检查 ──────────────────────────────────────────────────────────
def check_python() -> CheckResult:
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    passed = sys.version_info >= MIN_PYTHON
    msg = "" if passed else f"需要 Python {'.'.join(map(str, MIN_PYTHON))}+，当前 {ver}"
    return CheckResult("Python", required=True, passed=passed, version=ver, message=msg)


def check_git() -> CheckResult:
    code, out = _run(["git", "--version"])
    if code == 127:
        return CheckResult("Git", required=True, passed=False, message="未找到 git，请安装")
    ver_tuple = _parse_semver(out)
    ver_str = ".".join(map(str, ver_tuple)) if ver_tuple else "unknown"
    passed = bool(ver_tuple and ver_tuple >= MIN_GIT)
    msg = "" if passed else f"需要 Git {'.'.join(map(str, MIN_GIT))}+，当前 {ver_str}"
    return CheckResult("Git", required=True, passed=passed, version=ver_str, message=msg)


def check_node() -> CheckResult:
    code, out = _run(["node", "--version"])
    if code == 127:
        return CheckResult("Node.js", required=True, passed=False, message="未找到 node，请安装 22+")
    ver_str = out.lstrip("v").strip()
    passed = _version_ok(ver_str, MIN_NODE)
    msg = "" if passed else f"需要 Node.js 22+，当前 {ver_str}"
    return CheckResult("Node.js", required=True, passed=passed, version=ver_str, message=msg)


def check_ffmpeg() -> CheckResult:
    code, out = _run(["ffmpeg", "-version"])
    if code == 127:
        return CheckResult(
            "FFmpeg", required=True, passed=False,
            message="未找到 ffmpeg。安装：https://ffmpeg.org/download.html"
        )
    ver_tuple = _parse_semver(out)
    ver_str = ".".join(map(str, ver_tuple)) if ver_tuple else "unknown"
    passed = bool(ver_tuple and ver_tuple >= MIN_FFMPEG)
    msg = "" if passed else f"需要 FFmpeg 6.0+，当前 {ver_str}"
    return CheckResult("FFmpeg", required=True, passed=passed, version=ver_str, message=msg)


def check_ffprobe() -> CheckResult:
    code, out = _run(["ffprobe", "-version"])
    if code == 127:
        return CheckResult(
            "FFprobe", required=True, passed=False,
            message="未找到 ffprobe（通常随 ffmpeg 一起安装）"
        )
    ver_tuple = _parse_semver(out)
    ver_str = ".".join(map(str, ver_tuple)) if ver_tuple else "unknown"
    passed = bool(ver_tuple and ver_tuple >= MIN_FFMPEG)
    return CheckResult("FFprobe", required=True, passed=passed, version=ver_str)


def check_hyperframes() -> CheckResult:
    """检查 HyperFrames CLI（通过 npx）。"""
    code, out = _run(["npx", "hyperframes", "--version"])
    if code == 127 or "not found" in out.lower() or "npm error" in out.lower():
        return CheckResult(
            "HyperFrames", required=True, passed=False,
            message=(
                "未找到 HyperFrames CLI。\n"
                "安装命令：npx skills add heygen-com/hyperframes "
                "-a claude-code -a codex -a cursor --copy -y"
            ),
        )
    passed = code == 0
    ver = _parse_semver(out)
    ver_str = ".".join(map(str, ver)) if ver else out[:40]
    return CheckResult("HyperFrames", required=True, passed=passed, version=ver_str)


def check_git_lfs() -> CheckResult:
    """Git LFS 是可选项，缺失只报 WARN。"""
    code, out = _run(["git", "lfs", "version"])
    if code != 0 or "git-lfs" not in out.lower():
        return CheckResult(
            "Git LFS", required=False, passed=False,
            message="未安装（可选）。仅在需要提交大型 Fixture 时安装"
        )
    ver_tuple = _parse_semver(out)
    ver_str = ".".join(map(str, ver_tuple)) if ver_tuple else "unknown"
    return CheckResult("Git LFS", required=False, passed=True, version=ver_str)


def check_venv(project_root: Path) -> CheckResult:
    """检查 Python 虚拟环境是否存在。"""
    venv = project_root / ".venv"
    exists = venv.exists() and (venv / "Scripts" / "python.exe").exists() or \
             venv.exists() and (venv / "bin" / "python").exists()
    if not exists:
        return CheckResult(
            "Python venv", required=False, passed=False,
            message="虚拟环境未创建。运行 npm run bootstrap 初始化"
        )
    return CheckResult("Python venv", required=False, passed=True, version=str(venv))


def check_project_dirs(project_root: Path) -> CheckResult:
    """检查关键项目目录是否存在。"""
    required_dirs = [
        "config", "schemas", "src/avs", "skills-src",
        "episodes/inbox", "episodes/active",
    ]
    missing = [d for d in required_dirs if not (project_root / d).exists()]
    if missing:
        return CheckResult(
            "Project dirs", required=True, passed=False,
            message=f"缺少目录：{', '.join(missing)}"
        )
    return CheckResult("Project dirs", required=True, passed=True)


def check_skills(project_root: Path) -> CheckResult:
    """检查 skills-src 中的所有 Skill 目录是否有 SKILL.md。"""
    skills_dir = project_root / "skills-src"
    if not skills_dir.exists():
        return CheckResult("Skills", required=False, passed=False, message="skills-src/ 不存在")
    dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    missing = [d.name for d in dirs if not (d / "SKILL.md").exists()]
    if missing:
        return CheckResult(
            "Skills", required=False, passed=False,
            message=f"以下 Skill 缺少 SKILL.md：{', '.join(missing)}"
        )
    return CheckResult("Skills", required=False, passed=True, version=f"{len(dirs)} skills")


def check_disk_space(project_root: Path) -> CheckResult:
    """检查可用磁盘空间（至少 5 GB）。"""
    MIN_GB = 5
    try:
        usage = shutil.disk_usage(project_root)
        free_gb = usage.free / (1024 ** 3)
        passed = free_gb >= MIN_GB
        msg = "" if passed else f"可用空间 {free_gb:.1f} GB，建议至少 {MIN_GB} GB"
        return CheckResult(
            "Disk space", required=False, passed=passed,
            version=f"{free_gb:.1f} GB free", message=msg
        )
    except Exception as e:
        return CheckResult("Disk space", required=False, passed=False, message=str(e))


# ── 主入口 ────────────────────────────────────────────────────────────
def run_doctor(project_root: Path) -> DoctorReport:
    """运行所有检查，返回报告。"""
    report = DoctorReport()
    report.add(check_python())
    report.add(check_git())
    report.add(check_node())
    report.add(check_ffmpeg())
    report.add(check_ffprobe())
    report.add(check_hyperframes())
    report.add(check_git_lfs())
    report.add(check_venv(project_root))
    report.add(check_project_dirs(project_root))
    report.add(check_skills(project_root))
    report.add(check_disk_space(project_root))
    return report
