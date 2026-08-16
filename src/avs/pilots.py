"""SCREEN_DOCUMENTARY mining, Pilot rendering, and fail-closed visual gate.

All durable artifacts live below the Episode directory.  The VCI package and
the original capture are read-only inputs; no code here mutates either of them.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from avs.qa.creative_sampling import build_contact_sheets, extract_frames, extract_uniform_frames


PILOT_IDS = ("A-result", "B-reversal", "C-project")
CORE_DIMENSIONS = (
    "first_frame", "hook", "mobile_readability", "real_evidence",
    "caption_intrusion", "visual_density", "pacing", "ppt_feel",
    "cheap_ai_feel", "continue_watching",
)
MAX_REPAIR_ROUNDS = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _write(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def screen_documentary_rules() -> dict[str, Any]:
    payload = yaml.safe_load((_root() / "config" / "production-types.yaml").read_text(encoding="utf-8"))
    return dict(payload["production_types"]["SCREEN_DOCUMENTARY"])


def _vci_package() -> Path:
    return _root() / "video-content-intelligence" / "workspace" / "packages" / "VID-20260812-FDA0"


def _source_recording(ep_dir: Path) -> Path:
    candidates = (
        ep_dir / "work" / "prepared" / "screen" / "20260812_131106.mp4",
        _root() / "录屏" / "20260812_131106.mp4",
        _vci_package() / "original" / "source_video.mp4",
    )
    source = next((item for item in candidates if item.is_file()), None)
    if source is None:
        raise RuntimeError("找不到冻结的 EP01 原始录屏工作副本")
    return source


def _prepared_source(ep_dir: Path) -> Path:
    source = _source_recording(ep_dir)
    target = ep_dir / "work" / "prepared" / "screen" / "20260812_131106.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)
    return target


def mine_story(ep_dir: Path) -> dict[str, Path]:
    """Reuse the verified VCI result, without invoking ingest or transcription."""
    package = _vci_package()
    structured = _read(package / "structured" / "content.json")
    if structured.get("source_id") != "VID-20260812-FDA0":
        raise RuntimeError("EP01 必须复用已验证的 VID-20260812-FDA0 VCI 包")
    source = _prepared_source(ep_dir)
    scenes = [
        {"id": "binance-order-history", "source_start": 129.0, "source_end": 136.0, "label": "Binance Demo Order History", "target": "Balance + Order History", "region": [0.05, 0.42, 0.92, 0.50], "evidence": "SOURCE_INFERRED"},
        {"id": "binance-balance", "source_start": 136.0, "source_end": 140.0, "label": "Binance Demo Balance", "target": "Balance", "region": [0.80, 0.55, 0.19, 0.37], "evidence": "SOURCE_INFERRED"},
        {"id": "dashboard-overview", "source_start": 1.0, "source_end": 5.0, "label": "AI Quant dashboard", "target": "Simulated balance + chart", "region": [0.02, 0.05, 0.72, 0.90], "evidence": "SOURCE_INFERRED"},
        {"id": "why-no-trade", "source_start": 84.0, "source_end": 90.0, "label": "Why No Trade", "target": "Why No Trade", "region": [0.69, 0.30, 0.30, 0.42], "evidence": "SOURCE_EXPLICIT"},
        {"id": "decision-risk", "source_start": 68.0, "source_end": 75.0, "label": "Decision and risk", "target": "Decision / Risk", "region": [0.05, 0.07, 0.90, 0.80], "evidence": "SOURCE_EXPLICIT"},
        {"id": "research-validation", "source_start": 55.0, "source_end": 65.0, "label": "Strategy and validation", "target": "Strategy / Validation", "region": [0.02, 0.05, 0.96, 0.88], "evidence": "SOURCE_EXPLICIT"},
    ]
    output = ep_dir / "work" / "director"
    screen_index = {"episode_id": ep_dir.name, "vci_source_id": structured["source_id"], "source_recording": source.relative_to(ep_dir).as_posix(), "scenes": scenes, "generated_at": _now(), "reused_vci": True}
    evidence_index = {"episode_id": ep_dir.name, "facts": structured.get("claims", []) + structured.get("numbers", []), "scenes": scenes}
    _write(output / "录屏内容索引.json", screen_index)
    _write(output / "证据镜头索引.json", evidence_index)
    (output / "推荐片段.md").write_text("# 推荐片段\n\n- Binance Demo 129-136s：订单历史和余额是开场与真实性证据。\n- Dashboard 1-5s：系统总览与 K 线。\n- Why No Trade 84-90s：差异化解释能力。\n", encoding="utf-8")
    (output / "禁止使用片段.md").write_text("# 禁止使用片段\n\n- 125-128s Binance 页面加载骨架屏。\n- 任意整页横屏缩小、空背景、PPT 卡或旧 V1 时间线镜头。\n", encoding="utf-8")
    return {"screen_index": output / "录屏内容索引.json", "evidence_index": output / "证据镜头索引.json", "recommended": output / "推荐片段.md", "forbidden": output / "禁止使用片段.md"}


def direct_story(ep_dir: Path) -> Path:
    payload = {
        "episode_id": ep_dir.name, "production_type": "SCREEN_DOCUMENTARY",
        "core_story": "5000U 到当前约7355U是钩子；AI 产品经理用 Agent 做出连接 Binance Demo 的自动交易系统；阶段账户变化不等于策略成功。",
        "fact_boundary": ["5000U 为用户提供的初始基准，未由资金流水独立验证。", "约7355U 为画面快照，不能归因成策略收益。", "当前环境是 Binance Demo/Testnet 模拟盘。"],
        "target_duration_seconds": {"min": 45, "max": 55},
        "excluded": ["旧 V1 PPT 卡", "功能全量罗列", "收益承诺", "无关 B-roll"],
        "structure": ["Binance 真实证据与结果/反转", "AI 构建的系统", "K线-决策-风控", "Why No Trade", "交易所对账", "谨慎结论与下一集"], "generated_at": _now(),
    }
    return _write(ep_dir / "work" / "director" / "short-video-brief.json", payload)


def _pilot_spec(variant: str) -> list[dict[str, Any]]:
    specs: dict[str, list[dict[str, Any]]] = {
        "A-result": [
            {"start": 0.0, "duration": 4.1, "in": 129.0, "region": [0.05, 0.42, 0.92, 0.50], "target": "Binance Demo Order History", "caption": "5000U 到约7355U", "spoken": "我用 AI 做的交易系统，模拟盘从五千U到现在约七千三百五十五U。"},
            {"start": 4.1, "duration": 4.7, "in": 1.0, "region": [0.02, 0.05, 0.72, 0.90], "target": "Dashboard", "caption": "Binance Demo 模拟盘", "spoken": "但这只是阶段账户快照，不等于策略已经成功。"},
        ],
        "B-reversal": [
            {"start": 0.0, "duration": 4.2, "in": 129.0, "region": [0.05, 0.42, 0.92, 0.50], "target": "Binance Demo Order History", "caption": "阶段变化约47%", "spoken": "模拟盘涨了大约百分之四十七，但我现在不敢说策略赚钱。"},
            {"start": 4.2, "duration": 4.5, "in": 136.0, "region": [0.80, 0.55, 0.19, 0.37], "target": "Binance Demo Balance", "caption": "样本、回撤、手续费未验证", "spoken": "因为样本量、回撤和手续费，都还没验证完。"},
        ],
        "C-project": [
            {"start": 0.0, "duration": 4.4, "in": 1.0, "region": [0.02, 0.05, 0.72, 0.90], "target": "Dashboard + chart", "caption": "AI 做出的交易系统", "spoken": "我不会传统编程，却用 Codex 和 Claude Code 做出了这套系统。"},
            {"start": 4.4, "duration": 4.4, "in": 129.0, "region": [0.05, 0.42, 0.92, 0.50], "target": "Binance Demo Order History", "caption": "直接看 Binance Demo", "spoken": "它不是演示界面，订单我直接去 Binance Demo 看。"},
        ],
    }
    return specs[variant]


def _srt_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds_int, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds_int:02},{milliseconds:03}"


def _subtitles_filter(path: Path) -> str:
    filename = path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
    # Restrained single-line captions: no black outline, a translucent backing,
    # and enough bottom margin to avoid the primary ROI.
    style = "FontName=Microsoft YaHei,FontSize=42,PrimaryColour=&H00FFFFFF,BackColour=&H70000000,BorderStyle=3,Outline=0,Shadow=0,Alignment=2,MarginV=150,MarginL=68,MarginR=68"
    return f"subtitles='{filename}':force_style='{style}'"


def _run(command: list[str], *, timeout: int, error: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{error}: {(result.stderr or result.stdout)[-600:]}")


def _ensure_narration(work: Path, specs: list[dict[str, Any]], *, force: bool) -> Path:
    output = work / "narration.mp3"
    provenance = work / "narration.json"
    text = "\n".join(item["spoken"] for item in specs)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if output.is_file() and provenance.is_file() and not force:
        try:
            if _read(provenance).get("text_sha256") == digest:
                return output
        except (OSError, ValueError):
            pass
    _run([sys.executable, "-m", "edge_tts", "--voice", "zh-CN-YunxiNeural", "--rate", "+8%", "--text", text, "--write-media", str(output)], timeout=180, error="Edge TTS Pilot 旁白生成失败")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Edge TTS Pilot 旁白生成失败：没有生成音频文件")
    _write(provenance, {"provider": "edge_tts", "voice": "zh-CN-YunxiNeural", "rate": "+8%", "text_sha256": digest, "spoken_lines": [item["spoken"] for item in specs], "generated_at": _now()})
    return output


def _adjust_region(region: list[float], zoom: float) -> list[float]:
    if zoom <= 1:
        return region
    x, y, w, h = region
    width, height = w / zoom, h / zoom
    return [max(0.0, min(1 - width, x + (w - width) / 2)), max(0.0, min(1 - height, y + (h - height) / 2)), width, height]


def _render_pilot(ep_dir: Path, variant: str, specs: list[dict[str, Any]], *, force: bool) -> dict[str, Path]:
    source, work, renders = _prepared_source(ep_dir), ep_dir / "work" / "pilots" / variant, ep_dir / "renders" / "pilots"
    output, srt, timeline_path = renders / f"pilot-{variant}.mp4", work / "captions.srt", work / "timeline.json"
    if output.is_file() and srt.is_file() and timeline_path.is_file() and not force:
        return {"video": output, "srt": srt, "timeline": timeline_path}
    work.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)
    overrides_path = ep_dir / "work" / "pilots" / "pilot-overrides.json"
    overrides = _read(overrides_path) if overrides_path.is_file() else {}
    zoom = float(overrides.get(variant, {}).get("zoom", 1.0))
    segments: list[Path] = []
    clips: list[dict[str, Any]] = []
    for index, spec in enumerate(specs):
        segment = work / f"segment-{index:02}.mp4"
        x, y, w, h = _adjust_region(list(spec["region"]), zoom)
        vf = f"crop=iw*{w:g}:ih*{h:g}:iw*{x:g}:ih*{y:g},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
        _run(["ffmpeg", "-y", "-ss", str(spec["in"]), "-i", str(source), "-t", str(spec["duration"]), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", str(segment)], timeout=180, error=f"Pilot {variant} 镜头渲染失败")
        segments.append(segment)
        clips.append({"source_start": spec["in"], "source_end": spec["in"] + spec["duration"], "target": spec["target"], "region": {"x": x, "y": y, "w": w, "h": h}, "zoom": zoom, "pan": None, "caption_safe_zone": "bottom", "minimum_mobile_readability": True})
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{part.resolve().as_posix()}'\n" for part in segments), encoding="utf-8")
    lines: list[str] = []
    for index, spec in enumerate(specs, start=1):
        lines.extend([str(index), f"{_srt_timestamp(spec['start'])} --> {_srt_timestamp(spec['start'] + spec['duration'])}", spec["caption"], ""])
    srt.write_text("\n".join(lines), encoding="utf-8")
    narration = _ensure_narration(work, specs, force=force)
    total = sum(float(item["duration"]) for item in specs)
    # apad preserves the visual duration when narration ends before the last shot.
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(narration), "-filter_complex", "[1:a]apad=pad_dur=12[a]", "-map", "0:v:0", "-map", "[a]", "-vf", _subtitles_filter(srt), "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-pix_fmt", "yuv420p", str(output)], timeout=240, error=f"Pilot {variant} 合并、字幕或旁白失败")
    _run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(output)], timeout=30, error=f"Pilot {variant} 解码验证失败")
    timeline = {"episode_id": ep_dir.name, "variant": variant, "production_type": "SCREEN_DOCUMENTARY", "total_duration": total, "real_screen_footage_ratio": 1.0, "generated_card_count": 0, "generated_motion_seconds": 0.0, "spoken_lines": [item["spoken"] for item in specs], "clips": clips, "source_sha256": _sha256(source), "generated_at": _now()}
    _write(timeline_path, timeline)
    return {"video": output, "srt": srt, "timeline": timeline_path}


def _validate_pilot_timeline(timeline: dict[str, Any]) -> None:
    rules = screen_documentary_rules()
    pilot_rules = rules.get("pilot_duration_seconds", {"min": 20, "max": 30})
    if not float(pilot_rules["min"]) <= float(timeline["total_duration"]) <= float(pilot_rules["max"]):
        raise RuntimeError(
            f"Pilot 时长必须在 {pilot_rules['min']}-{pilot_rules['max']} 秒，"
            "并由真实口播字幕驱动"
        )
    if float(timeline["real_screen_footage_ratio"]) < float(rules["real_screen_footage_ratio_min"]):
        raise RuntimeError("Pilot 真实录屏占比不足")
    if timeline["generated_card_count"] > rules["generated_card_count_max"] or timeline["generated_motion_seconds"] > rules["generated_motion_total_seconds_max"]:
        raise RuntimeError("Pilot 生成包装超出 SCREEN_DOCUMENTARY 限制")
    if not timeline["clips"] or not timeline["clips"][0].get("region"):
        raise RuntimeError("Pilot 第一帧必须是带 ROI 的真实录屏")


def render_pilots(ep_dir: Path, *, force: bool = False) -> dict[str, Any]:
    if not (ep_dir / "work" / "director" / "short-video-brief.json").is_file():
        raise RuntimeError("请先完成 story-mine 与 direct")
    result: dict[str, Any] = {"episode_id": ep_dir.name, "pilots": {}}
    for variant in PILOT_IDS:
        output = _render_pilot(ep_dir, variant, _pilot_spec(variant), force=force)
        timeline = _read(output["timeline"])
        _validate_pilot_timeline(timeline)
        video, qa_root = output["video"], ep_dir / "work" / "qa" / "pilots" / variant
        dense = extract_frames(video, [0.0, .5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], qa_root / "dense", force=force)
        uniform = extract_uniform_frames(video, qa_root / "uniform", step_seconds=1.0, force=force)
        sheets = build_contact_sheets(uniform or dense, qa_root / "contact-sheets", label=f"pilot-{variant}")
        mobile = qa_root / "mobile-preview"
        mobile.mkdir(parents=True, exist_ok=True)
        from PIL import Image
        for stamp, frame in dense.items():
            with Image.open(frame) as image:
                image.resize((360, 640)).save(mobile / f"t{stamp:05.2f}.jpg")
        result["pilots"][variant] = {"video": video.relative_to(ep_dir).as_posix(), "timeline": output["timeline"].relative_to(ep_dir).as_posix(), "srt": output["srt"].relative_to(ep_dir).as_posix(), "dense_frames": len(dense), "uniform_frames": len(uniform), "contact_sheets": sheets, "facts": "work/director/证据镜头索引.json"}
    _write(ep_dir / "work" / "qa" / "pilots" / "pilot-manifest.json", result)
    return result


def _validate_variant_review(item: dict[str, Any], variant: str) -> dict[str, Any]:
    scores = item.get("scores")
    if not isinstance(scores, dict):
        raise ValueError(f"{variant} 缺失实际看片的 numeric scores")
    normalized: dict[str, float] = {}
    for dimension in CORE_DIMENSIONS:
        value = scores.get(dimension)
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 10:
            raise ValueError(f"{variant} Reviewer 维度无效: {dimension}")
        normalized[dimension] = float(value)
    overall = scores.get("overall")
    if not isinstance(overall, (int, float)) or not 0 <= float(overall) <= 10:
        raise ValueError(f"{variant} Reviewer 缺少有效 overall")
    findings = item.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError(f"{variant} findings 必须为数组")
    return {"scores": {**normalized, "overall": float(overall)}, "findings": findings}


def _validate_reviewer_payload(raw: dict[str, Any]) -> dict[str, Any]:
    reviewer_id, reviewer_kind = raw.get("reviewer_id"), raw.get("reviewer_kind")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise ValueError("Reviewer 必须提供 reviewer_id")
    if reviewer_kind not in {"agent", "provider"}:
        raise ValueError("Reviewer 必须标记 reviewer_kind=agent 或 provider")
    reviewed_artifacts = raw.get("reviewed_artifacts", [])
    if not isinstance(reviewed_artifacts, list) or not reviewed_artifacts or not all(
        isinstance(item, str) and item.strip() for item in reviewed_artifacts
    ):
        raise ValueError("Reviewer 必须列出实际查看过的 MP4、联系表或关键帧")
    variants = raw.get("variants")
    if not isinstance(variants, dict) or set(variants) != set(PILOT_IDS):
        raise ValueError("每个独立 Reviewer 必须对 A-result/B-reversal/C-project 全部评分")
    return {"reviewer_id": reviewer_id, "reviewer_kind": reviewer_kind, "reviewed_artifacts": reviewed_artifacts, "variants": {variant: _validate_variant_review(dict(variants[variant]), variant) for variant in PILOT_IDS}}


def review_pilots(ep_dir: Path, reviewer_payloads: list[dict[str, Any]] | None = None, *, force: bool = False) -> dict[str, Any]:
    manifest = ep_dir / "work" / "qa" / "pilots" / "pilot-manifest.json"
    if not manifest.is_file():
        raise RuntimeError("请先运行 pilot 生成三个真实 Pilot")
    output_dir, existing = ep_dir / "work" / "qa" / "pilots", ep_dir / "work" / "qa" / "pilots" / "pilot-review.json"
    if existing.is_file() and not force and reviewer_payloads is None:
        return _read(existing)
    previous_round = 0
    if existing.is_file():
        try:
            previous_round = int(_read(existing).get("repair_round", 0) or 0)
        except (OSError, ValueError):
            previous_round = 0
    if reviewer_payloads is None:
        report: dict[str, Any] = {"episode_id": ep_dir.name, "decision": "BLOCKED", "winner": None, "reviewers": [], "reviews": {}, "findings": [{"repair_target": "visual-critic", "observation": "缺少两份真实看片的独立 Reviewer 评分；无 Vision Provider 时必须 fail closed。"}], "repair_round": previous_round, "generated_at": _now()}
        _write(existing, report)
        return report
    if len(reviewer_payloads) not in {1, 2}:
        raise ValueError("Pilot Gate 必须提供至少一份独立、真实看片的 Reviewer 结果")
    reviewers = [_validate_reviewer_payload(dict(item)) for item in reviewer_payloads]
    if len(reviewers) == 2 and reviewers[0]["reviewer_id"] == reviewers[1]["reviewer_id"]:
        raise ValueError("两个 Reviewer 必须为独立身份")
    for reviewer in reviewers:
        _write(output_dir / f"reviewer-{reviewer['reviewer_id']}.json", reviewer)
    reviews: dict[str, Any] = {}
    aggregate_findings: list[dict[str, Any]] = []
    for variant in PILOT_IDS:
        scores = {dimension: round(sum(reviewer["variants"][variant]["scores"][dimension] for reviewer in reviewers) / len(reviewers), 2) for dimension in (*CORE_DIMENSIONS, "overall")}
        findings = [finding for reviewer in reviewers for finding in reviewer["variants"][variant]["findings"]]
        reviews[variant] = {"scores": scores, "findings": findings, "reviewer_ids": [reviewer["reviewer_id"] for reviewer in reviewers]}
        aggregate_findings.extend({"variant": variant, **finding} for finding in findings if isinstance(finding, dict))
    passing = [variant for variant, data in reviews.items() if data["scores"]["overall"] >= 8.5 and all(data["scores"][dimension] >= 8 for dimension in CORE_DIMENSIONS)]
    winner = max(passing, key=lambda item: reviews[item]["scores"]["overall"]) if passing else None
    if winner is None and not aggregate_findings:
        aggregate_findings = [{"repair_target": "mobile-screen-director", "observation": "没有 Pilot 达到任一核心项 8 / Overall 8.5 门槛"}]
    report = {"episode_id": ep_dir.name, "decision": "PASS" if winner else "REJECT", "winner": winner, "reviewers": reviewers, "reviews": reviews, "findings": aggregate_findings, "repair_round": previous_round, "generated_at": _now()}
    _write(existing, report)
    return report


def revise_pilots(ep_dir: Path, *, force: bool = False) -> dict[str, Any]:
    """Apply only deterministic, local fixes derived from explicit findings."""
    review_path = ep_dir / "work" / "qa" / "pilots" / "pilot-review.json"
    if not review_path.is_file():
        raise RuntimeError("请先运行 pilot-review")
    review = _read(review_path)
    round_number = int(review.get("repair_round", 0)) + 1
    if round_number > MAX_REPAIR_ROUNDS:
        return {"decision": "BLOCKED", "repair_round": round_number, "reason": "Pilot 已完成两轮自动返修，禁止第三轮渲染"}
    overrides: dict[str, dict[str, float]] = {}
    for finding in review.get("findings", []):
        target = finding.get("repair_target") if isinstance(finding, dict) else None
        variant = str(finding.get("variant") or "") if isinstance(finding, dict) else ""
        if target == "mobile-screen-director":
            targets = (variant,) if variant in PILOT_IDS else PILOT_IDS
            for item in targets:
                overrides[item] = {"zoom": 1.16}
    if not overrides:
        return {"decision": "BLOCKED", "repair_round": round_number, "reason": "findings 没有可自动执行的最小 repair_target"}
    _write(ep_dir / "work" / "pilots" / "pilot-overrides.json", overrides)
    review["repair_round"] = round_number
    _write(review_path, review)
    return {"decision": "RENDER_REQUIRED", "repair_round": round_number, "overrides": overrides}


def pilot_gate_passed(ep_dir: Path) -> bool:
    path = ep_dir / "work" / "qa" / "pilots" / "pilot-review.json"
    return path.is_file() and _read(path).get("decision") == "PASS"


def assert_screen_documentary_pilot_gate(ep_dir: Path, model: Any) -> None:
    """Shared fail-closed guard for every SCREEN_DOCUMENTARY render path."""
    if getattr(model, "production_type", "STANDARD") != "SCREEN_DOCUMENTARY":
        return
    if getattr(model, "status", None) != "PILOT_APPROVED" or not pilot_gate_passed(ep_dir):
        raise RuntimeError(
            "SCREEN_DOCUMENTARY 必须先通过字幕驱动的 20-30 秒 Pilot Gate；"
            "没有匹配录屏不是阻塞条件，但没有真实看片记录不能完整渲染"
        )
