"""scripts/ensure_video_plugins.py — 一键安装并打通视频第三方 Skills/CLI。

可无人值守完成：
- re-vendor + 同步到项目/全局 skills 目录
- 安装 capcut-david、@chatcut/skill（若可）
- 安装 video-use Python 依赖
- 校验 hyperframes 本地 CLI / browser
- 写入 readiness 报告

需要用户协助（无法代办）时写入 reports/video-plugins-readiness.md：
- ChatCut MCP 登录
- ElevenLabs / Seedance(Kie) API Key
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "video-plugins-readiness.md"


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 600) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def _which(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        for suffix in (".cmd", ".exe", ".bat"):
            found = shutil.which(name + suffix)
            if found:
                return found
    return None


def _npm_cmd(*args: str) -> list[str]:
    npm = _which("npm.cmd") or _which("npm")
    if not npm:
        raise RuntimeError("npm not found on PATH")
    return [npm, *args]


def _node_cmd(*args: str) -> list[str]:
    node = _which("node.exe") or _which("node")
    if not node:
        raise RuntimeError("node not found on PATH")
    return [node, *args]


def step_vendor() -> tuple[bool, str]:
    code, out = _run(_node_cmd("scripts/run-python.mjs", "scripts/vendor_video_skills.py"), timeout=900)
    code2, out2 = _run(_node_cmd("scripts/run-python.mjs", "scripts/apply_free_provider_overlays.py"))
    return code == 0 and code2 == 0, (out + "\n" + out2)[-2000:]


def step_hyperframes() -> tuple[bool, str]:
    cli = ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    notes: list[str] = []
    if not cli.is_file():
        code, out = _run(_npm_cmd("install"), timeout=600)
        notes.append(out[-500:])
        if code != 0:
            return False, "npm install failed\n" + "\n".join(notes)
    code, out = _run(_node_cmd(str(cli), "--version"))
    notes.append(f"hyperframes version rc={code} {out}")
    if code != 0:
        return False, "\n".join(notes)
    # browser ensure — best effort
    code_b, out_b = _run(_node_cmd(str(cli), "browser", "ensure"), timeout=600)
    notes.append(f"browser ensure rc={code_b} {out_b[-400:]}")
    # skills install into globals via existing script
    code_s, out_s = _run(_node_cmd("scripts/install_skills.mjs"), timeout=300)
    notes.append(f"install_skills rc={code_s} {out_s[-400:]}")
    return True, "\n".join(notes)


def step_capcut() -> tuple[bool, str]:
    binary = _which("capcut-david")
    if binary:
        code, out = _run([binary, "--help"])
        return code == 0, f"{binary}\n{out[:500]}"
    vendor = ROOT / "vendor" / "repos" / "capcut-david"
    if (vendor / "package.json").is_file() and (vendor / "dist" / "index.js").is_file():
        code, out = _run(_npm_cmd("link"), cwd=vendor, timeout=300)
        binary = _which("capcut-david")
        if code == 0 and binary:
            return True, f"linked from vendor\n{binary}\n{out[-300:]}"
    code, out = _run(_npm_cmd("install", "-g", "capcut-cli-david@2.5.0"), timeout=600)
    binary = _which("capcut-david")
    ok = code == 0 and bool(binary)
    return ok, f"binary={binary}\n{out[-800:]}"


def step_chatcut_cli() -> tuple[bool, str]:
    if _which("chatcut"):
        return True, f"chatcut on PATH: {_which('chatcut')}"
    last = ""
    for pkg in ("@chatcut/skill", "chatcut"):
        code, out = _run(_npm_cmd("install", "-g", pkg), timeout=600)
        last = out
        if code == 0 and _which("chatcut"):
            return True, f"installed {pkg}\n{_which('chatcut')}\n{out[-400:]}"
    # Soft-ok if skills exist
    basics = ROOT / "third_party_skills" / "chatcut" / "chatcut-plugin-basics-claude" / "SKILL.md"
    if basics.is_file():
        return True, f"CLI missing but skills present at {basics.parent}\n{last[-300:]}"
    return False, f"chatcut CLI/skills missing\n{last[-400:]}"


def step_video_use_deps() -> tuple[bool, str]:
    repo = ROOT / "vendor" / "repos" / "video-use"
    helpers = repo / "helpers"
    skill_helpers = ROOT / "third_party_skills" / "video-use" / "helpers"
    notes: list[str] = []
    if not helpers.is_dir():
        return False, "vendor/repos/video-use/helpers missing — re-run vendor"
    if not skill_helpers.is_dir():
        return False, "third_party_skills/video-use/helpers missing — re-run vendor"
    py = os.environ.get("AGENT_PYTHON") or sys.executable
    code, out = _run([py, "-m", "pip", "install", "-e", str(repo)], timeout=600)
    notes.append(out[-600:])
    # smoke: import helpers path
    smoke = _run(
        [
            py,
            "-c",
            f"import sys; sys.path.insert(0, r'{repo}'); from pathlib import Path; "
            f"assert Path(r'{helpers}').is_dir(); print('helpers-ok')",
        ]
    )
    notes.append(smoke[1])
    return code == 0 and smoke[0] == 0, "\n".join(notes)


def step_remotion_runtime() -> tuple[bool, str]:
    # Keep lightweight: ensure remotion skills present; optional npx create-video not required
    skills = ROOT / "third_party_skills" / "remotion-best-practices" / "SKILL.md"
    if not skills.is_file():
        return False, "remotion-best-practices missing"
    # Install remotion CLI as project optional for agent use
    code, out = _run(
        _npm_cmd("install", "--no-save", "--no-package-lock", "@remotion/cli@4"),
        timeout=600,
    )
    # Don't fail hard if network blocks — skills are enough for routing
    notes = [f"@remotion/cli install rc={code}", out[-400:]]
    return skills.is_file(), "\n".join(notes)


def step_cut_skill() -> tuple[bool, str]:
    skill = ROOT / "third_party_skills" / "cut-skill" / "SKILL.md"
    if not skill.is_file():
        return False, "cut-skill missing"
    # Optional: install python deps commonly needed
    py = os.environ.get("AGENT_PYTHON") or sys.executable
    code, out = _run([py, "-m", "pip", "install", "pymiere"], timeout=300)
    return True, f"skill present; pymiere pip rc={code} {out[-200:]}"


def step_seedance_tools() -> tuple[bool, str]:
    tools = ROOT / "third_party_skills" / "seedance" / "tools"
    skill = ROOT / "third_party_skills" / "seedance" / "SKILL.md"
    if not skill.is_file():
        return False, "seedance skill missing"
    return True, f"skill OK; tools_dir={tools.is_dir()}"


def step_openmontage() -> tuple[bool, str]:
    guide = ROOT / "vendor" / "repos" / "openmontage" / "AGENT_GUIDE.md"
    entry = ROOT / "third_party_skills" / "openmontage" / "SKILL.md"
    ok = guide.is_file() and entry.is_file()
    return ok, f"guide={guide.is_file()} entry={entry.is_file()}"


def step_ip_strategist() -> tuple[bool, str]:
    p = ROOT / "third_party_skills" / "ip-strategist" / "SKILL.md"
    return p.is_file(), f"present={p.is_file()}"


def step_free_providers() -> tuple[bool, str]:
    py = os.environ.get("AGENT_PYTHON") or sys.executable
    notes: list[str] = []
    code, out = _run([py, "-c", "from faster_whisper import WhisperModel; print('ok')"])
    notes.append(f"faster-whisper import rc={code} {out}")
    if code != 0:
        code_i, out_i = _run([py, "-m", "pip", "install", "faster-whisper>=1.0.0"], timeout=600)
        notes.append(out_i[-300:])
        code, out = _run([py, "-c", "from faster_whisper import WhisperModel; print('ok')"])
        notes.append(f"retry import rc={code} {out}")
    whisper_script = ROOT / "scripts" / "free_providers" / "whisper_transcribe.py"
    image_script = ROOT / "scripts" / "free_providers" / "image_to_clip.py"
    free_skill = ROOT / "third_party_skills" / "seedance-free" / "SKILL.md"
    ok = code == 0 and whisper_script.is_file() and image_script.is_file() and free_skill.is_file()
    return ok, "\n".join(notes)


def _user_needed() -> list[str]:
    needed: list[str] = []
    # Free defaults now exist — only note optional paid upgrades
    needed.append(
        "（可选付费升级）ElevenLabs：仅当免费 Whisper 不够用时再配 ELEVENLABS_API_KEY"
    )
    needed.append(
        "（可选付费升级）Seedance/Kie：仅当需要生成式视频时再配 KIE_API_KEY；"
        "默认用 seedance-free（FFmpeg Ken Burns）或 OpenMontage"
    )
    # ChatCut login status — soft reminder
    needed.append(
        "ChatCut：若已 `chatcut login` 成功可忽略；Claude Code MCP 插件路径仍需 marketplace install 后新会话"
    )
    return needed


def write_report(results: dict[str, tuple[bool, str]], needed: list[str]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Video Plugins Readiness",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Automated results",
        "",
        "| Step | OK | Notes |",
        "|------|----|-------|",
    ]
    for name, (ok, note) in results.items():
        short = note.replace("\n", " ")[:120]
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {short} |")
    lines.extend(["", "## Needs user action", ""])
    if needed:
        for item in needed:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Re-run",
            "",
            "```bash",
            "npm run skills:ensure",
            "```",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    results: dict[str, tuple[bool, str]] = {}
    print("[ensure] vendor ...")
    results["vendor"] = step_vendor()
    print(f"  -> {'OK' if results['vendor'][0] else 'FAIL'}")

    steps = [
        ("hyperframes", step_hyperframes),
        ("capcut-david", step_capcut),
        ("chatcut-cli", step_chatcut_cli),
        ("video-use-deps", step_video_use_deps),
        ("remotion", step_remotion_runtime),
        ("cut-skill", step_cut_skill),
        ("seedance", step_seedance_tools),
        ("free-providers", step_free_providers),
        ("openmontage", step_openmontage),
        ("ip-strategist", step_ip_strategist),
    ]
    for name, fn in steps:
        print(f"[ensure] {name} ...")
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001
            results[name] = (False, str(exc))
        print(f"  -> {'OK' if results[name][0] else 'FAIL'}")

    needed = _user_needed()
    write_report(results, needed)

    # Critical path: vendor + hyperframes + skill files must pass
    critical = [
        "vendor",
        "hyperframes",
        "video-use-deps",
        "remotion",
        "capcut-david",
        "seedance",
        "free-providers",
        "openmontage",
        "ip-strategist",
        "cut-skill",
    ]
    hard_fail = [k for k in critical if not results.get(k, (False, ""))[0]]
    # chatcut-cli is soft — skills may exist without CLI
    print(f"[report] {REPORT}")
    if hard_fail:
        print("[FAIL] critical steps:", ", ".join(hard_fail))
        return 1
    print("[OK] critical plugins installed/wired; see report for user-only items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
