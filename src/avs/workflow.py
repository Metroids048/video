"""Inspect and safely resume the canonical Agent Video Studio workflow.

This module deliberately owns no persistent state.  ``episode.json`` remains the
single source of truth; the returned next action is derived from it and files that
already belong to the episode workspace.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from avs.models.episode import EpisodeModel

ActionKind = Literal["command", "agent", "human", "input", "recovery", "complete"]
CommandRunner = Callable[[tuple[str, ...], bool], int]

_REFERENCE_VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"})


@dataclass(frozen=True)
class WorkflowAction:
    """The next safe action for an episode, derived without side effects."""

    kind: ActionKind
    stage: str
    summary: str
    command: tuple[str, ...] | None = None
    required_artifacts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "stage": self.stage,
            "summary": self.summary,
            "command": list(self.command) if self.command is not None else None,
            "required_artifacts": list(self.required_artifacts),
        }


@dataclass(frozen=True)
class WorkflowRunResult:
    """Commands executed by a resume operation and the resulting stopping point."""

    action: WorkflowAction
    executed_commands: list[tuple[str, ...]]
    controlled_pause: bool = False
    last_exit_code: int = 0


class WorkflowExecutionError(RuntimeError):
    """A supposedly deterministic command did not advance the workflow."""


def _has_reference_video(ep_dir: Path) -> bool:
    reference_dir = ep_dir / "input" / "reference"
    return reference_dir.is_dir() and any(
        path.is_file() and path.suffix.lower() in _REFERENCE_VIDEO_SUFFIXES
        for path in reference_dir.rglob("*")
    )


def _content_workspace_initialized(ep_dir: Path) -> bool:
    return (ep_dir / "work" / "content" / "brief.md").is_file()


_RETRY_COMMANDS: dict[str, tuple[str, ...]] = {
    "ingest": ("ingest",),
    "analyze": ("analyze",),
    "preview": ("preview",),
    "visual-review": ("visual-review",),
    "final-render": ("final-render",),
    "qa": ("qa",),
    "delivery": ("deliver",),
    "export": ("export",),
}
_VISION_RECOVERY_CODES = frozenset({"VISION_PROVIDER_UNAVAILABLE", "VISION_REVIEW_FAILED"})


def _visual_review_needs_human(ep_dir: Path) -> bool:
    report_path = ep_dir / "work" / "qa" / "visual-review.json"
    if not report_path.is_file():
        return False
    try:
        import json
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    failures = report.get("failures", [])
    codes = {
        str(item.get("failure_code"))
        for item in failures
        if isinstance(item, dict) and item.get("failure_code")
    }
    return bool(codes - _VISION_RECOVERY_CODES)


def _blocked_action(ep_dir: Path, model: EpisodeModel) -> WorkflowAction:
    stage = model.blocked_stage
    if stage == "ingest" or model.status == "WAITING_FOR_INPUT":
        return WorkflowAction(
            kind="input",
            stage="ingest",
            command=("ingest",),
            summary=model.last_error or "补充 input/ 中缺失的素材或文本后重新执行 ingest。",
        )
    if stage == "visual-review" and _visual_review_needs_human(ep_dir):
        return WorkflowAction(
            kind="human",
            stage="visual-review",
            summary="视觉审核发现内容或画面缺陷；修复上游后执行 episode reset --to CONTENT_READY --force。",
        )
    command = _RETRY_COMMANDS.get(stage or "")
    if command is not None:
        return WorkflowAction(
            kind="recovery",
            stage=stage or "recovery",
            command=command,
            summary=model.last_error or f"修复条件后重新执行 {stage}。",
        )
    return WorkflowAction(
        kind="human",
        stage="recovery",
        summary=model.last_error or "Active workflow 已阻塞，需要人工修复。",
    )


def action_for_episode(ep_dir: Path, model: EpisodeModel) -> WorkflowAction:
    """Return the next action without mutating state or creating files."""
    status = model.status
    active_manifest = ep_dir / "work" / "input-manifest.json"
    stages = set(model.completed_stages)

    if status == "WAITING_FOR_INPUT":
        return _blocked_action(ep_dir, model)
    if status == "FAILED":
        return WorkflowAction(
            kind="recovery",
            stage="recovery",
            summary="先阅读 episode.json 的 last_error，修复原因后选择允许的 reset 目标重试。",
        )
    if model.blocked:
        return _blocked_action(ep_dir, model)

    # The multimodal manifest switches publishable Episodes onto the only
    # active delivery path. Legacy actions below remain internal compatibility.
    if model.publishable and active_manifest.is_file() and status != "CREATED":
        if "analyze" not in stages:
            return WorkflowAction("command", "analyze", "理解全部输入并生成素材语义索引。", ("analyze",))
        if "plan" not in stages:
            return WorkflowAction(
                "human", "hook-review",
                "从 result/conflict/pain 三个 Hook 中确认一个，再执行 avs plan --hook。",
                required_artifacts=("work/analysis/asset-intelligence.json",),
            )
        if "preview" not in stages:
            return WorkflowAction("command", "preview", "生成原子镜头时间线和低清预览。", ("preview",))
        if "visual-review" not in stages:
            return WorkflowAction("command", "visual-review", "执行视觉语义审核。", ("visual-review",))
        if "final-render" not in stages:
            return WorkflowAction("command", "final-render", "渲染通过审核的最终视频。", ("final-render",))
        if "qa" not in stages:
            return WorkflowAction("command", "qa", "执行技术与发布质量 Gate。", ("qa",))
        if "approve" not in stages:
            return WorkflowAction("human", "approve", "人工完整播放后批准最终视频哈希。", ("approve",))
        if "delivery" not in stages:
            return WorkflowAction("command", "deliver", "生成完整交付包。", ("deliver",))
        if "export" not in stages:
            return WorkflowAction("command", "export", "导出可复验 Episode 包。", ("export",))
        return WorkflowAction("complete", "complete", "Active workflow 已完成并导出。")

    if status == "CREATED":
        return WorkflowAction(
            kind="command",
            stage="ingest",
            command=("ingest",),
            summary="清点 input/ 并创建工作副本与素材清单。",
        )
    if status == "INGESTED" and _has_reference_video(ep_dir):
        return WorkflowAction(
            kind="command",
            stage="reference",
            command=("reference", "analyze"),
            summary="分析本地参考视频，提取结构配方；不下载第三方平台视频。",
        )
    if status in {"INGESTED", "REFERENCE_READY"} and not _content_workspace_initialized(ep_dir):
        return WorkflowAction(
            kind="command",
            stage="content_workspace",
            command=("content", "init"),
            summary="创建内容简报模板和 Agent 内容工作区。",
        )
    if status in {"INGESTED", "REFERENCE_READY"}:
        return WorkflowAction(
            kind="agent",
            stage="content",
            summary="由内容 Skill 生成简报、脚本、分镜和缺口清单，再人工审核。",
            required_artifacts=(
                "work/content/brief.md",
                "work/content/script.json",
                "work/content/storyboard.json",
                "work/content/missing-assets.md",
            ),
        )
    if status == "CONTENT_READY":
        return WorkflowAction(
            kind="human",
            stage="assets",
            command=("assets", "approve"),
            summary="人工确认素材、缺口和版式后，才允许进入渲染。",
            required_artifacts=("work/asset-manifest.json", "work/content/missing-assets.md"),
        )
    if status == "ASSETS_READY":
        return WorkflowAction(
            kind="command",
            stage="render_and_delivery",
            command=("run",),
            summary="运行时间线、字幕、FFmpeg、HyperFrames、QA 和可编辑交付包。",
        )
    if status == "WAITING_FOR_REVIEW":
        return WorkflowAction(
            kind="human",
            stage="review",
            summary="完成所需内容或成片复核，再使用对应 approve/qa 命令推进。",
        )
    if status == "DELIVERY_READY":
        return WorkflowAction(
            kind="complete",
            stage="complete",
            summary="可编辑交付包已就绪，等待人工最终修改和发布。",
        )
    return WorkflowAction(
        kind="human",
        stage="review",
        summary=f"状态 {status} 需要人工复核后再继续。",
    )


def run_automatic_steps(
    ep_dir: Path,
    *,
    command_runner: CommandRunner,
    force: bool = False,
) -> WorkflowRunResult:
    """Run canonical deterministic commands until an editorial gate is reached."""
    ep_json = ep_dir / "episode.json"
    executed: list[tuple[str, ...]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    for _ in range(16):
        model = EpisodeModel.load(ep_json)
        if model.migrate_legacy_block():
            model.save(ep_json)
        action = action_for_episode(ep_dir, model)
        if action.kind not in {"command", "input", "recovery"} or action.command is None:
            return WorkflowRunResult(action=action, executed_commands=executed)

        fingerprint = (model.status, action.command)
        if fingerprint in seen:
            raise WorkflowExecutionError(
                f"命令 {' '.join(action.command)} 没有推进 Episode，请检查其产物或使用 --force。"
            )
        seen.add(fingerprint)
        before = (model.status, tuple(model.completed_stages), model.blocked, model.blocked_stage)
        exit_code = command_runner(
            action.command,
            force or (model.blocked and action.kind == "recovery"),
        )
        executed.append(action.command)

        current = EpisodeModel.load(ep_json)
        if current.migrate_legacy_block():
            current.save(ep_json)
        if exit_code == 2:
            return WorkflowRunResult(
                action=action_for_episode(ep_dir, current),
                executed_commands=executed,
                controlled_pause=True,
                last_exit_code=2,
            )
        if exit_code != 0:
            raise WorkflowExecutionError(
                f"命令 {' '.join(action.command)} 失败（exit {exit_code}）"
            )

        after = (current.status, tuple(current.completed_stages), current.blocked, current.blocked_stage)
        next_action = action_for_episode(ep_dir, current)
        if before == after and action == next_action:
            raise WorkflowExecutionError(
                f"命令 {' '.join(action.command)} 没有推进 Episode，请检查其产物或使用 --force。"
            )

    raise WorkflowExecutionError("自动步骤超过安全上限，请检查 Episode 状态和产物。")
