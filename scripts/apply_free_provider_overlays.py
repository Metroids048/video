"""Apply free-provider overlays onto third_party_skills after vendoring."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS = ROOT / "vendor" / "overlays"
SKILLS = ROOT / "third_party_skills"
TARGETS = [
    ROOT / ".claude" / "skills",
    ROOT / ".agents" / "skills",
    ROOT / ".cursor" / "skills",
]


def main() -> int:
    if not OVERLAYS.is_dir():
        print("[OK] no overlays")
        return 0
    copied = 0
    for src in OVERLAYS.rglob("*"):
        if not src.is_file() or src.name == "README.md":
            continue
        rel = src.relative_to(OVERLAYS)
        dest = SKILLS / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1
        for t in TARGETS:
            if not t.is_dir():
                continue
            # map video-use/... into each agent skills tree
            agent_dest = t / rel
            agent_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, agent_dest)
    # ensure seedance-free is synced
    free = SKILLS / "seedance-free"
    if free.is_dir():
        for t in TARGETS:
            if t.is_dir():
                dst = t / "seedance-free"
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(free, dst)
    print(f"[OK] applied {copied} overlay files + seedance-free sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
