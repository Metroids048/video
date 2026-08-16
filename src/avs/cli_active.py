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

    @main_group.command("story-mine")
    @click.argument("episode_id")
    def story_mine_cmd(episode_id: str) -> None:
        """复用已验证 VCI 包，生成录屏/证据镜头索引。"""
        from avs.active import active_story_mine
        try:
            ep_dir, model = _episode(episode_id)
            result = active_story_mine(ep_dir, model)
        except Exception as exc:
            console.print(f"[red]✗ story-mine 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(json.dumps(result, ensure_ascii=False, indent=2))

    @main_group.command("direct")
    @click.argument("episode_id")
    def direct_cmd(episode_id: str) -> None:
        """为 SCREEN_DOCUMENTARY 选择唯一故事并生成事实边界。"""
        from avs.active import active_direct
        try:
            ep_dir, model = _episode(episode_id)
            result = active_direct(ep_dir, model)
        except Exception as exc:
            console.print(f"[red]✗ direct 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(f"[green]✓ direct 完成[/green]  {result}")

    @main_group.command("pilot")
    @click.argument("episode_id")
    @click.option("--force", is_flag=True, help="覆盖可再生成的 Pilot 产物")
    def pilot_cmd(episode_id: str, force: bool) -> None:
        """生成 A/B/C 三个 8-10 秒真实录屏 Pilot。"""
        from avs.active import active_pilot
        try:
            ep_dir, model = _episode(episode_id)
            result = active_pilot(ep_dir, model, force=force)
        except Exception as exc:
            console.print(f"[red]✗ pilot 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(json.dumps(result, ensure_ascii=False, indent=2))

    @main_group.command("pilot-review")
    @click.argument("episode_id")
    @click.option("--reviewers", required=False, help="两份 Reviewer JSON 数组，或 JSON 文件路径")
    @click.option("--force", is_flag=True, help="覆盖已有 Pilot Review")
    def pilot_review_cmd(episode_id: str, reviewers: str | None, force: bool) -> None:
        """持久化两份独立视觉评分并执行 Pilot Gate。"""
        from avs.active import active_pilot_review

        def payload(raw: str) -> object:
            candidate = Path(raw)
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
            return json.loads(raw)

        try:
            ep_dir, model = _episode(episode_id)
            reviewer_payloads = None
            if reviewers:
                loaded = payload(reviewers)
                if not isinstance(loaded, list):
                    raise ValueError("--reviewers 必须是包含两份对象的 JSON 数组")
                reviewer_payloads = loaded
            report = active_pilot_review(ep_dir, model, reviewer_payloads, force=force)
        except Exception as exc:
            console.print(f"[red]✗ pilot-review 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["decision"] != "PASS":
            raise click.exceptions.Exit(2)

    @main_group.command("pilot-revise")
    @click.argument("episode_id")
    def pilot_revise_cmd(episode_id: str) -> None:
        """只按 Reviewer findings 的明确责任层返修 Pilot，最多两轮。"""
        from avs.active import active_pilot_revise

        try:
            ep_dir, model = _episode(episode_id)
            result = active_pilot_revise(ep_dir, model)
        except Exception as exc:
            console.print(f"[red]✗ pilot-revise 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["decision"] != "RENDER_REQUIRED":
            raise click.exceptions.Exit(2)

    @main_group.command("plan")
    @click.argument("episode_id")
    @click.option("--platform", type=click.Choice(["douyin", "xiaohongshu"]), default="douyin")
    @click.option("--hook", "hook_variant", type=click.Choice(["result", "conflict", "pain"]), default="conflict")
    @click.option("--pattern", "pattern_ids", multiple=True)
    @click.option(
        "--regenerate-script", is_flag=True,
        help="丢弃 Agent 撰写的脚本，改用确定性规划器重新生成（会覆盖创作内容）",
    )
    def plan_cmd(
        episode_id: str, platform: str, hook_variant: str,
        pattern_ids: tuple[str, ...], regenerate_script: bool,
    ) -> None:
        """生成 Brief、Script、Evidence Map 和 Shot Plan。

        已存在通过校验的 Agent 脚本时优先采用，不覆盖。
        """
        from avs.active import active_plan
        from avs.creative import script_summary
        try:
            ep_dir, model = _episode(episode_id)
            result = active_plan(
                ep_dir, model, platform=platform, hook_variant=hook_variant,
                pattern_ids=list(pattern_ids) or None, regenerate_script=regenerate_script,
            )
        except Exception as exc:
            console.print(f"[red]✗ plan 阻塞: {exc}[/red]")
            raise click.exceptions.Exit(2)
        summary = script_summary(result["script"])
        source = "Agent 撰写" if summary["authored_by"] == "agent" else "确定性规划器"
        console.print(
            f"[green]✓ plan 完成[/green]  脚本来源={source}"
            f"  segments={len(result['script'].get('segments', []))}"
            f"  shots={len(result['shot_plan'].get('shots', []))}"
            f"  总时长={summary['total_duration']}s"
        )

    @main_group.command("validate-script")
    @click.argument("episode_id")
    def validate_script_cmd(episode_id: str) -> None:
        """校验 Agent 撰写的发布脚本是否可信。"""
        from avs.creative import script_summary, validate_agent_script
        from avs.creative.agent_script import load_agent_script
        try:
            ep_dir, model = _episode(episode_id)
            script = load_agent_script(ep_dir)
            if script is None:
                console.print(
                    "[yellow]未找到 Agent 脚本[/yellow]  "
                    "需要 work/content/script.json 且 authored_by=agent"
                )
                raise click.exceptions.Exit(2)
            manifest = json.loads((ep_dir / "work/input-manifest.json").read_text(encoding="utf-8"))
            intelligence = json.loads(
                (ep_dir / "work/analysis/asset-intelligence.json").read_text(encoding="utf-8")
            )
            errors = validate_agent_script(
                script, manifest=manifest, intelligence=intelligence, episode_id=model.id,
            )
        except click.exceptions.Exit:
            raise
        except Exception as exc:
            console.print(f"[red]✗ validate-script 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        summary = script_summary(script)
        console.print(
            f"作者={summary['author_id']}  段落={summary['segment_count']}"
            f"  总时长={summary['total_duration']}s  证据段={summary['evidence_segments']}"
            f"  Narrative Beat={'有' if summary['has_narrative_beats'] else '无'}"
            f"  Visual Goal={'有' if summary['has_visual_goals'] else '无'}"
        )
        if errors:
            for item in errors:
                console.print(f"  [red]✗[/red] {item}")
            raise click.exceptions.Exit(2)
        console.print("[green]✓ Agent 脚本通过校验，可进入 plan[/green]")

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

    @main_group.group("creative")
    def creative_group() -> None:
        """成片创作质量审核：度量、评分、基线对比。"""

    @creative_group.command("review")
    @click.argument("episode_id")
    @click.option("--video", "video", type=click.Path(path_type=Path), default=None, help="指定被审视频，默认自动选择最新成片")
    @click.option("--force", is_flag=True, help="重新抽帧并重建审片包")
    def creative_review_cmd(episode_id: str, video: Path | None, force: bool) -> None:
        """度量成片并生成审片包（不评分）。"""
        from avs.qa.creative_review import build_review
        try:
            ep_dir, model = _episode(episode_id)
            review = build_review(ep_dir, model.id, video_path=video, force=force)
        except Exception as exc:
            console.print(f"[red]✗ creative review 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        metrics = review["metrics"]
        console.print(f"[green]✓ 审片包已生成[/green]  {review['video_path']}")
        console.print(
            f"  时长={metrics['duration_seconds']}s  镜头={metrics['shot_count']}"
            f"  时长档位={metrics['shot_duration_distinct_values']}"
            f"  最长静态={metrics['longest_static_run_seconds']}s"
            f"  Hook静态={metrics['hook_static_seconds']}s"
        )
        for sheet in review["review_package"]["contact_sheets"]:
            console.print(f"  拼图 {sheet['label']}: {sheet['path']} ({sheet['width']}px)")
        for item in review["findings"]:
            console.print(f"  [yellow]{item['severity']:8s}[/yellow] {item['dimension']:14s} {item['observation']}")
        console.print("[yellow]scores 为 null — 需由看过成片的审片人写入评分后才能过闸。[/yellow]")

    @creative_group.command("score")
    @click.argument("episode_id")
    @click.option("--scores", "scores_json", required=True, help="JSON 对象或 .json 文件路径，含 10 个维度评分")
    @click.option("--reviewer-kind", type=click.Choice(["agent", "provider"]), default="agent")
    @click.option("--reviewer-id", default=None, help="审片人标识，例如 claude-opus-5")
    @click.option("--reviewed-artifacts", required=True, help="审片人实际查看过的 MP4/联系表/关键帧 JSON 数组或文件路径")
    @click.option("--findings", "findings_json", default=None, help="JSON 数组或 .json 文件路径，补充主观失败点")
    @click.option("--repair-round", type=int, default=None, help="当前 Repair 轮次")
    def creative_score_cmd(
        episode_id: str, scores_json: str, reviewer_kind: str,
        reviewer_id: str | None, reviewed_artifacts: str, findings_json: str | None, repair_round: int | None,
    ) -> None:
        """写入审片评分并重新判定闸门。"""
        from avs.qa.creative_review import record_scores

        def _payload(raw: str) -> object:
            candidate = Path(raw)
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
            return json.loads(raw)

        try:
            ep_dir, _ = _episode(episode_id)
            scores = _payload(scores_json)
            if not isinstance(scores, dict):
                raise ValueError("--scores 必须是 JSON 对象")
            extra = _payload(findings_json) if findings_json else None
            if extra is not None and not isinstance(extra, list):
                raise ValueError("--findings 必须是 JSON 数组")
            watched = _payload(reviewed_artifacts)
            if not isinstance(watched, list) or not all(isinstance(item, str) for item in watched):
                raise ValueError("--reviewed-artifacts 必须是字符串数组")
            review = record_scores(
                ep_dir, scores, reviewer_kind=reviewer_kind,
                reviewer_id=reviewer_id, reviewed_artifacts=watched,
                findings=extra, repair_round=repair_round,
            )
        except Exception as exc:
            console.print(f"[red]✗ creative score 失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        gate = review["gate"]
        overall = review["scores"]["overall"]
        console.print(f"[green]✓ 评分已记录[/green]  Overall={overall}  阈值={gate['overall_threshold']}")
        console.print(f"  技术闸门={'PASS' if gate['technical_passed'] else 'FAIL'}  创作闸门={'PASS' if gate['creative_passed'] else 'FAIL'}")
        if gate["failed_dimensions"]:
            console.print(f"  [red]低于 {gate['dimension_floor']} 的核心维度: {', '.join(gate['failed_dimensions'])}[/red]")
        if not gate["creative_passed"]:
            console.print(f"  Repair 允许={gate['repair_allowed']}  当前轮次={gate['repair_round']}")

    @creative_group.command("baseline")
    @click.argument("episode_id")
    def creative_baseline_cmd(episode_id: str) -> None:
        """将当前已评分审核固定为对比基线。"""
        from avs.qa.creative_review import promote_baseline
        try:
            ep_dir, _ = _episode(episode_id)
            path = promote_baseline(ep_dir)
        except Exception as exc:
            console.print(f"[red]✗ 固定基线失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        console.print(f"[green]✓ 基线已固定[/green]  {path}")

    @creative_group.command("compare")
    @click.argument("episode_id")
    @click.option("--json", "as_json", is_flag=True, help="以 JSON 输出")
    def creative_compare_cmd(episode_id: str, as_json: bool) -> None:
        """输出 Baseline vs Current 对比表。"""
        from avs.qa.creative_review import compare_to_baseline
        try:
            ep_dir, _ = _episode(episode_id)
            result = compare_to_baseline(ep_dir)
        except Exception as exc:
            console.print(f"[red]✗ 对比失败: {exc}[/red]")
            raise click.exceptions.Exit(1)
        if as_json:
            click.echo(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if not result["has_baseline"]:
            console.print("[yellow]尚无基线；当前审核可用 creative baseline 固定为基线。[/yellow]")
        from rich.table import Table
        table = Table(title=f"Creative Score — {result['episode_id']}")
        table.add_column("维度", style="bold cyan")
        table.add_column("Baseline", justify="right")
        table.add_column("Current", justify="right")
        table.add_column("Delta", justify="right")
        for row in result["rows"]:
            delta = row["delta"]
            colour = "green" if delta is not None and delta > 0 else ("red" if delta is not None and delta < 0 else "white")
            table.add_row(
                row["dimension"],
                "—" if row["baseline"] is None else f"{row['baseline']:.2f}",
                "—" if row["current"] is None else f"{row['current']:.2f}",
                "—" if delta is None else f"[{colour}]{delta:+.2f}[/{colour}]",
            )
        console.print(table)
        metric_table = Table(title="确定性指标")
        metric_table.add_column("指标", style="bold cyan")
        metric_table.add_column("Baseline", justify="right")
        metric_table.add_column("Current", justify="right")
        metric_table.add_column("Delta", justify="right")
        for row in result["metric_deltas"]:
            metric_table.add_row(
                row["metric"],
                "—" if row["baseline"] is None else str(row["baseline"]),
                "—" if row["current"] is None else str(row["current"]),
                "—" if row["delta"] is None else f"{row['delta']:+g}",
            )
        console.print(metric_table)

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
