"""scripts/free_providers/image_to_clip.py — 免费图生短片（FFmpeg Ken Burns）。

代替付费 Seedance/Kie：把参考图做成可剪辑的竖屏/横屏运动镜头（无云端 API）。

用法：
  python scripts/free_providers/image_to_clip.py refs/a.jpg -o out/clip.mp4 --duration 5
  python scripts/free_providers/image_to_clip.py refs/*.jpg -o out/ --duration 4 --size 1080x1920
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def render_one(
    image: Path,
    output: Path,
    *,
    duration: float,
    size: str,
    fps: int,
) -> None:
    width, height = size.lower().split("x")
    w, h = int(width), int(height)
    # zoompan Ken Burns: slow zoom-in
    frames = max(int(duration * fps), 1)
    vf = (
        f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,"
        f"crop={w * 2}:{h * 2},"
        f"zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={w}x{h}:fps={fps},"
        f"format=yuv420p"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image),
        "-vf",
        vf,
        "-t",
        str(duration),
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Free FFmpeg Ken Burns image→clip (Seedance free alt)")
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output file or directory")
    ap.add_argument("--duration", type=float, default=4.0)
    ap.add_argument("--size", type=str, default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    images = [p.resolve() for p in args.images if p.is_file()]
    if not images:
        print("no images found", file=sys.stderr)
        return 1

    out = args.output
    if len(images) == 1 and out.suffix.lower() in {".mp4", ".mov", ".mkv"}:
        render_one(images[0], out, duration=args.duration, size=args.size, fps=args.fps)
        print(f"wrote {out}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    for img in images:
        dest = out / f"{img.stem}_kb.mp4"
        render_one(img, dest, duration=args.duration, size=args.size, fps=args.fps)
        print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
