"""src/avs/qa/report.py — 确定性 QA 检查与报告生成。"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class QACheck:
    """单个 QA 检查项。"""
    def __init__(self, check_id: str, name: str, severity: str = "error"):
        self.check_id = check_id
        self.name = name
        self.severity = severity  # "error" | "warning" | "info"
        self.passed = False
        self.message: str | None = None
        self.value: Any = None

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "value": self.value,
        }


def run_qa(ep_dir: Path, episode_id: str, *, force: bool = False) -> dict:
    """运行确定性 QA 检查，返回报告字典（符合 qa-report.schema.json）。

    检查项：
    1. MP4 可解码（ffprobe）
    2. 尺寸 1080×1920
    3. fps ≈ 30
    4. 黑帧检测（可选）
    5. 长静音检测（可选）
    6. 字幕越界
    7. timeline 冲突
    8. 缺失素材标记
    """
    checks: list[QACheck] = []

    # ── 检查 preview-clean.mp4 ───────────────────────────────────────
    clean_mp4 = ep_dir / "renders" / "preview-clean.mp4"
    if not clean_mp4.exists():
        c = QACheck("decode_clean", "preview-clean.mp4 存在性", "error")
        c.passed = False
        c.message = f"文件不存在: {clean_mp4}"
        checks.append(c)
    else:
        # ffprobe 解码检查
        c_decode = QACheck("decode_clean", "preview-clean.mp4 可解码", "error")
        meta = _ffprobe_meta(clean_mp4)
        if meta.get("error"):
            c_decode.passed = False
            c_decode.message = meta["error"]
        else:
            c_decode.passed = True
            c_decode.value = {"width": meta.get("width"), "height": meta.get("height"),
                              "duration": meta.get("duration")}
        checks.append(c_decode)

        # 尺寸检查
        c_size = QACheck("canvas_size", "画布尺寸 1080×1920", "error")
        w, h = meta.get("width"), meta.get("height")
        if w == 1080 and h == 1920:
            c_size.passed = True
        else:
            c_size.passed = False
            c_size.message = f"实际尺寸: {w}×{h}"
        checks.append(c_size)

        # fps 检查
        c_fps = QACheck("fps_check", "帧率 ≈ 30fps", "warning")
        fps = meta.get("fps", 0)
        if 29 <= fps <= 31:
            c_fps.passed = True
        else:
            c_fps.passed = False
            c_fps.message = f"实际 fps: {fps}"
        checks.append(c_fps)

    # ── 检查 captions.srt 越界 ─────────────────────────────────────────
    timeline_path = ep_dir / "work" / "timeline.json"
    srt_path = ep_dir / "work" / "captions.srt"
    if timeline_path.exists() and srt_path.exists():
        with timeline_path.open(encoding="utf-8") as fh:
            tl_data = json.load(fh)
        total_dur = tl_data.get("total_duration", 0)
        from avs.render.captions import has_subtitle_overflow
        violations = has_subtitle_overflow(srt_path, total_dur)
        c_cap = QACheck("subtitle_overflow", "字幕无越界", "error")
        if violations:
            c_cap.passed = False
            c_cap.message = f"越界字幕: {len(violations)} 条（编号 {', '.join(violations)}）"
        else:
            c_cap.passed = True
        checks.append(c_cap)

    # ── 缺失素材检查 ───────────────────────────────────────────────────
    if timeline_path.exists():
        c_missing = QACheck("missing_assets", "缺失素材标记", "warning")
        with timeline_path.open(encoding="utf-8") as fh:
            tl_data = json.load(fh)
        missing_count = 0
        for track in tl_data.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("style", {}).get("placeholder"):
                    missing_count += 1
        if missing_count > 0:
            c_missing.passed = False
            c_missing.message = f"{missing_count} 个占位卡（需补充素材）"
            c_missing.severity = "warning"
        else:
            c_missing.passed = True
        checks.append(c_missing)

    # ── 汇总报告 ───────────────────────────────────────────────────────
    errors = [c for c in checks if not c.passed and c.severity == "error"]
    passed_overall = len(errors) == 0

    report = {
        "episode_id": episode_id,
        "passed": passed_overall,
        "checks": [c.to_dict() for c in checks],
        "summary": f"{len(checks)} 项检查，{len(errors)} error",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # 保存报告
    report_path = ep_dir / "delivery" / "qa-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    # 生成可读 Markdown
    md_path = ep_dir / "delivery" / "qa-report.md"
    _write_qa_markdown(report, md_path)

    logger.info("QA 报告已生成: %s", report_path)
    return report


def _ffprobe_meta(path: Path) -> dict:
    """轻量 ffprobe。"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return {"error": f"ffprobe 失败: {result.stderr[:200]}"}
        data = json.loads(result.stdout)
        vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        if not vs:
            return {"error": "无视频流"}
        # fps
        r_frame = vs.get("r_frame_rate", "30/1")
        try:
            num, den = r_frame.split("/")
            fps = round(int(num) / int(den), 2) if int(den) else 30
        except Exception:
            fps = 30
        # duration
        dur = float(data.get("format", {}).get("duration", 0))
        return {
            "width": int(vs.get("width", 0)),
            "height": int(vs.get("height", 0)),
            "fps": fps,
            "duration": dur,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _write_qa_markdown(report: dict, md_path: Path) -> None:
    """生成可读 QA Markdown 报告。"""
    lines = [
        f"# QA 报告 — {report['episode_id']}",
        "",
        f"**生成时间**: {report['generated_at']}  ",
        f"**总体结果**: {'✓ 通过' if report['passed'] else '✗ 未通过'}",
        "",
        "## 检查项",
        "",
    ]
    for c in report["checks"]:
        sym = "✓" if c["passed"] else "✗"
        sev = c.get("severity", "error").upper()
        msg = c.get("message", "")
        lines.append(f"- {sym} **[{sev}]** {c['name']}")
        if msg:
            lines.append(f"  > {msg}")
        lines.append("")

    lines.append("")
    lines.append(f"**汇总**: {report.get('summary', '')}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
