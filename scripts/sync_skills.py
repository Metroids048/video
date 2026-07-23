"""scripts/sync_skills.py — 将 skills-src/ 同步到各 Agent 目标目录。

用法：
  python scripts/sync_skills.py          # 执行同步
  python scripts/sync_skills.py --check  # 只检查，不修改文件

规则：
- 使用复制而非符号链接（Windows 兼容）
- 幂等：相同内容不重复写入
- 每个 Skill 目录必须有 SKILL.md 且包含必需 frontmatter
- 仅同步 skills-src/ 中的项目自有 Skill，不同步第三方 Skill
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FRONTMATTER_FIELDS = [
    "trigger",
    "inputs",
    "read_only",
    "outputs",
    "run",
    "verify",
    "stop_when",
    "on_missing_input",
    "report_format",
]

TARGETS = [
    ".claude/skills",
    ".agents/skills",
]


def _compute_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compute_tree_hash(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        digest.update(path.relative_to(skill_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _update_or_check_lock(root: Path, skill_dirs: list[Path], check_only: bool) -> list[str]:
    lock_path = root / "skills.lock.json"
    if not lock_path.exists():
        return ["skills.lock.json 不存在"]
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"skills.lock.json 无法读取: {exc}"]

    entries = lock.setdefault("project_skills", {})
    errors: list[str] = []
    changed = False
    for skill_dir in skill_dirs:
        expected_hash = _compute_tree_hash(skill_dir)
        entry = entries.get(skill_dir.name)
        if not isinstance(entry, dict):
            errors.append(f"skills.lock.json 缺少项目 Skill: {skill_dir.name}")
            continue
        if check_only:
            if entry.get("status") != "synced" or entry.get("source_sha256") != expected_hash:
                errors.append(f"skills.lock.json 状态过期: {skill_dir.name}")
            continue
        if entry.get("status") != "synced" or entry.get("source_sha256") != expected_hash:
            entry["status"] = "synced"
            entry["source_sha256"] = expected_hash
            changed = True

    if changed:
        lock["locked_at"] = datetime.now(timezone.utc).isoformat()
        lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return errors


def _validate_skill(skill_dir: Path) -> list[str]:
    """校验 SKILL.md 是否包含必需 frontmatter 字段，返回缺失字段列表。"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return ["SKILL.md not found"]
    content = skill_md.read_text(encoding="utf-8")
    missing = [f for f in REQUIRED_FRONTMATTER_FIELDS if f not in content]
    return missing


def sync_skills(root: Path, check_only: bool = False) -> int:
    """同步 skills-src/ → 各 Target。返回 0=成功，1=失败。"""
    src_dir = root / "skills-src"
    if not src_dir.exists():
        print(f"[ERROR] skills-src/ 不存在: {src_dir}", file=sys.stderr)
        return 1

    skill_dirs = [d for d in src_dir.iterdir() if d.is_dir()]
    if not skill_dirs:
        print("[WARN] skills-src/ 中没有 Skill 目录")
        return 0

    errors: list[str] = []
    synced = 0
    skipped = 0

    for skill_dir in sorted(skill_dirs):
        missing_fields = _validate_skill(skill_dir)
        if missing_fields:
            errors.append(f"{skill_dir.name}: SKILL.md 缺少字段 {missing_fields}")
            continue

        for target_rel in TARGETS:
            target_dir = root / target_rel / skill_dir.name
            if not check_only:
                target_dir.mkdir(parents=True, exist_ok=True)

            for src_file in skill_dir.rglob("*"):
                if src_file.is_dir():
                    continue
                rel = src_file.relative_to(skill_dir)
                dst_file = target_dir / rel

                if not check_only:
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    if dst_file.exists() and _compute_hash(src_file) == _compute_hash(dst_file):
                        skipped += 1
                        continue
                    shutil.copy2(src_file, dst_file)
                    synced += 1
                else:
                    if not dst_file.exists():
                        errors.append(f"未同步: {target_rel}/{skill_dir.name}/{rel}")
                    elif _compute_hash(src_file) != _compute_hash(dst_file):
                        errors.append(f"内容不同步: {target_rel}/{skill_dir.name}/{rel}")

    errors.extend(_update_or_check_lock(root, skill_dirs, check_only))

    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    if check_only:
        print(f"[OK] Skills 同步状态一致（{len(skill_dirs)} skills）")
    else:
        print(f"[OK] 同步完成：{synced} 文件已更新，{skipped} 文件已跳过（内容相同）")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="同步 skills-src/ 到各 Agent 目标目录")
    parser.add_argument("--check", action="store_true", help="只检查，不修改文件")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    sys.exit(sync_skills(root, check_only=args.check))


if __name__ == "__main__":
    main()
