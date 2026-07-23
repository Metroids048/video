"""src/avs/ingest/errors.py — Ingest 模块专用异常。"""
from __future__ import annotations


class IngestError(Exception):
    """ingest 流程基础异常。"""


class ProbeError(IngestError):
    """FFprobe 探测失败（文件损坏或工具缺失时不使用此异常，直接降级）。"""


class NormalizeError(IngestError):
    """工作副本或 Proxy 创建失败。"""


class ManifestError(IngestError):
    """asset-manifest.json 写入或 Schema 校验失败。"""


class PathTraversalError(IngestError):
    """检测到路径穿越攻击。"""
