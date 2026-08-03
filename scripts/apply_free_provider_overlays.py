"""Apply free-provider overlays onto third_party_skills after vendoring."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS = ROOT / "vendor" / "overlays"
SKILLS = ROOT / "third_party_skills"
LOCK = ROOT / "skills.lock.json"
TARGETS = [
    ROOT / ".claude" / "skills",
    ROOT / ".agents" / "skills",
    ROOT / ".cursor" / "skills",
]


def _tree_hash(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        digest.update(path.relative_to(skill_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _refresh_lock_hashes(touched: set[str]) -> None:
    """Keep skills.lock.json hashes aligned after overlay mutation."""
    if not LOCK.is_file() or not touched:
        return
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    third = lock.setdefault("third_party_skills", {})
    now = datetime.now(timezone.utc).isoformat()
    for name in sorted(touched):
        path = SKILLS / name
        if not path.is_dir():
            continue
        entry = third.setdefault(name, {})
        entry["source_sha256"] = _tree_hash(path)
        entry["installed_at"] = now
    LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    if not OVERLAYS.is_dir():
        print("[OK] no overlays")
        return 0
    copied = 0
    touched: set[str] = set()
    for src in OVERLAYS.rglob("*"):
        if not src.is_file() or src.name == "README.md":
            continue
        rel = src.relative_to(OVERLAYS)
        dest = SKILLS / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1
        if rel.parts:
            touched.add(rel.parts[0])
        for t in TARGETS:
            if not t.is_dir():
                continue
            agent_dest = t / rel
            agent_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, agent_dest)
    free = SKILLS / "seedance-free"
    if free.is_dir():
        touched.add("seedance-free")
        for t in TARGETS:
            if t.is_dir():
                dst = t / "seedance-free"
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(free, dst)
    # Packages that overlays / ensure commonly mutate
    touched.update({"video-use", "seedance-free", "hyperframes"})
    _refresh_lock_hashes(touched)
    print(f"[OK] applied {copied} overlay files + seedance-free sync; lock hashes refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
