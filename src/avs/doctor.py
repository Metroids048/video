"""Agent Video Studio — 环境诊断模块。

所有检查均确定性执行，不调用大模型。
返回码：0 = 全部必需项通过；1 = 至少一个必需项失败。
"""
from __future__ import annotations

import importlib.util
import os
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


def check_python_environment(project_root: Path) -> CheckResult:
    """检查当前解释器及 AVS 必需模块。"""
    required_modules = ("click", "pydantic", "jsonschema", "yaml", "rich", "PIL")
    missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
    configured = os.environ.get("AGENT_PYTHON")
    executable = Path(sys.executable).resolve()
    if configured and executable != Path(configured).resolve():
        return CheckResult(
            "Python environment",
            required=True,
            passed=False,
            version=str(executable),
            message=f"当前解释器不是 AGENT_PYTHON: {configured}",
        )
    if missing:
        return CheckResult(
            "Python environment",
            required=True,
            passed=False,
            version=str(executable),
            message=f"缺少 Python 模块: {', '.join(missing)}；运行 npm run bootstrap",
        )
    return CheckResult(
        "Python environment",
        required=True,
        passed=True,
        version=str(executable),
    )


def check_git() -> CheckResult:
    code, out = _run(["git", "--version"])
    if code == 127:
        return CheckResult("Git", required=True, passed=False, message="未找到 git，请安装")
    ver_tuple = _parse_semver(out)
    ver_str = ".".join(map(str, ver_tuple)) if ver_tuple else "unknown"
    passed = bool(ver_tuple and ver_tuple >= MIN_GIT)
    msg = "" if passed else f"需要 Git {'.'.join(map(str, MIN_GIT))}+，当前 {ver_str}"
    return CheckResult("Git", required=True, passed=passed, version=ver_str, message=msg)


def check_git_repository(project_root: Path) -> CheckResult:
    code, out = _run([
        "git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree",
    ])
    passed = code == 0 and out.strip().lower() == "true"
    return CheckResult(
        "Git repository",
        required=True,
        passed=passed,
        message="" if passed else "项目目录尚未初始化为 Git 仓库",
    )


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


def _hyperframes_command(project_root: Path) -> list[str]:
    cli = project_root / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    return ["node", str(cli)]


def check_hyperframes(project_root: Path) -> CheckResult:
    """检查项目锁定的 HyperFrames CLI。"""
    command = _hyperframes_command(project_root)
    code, out = _run([*command, "--version"])
    if code == 127 or "not found" in out.lower() or "npm error" in out.lower():
        return CheckResult(
            "HyperFrames", required=True, passed=False,
            message=(
                "未找到项目锁定的 HyperFrames CLI；运行 npm ci"
            ),
        )
    passed = code == 0
    ver = _parse_semver(out)
    ver_str = ".".join(map(str, ver)) if ver else out[:40]
    return CheckResult("HyperFrames", required=True, passed=passed, version=ver_str)


def check_hyperframes_browser(project_root: Path) -> CheckResult:
    """检查 HyperFrames 本地渲染浏览器。"""
    code, out = _run([*_hyperframes_command(project_root), "browser", "path"])
    passed = code == 0 and "not found" not in out.lower() and bool(out.strip())
    return CheckResult(
        "HyperFrames browser",
        required=True,
        passed=passed,
        version=out.strip().splitlines()[-1][:120] if passed else None,
        message="" if passed else "缺少本地渲染浏览器；运行 npm run bootstrap",
    )


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


def check_third_party_video_skills(project_root: Path) -> CheckResult:
    """检查第三方视频 Skills 是否已 vendor 到 third_party_skills/。"""
    required = [
        "hyperframes",
        "remotion-best-practices",
        "video-use",
        "seedance",
        "chatcut",
        "capcut-david",
        "cut-skill",
        "ip-strategist",
        "openmontage",
    ]
    root = project_root / "third_party_skills"
    if not root.is_dir():
        return CheckResult(
            "Third-party video skills",
            required=False,
            passed=False,
            message="third_party_skills/ 不存在；运行 npm run skills:ensure",
        )
    missing: list[str] = []
    for name in required:
        path = root / name
        if name == "chatcut":
            ok = path.is_dir() and any(path.rglob("SKILL.md"))
        elif name == "video-use":
            ok = (path / "SKILL.md").is_file() and (path / "helpers").is_dir()
        else:
            ok = (path / "SKILL.md").is_file() or any(path.rglob("SKILL.md"))
        if not ok:
            missing.append(name)
    if missing:
        return CheckResult(
            "Third-party video skills",
            required=False,
            passed=False,
            message=f"缺失：{', '.join(missing)}；运行 npm run skills:ensure",
        )
    routing = project_root / "docs" / "video-plugin-routing.md"
    if not routing.is_file():
        return CheckResult(
            "Third-party video skills",
            required=False,
            passed=False,
            message="缺少 docs/video-plugin-routing.md",
        )
    return CheckResult(
        "Third-party video skills",
        required=False,
        passed=True,
        version=f"{len(required)} packages",
    )


def check_capcut_david_cli() -> CheckResult:
    """检查 capcut-david CLI（可选）。"""
    binary = shutil.which("capcut-david") or shutil.which("capcut-david.cmd")
    if not binary:
        return CheckResult(
            "capcut-david",
            required=False,
            passed=False,
            message="未安装；运行 npm run skills:ensure 或 npm i -g capcut-cli-david",
        )
    code, out = _run([binary, "--help"])
    return CheckResult(
        "capcut-david",
        required=False,
        passed=code == 0,
        version=binary,
        message="" if code == 0 else out[:200],
    )


def check_skill_sync(project_root: Path) -> CheckResult:
    """检查 skills-src 与 Codex/Claude 项目目标是否逐文件一致。"""
    source_root = project_root / "skills-src"
    targets = (project_root / ".agents" / "skills", project_root / ".claude" / "skills")
    if not source_root.exists():
        return CheckResult("Skill sync", required=True, passed=False, message="skills-src/ 不存在")

    mismatches: list[str] = []
    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        for target_root in targets:
            target = target_root / relative
            if not target.exists() or source.read_bytes() != target.read_bytes():
                mismatches.append(target.relative_to(project_root).as_posix())
    passed = not mismatches
    return CheckResult(
        "Skill sync",
        required=True,
        passed=passed,
        version=f"{len(list(source_root.glob('*/SKILL.md')))} project skills" if passed else None,
        message="" if passed else f"未同步或内容不同: {', '.join(mismatches[:5])}",
    )


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
    report.add(check_python_environment(project_root))
    report.add(check_git())
    report.add(check_git_repository(project_root))
    report.add(check_node())
    report.add(check_ffmpeg())
    report.add(check_ffprobe())
    report.add(check_hyperframes(project_root))
    report.add(check_hyperframes_browser(project_root))
    report.add(check_git_lfs())
    report.add(check_project_dirs(project_root))
    report.add(check_skills(project_root))
    report.add(check_third_party_video_skills(project_root))
    report.add(check_capcut_david_cli())
    report.add(check_skill_sync(project_root))
    report.add(check_disk_space(project_root))
    return report
