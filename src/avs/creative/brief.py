"""Deterministic creative brief construction."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "creative-brief.schema.json"


HOOKS = {
    "result": "我记录到一条模拟盘权益曲线：从约 4741 到 7228，但先别把它当成实盘盈利。",
    "conflict": "这个 AI 收到交易信号后，第一件事居然是拒绝下单。",
    "pain": "自动交易最危险的不是不赚钱，而是系统错了还继续下单。",
}


def build_creative_brief(
    episode_id: str,
    *,
    platform: str = "douyin",
    must_use_asset_ids: list[str] | None = None,
    hook_variant: str = "conflict",
    target_audience: str = "需要可审计自动化交易流程的量化团队",
    core_pain: str = "交易信号错误时系统仍然继续执行",
    angle: str = "先展示真实后台结果，再解释风险闸门如何工作",
    duration_seconds: float = 35.0,
) -> dict[str, Any]:
    if hook_variant not in HOOKS:
        raise ValueError(f"未知 Hook 类型: {hook_variant}")
    doc: dict[str, Any] = {
        "episode_id": episode_id,
        "platform": platform,
        "target_audience": target_audience,
        "core_pain": core_pain,
        "angle": angle,
        "hook": HOOKS[hook_variant],
        "duration_seconds": duration_seconds,
        "structure": ["hook", "真实结果", "操作证据", "风险解释", "结尾行动"],
        "must_use_asset_ids": list(must_use_asset_ids or []),
        "forbidden_content": ["通用科技背景替代产品证据", "无素材支撑的产品能力", "生成式篡改 UI"],
        "product_visual_ratio": 0.7,
        "hook_variants": [{"id": key, "text": value} for key, value in HOOKS.items()],
    }
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    return doc


def save_creative_brief(episode_dir: Path, brief: dict[str, Any]) -> Path:
    path = episode_dir / "work" / "content" / "creative-brief.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
