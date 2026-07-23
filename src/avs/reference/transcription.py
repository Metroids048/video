"""src/avs/reference/transcription.py — 转写 Provider 接口。

Provider 选择：auto | manual | disabled。
缺失 Provider 时不崩溃，返回 None transcript。
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_TRANSCRIPT_FILENAME = "transcript.json"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class TranscriptResult:
    """转写结果容器。"""
    def __init__(
        self,
        text: str,
        segments: list[dict] | None = None,
        provider: str = "unknown",
        language: str | None = None,
    ) -> None:
        self.text = text
        self.segments = segments or []
        self.provider = provider
        self.language = language

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "segments": self.segments,
            "provider": self.provider,
            "language": self.language,
            "generated_at": _now_iso(),
        }


def _try_whisper_cpp(audio_path: Path) -> TranscriptResult | None:
    """尝试用 whisper-cpp 转写；不可用时返回 None。"""
    if not shutil.which("whisper-cpp") and not shutil.which("whisper"):
        return None
    bin_name = "whisper-cpp" if shutil.which("whisper-cpp") else "whisper"
    cmd = [bin_name, str(audio_path), "--output-json", "--output-file", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            text = data.get("transcription", [{}])[0].get("text", "")
            return TranscriptResult(text=text, provider="whisper_cpp")
    except Exception as exc:
        log.debug("whisper-cpp 失败: %s", exc)
    return None


def _find_manual_transcript(episode_dir: Path) -> TranscriptResult | None:
    """在 input/ 下查找用户手动提供的转写文件（.srt/.txt）。"""
    for pattern in ["**/*.srt", "**/transcript.txt", "**/script.txt"]:
        for p in (episode_dir / "input").glob(pattern):
            try:
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    log.info("使用手动转写: %s", p)
                    return TranscriptResult(text=text, provider="manual")
            except Exception:
                pass
    return None


def run_transcription(
    audio_path: Path | None,
    episode_dir: Path,
    output_path: Path,
    *,
    provider: str = "auto",
) -> TranscriptResult | None:
    """执行转写并保存 transcript.json；失败时返回 None。

    provider:
        auto     — 依次尝试 whisper_cpp → manual
        manual   — 只用手动文件
        disabled — 跳过
    """
    if provider == "disabled":
        log.info("转写已禁用")
        return None

    result: TranscriptResult | None = None

    if provider in ("auto", "whisper_cpp") and audio_path and audio_path.exists():
        result = _try_whisper_cpp(audio_path)

    if result is None and provider in ("auto", "manual"):
        result = _find_manual_transcript(episode_dir)

    if result is None:
        log.info("无可用转写 Provider（provider=%s）— 跳过", provider)
        return None

    # 保存 transcript.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, ensure_ascii=False, indent=2)
        tmp.replace(output_path)
        log.info("转写完成 (%s): %s", result.provider, output_path)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        log.warning("transcript.json 写入失败: %s", exc)
    return result
