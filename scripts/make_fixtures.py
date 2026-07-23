"""scripts/make_fixtures.py — 生成模块3测试所需的最小媒体 Fixture。

用法：
    python scripts/make_fixtures.py [episode_dir]

若 episode_dir 未指定，默认创建 fixtures/ingest-demo/input/ 结构。
不依赖任何外部工具；二进制文件通过 struct/bytes 构造。
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def make_minimal_png(path: Path) -> None:
    """生成 1×1 像素纯红色 PNG（最小合法 PNG）。"""
    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    # 1×1 RGB pixel: filter byte 0x00 + R G B
    raw = b"\x00\xFF\x00\x00"
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sig + ihdr + idat + iend)


def make_minimal_wav(path: Path, duration_s: float = 0.1) -> None:
    """生成最小合法 WAV（单声道 16-bit 44100Hz）。"""
    sample_rate = 44100
    n_samples = int(sample_rate * duration_s)
    data_size = n_samples * 2  # 16-bit mono
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)


def make_corrupt_mp4(path: Path) -> None:
    """生成一个扩展名为 .mp4 但内容为垃圾字节的损坏文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xDE\xAD\xBE\xEF" * 64 + b"NOT A REAL MP4 FILE")


def make_minimal_mp4(path: Path) -> None:
    """生成最小合法 MP4（仅含 ftyp + mdat 骨架，ffprobe 可识别为 MP4 容器）。

    注：此文件无视频流，ffprobe 会报 duration=N/A，但不会报损坏。
    实际测试环境中 ffprobe 不可用时直接复制，此文件足够验证流程。
    """
    # ftyp box
    ftyp = (b"\x00\x00\x00\x18ftyp"
            b"isom"     # major brand
            b"\x00\x00\x00\x00"  # minor version
            b"isom" b"iso2")     # compatible brands
    # mdat box (empty)
    mdat = b"\x00\x00\x00\x08mdat"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ftyp + mdat)


def setup_fixtures(input_dir: Path) -> None:
    """在 input_dir 下创建完整测试 fixture 集合。"""
    input_dir.mkdir(parents=True, exist_ok=True)

    # 1. 普通文本文件
    (input_dir / "script.txt").write_text(
        "这是一个测试脚本文件。\n用于验证文本类素材 ingest。\n", encoding="utf-8"
    )

    # 2. links.txt（link 类型）
    (input_dir / "links.txt").write_text(
        "https://example.com/ref1\nhttps://example.com/ref2\n", encoding="utf-8"
    )

    # 3. 图片子目录
    img_dir = input_dir / "images"
    make_minimal_png(img_dir / "cover.png")
    # Unicode 文件名（测试路径处理）
    make_minimal_png(img_dir / "封面图片_测试.png")
    # 重复内容的图片（用于验证幂等性）
    import shutil
    shutil.copy2(img_dir / "cover.png", img_dir / "cover_dup.png")

    # 4. 音频子目录
    audio_dir = input_dir / "audio"
    make_minimal_wav(audio_dir / "bgm.wav")

    # 5. 参考视频目录（可播放的 MP4 骨架）
    ref_dir = input_dir / "reference"
    make_minimal_mp4(ref_dir / "ref_video.mp4")

    # 6. 屏幕录制目录（损坏视频 — 不进渲染）
    screen_dir = input_dir / "screen"
    make_corrupt_mp4(screen_dir / "corrupt_screen.mp4")

    print(f"✓ Fixture 创建完成: {input_dir}")
    for f in sorted(input_dir.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(input_dir)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        # 默认放在项目根的 fixtures/ingest-demo/input/
        here = Path(__file__).resolve().parent.parent
        target = here / "fixtures" / "ingest-demo" / "input"

    setup_fixtures(target)
