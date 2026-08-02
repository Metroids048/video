"""cut.platform — 跨平台路径与版本检测。

提供 detect() 函数，返回 PlatformInfo，描述当前操作系统的剪映/Premiere
安装情况、draft 文件目录、可用的后端。所有上层模块通过本模块获取路径，
绝不硬编码。
"""
from __future__ import annotations

import json
import os
import platform as _platform
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class BackendInfo:
    name: str                      # "jianying" | "premiere"
    installed: bool
    version: Optional[str] = None
    running: Optional[bool] = None
    install_path: Optional[str] = None
    drafts_dir: Optional[str] = None   # 剪映 draft 根目录
    schema_version: Optional[str] = None  # 剪映 draft schema 版本

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlatformInfo:
    os: str                        # "windows" | "darwin" | "linux"
    os_version: str
    python_version: str
    arch: str
    jianying: BackendInfo
    capcut: BackendInfo            # 国际版单独检测
    premiere: BackendInfo

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.os,
            "os_version": self.os_version,
            "python_version": self.python_version,
            "arch": self.arch,
            "jianying": self.jianying.to_dict(),
            "capcut": self.capcut.to_dict(),
            "premiere": self.premiere.to_dict(),
        }

    @property
    def primary_video_backend(self) -> str:
        """优先返回剪映（国内默认），否则 CapCut，最后 Premiere。"""
        if self.jianying.installed:
            return "jianying"
        if self.capcut.installed:
            return "capcut"
        if self.premiere.installed:
            return "premiere"
        return "none"


# ---------------------------------------------------------------------------
# 平台检测
# ---------------------------------------------------------------------------

def _os_name() -> str:
    s = _platform.system().lower()
    if s == "windows":
        return "windows"
    if s == "darwin":
        return "darwin"
    return "linux"


def _drafts_dir_candidates(app_name: str) -> List[Path]:
    """返回可能的 draft 根目录候选。app_name ∈ {"JianyingPro", "CapCut"}。"""
    os_name = _os_name()
    candidates: List[Path] = []
    if os_name == "windows":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(Path(local) / app_name / "User Data" / "Projects" / "com.lveditor.draft")
        # 某些版本会落到 AppData\LocalLow
        candidates.append(Path(os.path.expanduser("~")) / "AppData" / "LocalLow" / app_name / "User Data" / "Projects" / "com.lveditor.draft")
    elif os_name == "darwin":
        candidates.append(Path.home() / "Movies" / app_name / "User Data" / "Projects" / "com.lveditor.draft")
        candidates.append(Path.home() / "Library" / "Application Support" / app_name / "User Data" / "Projects" / "com.lveditor.draft")
    return candidates


def _detect_jianying_family(app_name: str) -> BackendInfo:
    """检测 剪映专业版 / CapCut 国际版。两者 draft 结构相同。"""
    candidates = _drafts_dir_candidates(app_name)
    drafts_dir: Optional[Path] = None
    for c in candidates:
        if c.exists() and c.is_dir():
            drafts_dir = c
            break

    # 推断版本：从最新修改的 draft 目录里读 draft_meta_info.json 或 draft_content.json
    version: Optional[str] = None
    schema_version: Optional[str] = None
    install_path: Optional[str] = None

    if drafts_dir:
        # 找最近修改的 draft 子目录
        try:
            subdirs = [p for p in drafts_dir.iterdir() if p.is_dir()]
            subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            for d in subdirs:
                dc = d / "draft_content.json"
                if dc.exists():
                    try:
                        with open(dc, "r", encoding="utf-8") as f:
                            content = json.load(f)
                        version = content.get("version")
                        schema_version = content.get("draft_version") or content.get("schema_version")
                        if version:
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    # 推断安装路径
    os_name = _os_name()
    if os_name == "windows":
        for base in (Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")),
                     Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))):
            for sub in (app_name, app_name + "Pro"):
                exe = base / sub / f"{app_name}.exe"
                if exe.exists():
                    install_path = str(exe.parent)
                    break
    elif os_name == "darwin":
        for n in ("/Applications", str(Path.home() / "Applications")):
            for label in (app_name, app_name + ".app", "剪映专业版.app", "CapCut.app"):
                p = Path(n) / label
                if p.exists():
                    install_path = str(p)
                    break

    installed = drafts_dir is not None or install_path is not None
    return BackendInfo(
        name=app_name.lower(),
        installed=installed,
        version=version,
        running=None,  # 不主动检测进程，避免依赖 psutil
        install_path=install_path,
        drafts_dir=str(drafts_dir) if drafts_dir else None,
        schema_version=schema_version,
    )


def _detect_premiere() -> BackendInfo:
    """检测 Adobe Premiere Pro。"""
    os_name = _os_name()
    install_path: Optional[str] = None
    version: Optional[str] = None

    if os_name == "windows":
        # Adobe 默认装在 C:\Program Files\Adobe\Adobe Premiere Pro YYYY
        adobe_base = Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Adobe"
        if adobe_base.exists():
            for d in sorted(adobe_base.iterdir()):
                low = d.name.lower()
                if "premiere" in low and "pro" in low:
                    exe = d / "Adobe Premiere Pro.exe"
                    if exe.exists():
                        install_path = str(d)
                        # 从目录名提取版本号
                        parts = d.name.split()
                        for p in parts:
                            if p[:4].isdigit():
                                version = p
                                break
                    break
    elif os_name == "darwin":
        for n in ("/Applications", str(Path.home() / "Applications")):
            p = Path(n) / "Adobe Premiere Pro 2024"
            if not p.exists():
                # 通配查找
                for d in Path(n).iterdir():
                    if d.name.lower().startswith("adobe premiere pro"):
                        p = d
                        break
            if p.exists():
                install_path = str(p)
                parts = p.name.split()
                for part in parts:
                    if part[:4].isdigit():
                        version = part
                        break
                break

    installed = install_path is not None
    running = None
    if installed:
        running = _is_premiere_running(os_name)

    return BackendInfo(
        name="premiere",
        installed=installed,
        version=version,
        running=running,
        install_path=install_path,
        drafts_dir=None,
        schema_version=None,
    )


def _is_premiere_running(os_name: str) -> bool:
    """轻量检测 Premiere 是否在运行，不依赖 psutil。"""
    try:
        if os_name == "windows":
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Adobe Premiere Pro.exe"],
                capture_output=True, text=True, timeout=5,
            )
            return "Adobe Premiere Pro.exe" in out.stdout
        elif os_name == "darwin":
            out = subprocess.run(
                ["pgrep", "-i", "premiere"],
                capture_output=True, text=True, timeout=5,
            )
            return out.returncode == 0 and bool(out.stdout.strip())
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def detect() -> PlatformInfo:
    """检测本机环境，返回 PlatformInfo。"""
    os_name = _os_name()
    return PlatformInfo(
        os=os_name,
        os_version=_platform.version(),
        python_version=sys.version.split()[0],
        arch=_platform.machine(),
        jianying=_detect_jianying_family("JianyingPro"),
        capcut=_detect_jianying_family("CapCut"),
        premiere=_detect_premiere(),
    )


def get_drafts_dir(app: str = "jianying") -> Path:
    """获取 draft 根目录。app ∈ {"jianying", "capcut"}。找不到抛 FileNotFoundError。"""
    app_name = "JianyingPro" if app == "jianying" else "CapCut"
    info = _detect_jianying_family(app_name)
    if not info.drafts_dir:
        raise FileNotFoundError(
            f"未找到 {app_name} 的 draft 目录。请确认 {app_name} 已安装且至少创建过一个项目。"
            "如果安装在其他位置，请手动指定环境变量 CUT_DRAFTS_DIR。"
        )
    return Path(info.drafts_dir)


def list_drafts(app: str = "jianying") -> List[Dict[str, Any]]:
    """列出所有剪映 draft 项目。"""
    drafts_dir = os.environ.get("CUT_DRAFTS_DIR")
    if drafts_dir:
        root = Path(drafts_dir)
    else:
        root = get_drafts_dir(app)

    projects = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        dc = d / "draft_content.json"
        if not dc.exists():
            continue
        try:
            with open(dc, "r", encoding="utf-8") as f:
                content = json.load(f)
            duration = content.get("duration", 0)
            projects.append({
                "name": d.name,
                "path": str(d),
                "duration_us": duration,
                "duration_hms": _us_to_hms(duration),
                "modified_at": d.stat().st_mtime,
                "version": content.get("version"),
            })
        except Exception as e:
            projects.append({"name": d.name, "path": str(d), "error": str(e)})
    projects.sort(key=lambda p: p.get("modified_at", 0), reverse=True)
    return projects


def find_draft(name: str, app: str = "jianying") -> Path:
    """按名称查找 draft 项目目录。"""
    if os.environ.get("CUT_DRAFTS_DIR"):
        root = Path(os.environ["CUT_DRAFTS_DIR"])
    else:
        root = get_drafts_dir(app)
    p = root / name
    if p.exists() and (p / "draft_content.json").exists():
        return p
    # 模糊匹配
    for d in root.iterdir():
        if d.is_dir() and name.lower() in d.name.lower():
            if (d / "draft_content.json").exists():
                return d
    raise FileNotFoundError(f"未找到名为 {name} 的剪映项目")


def _us_to_hms(us: int) -> str:
    """微秒转 HH:MM:SS.mmm。"""
    if not us:
        return "00:00:00.000"
    total_ms = us // 1000
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="cut.platform — 环境检测")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--list-drafts", action="store_true", help="列出剪映项目")
    args = parser.parse_args()

    if args.list_drafts:
        for p in list_drafts():
            print(f"{p['name']:30s}  {p.get('duration_hms', '?')}  {p.get('version', '?')}")
    else:
        info = detect()
        if args.json:
            print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"OS:         {info.os} {info.os_version}")
            print(f"Python:     {info.python_version}")
            print(f"Arch:       {info.arch}")
            print(f"剪映:        {'✓' if info.jianying.installed else '✗'} v{info.jianying.version or '?'}")
            if info.jianying.drafts_dir:
                print(f"  drafts:   {info.jianying.drafts_dir}")
            print(f"CapCut:     {'✓' if info.capcut.installed else '✗'} v{info.capcut.version or '?'}")
            print(f"Premiere:   {'✓' if info.premiere.installed else '✗'} v{info.premiere.version or '?'}"
                  + (" (running)" if info.premiere.running else ""))
