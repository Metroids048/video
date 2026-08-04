"""CLI commands for the active multimodal production path."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import click
from rich.console import Console

console = Console()


def _root() -> Path:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    return cwd


def _episode(episode_id: str):
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import episode_json_path, find_episode_dir
    ep_dir = find_episode_dir(Config(_root()).episodes_root, episode_id)
    if ep_dir is None:
        raise click.ClickException(f"Episode {episode_id!r} 不存在")
    return ep_dir, EpisodeModel.load(episode_json_path(ep_dir))


def register_commands(main_group: click.Group) -> None:
    @main_group.command("analyze")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True)
    def analyze_cmd(episode_id: str, force: bool) -> None:
        """理解输入素材；没有真实 Provider 时明确阻塞。"""
        from avs.active import active_analyze
        try:
            ep_dir, model = _episode(episode_id)
            result = active_analyze(ep_dir, model, force=force)
        except Exception as exc:
            console.print(f"[red]✗ analyze 阻塞: {exc}[/red]")
            raise click.exceptions.Exit(2)
        console.print(json.dumps({"blocked": result["asset_intelligence"].get("blocked"), "provider": result["asset_intelligence"].get("provider")}, ensure_ascii=False))
        if result["asset_intelligence"].get("blocked"):
            raise click.exceptions.Exit(2)

    @main_group.command("plan")
    @click.argument("episode_id")
    @click.option("--platform", type=click.Choice(["douyin", "xiaohongshu"]), default="douyin")
    @click.option("--hook", "hook_variant", type=click.Choice(["result", "conflict", "pain"]), default="conflict")
    @click.option("--pattern", "pattern_ids", multiple=True)
    def plan_cmd(episode_id: str, platform: str, hook_variant: str, pattern_ids: tuple[str, ...]) -> None:
        """生成 Brief、Script、Evidence Map 和 Shot Plan。"""
        from avs.active import active_plan
        try:
            ep_dir, model = _episode(episode_id)
            result = active_plan(ep_dir, model, platform=platform, hook_variant=hook_variant, pattern_ids=list(pattern_ids) or None)
        except Exception as exc:
            console.print(f"[red]✗ plan 阻塞: {exc}[/red]")
            raise click.exceptions.Exit(2)
        console.print(f"[green]✓ plan 完成[/green]  segments={len(result['script'].get('segments', []))} shots={len(result['shot_plan'].get('shots', []))}")

    @main_group.command("preview")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True)
    def preview_cmd(episode_id: str, force: bool) -> None:
        """构建低清预览时间线。"""
        from avs.active import active_preview
        try:
            ep_dir, model = _episode(episode_id)
            timeline = active_preview(ep_dir, model, force=force)
        except Exception as exc:
            console.print(f"[red]✗ preview 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(f"[green]✓ preview 完成[/green]  duration={timeline.total_duration}s")

    @main_group.command("visual-review")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True)
    def visual_review_cmd(episode_id: str, force: bool) -> None:
        """对预览执行视觉语义审核。"""
        from avs.qa.visual_reviewer import review_video
        try:
            ep_dir, model = _episode(episode_id)
            script = json.loads((ep_dir / "work/content/script.json").read_text(encoding="utf-8"))
            evidence = json.loads((ep_dir / "work/content/evidence-map.json").read_text(encoding="utf-8"))
            shot_plan = json.loads((ep_dir / "work/content/shot-plan.json").read_text(encoding="utf-8"))
            intelligence = json.loads((ep_dir / "work/analysis/asset-intelligence.json").read_text(encoding="utf-8"))
            selection = json.loads((ep_dir / "work/content/reference-selection.json").read_text(encoding="utf-8"))
            retry_force = force or model.blocked_stage == "visual-review"
            report = review_video(
                ep_dir, script=script, evidence_map=evidence, shot_plan=shot_plan,
                intelligence=intelligence, selection=selection, force=retry_force,
            )
            if not report["passed"]:
                model.block("视觉审核未通过或被 Provider 阻塞", stage="visual-review")
                model.save(ep_dir / "episode.json")
            else:
                model.clear_block(stage="visual-review")
                model.complete_stage("visual-review")
                model.save(ep_dir / "episode.json")
        except Exception as exc:
            console.print(f"[red]✗ visual-review 失败: {exc}[/red]")
            raise click.exceptions.Exit(2)
        console.print(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["passed"]:
            raise click.exceptions.Exit(2)

    @main_group.command("final-render")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True)
    def final_render_cmd(episode_id: str, force: bool) -> None:
        """确定性 FFmpeg 最终渲染。"""
        from avs.active import active_final_render
        try:
            ep_dir, model = _episode(episode_id)
            result = active_final_render(ep_dir, model, force=force)
        except Exception as exc:
            console.print(f"[red]✗ final-render 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(f"[green]✓ final-render 完成[/green]  {result}")

    @main_group.command("approve")
    @click.argument("episode_id")
    @click.option("--reviewer", default="human", show_default=True)
    def approve_cmd(episode_id: str, reviewer: str) -> None:
        """Record human visual approval bound to the current video hash."""
        from avs.qa.approval import create_approval, save_approval
        try:
            ep_dir, model = _episode(episode_id)
            video = ep_dir / "renders" / "final-with-captions.mp4"
            if not video.is_file():
                video = ep_dir / "renders" / "preview-with-motion.mp4"
            if not video.is_file():
                video = ep_dir / "renders" / "preview-with-captions.mp4"
            approval = create_approval(ep_dir, model.id, reviewer, video)
            save_approval(ep_dir, approval)
            model.complete_stage("approve")
            model.save(ep_dir / "episode.json")
        except Exception as exc:
            console.print(f"[red]✗ approve 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(f"[green]✓ 已批准[/green]  sha256={approval['video_sha256']}")

    @main_group.command("export")
    @click.argument("episode_id")
    def export_cmd(episode_id: str) -> None:
        """Export a self-contained re-verification archive."""
        try:
            ep_dir, model = _episode(episode_id)
            if "delivery" not in model.completed_stages:
                raise RuntimeError("请先通过 qa、approve 并运行 deliver")
            export_dir = ep_dir / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            archive = shutil.make_archive(str(export_dir / model.id), "zip", root_dir=ep_dir / "delivery")
            model.complete_stage("export")
            model.save(ep_dir / "episode.json")
        except Exception as exc:
            console.print(f"[red]✗ export 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(f"[green]✓ export 完成[/green]  {archive}")
