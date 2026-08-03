"""Deterministic extraction for user-supplied text and documents."""
from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    return "\n".join(text.strip() for text in root.itertext() if text.strip())


def _pdf_text(path: Path) -> str:
    executable = shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("pdftotext 不可用，无法提取 PDF")
    result = subprocess.run(
        [executable, "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-300:])
    return result.stdout


def extract_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".srt"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        return _docx_text(path)
    if suffix == ".pdf":
        return _pdf_text(path)
    raise RuntimeError(f"不支持提取该文档类型: {suffix}")


def analyze_documents(episode_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    blocked = False
    for asset in manifest.get("assets", []):
        if asset.get("source_type") not in {"document", "text"} or asset.get("status") != "ok":
            continue
        working = episode_dir / str(asset.get("working_path"))
        try:
            text = extract_document_text(working)
            assets.append({"asset_id": asset["asset_id"], "text": text, "status": "ok", "error": None})
        except Exception as exc:
            blocked = blocked or bool(asset.get("must_use"))
            assets.append({"asset_id": asset["asset_id"], "text": "", "status": "blocked", "error": str(exc)})
    doc = {"episode_id": manifest["episode_id"], "blocked": blocked, "assets": assets}
    output = episode_dir / "work" / "analysis" / "document-analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
