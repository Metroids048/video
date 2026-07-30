"""CLI registration for workflow inspection and deterministic resume."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from avs.models.episode import EpisodeModel
from avs.workflow import WorkflowAction, WorkflowExecutionError, action_for_episode, run_automatic_steps

console = Console()


def _find_project_root() -> Path:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "AGENTS.md").exists():
            return candidate
    return cwd


def _load_episode(episode_id: str) -> tuple[Path, EpisodeModel]:
    from avs.config import Config
    from avs.paths import PathError, episode_json_path, find_episode_dir

    cfg = Config(_find_project_root())
    try:
        ep_dir = find_episode_dir(cfg.episodes_root, episode_id)
    except PathError as exc:
        raise click.ClickException(str(exc)) from exc
    if ep_dir is None:
        raise click.ClickException(f"Episode {episode_id!r} 不存在")
    try:
        return ep_dir, EpisodeModel.load(episode_json_path(ep_dir))
    except Exception as exc:
        raise click.ClickException(f"加载 episode.json 失败: {exc}") from exc


def _render_action(episode_id: str, status: str, action: WorkflowAction, *, as_json: bool) -> None:
    payload = {"episode_id": episode_id, "status": status, "next_action": action.to_dict()}
    if as_json:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    table = Table(title=f"Workflow — {episode_id}", show_header=False)
    table.add_column("field", style="bold cyan", width=18)
    table.add_column("value")
    table.add_row("Episode 状态", status)
    table.add_row("下一阶段", action.stage)
    table.add_row("动作类型", action.kind)
    table.add_row("说明", action.summary)
    if action.command:
        table.add_row("命令", f"python -m avs {' '.join(action.command)} {episode_id}")
    if action.required_artifacts:
        table.add_row("所需产物", "\n".join(action.required_artifacts))
    console.print(table)


def register_commands(main_group: click.Group) -> None:
    """Register workflow commands on the canonical CLI group."""

    @main_group.group()
    def workflow() -> None:
        """检查并安全续跑完整短视频工作流。"""

    @workflow.command("status")
    @click.argument("episode_id")
    @click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出")
    def workflow_status(episode_id: str, as_json: bool) -> None:
        """显示 Episode 当前状态和下一步。"""
        ep_dir, model = _load_episode(episode_id)
        _render_action(model.id, model.status, action_for_episode(ep_dir, model), as_json=as_json)

    @workflow.command("next")
    @click.argument("episode_id")
    @click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出")
    def workflow_next(episode_id: str, as_json: bool) -> None:
        """仅输出当前最安全的下一步。"""
        ep_dir, model = _load_episode(episode_id)
        _render_action(model.id, model.status, action_for_episode(ep_dir, model), as_json=as_json)

    @workflow.command("resume")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="将 --force 传给可重建的确定性步骤")
    @click.option("--json", "as_json", is_flag=True, help="以 JSON 格式输出结果")
    def workflow_resume(episode_id: str, force: bool, as_json: bool) -> None:
        """运行确定性步骤，直至需要 Agent 或人工判断时安全停止。"""
        ep_dir, model = _load_episode(episode_id)
        root = _find_project_root()

        def runner(command: tuple[str, ...], run_force: bool) -> None:
            args = [sys.executable, "-m", "avs", *command, episode_id]
            if run_force and command != ("content", "init"):
                args.append("--force")
            env = os.environ.copy()
            env.setdefault("PYTHONPATH", str(root / "src"))
            result = subprocess.run(args, cwd=str(root), env=env)
            if result.returncode != 0:
                raise WorkflowExecutionError(
                    f"命令 {' '.join(command)} 失败（exit {result.returncode}）"
                )

        try:
            result = run_automatic_steps(ep_dir, command_runner=runner, force=force)
            current = _load_episode(episode_id)[1]
        except WorkflowExecutionError as exc:
            raise click.ClickException(str(exc)) from exc

        payload = {
            "episode_id": current.id,
            "status": current.status,
            "executed_commands": [list(command) for command in result.executed_commands],
            "next_action": result.action.to_dict(),
        }
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        if result.executed_commands:
            console.print("[green]✓ 已执行确定性步骤：[/green]" + ", ".join(" ".join(item) for item in result.executed_commands))
        else:
            console.print("[yellow]未执行确定性步骤；当前位于人工或 Agent 关口。[/yellow]")
        _render_action(current.id, current.status, result.action, as_json=False)
