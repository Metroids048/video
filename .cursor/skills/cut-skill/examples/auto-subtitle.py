"""自动字幕示例：从视频提取音频，做 ASR，把识别结果作为字幕批量添加到剪映。

场景：用户给一个视频，希望自动生成字幕。
流程：
1. 从视频提取音频（ffmpeg）
2. 调用 ASR 服务识别（这里用 mock，实际可接 whisper / 阿里 ASR / 讯飞）
3. 按 SRT 时间戳批量 add_subtitle 到剪映 draft

用法：
    python examples/auto-subtitle.py --project my_vlog --video /path/to/video.mp4

依赖：
    ffmpeg（提取音频）
    可选：openai-whisper 或其他 ASR SDK
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cut.jianying.draft import Draft
from cut.jianying import text as TX


# ---------------------------------------------------------------------------
# 1. 提取音频
# ---------------------------------------------------------------------------

def extract_audio(video_path: str, output_path: str) -> str:
    """用 ffmpeg 从视频提取音频（mp3, 16kHz, mono）。"""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame",
        "-ar", "16000", "-ac", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-500:]}")
    return output_path


# ---------------------------------------------------------------------------
# 2. ASR 识别（mock 版，实际请替换）
# ---------------------------------------------------------------------------

def transcribe_mock(audio_path: str) -> List[Dict]:
    """Mock ASR：返回假的字幕段。

    实际项目中替换为真实 ASR：
    - openai-whisper: `import whisper; model = whisper.load_model("base"); result = model.transcribe(audio_path)`
    - 阿里云 ASR: 用 nls SDK
    - 讯飞: 用 websdk
    """
    return [
        {"text": "大家好，欢迎来到我的频道", "start_us": 0, "duration_us": 3_000_000},
        {"text": "今天我们来聊一聊 AI 编程", "start_us": 3_000_000, "duration_us": 4_000_000},
        {"text": "首先，让我们看看 cut.skill 是什么", "start_us": 7_000_000, "duration_us": 3_500_000},
        {"text": "它可以让 agent 操控剪映和 Premiere", "start_us": 10_500_000, "duration_us": 3_500_000},
        {"text": "感谢观看，我们下期再见", "start_us": 14_000_000, "duration_us": 4_000_000},
    ]


def transcribe_whisper(audio_path: str) -> List[Dict]:
    """用 OpenAI Whisper 识别（需要 pip install openai-whisper）。"""
    try:
        import whisper
    except ImportError:
        print("whisper 未安装，回退到 mock", file=sys.stderr)
        return transcribe_mock(audio_path)

    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    segments = []
    for seg in result["segments"]:
        segments.append({
            "text": seg["text"].strip(),
            "start_us": int(seg["start"] * 1_000_000),
            "duration_us": int((seg["end"] - seg["start"]) * 1_000_000),
        })
    return segments


# ---------------------------------------------------------------------------
# 3. 批量添加字幕
# ---------------------------------------------------------------------------

def add_subtitles_to_draft(project_name: str, subtitles: List[Dict]) -> int:
    """把字幕段批量加到剪映 draft。"""
    draft = Draft.open(project_name=project_name)
    print(f"项目时长: {draft.duration_hms}")

    # 找或创建 text 轨
    if not draft.text_tracks:
        draft.add_track("text")

    added = 0
    for s in subtitles:
        try:
            TX.add_subtitle(
                draft, s["text"],
                start_us=s["start_us"],
                duration_us=s["duration_us"],
            )
            added += 1
            print(f"  + [{s['start_us']//1_000_000}s] {s['text']}")
        except Exception as e:
            print(f"  ! 失败: {e}")

    draft.save()
    return added


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="自动字幕示例")
    parser.add_argument("--project", required=True, help="剪映项目名")
    parser.add_argument("--video", required=True, help="视频文件路径")
    parser.add_argument("--engine", default="mock", choices=["mock", "whisper"],
                        help="ASR 引擎")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "audio.mp3")

        print(f"[1/3] 提取音频: {args.video}")
        extract_audio(args.video, audio_path)
        print(f"      → {audio_path}")

        print(f"[2/3] ASR 识别 (engine={args.engine})")
        if args.engine == "whisper":
            subs = transcribe_whisper(audio_path)
        else:
            subs = transcribe_mock(audio_path)
        print(f"      识别到 {len(subs)} 段字幕")

        print(f"[3/3] 添加到剪映项目: {args.project}")
        n = add_subtitles_to_draft(args.project, subs)
        print(f"\n✓ 完成。添加 {n} 段字幕。请在剪映中重新打开项目查看。")


if __name__ == "__main__":
    main()
