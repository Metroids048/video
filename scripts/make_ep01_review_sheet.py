from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> int:
    ep = Path(sys.argv[1]).resolve()
    video = ep / "renders" / "final-with-captions.mp4"
    out_dir = ep / "work" / "qa" / "final-review"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("frame-*.jpg"):
        old.unlink()
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf", "fps=1", "-q:v", "3", str(out_dir / "frame-%03d.jpg")], check=True)
    frames = sorted(out_dir.glob("frame-*.jpg"))
    thumbs = []
    for frame in frames:
        image = Image.open(frame).convert("RGB")
        image.thumbnail((270, 480))
        canvas = Image.new("RGB", (290, 520), "#111111")
        canvas.paste(image, ((290 - image.width) // 2, 20))
        ImageDraw.Draw(canvas).text((12, 492), frame.stem, fill="white")
        thumbs.append(canvas)
    cols = 6
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 290, rows * 520), "#222222")
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % cols) * 290, (index // cols) * 520))
    sheet.save(out_dir / "contact-sheet.jpg", quality=92)
    print(out_dir / "contact-sheet.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
