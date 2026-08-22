"""CLI registration for research-only ingestion subsystems."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console

from avs.config import Config

console = Console()


def _channel_dir(root: Path, value: str) -> Path:
    from avs.research.youtube.url import normalize_channel_url

    if value.startswith("http://") or value.startswith("https://") or value.startswith("@"):
        slug = normalize_channel_url(value).slug
    else:
        slug = value.strip().lower()
    if not slug or any(part in slug for part in ("..", "/", "\\")):
        raise click.ClickException("非法 channel slug")
    return Config(root).youtube_research_root / slug


def register_commands(main: click.Group) -> None:
    @main.group()
    def research() -> None:
        """研究旁路命令，不改变 Episode 制片主链。"""

    @research.group()
    def youtube() -> None:
        """YouTube 研究语料 discovery 命令。"""

    @youtube.command("discover")
    @click.argument("channel_url")
    @click.option("--provider", type=click.Choice(["auto", "api", "ytdlp"]), default="auto", show_default=True)
    @click.option("--force", is_flag=True, help="重新写入 channel/catalog/manifest，但仍按 video_id 幂等合并")
    def discover_cmd(channel_url: str, provider: str, force: bool) -> None:
        """只发现频道视频清单，不下载媒体。"""
        from avs.research.youtube.discovery import discover_channel
        from avs.research.youtube.url import normalize_channel_url

        root = Path.cwd()
        while root != root.parent and not (root / "AGENTS.md").exists():
            root = root.parent
        normalized = normalize_channel_url(channel_url)
        output = Config(root).youtube_research_root / normalized.slug
        try:
            result = discover_channel(
                channel_url,
                output,
                provider=provider,
                force=force,
                api_key=os.environ.get("YOUTUBE_API_KEY"),
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            api_key = os.environ.get("YOUTUBE_API_KEY")
            if api_key:
                message = message.replace(api_key, "***")
            raise click.ClickException(message) from exc
        report = {
            "channel": result.channel.title or result.channel.handle or result.channel.channel_id,
            "discovered": len(result.videos),
            "unique_ids": len({video.video_id for video in result.videos}),
            "duplicates": result.duplicates,
            "unknown": result.unknown_items,
            "provider": result.provider,
            "run_id": result.channel.discovered_at,
        }
        console.print(json.dumps(report, ensure_ascii=False, indent=2))
        console.print("[green]YOUTUBE_DISCOVERY: PASS[/green]")

    @youtube.command("status")
    @click.argument("channel")
    @click.option("--json", "as_json", is_flag=True)
    def status_cmd(channel: str, as_json: bool) -> None:
        """查看频道 discovery manifest 状态。"""
        from avs.research.youtube.storage import audit_corpus

        root = Path.cwd()
        while root != root.parent and not (root / "AGENTS.md").exists():
            root = root.parent
        report = audit_corpus(_channel_dir(root, channel))
        payload = {"passed": report.passed, "checks": report.checks, "counts": report.counts, "errors": report.errors}
        if as_json:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            console.print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise click.exceptions.Exit(0 if report.passed else 1)

    @youtube.command("audit")
    @click.argument("channel")
    def audit_cmd(channel: str) -> None:
        """执行 discovery 完整性 Gate。"""
        from avs.research.youtube.storage import audit_corpus

        root = Path.cwd()
        while root != root.parent and not (root / "AGENTS.md").exists():
            root = root.parent
        report = audit_corpus(_channel_dir(root, channel))
        console.print(json.dumps({"passed": report.passed, "checks": report.checks,
                                  "counts": report.counts, "errors": report.errors},
                                 ensure_ascii=False, indent=2))
        console.print("[green]YOUTUBE_DISCOVERY: PASS[/green]" if report.passed else "[red]YOUTUBE_DISCOVERY: NOT PASS[/red]")
        raise click.exceptions.Exit(0 if report.passed else 1)
