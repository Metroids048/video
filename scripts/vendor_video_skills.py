"""scripts/vendor_video_skills.py — 下载并同步视频第三方 Skills。

用法：
  python scripts/vendor_video_skills.py
  python scripts/vendor_video_skills.py --check

规则：
- 大仓落在 vendor/repos/（可再生成，gitignore）
- 可提交副本落在 third_party_skills/
- 再复制到 .claude/skills 与 .agents/skills（Windows 复制，非 symlink）
- 更新 skills.lock.json 的 third_party_skills 节
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "vendor" / "manifests" / "video-third-party.yaml"


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _tree_hash(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        digest.update(path.relative_to(skill_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rmtree(path: Path) -> None:
    """Windows-safe rmtree (clear read-only / nested .git)."""
    if not path.exists():
        return

    def _onexc(func, p, _exc_info):  # noqa: ANN001
        try:
            Path(p).chmod(0o700)
            func(p)
        except OSError:
            pass

    shutil.rmtree(path, onexc=_onexc)


def _copy_tree(src: Path, dst: Path) -> None:
    _rmtree(dst)

    def _ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = {".git", ".github", "node_modules", "__pycache__", ".venv"}
        return {n for n in names if n in ignored}

    shutil.copytree(src, dst, ignore=_ignore)


def _find_skill_root(repo: Path, hint: str) -> Path | None:
    """Locate a directory that contains SKILL.md."""
    if hint and hint != "auto" and hint != "curated_entry":
        candidate = repo / hint
        if (candidate / "SKILL.md").is_file():
            return candidate
        if candidate.is_dir():
            for child in sorted(candidate.iterdir()):
                if child.is_dir() and (child / "SKILL.md").is_file():
                    return child
        if (repo / "SKILL.md").is_file() and hint in {".", ""}:
            return repo

    if (repo / "SKILL.md").is_file():
        return repo

    for pattern in ("skills/*/SKILL.md", "*/SKILL.md", "**/SKILL.md"):
        matches = sorted(repo.glob(pattern))
        # Prefer shallow matches
        matches = [m for m in matches if "node_modules" not in m.parts]
        if matches:
            # For remotion-dev/skills there may be multiple; pick first top-level skill dir
            # Prefer directory named like the package if present
            return matches[0].parent
    return None


def _git_head(repo: Path) -> str:
    result = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _ensure_git_repo(
    name: str,
    url: str,
    dest: Path,
    *,
    sparse_paths: list[str],
    commit: str,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        if dest.exists():
            _rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        cmds: list[list[str]] = [
            ["git", "init"],
            ["git", "remote", "add", "origin", url],
        ]
        if sparse_paths:
            cmds.append(["git", "sparse-checkout", "init", "--cone"])
            cmds.append(["git", "sparse-checkout", "set", *sparse_paths])
        cmds.append(["git", "fetch", "--depth", "1", "origin", "HEAD"])
        cmds.append(["git", "checkout", "FETCH_HEAD"])
        for cmd in cmds:
            result = _run(cmd, cwd=dest)
            if result.returncode != 0:
                if dest.exists():
                    _rmtree(dest)
                result = _run(
                    ["git", "clone", "--depth", "1", url, str(dest)],
                    cwd=ROOT,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"[{name}] git clone failed: {result.stderr or result.stdout}"
                    )
                break
    else:
        if sparse_paths:
            _run(["git", "sparse-checkout", "init", "--cone"], cwd=dest)
            _run(["git", "sparse-checkout", "set", *sparse_paths], cwd=dest)
        _run(["git", "fetch", "--depth", "1", "origin", "HEAD"], cwd=dest)
        _run(["git", "checkout", "FETCH_HEAD"], cwd=dest)

    if commit:
        result = _run(["git", "fetch", "--depth", "1", "origin", commit], cwd=dest)
        if result.returncode == 0:
            checkout = _run(["git", "checkout", commit], cwd=dest)
            if checkout.returncode != 0:
                raise RuntimeError(f"[{name}] checkout {commit} failed: {checkout.stderr}")
        if sparse_paths:
            _run(["git", "sparse-checkout", "set", *sparse_paths], cwd=dest)
            _run(["git", "checkout", commit or "HEAD", "--", *sparse_paths], cwd=dest)
    return dest


def _write_openmontage_entry(dest: Path, repo: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    guide = repo / "AGENT_GUIDE.md"
    guide_note = (
        f"Full sparse checkout at `{repo.relative_to(ROOT).as_posix()}`."
        if repo.exists()
        else "Run `npm run skills:vendor` to materialize vendor/repos/openmontage."
    )
    skill = f"""---
name: openmontage
description: >
  【开放蒙太奇】OpenMontage agentic video production entry skill.
  Use for multi-pipeline documentary montage, explainer, and stock-footage workflows.
  Read AGENT_GUIDE.md in the vendored repo before driving pipelines.
trigger: 多管线 Agent 制片、纪录片蒙太奇、OpenMontage pipeline
inputs: []
read_only:
  - input/
outputs: []
run: "参阅 vendor/repos/openmontage/AGENT_GUIDE.md 与 pipeline_defs/"
verify: "确认最终 MP4 与 Episode 工作目录产物已挂载"
stop_when: "用户要求停止或 pipeline 自检失败"
on_missing_input: "列出缺口并停止，不伪造素材"
report_format: "命令、退出码、产物路径、已知限制"
---

# OpenMontage（开放蒙太奇）入口

{guide_note}

上游：https://github.com/calesthio/OpenMontage

## 必读

1. `{repo.relative_to(ROOT).as_posix()}/AGENT_GUIDE.md`（若已 vendor）
2. `{repo.relative_to(ROOT).as_posix()}/PROJECT_CONTEXT.md`
3. `{repo.relative_to(ROOT).as_posix()}/pipeline_defs/`

## 与 AVS 的关系

- Episode 状态机仍由 `python -m avs` 管理。
- OpenMontage 产出必须落到对应 Episode 的 `work/` 或 `output/`。
- 不得跳过状态机或伪造 `QA_PASSED`。

## AGPL 注意

OpenMontage 为 AGPL-3.0。用于正式交付前确认合规。
"""
    (dest / "SKILL.md").write_text(skill, encoding="utf-8")
    if guide.is_file():
        shutil.copy2(guide, dest / "AGENT_GUIDE.md")


def _write_pixelle_video_entry(dest: Path, repo: Path) -> None:
    """Curated entry — Pixelle-Video has no upstream SKILL.md; sparse docs only."""
    dest.mkdir(parents=True, exist_ok=True)
    rel = repo.relative_to(ROOT).as_posix()
    guide_note = (
        f"Sparse checkout at `{rel}` (README / docs / config.example)."
        if repo.exists()
        else "Run `npm run skills:vendor` to materialize vendor/repos/pixelle-video."
    )
    skill = f"""---
name: pixelle-video
description: >
  【Pixelle-Video】AI 全自动短视频引擎入口。
  主题一键：文案 → AI 配图/视频 → TTS → BGM → 成片。
  基于 ComfyUI / RunningHub / 直连 API；产物必须回挂 Episode。
trigger: Pixelle、Pixelle-Video、主题一键短视频、ComfyUI 短视频引擎
inputs: []
read_only:
  - input/
outputs: []
run: "参阅 vendor/repos/pixelle-video/README.md 与 docs/；按官方方式生成后回挂 Episode"
verify: "确认 MP4 落入 Episode work/ 或 output/，且未伪造 QA_PASSED"
stop_when: "缺 LLM/ComfyUI/API 凭证或用户停止"
on_missing_input: "列出服务/密钥缺口并停止，不伪造成片"
report_format: "命令、退出码、产物路径、已知限制"
---

# Pixelle-Video 入口

{guide_note}

上游：https://github.com/AIDC-AI/Pixelle-Video

文档站：https://aidc-ai.github.io/Pixelle-Video/zh

## 必读

1. `{rel}/README.md`（或 `README_EN.md`）
2. `{rel}/docs/`（安装、工作流、API）
3. `{rel}/config.example.yaml`（本机配置模板；真实密钥只进 `.env` / 本机配置，永不入库）

## 硬规则

1. **禁止**把完整 ComfyUI 模型仓或整仓 Python 包复制进 `third_party_skills/`。
2. 旁路生成的成片必须落到对应 Episode 的 `work/` 或 `output/`。
3. 不得跳过 AVS 状态机或伪造 `QA_PASSED`。
4. LLM / RunningHub / DashScope 等密钥只放本机 `.env`，不写入仓库。

## 与 AVS 的关系

- Episode 状态机仍由 `python -m avs` 管理。
- Pixelle-Video 是主题一键短视频旁路（与 `moneyprinterturbo` 类似），不是默认主链替代。
- 共享协议仍是 `timeline.json`；旁路产物在交付说明中标明来源。

## Agent 操作（摘要）

1. 确认用户要「主题 → 成片」且同意走 Pixelle 旁路。
2. 检查本机是否已按官方文档安装（Windows 整合包或源码 + uv）。
3. 缺凭证时一次性列出缺口；有凭证则按 README/API 生成竖屏短视频。
4. 将最终 MP4 复制/挂载到当前 Episode 工作目录并报告路径。
"""
    (dest / "SKILL.md").write_text(skill, encoding="utf-8")
    readme = repo / "README.md"
    if readme.is_file():
        shutil.copy2(readme, dest / "README.md")


def _write_epidemic_sound_entry(dest: Path, pkg: dict) -> None:
    """Curated thin skill — Epidemic Sound has MCP, not a public SKILL.md repo."""
    dest.mkdir(parents=True, exist_ok=True)
    mcp_url = pkg.get("source_repository") or "https://www.epidemicsound.com/a/mcp-service/mcp"
    skill = f"""---
name: epidemic-sound
description: >
  【Epidemic Sound】版权音乐 / SFX 素材检索入口。
  官方提供 MCP（无公开 GitHub SKILL.md 仓）。用于短视频 BGM、音效匹配；
  无账号时标记素材缺口，不硬凑无关音频。
trigger: 版权音乐、Epidemic Sound、BGM 检索、配乐素材
inputs: []
read_only:
  - input/
outputs: []
run: "通过官方 MCP 检索曲目；下载到 Episode work/ 工作副本"
verify: "记录曲目 ID/许可范围与本地音频路径"
stop_when: "无账号/MCP 不可用或用户停止"
on_missing_input: "标记音乐缺口并停止，不伪造授权"
report_format: "命令、退出码、产物路径、已知限制"
---

# Epidemic Sound（版权音乐）入口

上游 MCP：{mcp_url}

GitHub org（无 Agent Skill 仓）：https://github.com/epidemicsound

## 硬规则

1. 不将 API Key / Cookie / Token 写入仓库；仅用本机 `.env` 或 MCP 登录态。
2. 无账号或 MCP 失败时：在素材缺口清单中标记，**禁止**用明显无关音频硬凑。
3. 下载的音频只进 Episode `work/` 工作副本，不得写入 `input/`。
4. 旁路配乐不得伪造 Episode 状态机完成态。

## 与 AVS 的关系

- Episode 状态机仍由 `python -m avs` 管理。
- 选中曲目路径应可被 `timeline.json` 音频轨引用或在交付说明中标明。
- 默认仍可用本地/免版税平替；Epidemic Sound 为版权曲库升级路径。

## Agent 操作

1. 确认 MCP `epidemic-sound`（或等价）已配置。
2. 按情绪/时长/BPM 检索，记录 track id 与许可范围。
3. 将预览或授权下载落到 `work/audio/`。
"""
    (dest / "SKILL.md").write_text(skill, encoding="utf-8")


def _vendor_curated_skill(name: str, pkg: dict, skills_dir: Path) -> dict:
    out_name = pkg.get("skill_dir_name", name)
    out_dir = skills_dir / out_name
    if name == "epidemic-sound" or out_name == "epidemic-sound":
        _write_epidemic_sound_entry(out_dir, pkg)
    else:
        raise RuntimeError(f"[{name}] unknown curated_skill template")
    return {
        "source_repository": pkg.get("source_repository", ""),
        "commit": "",
        "license": pkg.get("license", "unknown"),
        "usage": pkg.get("usage", "production_allowed"),
        "status": "vendored",
        "install_method": "curated_skill",
        "repo_path": "",
        "destinations": [out_dir.relative_to(ROOT).as_posix()],
        "source_sha256": _tree_hash(out_dir),
        "remotion_primary_renderer": False,
        "note": pkg.get("note", ""),
    }


def _copy_named_skills(repo: Path, skills_dir: Path, pkg: dict, out_dir: Path) -> None:
    """Copy listed top-level skill dirs; primary_skill also copied to skill_dir_name."""
    names = list(pkg.get("skill_names") or [])
    primary = pkg.get("primary_skill") or (names[0] if names else "")
    if not names:
        raise RuntimeError("multi_named requires skill_names")
    for child_name in names:
        src = repo / child_name
        if not src.is_dir() or not (src / "SKILL.md").is_file():
            raise RuntimeError(f"missing skill dir {child_name} under {repo}")
        _copy_tree(src, skills_dir / child_name)
    if primary:
        primary_src = repo / primary
        _copy_tree(primary_src, out_dir)


def _vendor_npm_hyperframes(pkg: dict, skills_dir: Path) -> dict:
    names = pkg.get("skill_names") or ["hyperframes", "hyperframes-cli"]
    source_root = ROOT / "node_modules" / "hyperframes" / "dist" / "skills"
    if not source_root.is_dir():
        raise RuntimeError(
            "hyperframes npm skills missing; run npm install && ensure hyperframes package"
        )
    destinations: list[str] = []
    hashes: dict[str, str] = {}
    for name in names:
        src = source_root / name
        if not src.is_dir():
            continue
        dst = skills_dir / name
        _copy_tree(src, dst)
        destinations.append(str(dst.relative_to(ROOT).as_posix()))
        hashes[name] = _tree_hash(dst)
    return {
        "source_repository": pkg["source_repository"],
        "package": pkg.get("npm_package", "hyperframes"),
        "license": pkg.get("license", "MIT"),
        "usage": pkg.get("usage", "production_allowed"),
        "status": "vendored",
        "install_method": "npm_bundle_copy",
        "source": "node_modules/hyperframes/dist/skills",
        "destinations": destinations,
        "source_sha256": hashes.get("hyperframes") or next(iter(hashes.values()), ""),
        "skill_hashes": hashes,
        "note": pkg.get("note", ""),
    }


def _vendor_local_skill(name: str, pkg: dict, skills_dir: Path) -> dict:
    """Register an in-repo skill (no git clone)."""
    out_name = pkg.get("skill_dir_name", name)
    out_dir = skills_dir / out_name
    if not (out_dir / "SKILL.md").is_file():
        raise RuntimeError(
            f"[{name}] local skill missing: {out_dir.relative_to(ROOT).as_posix()}/SKILL.md"
        )
    return {
        "source_repository": None,
        "commit": None,
        "license": pkg.get("license", "project"),
        "usage": pkg.get("usage", "production_allowed"),
        "status": "local",
        "install_method": "local_skill",
        "destinations": [out_dir.relative_to(ROOT).as_posix()],
        "source_sha256": _tree_hash(out_dir),
        "remotion_primary_renderer": bool(pkg.get("remotion_primary_renderer", False)),
        "note": pkg.get("note", ""),
    }


def _vendor_git_package(name: str, pkg: dict, repos_dir: Path, skills_dir: Path) -> dict:
    url = pkg["source_repository"]
    dest = repos_dir / name
    sparse = list(pkg.get("sparse_paths") or [])
    commit = (pkg.get("commit") or "").strip()
    _ensure_git_repo(name, url, dest, sparse_paths=sparse, commit=commit)
    head = _git_head(dest)

    skill_hint = pkg.get("skill_source", "auto")
    out_name = pkg.get("skill_dir_name", name)
    out_dir = skills_dir / out_name

    if skill_hint == "curated_entry":
        if name in {"pixelle-video", "pixelle_video"} or out_name == "pixelle-video":
            _write_pixelle_video_entry(out_dir, dest)
        else:
            _write_openmontage_entry(out_dir, dest)
    elif skill_hint == "multi_named":
        _copy_named_skills(dest, skills_dir, pkg, out_dir)
    else:
        skill_root = _find_skill_root(dest, skill_hint)
        if skill_root is None:
            # Remotion skills repo: may nest under packages or skills/
            # Create a thin wrapper pointing at the repo README if no SKILL.md
            readme = dest / "README.md"
            out_dir.mkdir(parents=True, exist_ok=True)
            body = (
                f"# {out_name}\n\nVendored from {url} @ {head or 'HEAD'}.\n\n"
                f"Repo path: `{dest.relative_to(ROOT).as_posix()}`\n"
            )
            if readme.is_file():
                body += "\nSee vendored README in vendor/repos.\n"
            (out_dir / "SKILL.md").write_text(
                "---\n"
                f"name: {out_name}\n"
                f"description: Vendored skill from {url}\n"
                "trigger: video-related task matching this package\n"
                "inputs: []\n"
                "read_only: []\n"
                "outputs: []\n"
                "run: see SKILL body\n"
                "verify: skill files present\n"
                "stop_when: task complete or blocked\n"
                "on_missing_input: stop and report\n"
                "report_format: commands exit codes artifacts\n"
                "---\n\n"
                + body,
                encoding="utf-8",
            )
            # Also copy entire skills tree if present as siblings
            skills_folder = dest / "skills"
            if skills_folder.is_dir():
                for child in skills_folder.iterdir():
                    if child.is_dir() and (child / "SKILL.md").is_file():
                        _copy_tree(child, skills_dir / child.name)
        else:
            # If skill_root is repo root with one SKILL.md, copy that folder
            # If remotion has multiple skill dirs, copy all under skills/
            parent = skill_root.parent
            if skill_root.name != dest.name and parent.name in {"skills", "claude"}:
                # Copy all sibling skill packages
                for child in parent.iterdir():
                    if child.is_dir() and (child / "SKILL.md").is_file():
                        # For chatcut, nest under chatcut/ or flatten
                        if name == "chatcut":
                            nest = skills_dir / "chatcut" / child.name
                            nest.parent.mkdir(parents=True, exist_ok=True)
                            _copy_tree(child, nest)
                        else:
                            _copy_tree(child, skills_dir / child.name)
                # Ensure canonical dir exists for lock entry
                if not out_dir.exists():
                    if skill_root.is_dir():
                        _copy_tree(skill_root, out_dir)
            else:
                _copy_tree(skill_root, out_dir)

    if not out_dir.exists():
        # Ensure lock destination exists
        raise RuntimeError(f"[{name}] failed to produce {out_dir}")

    destinations = [out_dir.relative_to(ROOT).as_posix()]
    for extra in pkg.get("skill_names") or []:
        extra_path = skills_dir / extra
        if extra_path.is_dir() and extra_path != out_dir:
            destinations.append(extra_path.relative_to(ROOT).as_posix())

    return {
        "source_repository": url,
        "commit": head or commit or "",
        "license": pkg.get("license", "unknown"),
        "usage": pkg.get("usage", "production_allowed"),
        "status": "vendored",
        "install_method": "git_sparse_or_shallow",
        "repo_path": dest.relative_to(ROOT).as_posix(),
        "destinations": destinations,
        "source_sha256": _tree_hash(out_dir),
        "remotion_primary_renderer": bool(pkg.get("remotion_primary_renderer", False)),
        "note": pkg.get("note", ""),
    }


def _expand_target(target: str) -> Path:
    if target.startswith("~"):
        return Path(target).expanduser()
    return ROOT / target


def _sync_to_agent_dirs(skills_dir: Path, targets: list[str]) -> list[str]:
    synced: list[str] = []
    for target in targets:
        target_root = _expand_target(target)
        target_root.mkdir(parents=True, exist_ok=True)
        for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            if not any(skill.rglob("SKILL.md")):
                continue
            dst = target_root / skill.name
            _copy_tree(skill, dst)
            synced.append(str(dst))
    return synced


def _load_manifest() -> dict:
    if not MANIFEST.is_file():
        raise FileNotFoundError(f"manifest missing: {MANIFEST}")
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _update_lock(entries: dict[str, dict], check_only: bool) -> list[str]:
    lock_path = ROOT / "skills.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    third = lock.setdefault("third_party_skills", {})
    errors: list[str] = []
    now = datetime.now(timezone.utc).isoformat()
    changed = False
    for name, details in entries.items():
        current = third.get(name, {})
        if check_only:
            if current.get("status") not in {
                "vendored",
                "installed",
                "installed_offline_bundle",
                "local",
            }:
                errors.append(f"lock missing/invalid for {name}")
                continue
            # Overlay / npm install_skills may mutate these trees after pin.
            mutable = {"hyperframes", "video-use", "seedance-free"}
            if (
                details.get("source_sha256")
                and current.get("source_sha256") != details["source_sha256"]
            ):
                if name in mutable:
                    print(
                        f"[WARN] lock hash drift for {name} "
                        "(expected after overlays / install_skills)",
                        file=sys.stderr,
                    )
                else:
                    errors.append(f"lock hash mismatch for {name}")
            continue
        merged = {**current, **details, "installed_at": now}
        if json.dumps(current, sort_keys=True) != json.dumps(merged, sort_keys=True):
            third[name] = merged
            changed = True
        else:
            third[name] = merged
    if not check_only and (changed or True):
        lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Vendor video third-party skills")
    parser.add_argument("--check", action="store_true", help="Verify only")
    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Only sync existing third_party_skills (no network)",
    )
    args = parser.parse_args()

    try:
        manifest = _load_manifest()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    defaults = manifest.get("defaults") or {}
    repos_dir = ROOT / defaults.get("repos_dir", "vendor/repos")
    skills_dir = ROOT / defaults.get("skills_dir", "third_party_skills")
    targets = list(defaults.get("sync_targets") or [".claude/skills", ".agents/skills"])
    global_targets = list(defaults.get("global_sync_targets") or [])
    packages: dict = manifest.get("packages") or {}

    if not args.check and not args.skip_git:
        skills_dir.mkdir(parents=True, exist_ok=True)

    entries: dict[str, dict] = {}
    failures: list[str] = []

    for name, pkg in packages.items():
        kind = pkg.get("kind")
        try:
            if args.check or args.skip_git:
                out_name = pkg.get("skill_dir_name", name)
                # hyperframes installs multiple
                if kind == "npm_bundle":
                    for sn in pkg.get("skill_names") or ["hyperframes"]:
                        path = skills_dir / sn
                        if not path.is_dir():
                            failures.append(f"missing third_party_skills/{sn}")
                        else:
                            entries[sn if sn != "hyperframes-cli" else "hyperframes"] = {
                                "source_sha256": _tree_hash(path),
                                "status": "vendored",
                            }
                    # Keep single hyperframes lock key; also note cli
                    if (skills_dir / "hyperframes").is_dir():
                        entries["hyperframes"] = {
                            "source_repository": pkg["source_repository"],
                            "source_sha256": _tree_hash(skills_dir / "hyperframes"),
                            "status": "vendored",
                            "usage": pkg.get("usage"),
                            "license": pkg.get("license"),
                        }
                    continue
                path = skills_dir / out_name
                if not path.is_dir():
                    failures.append(f"missing third_party_skills/{out_name}")
                    continue
                status = "local" if kind == "local_skill" else "vendored"
                entries[name] = {
                    "source_repository": pkg.get("source_repository"),
                    "source_sha256": _tree_hash(path),
                    "status": status,
                    "usage": pkg.get("usage"),
                    "license": pkg.get("license"),
                    "remotion_primary_renderer": bool(pkg.get("remotion_primary_renderer", False)),
                }
                continue

            print(f"[vendor] {name} ...")
            if kind == "npm_bundle":
                entries["hyperframes"] = _vendor_npm_hyperframes(pkg, skills_dir)
            elif kind == "git_skills":
                entries[name] = _vendor_git_package(name, pkg, repos_dir, skills_dir)
            elif kind == "local_skill":
                entries[name] = _vendor_local_skill(name, pkg, skills_dir)
            elif kind == "curated_skill":
                entries[name] = _vendor_curated_skill(name, pkg, skills_dir)
            else:
                failures.append(f"unknown kind for {name}: {kind}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
            print(f"[WARN] {name}: {exc}", file=sys.stderr)

    if not args.check:
        synced = _sync_to_agent_dirs(skills_dir, targets + global_targets)
        print(f"[sync] copied {len(synced)} skill trees to agent dirs")
        lock_errors = _update_lock(entries, check_only=False)
    else:
        lock_errors = _update_lock(entries, check_only=True)

    failures.extend(lock_errors)

    # Existence check for project agent dirs only
    project_targets = [t for t in targets if not t.startswith("~")]
    for name in entries:
        for target in project_targets:
            skill_name = name
            path = ROOT / target / skill_name
            if not path.is_dir():
                if name == "chatcut" and (ROOT / target / "chatcut").is_dir():
                    continue
                failures.append(f"missing {target}/{skill_name}")

    if failures:
        print("[FAIL] vendor check failed:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    if not args.check and not args.skip_git:
        # Free-provider overlays mutate video-use / seedance-free; refresh lock hashes.
        overlay = ROOT / "scripts" / "apply_free_provider_overlays.py"
        if overlay.is_file():
            ov = _run([sys.executable, str(overlay)], cwd=ROOT)
            if ov.returncode != 0:
                print(ov.stdout or "", end="")
                print(ov.stderr or "", file=sys.stderr)
                print("[FAIL] apply_free_provider_overlays failed", file=sys.stderr)
                return 1
            if ov.stdout:
                print(ov.stdout.strip())

    print(f"[OK] vendored {len(entries)} third-party skill packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
