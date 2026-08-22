"""Agent Video Studio — 统一 CLI 入口。

模块1实现 `doctor`；模块2扩展 `episode` 子命令。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from avs.cli_timeline import register_commands as _reg_timeline
from avs.cli_workflow import register_commands as _reg_workflow
from avs.cli_active import register_commands as _reg_active
from avs.cli_research import register_commands as _reg_research

console = Console()


def _find_project_root() -> Path:
    """从当前目录向上查找项目根（包含 AGENTS.md 的目录）。"""
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "AGENTS.md").exists():
            return candidate
    return cwd


@click.group()
@click.version_option(version="1.0.0", prog_name="avs")
def main() -> None:
    """Agent Video Studio — 通用短视频粗剪生产工具。"""


# ── doctor ────────────────────────────────────────────────────────────
@main.command()
@click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出结果")
def doctor(as_json: bool) -> None:
    """诊断开发环境，检查所有必需和可选工具。"""
    from avs.doctor import run_doctor

    root = _find_project_root()
    report = run_doctor(root)

    if as_json:
        data = [
            {
                "name": r.name,
                "required": r.required,
                "passed": r.passed,
                "version": r.version,
                "message": r.message,
                "status": r.status_label,
            }
            for r in report.results
        ]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        sys.exit(0 if report.all_required_passed else 1)

    table = Table(title="AVS Doctor Report", show_header=True, header_style="bold")
    table.add_column("检查项", style="bold")
    table.add_column("状态", justify="center", width=8)
    table.add_column("版本")
    table.add_column("信息")

    status_style = {"OK": "green", "WARN": "yellow", "FAIL": "red bold"}

    for r in report.results:
        label = r.status_label
        style = status_style.get(label, "white")
        table.add_row(
            r.name,
            f"[{style}]{label}[/{style}]",
            r.version or "-",
            r.message or "",
        )

    console.print(table)

    if report.all_required_passed:
        console.print("\n[green]✓ 所有必需项通过，环境就绪。[/green]")
        sys.exit(0)
    else:
        failed = [r.name for r in report.results if r.required and not r.passed]
        console.print(
            f"\n[red]✗ 以下必需项未通过：{', '.join(failed)}[/red]\n"
            "请按上方提示修复后重新运行 `python -m avs doctor`"
        )
        sys.exit(1)


# ── episode ───────────────────────────────────────────────────────────
@main.group()
def episode() -> None:
    """Episode 管理命令。"""


@episode.command("create")
@click.argument("episode_id")
@click.option(
    "--mode",
    default="REFERENCE_ADAPT",
    type=click.Choice(["REFERENCE_CLONE", "REFERENCE_ADAPT", "ORIGINAL"], case_sensitive=True),
    help="制作模式（默认 REFERENCE_ADAPT）",
)
@click.option(
    "--platforms",
    default="douyin,xiaohongshu",
    help="目标平台，逗号分隔（默认 douyin,xiaohongshu）",
)
@click.option(
    "--input-mode",
    type=click.Choice(["multimodal", "screenshot_intro"], case_sensitive=True),
    default="multimodal",
    show_default=True,
    help="输入路线；screenshot_intro 先生成待审阅截图图文预览",
)
@click.option(
    "--production-type",
    type=click.Choice(["STANDARD", "SCREEN_DOCUMENTARY"], case_sensitive=True),
    default="STANDARD",
    show_default=True,
    help="制作类型；SCREEN_DOCUMENTARY 强制真实录屏与 Pilot Gate",
)
def episode_create(episode_id: str, mode: str, platforms: str, input_mode: str, production_type: str) -> None:
    """创建新 Episode，生成规范目录和 episode.json。"""
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import (
        PathError,
        create_episode_skeleton,
        episode_dir,
        episode_json_path,
        find_episode_dir,
    )

    root = _find_project_root()
    cfg = Config(root)

    # 解析平台列表
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    # 路径校验（含 ID 格式 + 路径穿越）
    try:
        ep_dir = episode_dir(cfg.episodes_root, episode_id, lifecycle="active")
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    # 重复创建检测（跨全部 lifecycle 分区）
    existing = find_episode_dir(cfg.episodes_root, episode_id)
    if existing is not None:
        console.print(f"[red]✗ Episode {episode_id!r} 已存在: {existing}[/red]")
        sys.exit(1)
    ep_json = episode_json_path(ep_dir)
    if ep_dir.exists() or ep_json.exists():
        console.print(
            f"[red]✗ Episode {episode_id!r} 已存在: {ep_dir}[/red]\n"
            "若需重建请先删除该目录，或使用 `episode reset --force`。"
        )
        sys.exit(1)

    # 原子创建：先构造模型再落盘，失败时清理半成品
    try:
        model = EpisodeModel.create(
            episode_id, mode=mode, platforms=platform_list, input_mode=input_mode,
            production_type=production_type,
        )
        ep_dir.mkdir(parents=True, exist_ok=False)
        create_episode_skeleton(ep_dir)
        model.save(ep_json)
    except Exception as exc:
        # 清理半成品目录
        if ep_dir.exists():
            import shutil
            shutil.rmtree(ep_dir, ignore_errors=True)
        console.print(f"[red]✗ 创建失败，已清理半成品: {exc}[/red]")
        sys.exit(1)

    publishable_note = "" if model.publishable else "  [yellow](publishable=false — REFERENCE_CLONE)[/yellow]"
    console.print(
        f"[green]✓ Episode {episode_id!r} 创建成功[/green]{publishable_note}\n"
        f"  目录: {ep_dir}\n"
        f"  模式: {mode}  制作类型: {production_type}  平台: {', '.join(platform_list)}"
    )
    sys.exit(0)


@episode.command("status")
@click.argument("episode_id")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出")
def episode_status(episode_id: str, as_json: bool) -> None:
    """查看 Episode 当前状态。"""
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, find_episode_dir, episode_json_path

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
    except Exception as exc:
        console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(model.to_dict(), ensure_ascii=False, indent=2))
        sys.exit(0)

    data = model.to_dict()
    console.print(f"\n[bold]Episode {model.id}[/bold]")
    console.print(f"  状态      : [cyan]{model.status}[/cyan]")
    console.print(f"  模式      : {model.mode}")
    console.print(f"  输入路线  : {model.input_mode}")
    console.print(f"  可发布    : {'是' if model.publishable else '[yellow]否[/yellow]'}")
    console.print(f"  平台      : {', '.join(data.get('platforms', []))}")
    console.print(f"  已完成阶段: {', '.join(model.completed_stages) or '（无）'}")
    if model.last_error:
        console.print(f"  最后错误  : [red]{model.last_error}[/red]")
    console.print(f"  更新时间  : {data.get('updated_at', '-')}")
    sys.exit(0)


@episode.command("validate")
@click.argument("episode_id")
def episode_validate(episode_id: str) -> None:
    """对 episode.json 进行 Schema 校验。"""
    from avs.config import Config
    from avs.models.episode import EpisodeModel, EpisodeValidationError
    from avs.paths import PathError, find_episode_dir, episode_json_path

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
    except EpisodeValidationError as exc:
        console.print(f"[red]✗ Schema 校验失败: {exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]✗ 加载失败: {exc}[/red]")
        sys.exit(1)

    console.print(
        f"[green]✓ {episode_id} — episode.json Schema 校验通过[/green]\n"
        f"  状态: {model.status}  模式: {model.mode}"
    )
    sys.exit(0)


@episode.command("fail")
@click.argument("episode_id")
@click.option("--reason", required=True, help="失败原因说明")
def episode_fail(episode_id: str, reason: str) -> None:
    """将 Episode 标记为 FAILED 并记录原因。"""
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, find_episode_dir, episode_json_path

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
        model.fail(reason)
        model.save(ep_json)
    except Exception as exc:
        console.print(f"[red]✗ 操作失败: {exc}[/red]")
        sys.exit(1)

    console.print(
        f"[yellow]⚠ Episode {episode_id!r} 已标记为 FAILED[/yellow]\n"
        f"  原因: {reason}"
    )
    sys.exit(0)


@episode.command("reset")
@click.argument("episode_id")
@click.option("--to", "target_status", required=True, help="目标状态")
@click.option("--force", is_flag=True, help="强制重置（允许非常规转换）")
def episode_reset(episode_id: str, target_status: str, force: bool) -> None:
    """重置 Episode 状态（需要 --force）。"""
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, find_episode_dir, episode_json_path
    from avs.state import TransitionError

    root = _find_project_root()
    cfg = Config(root)

    if not force:
        console.print("[red]✗ reset 命令需要 --force 参数[/red]")
        sys.exit(1)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
        old_status = model.status
        model.transition(target_status, force=True)
        model.save(ep_json)
    except TransitionError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]✗ 操作失败: {exc}[/red]")
        sys.exit(1)

    console.print(
        f"[green]✓ Episode {episode_id!r} 状态已重置[/green]\n"
        f"  {old_status} → {target_status}"
    )
    sys.exit(0)


# ── ingest ────────────────────────────────────────────────────────────
@main.command("ingest")
@click.argument("episode_id")
@click.option("--force", is_flag=True, help="强制重新处理所有文件（忽略幂等缓存）")
def ingest_cmd(episode_id: str, force: bool) -> None:
    """清点 input/ 素材，生成 asset-manifest.json，状态 → INGESTED。"""
    import logging
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, find_episode_dir, episode_json_path
    from avs.ingest import run_ingest
    from avs.intake.manifest import InputCompletenessError

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
    except Exception as exc:
        console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
        sys.exit(1)

    try:
        proxy = cfg.visual.get("visual", {}).get("proxy", {})
        assets = run_ingest(
            ep_dir,
            model.id,
            force=force,
            config={
                "canvas_w": proxy.get("width", 540),
                "canvas_h": proxy.get("height", 960),
                "video_crf": proxy.get("crf", 28),
            },
        )
    except InputCompletenessError as exc:
        model.block(str(exc), stage="ingest", waiting_for_input=True)
        model.save(ep_json)
        console.print(f"[yellow]⚠ ingest 输入不完整: {exc}[/yellow]")
        raise click.exceptions.Exit(2)
    except Exception as exc:
        console.print(f"[red]✗ ingest 失败: {exc}[/red]")
        model.fail(str(exc))
        model.save(ep_json)
        sys.exit(1)

    if not assets:
        try:
            model.block("input/ 中没有素材", stage="ingest", waiting_for_input=True)
            model.save(ep_json)
        except Exception as exc:
            console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
            sys.exit(1)
        console.print(
            "[yellow]⚠ input/ 中没有素材，已生成空清单；状态 → WAITING_FOR_INPUT[/yellow]"
        )
        raise click.exceptions.Exit(2)

    unassigned_audio = [
        asset["asset_id"] for asset in assets
        if asset.get("kind") == "audio" and asset.get("status") == "ok" and not asset.get("audio_role")
    ]
    if unassigned_audio:
        reason = "音频素材缺少 Manifest audio_role: " + ", ".join(unassigned_audio)
        model.block(reason, stage="ingest", waiting_for_input=True)
        model.save(ep_json)
        console.print(f"[yellow]⚠ {reason}[/yellow]")
        raise click.exceptions.Exit(2)

    # 状态转换 → INGESTED；不允许静默跳过非法状态
    try:
        model.clear_block(stage="ingest")
        model.ensure_stage("ingest", "INGESTED")
        model.complete_stage("ingest")
        model.save(ep_json)
    except Exception as exc:
        console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
        sys.exit(1)

    ok = sum(1 for a in assets if a["status"] == "ok")
    bad = sum(1 for a in assets if a["status"] == "corrupt")
    console.print(
        f"[green]✓ ingest 完成[/green]  "
        f"共 {len(assets)} 个素材  "
        f"正常 {ok}  损坏 {bad}{'  [yellow](有损坏文件，已标记，不进渲染)[/yellow]' if bad else ''}"
    )
    sys.exit(0)


# ── assets ────────────────────────────────────────────────────────────
@main.group()
def assets() -> None:
    """素材清单查询命令。"""


@assets.command("list")
@click.argument("episode_id")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出")
@click.option("--kind", default=None, help="过滤类型 video/audio/image/text/link/unknown")
def assets_list(episode_id: str, as_json: bool, kind: str | None) -> None:
    """列出 Episode 的 asset-manifest.json 中所有素材。"""
    from avs.config import Config
    from avs.paths import PathError, find_episode_dir
    from avs.ingest.manifest import load_manifest
    from avs.ingest.errors import ManifestError

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    try:
        manifest = load_manifest(ep_dir)
    except ManifestError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    items = manifest["assets"]
    if kind:
        items = [a for a in items if a["kind"] == kind]

    if as_json:
        click.echo(json.dumps(items, ensure_ascii=False, indent=2))
        sys.exit(0)

    table = Table(title=f"Assets — {episode_id}", show_header=True, header_style="bold")
    table.add_column("asset_id", max_width=32)
    table.add_column("kind", width=8)
    table.add_column("status", width=8)
    table.add_column("source_path")
    table.add_column("working_path")

    status_style = {"ok": "green", "corrupt": "red bold", "missing": "yellow", "unsupported": "dim"}
    for a in items:
        st = a["status"]
        style = status_style.get(st, "white")
        table.add_row(
            a["asset_id"][:32],
            a["kind"],
            f"[{style}]{st}[/{style}]",
            a["source_path"],
            a["working_path"],
        )
    console.print(table)
    sys.exit(0)


@assets.command("validate")
@click.argument("episode_id")
def assets_validate(episode_id: str) -> None:
    """校验 asset-manifest.json：Schema 合规 + 路径为相对路径 + 工作副本存在。"""
    from avs.config import Config
    from avs.paths import PathError, find_episode_dir
    from avs.ingest.manifest import load_manifest
    from avs.ingest.errors import ManifestError

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)

    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    try:
        manifest = load_manifest(ep_dir)
    except ManifestError as exc:
        console.print(f"[red]✗ Schema 校验失败: {exc}[/red]")
        sys.exit(1)

    errors: list[str] = []
    from pathlib import Path as _P
    for a in manifest["assets"]:
        aid = a["asset_id"]
        # 路径必须是相对路径
        if _P(a["source_path"]).is_absolute():
            errors.append(f"{aid}: source_path 为绝对路径")
        if _P(a["working_path"]).is_absolute():
            errors.append(f"{aid}: working_path 为绝对路径")
        # ok 状态的工作副本必须存在
        if a["status"] == "ok" and a.get("working_path"):
            wp = ep_dir / a["working_path"]
            if not wp.exists():
                errors.append(f"{aid}: working_path 不存在 ({a['working_path']})")

    if errors:
        for e in errors:
            console.print(f"  [red]✗ {e}[/red]")
        sys.exit(1)

    console.print(
        f"[green]✓ {episode_id} — asset-manifest 校验通过[/green]  "
        f"共 {len(manifest['assets'])} 个素材"
    )
    sys.exit(0)


@assets.command("approve")
@click.argument("episode_id")
def assets_approve(episode_id: str) -> None:
    """确认素材与占位声明完整，状态 → ASSETS_READY。"""
    from avs.config import Config
    from avs.content.schema import validate_content_bundle
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, episode_json_path, find_episode_dir

    root = _find_project_root()
    cfg = Config(root)
    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)
    try:
        validate_content_bundle(ep_dir)
        model = EpisodeModel.load(episode_json_path(ep_dir))
        model.ensure_stage("assets", "ASSETS_READY")
        model.complete_stage("assets")
        model.save(episode_json_path(ep_dir))
    except Exception as exc:
        console.print(f"[red]✗ 素材确认失败: {exc}[/red]")
        sys.exit(1)
    console.print("[green]✓ 素材与缺口声明已确认，状态 → ASSETS_READY[/green]")
    sys.exit(0)


# ── reference ─────────────────────────────────────────────────────────
@main.group()
def reference() -> None:
    """参考视频分析命令。"""


@reference.command("analyze")
@click.argument("episode_id")
@click.option("--transcription", default="auto",
              type=click.Choice(["auto", "manual", "disabled"], case_sensitive=False),
              help="转写 Provider（默认 auto）")
@click.option("--force", is_flag=True, help="强制重新分析（忽略缓存）")
def reference_analyze(episode_id: str, transcription: str, force: bool) -> None:
    """分析参考视频，生成镜头数据、关键帧与 reference-recipe.json。状态 → REFERENCE_READY。"""
    import logging
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, find_episode_dir, episode_json_path
    from avs.reference import run_reference_analyze

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
    except Exception as exc:
        console.print(f"[red]✗ 加载 episode.json 失败: {exc}[/red]")
        sys.exit(1)

    try:
        recipes = run_reference_analyze(
            ep_dir, model.id,
            transcription_provider=transcription,
            force=force,
        )
    except Exception as exc:
        console.print(f"[red]✗ reference analyze 失败: {exc}[/red]")
        model.fail(str(exc))
        model.save(ep_json)
        sys.exit(1)

    if not recipes:
        console.print(
            "[yellow]⚠ 未找到可分析的参考视频；保持当前状态，"
            "可直接执行内容工作流[/yellow]"
        )
        sys.exit(0)

    # 状态转换 → REFERENCE_READY
    try:
        model.ensure_stage("reference", "REFERENCE_READY")
        model.complete_stage("reference")
        model.save(ep_json)
    except Exception as exc:
        console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
        sys.exit(1)

    console.print(
        f"[green]✓ 参考分析完成[/green]  共 {len(recipes)} 个参考视频  "
        f"状态 → REFERENCE_READY"
    )
    sys.exit(0)


@reference.command("validate")
@click.argument("episode_id")
def reference_validate(episode_id: str) -> None:
    """校验 reference-recipe.json Schema 合规性。"""
    from avs.config import Config
    from avs.paths import PathError, find_episode_dir
    from avs.reference.recipe import load_recipe

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    try:
        recipe = load_recipe(ep_dir)
        console.print(
            f"[green]✓ reference-recipe.json 校验通过[/green]  "
            f"镜头数: {len(recipe['shots'])}  "
            f"时长: {recipe['duration']:.1f}s"
        )
        sys.exit(0)
    except FileNotFoundError as exc:
        console.print(f"[yellow]⚠ {exc}[/yellow]")
        sys.exit(1)
    except Exception as exc:
        console.print(f"[red]✗ 校验失败: {exc}[/red]")
        sys.exit(1)


# ── content ──────────────────────────────────────────────────────────
@main.group()
def content() -> None:
    """内容、脚本与分镜命令（Agent驱动）。"""


@content.command("init")
@click.argument("episode_id")
def content_init(episode_id: str) -> None:
    """初始化内容工作区，输出Agent待办清单。"""
    from avs.config import Config
    from avs.paths import PathError, find_episode_dir
    from avs.content import init_content_workspace, check_prerequisites

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    # 初始化目录
    content_dir = init_content_workspace(ep_dir)
    console.print(f"[green]✓ 内容工作区初始化[/green]: {content_dir}")

    # 检查前置条件
    prereqs = check_prerequisites(ep_dir)
    console.print("\n前置条件:")
    for key, val in prereqs.items():
        sym = "✓" if val else "✗"
        console.print(f"  {sym} {key}")

    # Agent 待办清单
    console.print("\n[bold]Agent 待办清单：[/bold]")
    console.print("1. 阅读 input/ 下所有文本、links.txt")
    if prereqs["has_reference_recipe"]:
        console.print("2. 阅读 work/reference/reference-recipe.json（参考结构）")
    console.print("3. 调用 Skills:")
    console.print("   - write-video-script → 生成 work/content/script.json + script.md")
    console.print("   - create-storyboard → 生成 work/content/storyboard.json + storyboard.md")
    console.print("4. 标注缺失素材 → work/content/missing-assets.md")
    console.print("\n完成后运行: [cyan]avs content validate <ID>[/cyan]")
    sys.exit(0)


@content.command("validate")
@click.argument("episode_id")
def content_validate(episode_id: str) -> None:
    """校验 script.json 和 storyboard.json Schema。"""
    from avs.config import Config
    from avs.paths import PathError, find_episode_dir
    from avs.content.schema import load_script, load_storyboard, validate_content_bundle
    import jsonschema

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    errors: list[str] = []

    # 校验 script.json
    try:
        script = load_script(ep_dir)
        console.print(f"[green]✓ script.json Schema 通过[/green]  段落数: {len(script['segments'])}")
    except FileNotFoundError as exc:
        errors.append(f"script.json 缺失: {exc}")
    except jsonschema.ValidationError as exc:
        errors.append(f"script.json Schema 校验失败: {exc.message}")
    except Exception as exc:
        errors.append(f"script.json 错误: {exc}")

    # 校验 storyboard.json
    try:
        storyboard = load_storyboard(ep_dir)
        console.print(f"[green]✓ storyboard.json Schema 通过[/green]  镜头数: {len(storyboard['shots'])}")
        if storyboard.get("asset_gaps"):
            console.print(f"  [yellow]⚠ 缺失素材: {len(storyboard['asset_gaps'])} 项[/yellow]")
    except FileNotFoundError as exc:
        errors.append(f"storyboard.json 缺失: {exc}")
    except jsonschema.ValidationError as exc:
        errors.append(f"storyboard.json Schema 校验失败: {exc.message}")
    except Exception as exc:
        errors.append(f"storyboard.json 错误: {exc}")

    if errors:
        for e in errors:
            console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    try:
        validate_content_bundle(ep_dir)
    except Exception as exc:
        console.print(f"[red]✗ 内容可追溯性校验失败: {exc}[/red]")
        sys.exit(1)

    console.print("\n[green]✓ 所有内容产物校验通过[/green]")
    sys.exit(0)


@content.command("approve")
@click.argument("episode_id")
def content_approve(episode_id: str) -> None:
    """人工审核通过，状态 → CONTENT_READY。"""
    from avs.config import Config
    from avs.models.episode import EpisodeModel
    from avs.paths import PathError, find_episode_dir, episode_json_path
    from avs.content.schema import load_script, load_storyboard, validate_content_bundle, save_script

    root = _find_project_root()
    cfg = Config(root)

    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        sys.exit(1)
    if ep_dir is None:
        console.print(f"[red]✗ Episode {episode_id!r} 不存在[/red]")
        sys.exit(1)

    # 验证产物存在
    try:
        script = load_script(ep_dir)
        load_storyboard(ep_dir)
        validate_content_bundle(ep_dir)
    except Exception as exc:
        console.print(f"[red]✗ 内容产物缺失或校验失败: {exc}[/red]")
        sys.exit(1)

    # 状态转换
    ep_json = episode_json_path(ep_dir)
    try:
        model = EpisodeModel.load(ep_json)
        model.ensure_stage("content", "CONTENT_READY")
        for segment in script["segments"]:
            segment["status"] = "approved"
        save_script(ep_dir, script)
        model.complete_stage("content")
        model.save(ep_json)
        console.print("[green]✓ 内容已审核通过，状态 → CONTENT_READY[/green]")
        sys.exit(0)
    except Exception as exc:
        console.print(f"[red]✗ 状态转换失败: {exc}[/red]")
        sys.exit(1)


# ── 注册 timeline / subtitles / render / qa / deliver / run 命令 ──
_reg_timeline(main)
_reg_workflow(main)
_reg_active(main)
_reg_research(main)


if __name__ == "__main__":
    main()
