"""Asset-level visual intelligence.

The deterministic part records dimensions and safe default ROI metadata.  It
does not invent product facts: semantic fields remain blocked until a real
vision provider returns them.
"""
from __future__ import annotations

import json
import os
import base64
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import jsonschema
import yaml

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "asset-intelligence.schema.json"


class VisionProviderUnavailable(RuntimeError):
    """No configured provider credentials are available for semantic vision."""


def vision_provider_name() -> str:
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "none"


def _manual_facts(user_note: str | None) -> list[str]:
    if not user_note:
        return []
    # 只承接用户明确写出的标签，不把 OCR 或项目能力自行冒充视觉事实。
    return [item.strip() for item in user_note.replace("\n", "；").replace(",", "；").split("；") if item.strip()]


def _asset_intelligence(asset: dict[str, Any], *, allow_manual_notes: bool = False) -> dict[str, Any]:
    width = asset.get("original_width") or asset.get("width")
    height = asset.get("original_height") or asset.get("height")
    # A full-frame ROI is structural metadata, not a semantic claim.
    facts = _manual_facts(asset.get("user_note")) if allow_manual_notes else []
    return {
        "asset_id": asset["asset_id"],
        "summary": "用户备注标注的产品截图（待视觉 Provider 复核）" if facts else "待视觉 Provider 识别的产品素材",
        "product_area": facts[0] if facts else "未识别",
        "visible_facts": facts,
        "regions": [{
            "region_id": "full-frame",
            "box": [0.0, 0.0, 1.0, 1.0],
            "meaning": "完整画面（待语义标注）",
            "priority": 0.5,
        }],
        "recommended_uses": ["仅用于待审阅截图图文预览"] if facts else [],
        "metadata": {
            "original_width": width,
            "original_height": height,
            "source_type": asset.get("source_type"),
            "semantic_source": "user_note" if facts else "pending_provider",
        },
    }


def _project_root(episode_dir: Path) -> Path:
    for candidate in (episode_dir, *episode_dir.parents):
        if (candidate / "config" / "providers.yaml").is_file():
            return candidate
    raise FileNotFoundError("无法定位 config/providers.yaml")


def _vision_model(episode_dir: Path, provider: str) -> str:
    config = yaml.safe_load((_project_root(episode_dir) / "config" / "providers.yaml").read_text(encoding="utf-8"))
    llm = config.get("providers", {}).get("llm", {})
    return str(llm.get(provider, {}).get("model") or ("gpt-4o" if provider == "openai" else "claude-sonnet-4-20250514"))


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Vision Provider 未返回 JSON 对象")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Vision Provider JSON 根节点必须是对象")
    return value


def _request_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Vision Provider 请求失败: {exc}") from exc


def _analyze_image(path: Path, *, provider: str, model: str, user_note: str | None) -> dict[str, Any]:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    prompt = (
        "分析这张真实产品截图。只描述画面可见事实，不推断未显示能力。"
        "返回一个 JSON 对象，字段必须为 summary, product_area, visible_facts, regions, recommended_uses。"
        "regions 每项包含 region_id, box=[x,y,w,h]（0到1归一化）, meaning, priority（0到1）。"
        f"用户备注：{user_note or '无'}"
    )
    if provider == "anthropic":
        key = os.environ["ANTHROPIC_API_KEY"]
        response = _request_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            {
                "model": model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}},
                    {"type": "text", "text": prompt},
                ]}],
            },
        )
        text = "\n".join(item.get("text", "") for item in response.get("content", []) if item.get("type") == "text")
    elif provider == "openai":
        key = os.environ["OPENAI_API_KEY"]
        response = _request_json(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {key}"},
            {
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}},
                ]}],
            },
        )
        text = str(response["choices"][0]["message"]["content"])
    else:
        raise VisionProviderUnavailable("没有可用 Vision Provider")
    result = _extract_json(text)
    regions: list[dict[str, Any]] = []
    for index, region in enumerate(result.get("regions", [])):
        if not isinstance(region, dict) or not isinstance(region.get("box"), list) or len(region["box"]) != 4:
            continue
        try:
            box = [max(0.0, min(1.0, float(value))) for value in region["box"]]
            priority = max(0.0, min(1.0, float(region.get("priority", 0.5))))
        except (TypeError, ValueError):
            continue
        regions.append({
            "region_id": str(region.get("region_id") or f"region-{index + 1}"),
            "box": box,
            "meaning": str(region.get("meaning", "")),
            "priority": priority,
        })
    return {
        "summary": str(result.get("summary", "")),
        "product_area": str(result.get("product_area", "")),
        "visible_facts": [str(value) for value in result.get("visible_facts", [])],
        "regions": regions or [{"region_id": "full-frame", "box": [0.0, 0.0, 1.0, 1.0], "meaning": "完整画面", "priority": 0.5}],
        "recommended_uses": [str(value) for value in result.get("recommended_uses", [])],
    }


def analyze_assets(
    episode_dir: Path,
    *,
    manifest: dict[str, Any] | None = None,
    require_provider: bool = True,
    allow_manual_notes: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Create ``work/analysis/asset-intelligence.json``.

    Without credentials the output is explicitly blocked.  Callers may use
    ``require_provider=False`` for structural unit tests, but that output is
    never publishable.
    """
    output = episode_dir / "work" / "analysis" / "asset-intelligence.json"
    if output.is_file() and not force:
        return json.loads(output.read_text(encoding="utf-8"))
    if manifest is None:
        manifest = json.loads((episode_dir / "work" / "input-manifest.json").read_text(encoding="utf-8"))
    provider = vision_provider_name()
    blocked = require_provider and provider == "none"
    blocking_reason = "缺少 ANTHROPIC_API_KEY 或 OPENAI_API_KEY，不能完成截图语义理解" if blocked else None
    assets: list[dict[str, Any]] = []
    model = _vision_model(episode_dir, provider) if provider != "none" else "none"
    for asset in manifest.get("assets", []):
        if asset.get("status") != "ok":
            continue
        item = _asset_intelligence(asset, allow_manual_notes=allow_manual_notes)
        if asset.get("source_type") == "screenshot" and provider != "none":
            working = asset.get("working_path")
            path = episode_dir / str(working) if working else None
            try:
                if path is None or not path.is_file():
                    raise FileNotFoundError(str(path))
                semantic = _analyze_image(path, provider=provider, model=model, user_note=asset.get("user_note"))
                item.update(semantic)
            except Exception as exc:
                blocked = True
                blocking_reason = f"素材 {asset.get('asset_id')} 视觉分析失败: {exc}"
        assets.append(item)
    doc: dict[str, Any] = {
        "episode_id": manifest["episode_id"],
        "provider": provider if provider != "none" else ("manual" if allow_manual_notes else "none"),
        "blocked": blocked,
        "blocking_reason": blocking_reason,
        "requires_provider_review": bool(allow_manual_notes),
        "assets": assets,
    }
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
