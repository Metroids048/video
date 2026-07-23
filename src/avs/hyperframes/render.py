"""src/avs/hyperframes/render.py — HyperFrames CLI 调用封装 + 降级。"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def hyperframes_available() -> bool:
    """检查 npx hyperframes 是否可用。"""
    return shutil.which("npx") is not None


def try_render_hyperframes(
    component_path: Path,
    output_path: Path,
    props: dict[str, Any] | None = None,
    timeout: int = 120,
) -> bool:
    """尝试用 HyperFrames 渲染组件，返回 True=成功，False=失败需降级。

    失败时记录 warning 日志，调用方应降级到 FFmpeg 静态卡片。
    """
    if not hyperframes_available():
        logger.warning("npx 不可用，HyperFrames 跳过")
        return False

    # 构建 doctor 检查
    try:
        result = subprocess.run(
            ["npx", "hyperframes", "doctor"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("hyperframes doctor 失败: %s", result.stderr[:200])
            # 不阻断，继续尝试 render
    except Exception as exc:
        logger.warning("hyperframes doctor 异常: %s", exc)

    # 构建 render 命令
    cmd = ["npx", "hyperframes", "render", str(component_path), "--output", str(output_path)]
    if props:
        # 通过环境变量或临时 JSON 传参（简化版：忽略 props）
        pass

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning("hyperframes render 超时 (%ds)", timeout)
        return False
    except Exception as exc:
        logger.warning("hyperframes render 异常: %s", exc)
        return False

    if result.returncode != 0:
        logger.warning("hyperframes render 失败 (exit %d): %s",
                       result.returncode, result.stderr[:300])
        return False

    # 检查输出文件
    if not output_path.exists() or output_path.stat().st_size == 0:
        logger.warning("hyperframes 输出文件缺失或为空: %s", output_path)
        return False

    logger.info("hyperframes 渲染成功: %s", output_path)
    return True


def render_static_fallback(
    ep_dir: Path,
    component_type: str,
    props: dict[str, Any],
    output_path: Path,
) -> None:
    """降级：FFmpeg 静态卡片（黑底白字）。"""
    text = props.get("title") or props.get("heading") or props.get("message") or "静态卡片"
    duration = props.get("duration", 3.0)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r=30:d={duration}",
        "-vf", f"drawtext=text='{_escape_text(text)}':fontcolor=white:fontsize=48"
               f":x=(w-text_w)/2:y=(h-text_h)/2",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
        logger.info("FFmpeg 静态卡片降级成功: %s", output_path)
    except Exception as exc:
        logger.error("FFmpeg 降级失败: %s", exc)
        raise


def _escape_text(text: str) -> str:
    return text.replace("'", "\\'").replace(":", "\\:")
