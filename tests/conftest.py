"""tests/conftest.py — pytest 全局配置与共享 fixture。"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest


def _make_png_bytes() -> bytes:
    """生成最小合法 1×1 PNG 字节串。"""
    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xFF\x00\x00"
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _make_wav_bytes(duration_s: float = 0.05) -> bytes:
    """生成最小合法 WAV 字节串（单声道 16-bit 44100Hz）。"""
    sr = 44100
    n = int(sr * duration_s)
    data_size = n * 2
    buf = bytearray()
    buf += b"RIFF"
    buf += struct.pack("<I", 36 + data_size)
    buf += b"WAVE"
    buf += b"fmt "
    buf += struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
    buf += b"data"
    buf += struct.pack("<I", data_size)
    buf += b"\x00" * data_size
    return bytes(buf)


@pytest.fixture(scope="session")
def png_bytes() -> bytes:
    return _make_png_bytes()


@pytest.fixture(scope="session")
def wav_bytes() -> bytes:
    return _make_wav_bytes()
