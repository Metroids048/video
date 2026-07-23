"""Extract representative final-video frames and assemble a contact sheet."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from avs.reference.contact_sheet import make_contact_sheet


def create_final_contact_sheet(video_path: Path, output_path: Path, duration: float, count: int = 6) -> Path | None:
    if duration <= 0:
        return None
    with tempfile.TemporaryDirectory(prefix="avs_qa_frames_") as temp:
        temp_dir = Path(temp)
        frames: dict[str, Path] = {}
        for index in range(count):
            timestamp = duration * (index + 0.5) / count
            frame = temp_dir / f"frame-{index:02d}.jpg"
            result = subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{timestamp:.3f}", "-i", str(video_path), "-frames:v", "1", "-q:v", "2", str(frame)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and frame.is_file():
                frames[f"frame-{index:02d}"] = frame
        return make_contact_sheet(frames, output_path, cols=3, thumb_w=270, thumb_h=480)
