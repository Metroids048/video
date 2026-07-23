"""src/avs/ingest/hashing.py — SHA-256 文件哈希（只读原文件）。"""
from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 65536  # 64 KiB


def sha256_file(path: Path) -> str:
    """返回文件的十六进制 SHA-256 摘要（不修改文件）。"""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def config_hash(params: dict) -> str:
    """对配置参数字典计算稳定哈希，用于幂等性判断。"""
    import json
    payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
