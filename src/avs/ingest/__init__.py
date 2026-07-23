"""src/avs/ingest/__init__.py — 模块3主入口：run_ingest()。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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
_INGEST_CONFIG = {"canvas_w": 540, "canvas_h": 960, "video_crf": 28}


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
    import hashlib
    suffix = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:8]
    return f"{slug[:119]}-{suffix}"


def run_ingest(
    episode_dir: Path,
    episode_id: str,
    *,
    force: bool = False,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """扫描 input/、探测媒体、创建工作副本，生成 asset-manifest.json。

    返回 asset 字典列表（同时写入 manifest）。
    force=True 时跳过幂等缓存，重新转码所有文件。
    """
    ingest_config = {**_INGEST_CONFIG, **(config or {})}
    cfg_hash = config_hash(ingest_config)
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

        if df.kind == "unknown":
            assets.append(_unsupported_record(df, file_hash))
            cache[rel] = {
                "sha256": file_hash, "cfg_hash": cfg_hash, "status": "unsupported",
            }
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
            normalize_asset(src, dst, df.kind, media_probe, config=ingest_config)
        except Exception as exc:
            log.warning("规范化失败 %s: %s", rel, exc)
            rec = _corrupt_record(df, f"规范化失败: {exc}")
            rec["sha256"] = file_hash
            assets.append(rec)
            cache[cache_key] = {
                "sha256": file_hash, "cfg_hash": cfg_hash, "status": "corrupt",
            }
            continue

        if sha256_file(src) != file_hash:
            raise IngestError(f"原始素材在规范化过程中发生变化: {rel}")

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

    # 标记内容重复项，但保留各自工作副本和来源追踪。
    first_by_hash: dict[str, str] = {}
    for asset in assets:
        duplicate_of = first_by_hash.get(asset["sha256"])
        asset["duplicate_of"] = duplicate_of
        if asset["status"] == "ok" and duplicate_of is None:
            first_by_hash[asset["sha256"]] = asset["asset_id"]

    # --- 写 manifest 和日志 ---
    save_manifest(episode_dir, episode_id, assets)
    _save_cache(episode_dir, cache)
    _write_ingest_log(episode_dir, episode_id, assets, cfg_hash)
    log.info("ingest 完成：%d 个素材（%d corrupt）",
             len(assets), sum(1 for a in assets if a["status"] == "corrupt"))
    return assets


def _write_ingest_log(
    episode_dir: Path,
    episode_id: str,
    assets: list[dict[str, Any]],
    cfg_hash: str,
) -> None:
    log_path = episode_dir / "logs" / "ingest.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "episode_id": episode_id,
        "config_hash": cfg_hash,
        "assets": [
            {
                "source_path": asset["source_path"],
                "working_path": asset["working_path"],
                "sha256": asset["sha256"],
                "status": asset["status"],
            }
            for asset in assets
        ],
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


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
        "codec_video": probe.get("codec_video"),
        "codec_audio": probe.get("codec_audio"),
        "layout": "contain" if df.kind == "video" else None,
        "notes": None,
    }


def _corrupt_record(df, reason: str) -> dict:
    return {
        "asset_id": _asset_id(df.rel_path),
        "source_path": df.rel_path,
        "working_path": None,
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


def _unsupported_record(df, sha: str) -> dict:
    record = _corrupt_record(df, "不支持的文件类型，未创建工作副本")
    record["sha256"] = sha
    record["status"] = "unsupported"
    return record


def _rebuild_from_cache(df, cached: dict, sha: str, dst_rel: str) -> dict:
    probe = cached.get("probe", {})
    status = cached.get("status", "ok")
    return {
        "asset_id": _asset_id(df.rel_path),
        "source_path": df.rel_path,
        "working_path": dst_rel if status == "ok" else None,
        "kind": df.kind,
        "mime_type": df.mime_type,
        "sha256": sha,
        "status": status,
        "duration": probe.get("duration"),
        "width": probe.get("width"),
        "height": probe.get("height"),
        "fps": probe.get("fps"),
        "has_audio": probe.get("has_audio"),
        "codec_video": probe.get("codec_video"),
        "codec_audio": probe.get("codec_audio"),
        "layout": "contain" if df.kind == "video" else None,
        "notes": None,
    }
