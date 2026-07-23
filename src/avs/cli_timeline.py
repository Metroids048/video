"""src/avs/cli_timeline.py — timeline / subtitles / render 子命令。

通过 register_commands(main) 注册到主 CLI。
"""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


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
            console.print(f"[yellow]⚠ 状态转换失败: {exc}[/yellow]")

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
            console.print(f"[green]✓ captions.srt 已存在（use --force 重建）[/green]")
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
            console.print(f"[yellow]⚠ 状态转换失败: {exc}[/yellow]")

        clean = result["preview_clean"]
        cap = result["preview_with_captions"]
        console.print(
            f"[green]✓ 粗剪渲染完成[/green]\n"
            f"  无字幕: {clean}\n"
            f"  含字幕: {cap}"
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
            report = run_qa(ep_dir, model.id, force=force)
        except ImportError:
            console.print("[yellow]⚠ qa 模块尚未实现（模块8），跳过[/yellow]")
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

        # 状态转换 → QA_PASSED
        try:
            model.ensure_stage("qa", "QA_PASSED")
            model.complete_stage("qa")
            model.save(ep_json)
        except Exception as exc:
            console.print(f"[yellow]⚠ 状态转换失败: {exc}[/yellow]")

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

        try:
            from avs.delivery import run_delivery
            manifest = run_delivery(ep_dir, model, force=force)
        except ImportError:
            console.print("[yellow]⚠ delivery 模块尚未实现（模块8），跳过[/yellow]")
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
            console.print(f"[yellow]⚠ 状态转换失败: {exc}[/yellow]")

        console.print(f"[green]✓ 交付包生成完成[/green]")
        sys.exit(0)

    # ── run（全流程）──────────────────────────────────────────────────
    @main_group.command("run")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="强制重建所有产物")
    def run_cmd(episode_id: str, force: bool) -> None:
        """全流程执行: timeline→subtitles→render→qa→deliver。"""
        import logging
        from avs.config import Config
        from avs.models.episode import EpisodeModel
        from avs.paths import episode_json_path

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        root = _find_project_root()
        cfg = Config(root)
        ep_dir = _get_ep_dir(cfg, episode_id)

        steps = ["timeline build", "subtitles build", "render rough"]
        for step in steps:
            console.print(f"\n[bold cyan]── {step} ──[/bold cyan]")
            force_args = ["--force"] if force else []
            # 用 subprocess 调用自身，保证 Click 命令上下文隔离
            import subprocess as _sp
            import os as _os
            env = _os.environ.copy()
            env.setdefault("PYTHONPATH", str(root / "src"))
            ret = _sp.run(
                ["python", "-m", "avs"] + step.split() + [episode_id] + force_args,
                cwd=str(root),
                env=env,
            )
            if ret.returncode != 0:
                console.print(f"[red]✗ {step} 失败（exit {ret.returncode}），中止 run[/red]")
                sys.exit(ret.returncode)

        console.print(f"\n[green]✓ 全流程完成[/green]")
        sys.exit(0)
