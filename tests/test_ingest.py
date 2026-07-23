"""tests/test_ingest.py — 模块3验收测试。"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

# 确保 src 在 path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from avs.ingest import run_ingest
from avs.ingest.discovery import discover_inputs
from avs.ingest.hashing import sha256_file
from avs.ingest.manifest import load_manifest, manifest_path
from avs.ingest.normalize import prepared_path
from avs.ingest.errors import PathTraversalError
from avs.paths import create_episode_skeleton
from avs.cli import main
from avs.models.episode import EpisodeModel


# ── Fixture helpers ───────────────────────────────────────────────────

def _make_png(path: Path) -> None:
    import struct
    import zlib
    def chunk(name, data):
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xFF\x00\x00"
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sig + ihdr + idat + iend)


def _make_wav(path: Path) -> None:
    import struct
    sr, n = 44100, 441
    data_size = n * 2
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)


@pytest.fixture()
def ep_dir(tmp_path: Path) -> Path:
    """创建含 fixture 素材的 Episode 目录。"""
    d = tmp_path / "EP-TEST-001"
    d.mkdir()
    create_episode_skeleton(d)

    inp = d / "input"
    # 文本
    (inp / "notes.txt").write_text("测试笔记\n", encoding="utf-8")
    # links.txt
    (inp / "links.txt").write_text("https://example.com\n", encoding="utf-8")
    # 图片
    _make_png(inp / "images" / "photo.png")
    # Unicode 文件名
    _make_png(inp / "images" / "照片_测试.png")
    # 音频
    _make_wav(inp / "audio" / "bgm.wav")
    # 损坏视频（垃圾字节 .mp4）
    corrupt = inp / "screen" / "corrupt.mp4"
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_bytes(b"\xDE\xAD\xBE\xEF" * 8 + b"NOT A REAL MP4")

    return d


# ── 测试用例 ──────────────────────────────────────────────────────────

class TestDiscovery:
    def test_finds_all_files(self, ep_dir: Path) -> None:
        files = discover_inputs(ep_dir)
        assert len(files) >= 5

    def test_links_txt_kind(self, ep_dir: Path) -> None:
        files = discover_inputs(ep_dir)
        link_files = [f for f in files if f.kind == "link"]
        assert len(link_files) == 1

    def test_image_kind(self, ep_dir: Path) -> None:
        files = discover_inputs(ep_dir)
        imgs = [f for f in files if f.kind == "image"]
        assert len(imgs) >= 2

    def test_unicode_filename(self, ep_dir: Path) -> None:
        files = discover_inputs(ep_dir)
        names = [f.abs_path.name for f in files]
        assert any("测试" in n for n in names)

    def test_all_paths_relative(self, ep_dir: Path) -> None:
        files = discover_inputs(ep_dir)
        for f in files:
            assert not Path(f.rel_path).is_absolute(), f"绝对路径: {f.rel_path}"

    def test_gitkeep_excluded(self, ep_dir: Path) -> None:
        (ep_dir / "input" / ".gitkeep").write_bytes(b"")
        files = discover_inputs(ep_dir)
        assert all(".gitkeep" not in f.rel_path for f in files)

    def test_symlink_escape_rejected(self, ep_dir: Path, tmp_path: Path) -> None:
        if not hasattr(Path, "symlink_to"):
            pytest.skip("symlink unsupported")
        outside = tmp_path / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = ep_dir / "input" / "escape.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlink privilege unavailable")
        with pytest.raises(PathTraversalError):
            discover_inputs(ep_dir)


class TestPreparedPath:
    def test_rejects_parent_traversal(self, ep_dir: Path) -> None:
        with pytest.raises(PathTraversalError):
            prepared_path(ep_dir, "input/../../escape.txt")


class TestHashing:
    def test_sha256_deterministic(self, tmp_path: Path) -> None:
        p = tmp_path / "file.txt"
        p.write_bytes(b"hello world")
        h1 = sha256_file(p)
        h2 = sha256_file(p)
        assert h1 == h2
        assert len(h1) == 64
        assert all(c in "0123456789abcdef" for c in h1)

    def test_sha256_unchanged_after_ingest(self, ep_dir: Path) -> None:
        """验收 3：原文件 sha256 ingest 前后一致。"""
        src = ep_dir / "input" / "images" / "photo.png"
        before = sha256_file(src)
        run_ingest(ep_dir, "EP-TEST-001")
        after = sha256_file(src)
        assert before == after


class TestRunIngest:
    def test_exit_creates_manifest(self, ep_dir: Path) -> None:
        assets = run_ingest(ep_dir, "EP-TEST-001")
        assert manifest_path(ep_dir).exists()
        assert len(assets) > 0
        assert (ep_dir / "logs" / "ingest.log").is_file()

    def test_ok_assets_have_working_copy(self, ep_dir: Path) -> None:
        assets = run_ingest(ep_dir, "EP-TEST-001")
        ok = [a for a in assets if a["status"] == "ok"]
        for a in ok:
            wp = ep_dir / a["working_path"]
            assert wp.exists(), f"working_path 不存在: {a['working_path']}"

    def test_corrupt_marked_not_ok(self, ep_dir: Path) -> None:
        """验收 4：损坏文件标记 corrupt，不进入下游渲染列表。"""
        assets = run_ingest(ep_dir, "EP-TEST-001")
        corrupt = [a for a in assets if "corrupt" in a["source_path"]]
        # 若 ffprobe 不可用，corrupt mp4 仍被拷贝（状态 ok），只有 ffprobe 可用时才能检测
        # 此测试仅当 ffprobe 可用时严格检查
        import shutil as _sh
        if _sh.which("ffprobe"):
            assert corrupt and corrupt[0]["status"] == "corrupt"
        # ffprobe 不可用时：至少文件存在于 assets 中
        assert any("corrupt" in a["source_path"] for a in assets)
        if shutil.which("ffprobe"):
            assert corrupt[0]["working_path"] is None

    def test_unknown_file_is_unsupported_and_not_copied(self, ep_dir: Path) -> None:
        unknown = ep_dir / "input" / "payload.bin"
        unknown.write_bytes(b"not a supported asset")
        assets = run_ingest(ep_dir, "EP-TEST-001")
        record = next(a for a in assets if a["source_path"].endswith("payload.bin"))
        assert record["status"] == "unsupported"
        assert record["working_path"] is None

    def test_duplicate_content_is_marked(self, ep_dir: Path) -> None:
        original = ep_dir / "input" / "images" / "photo.png"
        duplicate = ep_dir / "input" / "images" / "photo-copy.png"
        shutil.copy2(original, duplicate)
        assets = run_ingest(ep_dir, "EP-TEST-001")
        copies = [a for a in assets if a["sha256"] == sha256_file(original)]
        assert len(copies) >= 3
        assert copies[0]["duplicate_of"] is None
        assert copies[1]["duplicate_of"] == copies[0]["asset_id"]

    def test_idempotent_no_retranscode(self, ep_dir: Path) -> None:
        """验收 5：再次 ingest，未变文件不重复转码（working_path mtime 不变）。"""
        run_ingest(ep_dir, "EP-TEST-001")
        # 获取首次 mtime
        # 找到对应 working_path
        manifest = load_manifest(ep_dir)
        png_asset = next(
            (a for a in manifest["assets"] if "photo.png" in a["source_path"] and a["status"] == "ok"),
            None
        )
        if png_asset:
            wp = ep_dir / png_asset["working_path"]
            mtime1 = wp.stat().st_mtime_ns
            run_ingest(ep_dir, "EP-TEST-001")   # 第二次
            mtime2 = wp.stat().st_mtime_ns
            assert mtime1 == mtime2, "幂等性失败：working_path 被重新写入"

    def test_manifest_schema_valid(self, ep_dir: Path) -> None:
        """验收 6：manifest 通过 Schema。"""
        run_ingest(ep_dir, "EP-TEST-001")
        doc = load_manifest(ep_dir)   # load_manifest 内部做 Schema 校验
        assert doc["episode_id"] == "EP-TEST-001"
        assert isinstance(doc["assets"], list)

    def test_all_paths_relative_in_manifest(self, ep_dir: Path) -> None:
        """验收 7：asset-manifest 中所有路径为相对路径。"""
        run_ingest(ep_dir, "EP-TEST-001")
        doc = load_manifest(ep_dir)
        for a in doc["assets"]:
            assert not Path(a["source_path"]).is_absolute(), a["source_path"]
            if a["working_path"] is not None:
                assert not Path(a["working_path"]).is_absolute(), a["working_path"]

    def test_force_rebuilds(self, ep_dir: Path) -> None:
        run_ingest(ep_dir, "EP-TEST-001")
        png_asset_before = None
        for a in load_manifest(ep_dir)["assets"]:
            if "photo.png" in a["source_path"] and a["status"] == "ok":
                png_asset_before = a
                break
        assert png_asset_before is not None
        # force 重建
        run_ingest(ep_dir, "EP-TEST-001", force=True)
        for a in load_manifest(ep_dir)["assets"]:
            if "photo.png" in a["source_path"]:
                assert a["sha256"] == png_asset_before["sha256"]   # hash 不变

    def test_landscape_video_proxy_is_vertical(self, ep_dir: Path) -> None:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            pytest.skip("ffmpeg/ffprobe required")
        source = ep_dir / "input" / "screen" / "landscape.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x180:d=0.2",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
        ], check=True, capture_output=True)
        before = sha256_file(source)
        assets = run_ingest(ep_dir, "EP-TEST-001")
        record = next(a for a in assets if a["source_path"].endswith("landscape.mp4"))
        assert sha256_file(source) == before
        assert record["status"] == "ok"
        assert record["width"] == 320 and record["height"] == 180
        proxy = ep_dir / record["working_path"]
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(proxy),
        ], check=True, capture_output=True, text=True)
        assert probe.stdout.strip() == "540x960"


def test_empty_input_cli_waits_for_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path
    real_root = Path(__file__).resolve().parents[1]
    shutil.copytree(real_root / "config", root / "config")
    (root / "AGENTS.md").write_text("# test", encoding="utf-8")
    ep_dir = root / "episodes" / "active" / "EP-EMPTY"
    ep_dir.mkdir(parents=True)
    create_episode_skeleton(ep_dir)
    EpisodeModel.create("EP-EMPTY").save(ep_dir / "episode.json")
    monkeypatch.setattr("avs.cli._find_project_root", lambda: root)

    result = CliRunner().invoke(main, ["ingest", "EP-EMPTY"])
    assert result.exit_code == 0, result.output
    model = EpisodeModel.load(ep_dir / "episode.json")
    assert model.status == "WAITING_FOR_INPUT"
    assert load_manifest(ep_dir)["assets"] == []
