"""Diagnose video third-party skills/plugins readiness."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            shell=False,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def main() -> None:
    lock = json.loads((ROOT / "skills.lock.json").read_text(encoding="utf-8"))
    print("=== lock third_party ===")
    for k, v in sorted(lock.get("third_party_skills", {}).items()):
        commit = (v.get("commit") or "")[:12]
        print(f"{k}: status={v.get('status')} usage={v.get('usage')} commit={commit}")

    print("=== skill dirs ===")
    for d in [
        "third_party_skills",
        ".claude/skills",
        ".agents/skills",
        ".cursor/skills",
    ]:
        p = ROOT / d
        n = len([x for x in p.iterdir() if x.is_dir()]) if p.is_dir() else 0
        print(f"{d}: {'OK' if p.is_dir() else 'MISSING'} dirs={n}")

    home = Path.home()
    print("=== global skill homes ===")
    for d in [".claude/skills", ".codex/skills", ".cursor/skills"]:
        p = home / d
        n = len([x for x in p.iterdir() if x.is_dir()]) if p.is_dir() else 0
        print(f"~/{d}: {'OK' if p.is_dir() else 'MISSING'} dirs={n}")

    print("=== CLIs ===")
    checks = [
        ([str(ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"), "--version"], "hyperframes-local"),
        (["where", "capcut-david"], "capcut-david"),
        (["where", "chatcut"], "chatcut"),
        (["ffmpeg", "-version"], "ffmpeg"),
        (["ffprobe", "-version"], "ffprobe"),
        (["node", "--version"], "node"),
    ]
    for cmd, label in checks:
        if label == "hyperframes-local":
            code, out = run(["node", *cmd])
        else:
            code, out = run(cmd)
        line = out.splitlines()[0] if out else ""
        print(f"{label}: rc={code} {line[:120]}")

    vu_helpers = ROOT / "third_party_skills" / "video-use" / "helpers"
    print(f"video-use helpers: {vu_helpers.is_dir()}")

    print("=== vendor repos ===")
    repos = ROOT / "vendor" / "repos"
    if repos.is_dir():
        for p in sorted(repos.iterdir()):
            if p.is_dir():
                print(f"  {p.name}: OK")
    else:
        print("  MISSING vendor/repos")

    print("=== env hints ===")
    for key in ["ELEVENLABS_API_KEY", "AGENT_PYTHON", "KIE_API_KEY", "SEEDANCE_API_KEY"]:
        print(f"  {key}: {'set' if os.environ.get(key) else 'unset'}")

    print("=== npm local ===")
    hf = ROOT / "node_modules" / "hyperframes"
    print(f"  hyperframes package: {hf.is_dir()}")


if __name__ == "__main__":
    main()
