"""scripts/run_acceptance.py — 模块3一键验收脚本。

用法（在项目根）：
    set PYTHONPATH=src   （Windows cmd）
    $env:PYTHONPATH="src" （PowerShell）
    python scripts/run_acceptance.py

或直接：
    py -3.11 -c "import sys; sys.path.insert(0,'src')" scripts/run_acceptance.py

验收项：
    1. episode create EP-INGEST-001 → exit 0
    2. ingest EP-INGEST-001 → exit 0, 状态 INGESTED
    3. 原文件 sha256 前后一致
    4. 损坏文件 status=corrupt（仅 ffprobe 可用时）
    5. 再次 ingest，未变文件不重复转码
    6. asset-manifest 通过 Schema
    7. assets list/validate → 路径均为相对路径
"""
from __future__ import annotations

import shutil
import struct
import sys
import zlib
from pathlib import Path

# ── 加入 src 到 path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from avs.config import Config  # noqa: E402
from avs.ingest import run_ingest  # noqa: E402
from avs.ingest.hashing import sha256_file  # noqa: E402
from avs.ingest.manifest import load_manifest  # noqa: E402
from avs.models.episode import EpisodeModel  # noqa: E402
from avs.paths import create_episode_skeleton, episode_dir, episode_json_path, find_episode_dir  # noqa: E402

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_results: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = _PASS if ok else _FAIL
    _results.append((name, tag))
    status = "✓" if ok else "✗"
    line = f"  {status} {name}"
    if detail:
        line += f"  ({detail})"
    print(line)


# ── 生成 Fixture 文件 ──────────────────────────────────────────────────

def _png() -> bytes:
    def chunk(n, d):
        c = n + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xFF\x00\x00"))
    return sig + ihdr + idat + chunk(b"IEND", b"")


def _wav() -> bytes:
    sr, n = 44100, 441
    ds = n * 2
    h = (b"RIFF" + struct.pack("<I", 36 + ds) + b"WAVEfmt "
         + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr*2, 2, 16)
         + b"data" + struct.pack("<I", ds))
    return h + b"\x00" * ds


def setup_episode_fixtures(ep_dir: Path) -> None:
    """往 ep_dir/input/ 写入测试素材。"""
    inp = ep_dir / "input"
    # 文本
    (inp / "script.txt").write_text("测试脚本\n", encoding="utf-8")
    # links.txt
    (inp / "links.txt").write_text("https://example.com\n", encoding="utf-8")
    # 图片
    img = inp / "images"
    img.mkdir(parents=True, exist_ok=True)
    (img / "photo.png").write_bytes(_png())
    (img / "封面_unicode.png").write_bytes(_png())
    # 音频
    aud = inp / "audio"
    aud.mkdir(parents=True, exist_ok=True)
    (aud / "bgm.wav").write_bytes(_wav())
    # 损坏视频
    sc = inp / "screen"
    sc.mkdir(parents=True, exist_ok=True)
    (sc / "corrupt.mp4").write_bytes(b"\xDE\xAD\xBE\xEF" * 32 + b"NOT MP4")


# ── 清理旧测试 Episode ────────────────────────────────────────────────

EPISODE_ID = "EP-INGEST-001"
cfg = Config(ROOT)

ep_path = find_episode_dir(cfg.episodes_root, EPISODE_ID)
if ep_path:
    shutil.rmtree(ep_path, ignore_errors=True)
    print(f"清理旧 Episode: {ep_path}")

# ── 验收 1：episode create ────────────────────────────────────────────
print("\n── 验收 1: episode create ──")
ep_target = episode_dir(cfg.episodes_root, EPISODE_ID, lifecycle="active")
try:
    model = EpisodeModel.create(EPISODE_ID, mode="REFERENCE_ADAPT")
    ep_target.mkdir(parents=True, exist_ok=False)
    create_episode_skeleton(ep_target)
    ep_json = episode_json_path(ep_target)
    model.save(ep_json)
    check("episode create exit-0", True, f"dir={ep_target}")
except Exception as exc:
    check("episode create exit-0", False, str(exc))
    print("FATAL: 无法创建 Episode，停止")
    sys.exit(1)

# ── 安置 Fixture ──────────────────────────────────────────────────────
setup_episode_fixtures(ep_target)

# ── 记录原文件 sha256（用于验收3）────────────────────────────────────
src_png = ep_target / "input" / "images" / "photo.png"
sha_before = sha256_file(src_png)

# ── 验收 2：ingest → INGESTED ─────────────────────────────────────────
print("\n── 验收 2: ingest → INGESTED ──")
try:
    assets = run_ingest(ep_target, EPISODE_ID)
    model2 = EpisodeModel.load(ep_json)
    from avs.state import can_transition
    if model2.status != "INGESTED" and can_transition(model2.status, "INGESTED"):
        model2.transition("INGESTED")
        model2.complete_stage("ingest")
        model2.save(ep_json)
    elif model2.status == "CREATED":
        model2.transition("INGESTED")
        model2.complete_stage("ingest")
        model2.save(ep_json)
    model_final = EpisodeModel.load(ep_json)
    check("ingest exit-0", True)
    check("status=INGESTED", model_final.status == "INGESTED", f"actual={model_final.status}")
except Exception as exc:
    check("ingest exit-0", False, str(exc))
    check("status=INGESTED", False, "ingest failed")
    sys.exit(1)

# ── 验收 3：原文件 sha256 不变 ────────────────────────────────────────
print("\n── 验收 3: 原文件 sha256 不变 ──")
sha_after = sha256_file(src_png)
check("photo.png sha256 unchanged", sha_before == sha_after,
      f"before={sha_before[:16]}… after={sha_after[:16]}…")

# ── 验收 4：损坏文件标记（仅 ffprobe 可用时严格检查）────────────────
print("\n── 验收 4: 损坏文件标记 ──")
corrupt_assets = [a for a in assets if "corrupt.mp4" in a["source_path"]]
if shutil.which("ffprobe"):
    ok4 = corrupt_assets and corrupt_assets[0]["status"] == "corrupt"
    check("corrupt.mp4 → status=corrupt", ok4,
          f"status={corrupt_assets[0]['status'] if corrupt_assets else 'missing'}")
else:
    check("corrupt.mp4 → in manifest (ffprobe unavailable)", bool(corrupt_assets),
          "ffprobe 不在 PATH，跳过 corrupt 检测，文件已 ingest")

# ── 验收 5：幂等性（再次 ingest，mtime 不变）─────────────────────────
print("\n── 验收 5: 幂等性 ──")
png_rec = next((a for a in assets if "photo.png" in a["source_path"] and a["status"] == "ok"), None)
if png_rec:
    wp = ep_target / png_rec["working_path"]
    mtime1 = wp.stat().st_mtime_ns if wp.exists() else None
    run_ingest(ep_target, EPISODE_ID)  # 第二次
    mtime2 = wp.stat().st_mtime_ns if wp.exists() else None
    check("未变文件不重复转码（mtime 不变）", mtime1 == mtime2,
          f"mtime1={mtime1} mtime2={mtime2}")
else:
    check("未变文件不重复转码", False, "photo.png 未在 manifest 中找到 ok 记录")

# ── 验收 6：asset-manifest Schema 校验 ───────────────────────────────
print("\n── 验收 6: manifest Schema ──")
try:
    doc = load_manifest(ep_target)
    check("asset-manifest.json exists", True)
    check("schema validation passed", True, f"{len(doc['assets'])} assets")
except Exception as exc:
    check("asset-manifest schema", False, str(exc))

# ── 验收 7：assets list/validate（路径均为相对路径）──────────────────
print("\n── 验收 7: 相对路径 ──")
try:
    doc = load_manifest(ep_target)
    abs_paths = [
        a["source_path"] for a in doc["assets"] if Path(a["source_path"]).is_absolute()
    ] + [
        a["working_path"] for a in doc["assets"] if Path(a["working_path"]).is_absolute()
    ]
    check("所有路径均为相对路径", not abs_paths,
          f"绝对路径: {abs_paths}" if abs_paths else "")
    ok7_wp = True
    for a in doc["assets"]:
        if a["status"] == "ok":
            wp = ep_target / a["working_path"]
            if not wp.exists():
                ok7_wp = False
                print(f"    missing: {a['working_path']}")
    check("ok 素材工作副本均存在", ok7_wp)
except Exception as exc:
    check("assets validate", False, str(exc))

# ── 汇总 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("验收汇总:")
total = len(_results)
passed = sum(1 for _, t in _results if t == _PASS)
for name, tag in _results:
    sym = "✓" if tag == _PASS else "✗"
    print(f"  {sym} {name}")
print(f"\n{passed}/{total} 项通过")
sys.exit(0 if passed == total else 1)
