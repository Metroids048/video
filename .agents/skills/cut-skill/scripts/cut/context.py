"""cut.context — 统一上下文感知接口。

不论后端是剪映还是 Premiere，都提供同一组只读接口让 agent 读取项目状态：
- get_project_state(): 项目概要
- list_materials(): 素材池
- get_timeline(): 时间轴结构
- get_selection(): 当前选中（仅 Premiere 支持）
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional

from . import platform as P


def get_project_state(backend: str = "jianying",
                      project_name: Optional[str] = None,
                      project_dir: Optional[str] = None) -> Dict[str, Any]:
    """读取项目状态。

    backend: "jianying" / "capcut" / "premiere"
    """
    if backend in ("jianying", "capcut"):
        from .jianying.state import get_state
        return get_state(project_name=project_name, project_dir=project_dir, app=backend)
    elif backend == "premiere":
        from .premiere.state import get_state
        return get_state()
    else:
        raise ValueError(f"未知 backend: {backend}")


def list_materials(backend: str = "jianying",
                   project_name: Optional[str] = None,
                   project_dir: Optional[str] = None,
                   mtype: Optional[str] = None) -> List[Dict[str, Any]]:
    if backend in ("jianying", "capcut"):
        from .jianying.state import list_materials as _lm
        return _lm(project_name=project_name, project_dir=project_dir, mtype=mtype, app=backend)
    elif backend == "premiere":
        from .premiere.state import list_materials as _lm
        return _lm()
    else:
        raise ValueError(f"未知 backend: {backend}")


def get_timeline(backend: str = "jianying",
                 project_name: Optional[str] = None,
                 project_dir: Optional[str] = None) -> Dict[str, Any]:
    if backend in ("jianying", "capcut"):
        from .jianying.state import get_timeline as _gt
        return _gt(project_name=project_name, project_dir=project_dir, app=backend)
    elif backend == "premiere":
        from .premiere.state import get_timeline as _gt
        return _gt()
    else:
        raise ValueError(f"未知 backend: {backend}")


def get_selection(backend: str = "premiere") -> Dict[str, Any]:
    """读取当前选中片段。仅 Premiere 支持实时选中状态。"""
    if backend == "premiere":
        from .premiere.state import get_selection
        return get_selection()
    elif backend in ("jianying", "capcut"):
        return {"error": "剪映 draft 文件不记录选中状态，无法读取。请在剪映 UI 中查看。"}
    else:
        raise ValueError(f"未知 backend: {backend}")


def detect_environment() -> Dict[str, Any]:
    """检测本机环境与可用后端。"""
    info = P.detect()
    return info.to_dict()
