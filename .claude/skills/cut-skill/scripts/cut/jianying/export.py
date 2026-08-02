"""cut.jianying.export — 导出渲染。

剪映没有真正的命令行导出 API。本模块提供两种方案：
1. UI 自动化（pyautogui）触发剪映导出对话框
2. 用 ffmpeg 直接根据 draft 信息合成视频（实验性，仅简单拼接）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Optional, Dict, Any

from .draft import Draft


def shutil_which(cmd: str) -> Optional[str]:
    """检查命令是否在 PATH 中可用。"""
    return shutil.which(cmd)


# ---------------------------------------------------------------------------
# 方案 1：UI 自动化导出
# ---------------------------------------------------------------------------

def export_via_ui(draft: Draft,
                  output_dir: str = ".",
                  filename: Optional[str] = None,
                  resolution: str = "1080p",
                  fps: int = 30,
                  format: str = "mp4",
                  timeout: int = 600) -> Dict[str, Any]:
    """通过 pyautogui 自动化点击剪映导出。

    要求：
    - 剪映已打开，且当前项目已加载
    - 屏幕分辨率 ≥ 1280x720
    - pyautogui 已安装

    注意：本方法因剪映版本不同可能失效。导出完成后会检查输出文件是否存在。
    返回 {success, output_path, note}
    """
    try:
        import pyautogui
        import pygetwindow as gw
    except ImportError as e:
        return {
            "success": False,
            "error": f"pyautogui/pygetwindow 未安装: {e}. 请 pip install pyautogui pygetwindow",
        }

    import platform as _p
    _p.system().lower()

    # 激活剪映窗口
    window_title_keywords = ["剪映", "JianYing", "CapCut"]
    win = None
    for kw in window_title_keywords:
        wins = gw.getWindowsWithTitle(kw)
        if wins:
            win = wins[0]
            break
    if not win:
        return {"success": False, "error": "未找到剪映窗口，请确认剪映已打开并加载项目"}

    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.5)

    # 点击导出按钮（右上角，分辨率依赖，1920x1080 下大约在右上 1/6 处）
    screen_w, screen_h = pyautogui.size()
    export_btn_x = int(screen_w * 0.93)
    export_btn_y = int(screen_h * 0.06)
    pyautogui.click(export_btn_x, export_btn_y)
    time.sleep(1.5)

    # 设置输出路径与文件名（这步因版本差异较大，仅做尝试）
    if filename:
        pyautogui.hotkey("tab")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.typewrite(filename, interval=0.02)
        time.sleep(0.3)

    # 点击导出按钮（弹窗内）
    pyautogui.press("enter")
    start_t = time.time()

    # 轮询等待：检查输出文件是否存在且大小稳定
    output_path = os.path.join(output_dir, f"{filename or draft.name}.{format}")
    last_size = -1
    stable_count = 0
    while time.time() - start_t < timeout:
        time.sleep(5)
        if os.path.exists(output_path):
            cur_size = os.path.getsize(output_path)
            if cur_size > 0 and cur_size == last_size:
                stable_count += 1
                if stable_count >= 2:  # 连续两次大小一致，认为导出完成
                    return {
                        "success": True,
                        "output_path": output_path,
                        "elapsed_s": time.time() - start_t,
                        "size_bytes": cur_size,
                    }
            else:
                stable_count = 0
            last_size = cur_size

    # 超时
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return {
            "success": True,
            "output_path": output_path,
            "elapsed_s": time.time() - start_t,
            "note": "导出可能仍在进行，文件已存在但未确认完成",
        }
    return {
        "success": False,
        "error": f"超时 {timeout}s 未检测到输出文件",
        "output_path": output_path,
    }


# ---------------------------------------------------------------------------
# 方案 2：ffmpeg 直接合成（实验性）
# ---------------------------------------------------------------------------

def export_via_ffmpeg(draft: Draft,
                      output_path: str,
                      resolution: Optional[tuple] = None,
                      fps: int = 30) -> Dict[str, Any]:
    """用 ffmpeg 根据 draft 直接合成视频。

    仅支持简单场景：单视频轨、视频片段按顺序拼接。
    转场/特效/字幕**不支持**，复杂项目请用 UI 导出。
    """
    if not shutil_which("ffmpeg"):
        return {"success": False, "error": "ffmpeg 未安装"}

    vts = draft.video_tracks
    if not vts or not vts[0].segments:
        return {"success": False, "error": "没有视频片段可导出"}

    track = vts[0]
    # 用 list 形式构造命令，避免 shell 注入
    cmd = ["ffmpeg", "-y"]
    n_inputs = 0
    for seg in track.segments:
        mat = draft.find_material(seg.material_id)
        if not mat or not mat.get("path"):
            continue
        path = mat["path"]
        ss = seg.source_start_us / 1_000_000
        dur = seg.source_duration_us / 1_000_000
        cmd += ["-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", str(path)]
        n_inputs += 1

    if n_inputs == 0:
        return {"success": False, "error": "没有有效的视频素材路径"}

    # 用 concat filter
    filter_str = "".join(f"[{i}:v]" for i in range(n_inputs)) + f"concat=n={n_inputs}:v=1:a=0[v]"

    canvas = draft.canvas
    w, h = resolution or (canvas["width"], canvas["height"])

    cmd += [
        "-filter_complex", f"{filter_str};[v]scale={w}:{h}[v2]",
        "-map", "[v2]",
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            return {"success": False, "error": result.stderr[-2000:], "cmd": cmd}
        return {"success": True, "output_path": output_path, "cmd": cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "ffmpeg 超时（>30min）"}


# ---------------------------------------------------------------------------
# 通用入口
# ---------------------------------------------------------------------------

def export(draft: Draft, output_path: str,
           method: str = "ui",
           **kwargs) -> Dict[str, Any]:
    """统一导出入口。

    method: "ui"（剪映 UI 自动化）或 "ffmpeg"（直接合成）
    """
    if method == "ui":
        return export_via_ui(draft, output_dir=os.path.dirname(output_path) or ".",
                             filename=os.path.splitext(os.path.basename(output_path))[0],
                             **kwargs)
    elif method == "ffmpeg":
        return export_via_ffmpeg(draft, output_path, **kwargs)
    else:
        raise ValueError(f"未知导出方法: {method}")
