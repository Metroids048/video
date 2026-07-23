"""src/avs/ingest/__init__.py — 模块3主入口：run_ingest()。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from avs.ingest.discovery import discover_inputs
from avs.ingest.errors import IngestError
from avs.ingest.hashing import sha256_file, config_hash
from avs.ingest.manifest import save_manifest
from avs.ingest.normalize import normalize_asset, prepared_path
from avs.ingest.probe import probe_media

log = logging.getLogger(__name__)

_CACHE_FILE = "work/.ingest-cache.json"
_INGEST_CONFIG_KEYS = ["canvas_w", "canvas_h", "video_crf"]
_INGEST_CONFIG = {"canvas_w": 1080, "canvas_h": 1920, "video_crf": 28}


def _load_cache(episode_dir: Path) -> dict:
    p = episode_dir / _CACHE_FILE
    if p.exists():
        try:
            with p.open(encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def _save_cache(episode_dir: Path, cache: dict) -> None:
    p = episode_dir / _CACHE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        log.warning("缓存写入失败（非致命）: %s", exc)


def _asset_id(rel_path: str) -> str:
    """将相对路径转为合法 asset_id（斜杠转下划线，去掉 input/ 前缀）。"""
    parts = Path(rel_path).parts
    if parts and parts[0] == "input":
        parts = parts[1:]
    slug = "_".join(parts)
    # 替换非法字符
    import re
    slug = re.sub(r"[^A-Za-z0-9_\-.]", "_", slug)
    return slug[:128]


def run_ingest(
    episode_dir: Path,
    episode_id: str,
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    """扫描 input/、探测媒体、创建工作副本，生成 asset-manifest.json。

    返回 asset 字典列表（同时写入 manifest）。
    force=True 时跳过幂等缓存，重新转码所有文件。
    """
    cfg_hash = config_hash(_INGEST_CONFIG)
    cache = {} if force else _load_cache(episode_dir)

    files = discover_inputs(episode_dir)
    log.info("发现 %d 个输入文件", len(files))

    assets: list[dict[str, Any]] = []

    for df in files:
        rel = df.rel_path
        src = df.abs_path

        # --- 计算源文件 hash ---
        try:
            file_hash = sha256_file(src)
        except Exception as exc:
            log.warning("无法哈希 %s: %s — 标记为 corrupt", rel, exc)
            assets.append(_corrupt_record(df, str(exc)))
            continue

        # --- 幂等检查 ---
        cache_key = rel
        cached = cache.get(cache_key, {})
        dst = prepared_path(episode_dir, rel)
        dst_rel = dst.relative_to(episode_dir).as_posix()

        if (
            not force
            and cached.get("sha256") == file_hash
            and cached.get("cfg_hash") == cfg_hash
            and dst.exists()
        ):
            log.info("跳过（未变）: %s", rel)
            # 重建 asset 记录（从缓存拿 probe 数据）
            assets.append(_rebuild_from_cache(df, cached, file_hash, dst_rel))
            continue

        # --- FFprobe 探测 ---
        media_probe: dict[str, Any] = {}
        if df.kind in ("video", "audio", "image"):
            media_probe = probe_media(src)
            if media_probe.get("ffprobe_skipped"):
                log.warning("ffprobe 不可用，跳过媒体字段: %s", rel)
            elif media_probe.get("decodable") is False and not media_probe.get("ffprobe_skipped"):
                log.warning("文件可能损坏 (%s): %s", media_probe.get("error", ""), rel)
                rec = _corrupt_record(df, media_probe.get("error") or "ffprobe 报告不可解码")
                rec["sha256"] = file_hash  # 有真实 sha256 时覆盖占位值
                assets.append(rec)
                # 更新缓存
                cache[cache_key] = {"sha256": file_hash, "cfg_hash": cfg_hash, "status": "corrupt"}
                continue

        # --- 规范化（创建工作副本）---
        try:
            normalize_asset(src, dst, df.kind, media_probe)
        except Exception as exc:
            log.warning("规范化失败 %s: %s — 尝试直接复制", rel, exc)
            import shutil
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            except Exception as copy_exc:
                assets.append(_corrupt_record(df, f"规范化+复制均失败: {copy_exc}"))
                continue

        # --- 构建 asset 记录 ---
        record = _build_record(df, file_hash, dst_rel, media_probe)
        assets.append(record)

        # 更新缓存
        cache[cache_key] = {
            "sha256": file_hash,
            "cfg_hash": cfg_hash,
            "status": "ok",
            "probe": {k: media_probe.get(k) for k in
                      ("duration", "width", "height", "fps", "has_audio",
                       "codec_video", "codec_audio")},
        }

    # --- 写 manifest ---
    save_manifest(episode_dir, episode_id, assets)
    _save_cache(episode_dir, cache)
    log.info("ingest 完成：%d 个素材（%d corrupt）",
             len(assets), sum(1 for a in assets if a["status"] == "corrupt"))
    return assets


def _build_record(df, sha: str, dst_rel: str, probe: dict) -> dict:
    return {
        "asset_id": _asset_id(df.rel_path),
        "source_path": df.rel_path,
        "working_path": dst_rel,
        "kind": df.kind,
        "mime_type": df.mime_type,
        "sha256": sha,
        "status": "ok",
        "duration": probe.get("duration"),
        "width": probe.get("width"),
        "height": probe.get("height"),
        "fps": probe.get("fps"),
        "has_audio": probe.get("has_audio"),
        "notes": None,
    }


def _corrupt_record(df, reason: str) -> dict:
    return {
        "asset_id": _asset_id(df.rel_path),
        "source_path": df.rel_path,
        "working_path": df.rel_path,   # 损坏文件不复制，保留原路径
        "kind": df.kind,
        "mime_type": df.mime_type,
        "sha256": "0" * 64,            # 占位，防止 Schema 拒绝
        "status": "corrupt",
        "duration": None,
        "width": None,
        "height": None,
        "fps": None,
        "has_audio": None,
        "notes": reason,
    }


def _rebuild_from_cache(df, cached: dict, sha: str, dst_rel: str) -> dict:
    probe = cached.get("probe", {})
    return {
        "asset_id": _asset_id(df.rel_path),
        "source_path": df.rel_path,
        "working_path": dst_rel,
        "kind": df.kind,
        "mime_type": df.mime_type,
        "sha256": sha,
        "status": cached.get("status", "ok"),
        "duration": probe.get("duration"),
        "width": probe.get("width"),
        "height": probe.get("height"),
        "fps": probe.get("fps"),
        "has_audio": probe.get("has_audio"),
        "notes": None,
    }
