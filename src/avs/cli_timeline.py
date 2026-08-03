"""src/avs/cli_timeline.py — timeline / subtitles / render 子命令。

通过 register_commands(main) 注册到主 CLI。
"""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()

RUN_STEPS = (
    "timeline build",
    "subtitles build",
    "render rough",
    "motion render",
    "qa",
    "deliver",
)


def _find_project_root() -> Path:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "AGENTS.md").exists():
            return candidate
    return cwd


def _get_ep_dir(cfg, episode_id: str) -> Path:
    from avs.paths import PathError, find_episode_dir
    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)
    return ep_dir


def register_commands(main_group: click.Group) -> None:
    """将 timeline / subtitles / render 子命令注册到 main_group。"""

    # ── timeline ──────────────────────────────────────────────────────
    @main_group.group()
    def timeline() -> None:
        """时间线构建与校验命令。"""

    @timeline.command("build")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重建（忽略已有 timeline.json）")
    def timeline_build(episode_id: str, force: bool) -> None:
        """从 storyboard + asset-manifest 构建 timeline.json，状态 → TIMELINE_READY。"""
        import logging
        from avs.config import Config
        from avs.models.episode import EpisodeModel
        from avs.paths import episode_json_path
        from avs.timeline import build_timeline
        from avs.timeline.csv_export import export_csv

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        ep_json = episode_json_path(ep_dir)

        try:
            model = EpisodeModel.load(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
            sys.exit(1)

        try:
            tl = build_timeline(ep_dir, model.id, force=force)
        except Exception as exc:
            console.print(f"[red]✗ timeline build 失败: {exc}[/red]")
            model.fail(str(exc))
            model.save(ep_json)
            sys.exit(1)

        # 导出 CSV
        try:
            export_csv(tl, ep_dir / "work" / "timeline.csv")
        except Exception as exc:
            console.print(f"[yellow]⚠ CSV 导出失败: {exc}[/yellow]")

        # 状态转换
        try:
            model.ensure_stage("timeline", "TIMELINE_READY")
            model.complete_stage("timeline")
            model.save(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
            sys.exit(1)

        total_dur = tl.total_duration or tl.compute_duration()
        console.print(
            f"[green]✓ timeline build 完成[/green]\n"
            f"  总时长: {total_dur:.1f}s  "
            f"轨道数: {len(tl.tracks)}  "
            f"Clips: {sum(len(t.clips) for t in tl.tracks)}"
        )
        sys.exit(0)

    @timeline.command("validate")
    @click.argument("episode_id")
    def timeline_validate(episode_id: str) -> None:
        """校验 timeline.json（Schema + 语义）。"""
        from avs.config import Config
        from avs.timeline.validate import validate_timeline, TimelineValidationError

        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        timeline_path = ep_dir / "work" / "timeline.json"

        try:
            issues = validate_timeline(timeline_path)
        except TimelineValidationError as exc:
            console.print(f"[red]✗ 校验失败: {exc}[/red]")
            sys.exit(1)
        except Exception as exc:
            console.print(f"[red]✗ {exc}[/red]")
            sys.exit(1)

        errors = [i for i in issues if i.level == "error"]
        warnings = [i for i in issues if i.level == "warning"]

        for i in issues:
            color = "red" if i.level == "error" else "yellow"
            sym = "✗" if i.level == "error" else "⚠"
            console.print(f"  [{color}]{sym} [{i.level.upper()}] {i.message}[/{color}]")

        if errors:
            console.print(f"[red]✗ timeline.json 校验失败（{len(errors)} error，{len(warnings)} warning）[/red]")
            sys.exit(1)

        console.print(f"[green]✓ timeline.json 校验通过[/green]  warning: {len(warnings)}")
        sys.exit(0)

    # ── subtitles ─────────────────────────────────────────────────────
    @main_group.group()
    def subtitles() -> None:
        """字幕生成命令。"""

    @subtitles.command("build")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重建 SRT")
    def subtitles_build(episode_id: str, force: bool) -> None:
        """从 timeline caption 轨道生成 captions.srt。"""
        from avs.config import Config
        from avs.timeline.models import Timeline
        from avs.render.captions import build_srt

        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        timeline_path = ep_dir / "work" / "timeline.json"
        srt_path = ep_dir / "work" / "captions.srt"

        if not timeline_path.exists():
            console.print("[red]✗ timeline.json 不存在，请先运行 avs timeline build[/red]")
            sys.exit(1)

        if srt_path.exists() and not force:
            console.print("[green]✓ captions.srt 已存在（use --force 重建）[/green]")
            sys.exit(0)

        try:
            tl = Timeline.load(timeline_path)
            count = build_srt(tl, srt_path)
        except Exception as exc:
            console.print(f"[red]✗ subtitles build 失败: {exc}[/red]")
            sys.exit(1)

        # 同步到 delivery/
        delivery_srt = ep_dir / "delivery" / "captions.srt"
        delivery_srt.parent.mkdir(parents=True, exist_ok=True)
        try:
            import shutil
            shutil.copy2(str(srt_path), str(delivery_srt))
        except Exception:
            pass

        console.print(f"[green]✓ captions.srt 生成完成[/green]  字幕条数: {count}")
        sys.exit(0)

    # ── render ────────────────────────────────────────────────────────
    @main_group.group()
    def render() -> None:
        """渲染命令。"""

    @render.command("rough")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重新渲染")
    def render_rough(episode_id: str, force: bool) -> None:
        """FFmpeg 粗剪渲染，输出 preview-clean.mp4 + preview-with-captions.mp4。状态 → ROUGH_CUT_READY。"""
        import logging
        from avs.config import Config
        from avs.models.episode import EpisodeModel
        from avs.paths import episode_json_path
        from avs.timeline.models import Timeline
        from avs.render import render_rough_cut
        from avs.render.ffmpeg import RenderError

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        ep_json = episode_json_path(ep_dir)

        timeline_path = ep_dir / "work" / "timeline.json"
        if not timeline_path.exists():
            console.print("[red]✗ timeline.json 不存在，请先运行 avs timeline build[/red]")
            sys.exit(1)

        try:
            model = EpisodeModel.load(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
            sys.exit(1)

        try:
            tl = Timeline.load(timeline_path)
        except Exception as exc:
            console.print(f"[red]✗ 加载 timeline.json 失败: {exc}[/red]")
            sys.exit(1)

        try:
            result = render_rough_cut(ep_dir, tl, force=force)
        except RenderError as exc:
            console.print(f"[red]✗ 渲染失败: {exc}[/red]")
            model.fail(str(exc))
            model.save(ep_json)
            sys.exit(1)
        except Exception as exc:
            console.print(f"[red]✗ 渲染异常: {exc}[/red]")
            model.fail(str(exc))
            model.save(ep_json)
            sys.exit(1)

        # 状态转换 → ROUGH_CUT_READY
        try:
            model.ensure_stage("rough_cut", "ROUGH_CUT_READY")
            model.complete_stage("rough_cut")
            model.save(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
            sys.exit(1)

        clean = result["preview_clean"]
        cap = result["preview_with_captions"]
        console.print(
            f"[green]✓ 粗剪渲染完成[/green]\n"
            f"  无字幕: {clean}\n"
            f"  含字幕: {cap}"
        )
        sys.exit(0)

    # ── motion graphics ────────────────────────────────────────────────
    @main_group.group()
    def motion() -> None:
        """HyperFrames 动效渲染与 FFmpeg 降级合成。"""

    @motion.command("render")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重新渲染动效和合成视频")
    def motion_render(episode_id: str, force: bool) -> None:
        """从 timeline graphic 轨渲染动效；不修改 Episode 状态。"""
        from avs.config import Config
        from avs.hyperframes import render_motion_graphics
        from avs.models.episode import EpisodeModel
        from avs.paths import episode_json_path
        from avs.timeline.models import Timeline

        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        try:
            model = EpisodeModel.load(episode_json_path(ep_dir))
            if model.status not in {"ROUGH_CUT_READY", "QA_PASSED", "DELIVERY_READY"}:
                raise ValueError(
                    f"当前状态 {model.status}，请先完成 FFmpeg 基础粗剪",
                )
            timeline_data = Timeline.load(ep_dir / "work" / "timeline.json")
            result = render_motion_graphics(
                root, ep_dir, timeline_data, force=force,
            )
        except Exception as exc:
            console.print(f"[red]✗ motion render 失败: {exc}[/red]")
            sys.exit(1)

        for warning in result.warnings:
            console.print(f"[yellow]⚠ {warning}[/yellow]")
        console.print(
            "[green]✓ 动效处理完成[/green]\n"
            f"  HyperFrames: {len(result.rendered)}  "
            f"FFmpeg 降级: {len(result.fallbacks)}\n"
            f"  合成视频: {result.output_path or '无 graphic clip'}\n"
            f"  Manifest: {result.manifest_path}"
        )
        sys.exit(0)

    # ── qa ────────────────────────────────────────────────────────────
    @main_group.command("qa")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重新 QA")
    def qa_cmd(episode_id: str, force: bool) -> None:
        """运行 QA 检查，生成 qa-report.md。状态 → QA_PASSED（无 error 时）。"""
        import logging
        from avs.config import Config
        from avs.models.episode import EpisodeModel
        from avs.paths import episode_json_path

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        ep_json = episode_json_path(ep_dir)

        try:
            model = EpisodeModel.load(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
            sys.exit(1)

        try:
            from avs.qa import run_qa
            active_path = "final-render" in model.completed_stages
            report = run_qa(
                ep_dir,
                model.id,
                publishable=model.publishable,
                force=force,
                require_human_approval=not active_path,
            )
        except ImportError as exc:
            console.print(f"[red]✗ QA 核心模块加载失败: {exc}[/red]")
            sys.exit(1)
        except Exception as exc:
            console.print(f"[red]✗ QA 失败: {exc}[/red]")
            sys.exit(1)

        errors = [c for c in report.get("checks", []) if not c["passed"] and c.get("severity") == "error"]
        warnings = [c for c in report.get("checks", []) if not c["passed"] and c.get("severity") == "warning"]

        console.print(f"\n[bold]QA 报告 — {episode_id}[/bold]")
        for c in report.get("checks", []):
            if not c["passed"]:
                color = "red" if c.get("severity") == "error" else "yellow"
                console.print(f"  [{color}]✗ [{c.get('severity','?').upper()}] {c['name']}: {c.get('message','')}[/{color}]")
            else:
                console.print(f"  [green]✓ {c['name']}[/green]")

        if errors:
            console.print(f"\n[red]✗ QA 未通过（{len(errors)} error，{len(warnings)} warning）[/red]")
            sys.exit(1)

        # Check three-layer gate status
        technical_passed = report.get("technical_passed", False)
        publishability_passed = report.get("publishability_passed", True)
        human_approved = report.get("human_approved", False)
        blocking_reasons = report.get("blocking_reasons", [])

        if not technical_passed:
            console.print("\n[red]✗ 技术检查失败[/red]")
            sys.exit(1)

        if model.publishable and (not publishability_passed or (not human_approved and "final-render" not in model.completed_stages)):
            console.print("\n[yellow]⚠ 技术检查通过，但尚未满足发布条件：[/yellow]")
            for reason in blocking_reasons:
                console.print(f"  [yellow]- {reason}[/yellow]")

            if not human_approved and "final-render" not in model.completed_stages:
                console.print("\n[yellow]状态将转为 WAITING_FOR_REVIEW，等待人工视觉批准[/yellow]")
                model.transition("WAITING_FOR_REVIEW")
                model.save(ep_json)
                sys.exit(2)  # Exit code 2: waiting for human approval
            else:
                console.print("\n[red]✗ 发布质量检查未通过[/red]")
                sys.exit(1)

        # 状态转换 → QA_PASSED
        try:
            model.ensure_stage("qa", "QA_PASSED")
            model.complete_stage("qa")
            model.save(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
            sys.exit(1)

        console.print(f"[green]✓ QA 通过[/green]  warning: {len(warnings)}")
        sys.exit(0)

    # ── deliver ───────────────────────────────────────────────────────
    @main_group.command("deliver")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重建交付包")
    def deliver_cmd(episode_id: str, force: bool) -> None:
        """生成可编辑交付包，状态 → DELIVERY_READY。"""
        import logging
        from avs.config import Config
        from avs.models.episode import EpisodeModel
        from avs.paths import episode_json_path

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)
        ep_json = episode_json_path(ep_dir)

        try:
            model = EpisodeModel.load(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
            sys.exit(1)

        if "final-render" in model.completed_stages:
            if "qa" not in model.completed_stages or "approve" not in model.completed_stages:
                console.print("[red]✗ Active Episode 必须先通过 qa 并完成人工 approve[/red]")
                sys.exit(1)
        elif model.status not in {"QA_PASSED", "DELIVERY_READY"}:
            console.print(f"[red]✗ 当前状态 {model.status}，请先运行 avs qa 并通过[/red]")
            sys.exit(1)

        try:
            from avs.delivery import run_delivery
            run_delivery(ep_dir, model, force=force)
        except ImportError as exc:
            console.print(f"[red]✗ delivery 核心模块加载失败: {exc}[/red]")
            sys.exit(1)
        except Exception as exc:
            console.print(f"[red]✗ deliver 失败: {exc}[/red]")
            sys.exit(1)

        # 状态转换 → DELIVERY_READY
        try:
            model.ensure_stage("delivery", "DELIVERY_READY")
            model.complete_stage("delivery")
            model.save(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
            sys.exit(1)

        console.print("[green]✓ 交付包生成完成[/green]")
        sys.exit(0)

    # ── run（全流程）──────────────────────────────────────────────────
    @main_group.command("run")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重建所有产物")
    def run_cmd(episode_id: str, force: bool) -> None:
        """Resume the canonical workflow until the next human/Agent gate."""
        import logging
        from avs.config import Config

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        root = _find_project_root()
        cfg = Config(root)
        _get_ep_dir(cfg, episode_id)

        import subprocess as _sp
        import os as _os
        env = _os.environ.copy()
        env.setdefault("PYTHONPATH", str(root / "src"))
        args = [sys.executable, "-m", "avs", "workflow", "resume", episode_id]
        if force:
            args.append("--force")
        result = _sp.run(args, cwd=str(root), env=env)
        if result.returncode != 0:
            console.print(f"[red]✗ Active workflow 停止（exit {result.returncode}）[/red]")
        sys.exit(result.returncode)
