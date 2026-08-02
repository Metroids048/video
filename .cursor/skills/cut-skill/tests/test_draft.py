"""测试 Draft 解析与基本操作。

构造一个最小化的 draft_content.json，验证：
- 打开与摘要
- 轨道与片段解析
- split 操作
- add_text 操作
- 保存与重读
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cut.jianying.draft import Draft, _new_id
from cut.jianying import segments, text as TX


def make_minimal_draft(project_dir: Path):
    """创建最小化 draft_content.json。"""
    content = {
        "version": "5.9.0",
        "draft_version": "5.9.0",
        "duration": 5_000_000,
        "canvas_config": {"width": 1920, "height": 1080, "ratio": "original"},
        "id": "test-project",
        "create_time": 1700000000,
        "fps": 30,
        "materials": {
            "videos": [{
                "id": "mat-video-1",
                "type": "video",
                "path": "/tmp/test.mp4",
                "duration": 5_000_000,
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "has_audio": True,
                "material_name": "test",
            }],
            "audios": [],
            "images": [],
            "stickers": [],
            "texts": [],
            "effects": [],
            "audio_effects": [],
        },
        "tracks": [{
            "id": "track-video-1",
            "type": "video",
            "segments": [{
                "id": "seg-1",
                "material_id": "mat-video-1",
                "track_id": "track-video-1",
                "source_timerange": {"start": 0, "duration": 5_000_000},
                "target_timerange": {"start": 0, "duration": 5_000_000},
                "source_in_speed": 1.0,
                "speed": 1.0,
                "volume": 1.0,
                "common_keyframes": [],
                "material_animations": [],
                "enabled": True,
                "render_index": 0,
                "visible": True,
                "is_placeholder": False,
                "clip": {"alpha": 1.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0, "y": 0}},
                "extra_material_refs": [],
            }],
            "attribute": 0,
            "flag": 0,
            "volume": 1.0,
            "visible": True,
            "enabled": True,
        }],
    }
    project_dir.mkdir(parents=True, exist_ok=True)
    with open(project_dir / "draft_content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False)
    return project_dir


def test_parse():
    """测试解析。"""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "test_project"
        make_minimal_draft(pdir)

        draft = Draft.open(project_dir=pdir)
        print(f"✓ 打开项目: {draft.name}")
        print(f"  时长: {draft.duration_hms}")
        print(f"  画布: {draft.canvas}")
        print(f"  schema: {draft.schema_version}")

        # 测试轨道
        vts = draft.video_tracks
        assert len(vts) == 1, f"应有 1 条 video track，实际 {len(vts)}"
        assert len(vts[0].segments) == 1
        seg = vts[0].segments[0]
        assert seg.start_us == 0
        assert seg.end_us == 5_000_000
        print(f"✓ 轨道解析: {len(vts)} video track, 1 segment [{seg.start_us}-{seg.end_us}]")

        # 测试素材
        mats = draft.list_materials(mtype="video")
        assert len(mats) == 1
        assert mats[0].path == "/tmp/test.mp4"
        print(f"✓ 素材解析: {len(mats)} video material, path={mats[0].path}")

        # 测试摘要
        s = draft.to_summary()
        assert s["duration_us"] == 5_000_000
        print(f"✓ 摘要: {s['duration_hms']}, tracks={len(s['tracks'])}")

        return draft, pdir


def test_split():
    """测试切分。"""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "test_project"
        make_minimal_draft(pdir)

        draft = Draft.open(project_dir=pdir)
        seg = draft.video_tracks[0].segments[0]

        # 在 2.5s 切分
        left, right = segments.split_segment(draft, seg, at_us=2_500_000)
        print(f"✓ 切分: left={left[:8]} right={right[:8]}")

        # 验证
        draft2 = Draft.open(project_dir=pdir)
        # 注意：draft 对象已经在内存中修改了，但还没 save。重新 open 会读磁盘原文件
        # 让我们先在内存验证
        vts = draft.video_tracks
        assert len(vts[0].segments) == 2
        s1, s2 = vts[0].segments
        assert s1.start_us == 0 and s1.end_us == 2_500_000
        assert s2.start_us == 2_500_000 and s2.end_us == 5_000_000
        print(f"  left seg: [{s1.start_us}-{s1.end_us}]")
        print(f"  right seg: [{s2.start_us}-{s2.end_us}]")

        # 保存并重读
        draft.save()
        draft3 = Draft.open(project_dir=pdir)
        assert len(draft3.video_tracks[0].segments) == 2
        print(f"✓ 保存重读: 2 segments 确认")


def test_add_text():
    """测试加字幕。"""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "test_project"
        make_minimal_draft(pdir)

        draft = Draft.open(project_dir=pdir)
        sid = TX.add_subtitle(draft, "Hello World", start_us=1_000_000, duration_us=2_000_000)
        print(f"✓ 添加字幕: segment_id={sid[:8]}")

        # 验证
        tts = draft.text_tracks
        assert len(tts) == 1
        assert len(tts[0].segments) == 1
        seg = tts[0].segments[0]
        assert seg.start_us == 1_000_000
        assert seg.end_us == 3_000_000

        mat = draft.find_material(seg.material_id)
        assert mat["text"] == "Hello World"
        print(f"  字幕内容: {mat['text']}")
        print(f"  位置: [{seg.start_us}-{seg.end_us}]")

        # 保存
        draft.save()
        # 重读验证
        draft2 = Draft.open(project_dir=pdir)
        assert len(draft2.text_tracks) == 1
        assert len(draft2.text_tracks[0].segments) == 1
        print(f"✓ 保存重读: text segment 确认")


def test_backup():
    """测试备份。"""
    with tempfile.TemporaryDirectory() as tmp:
        pdir = Path(tmp) / "test_project"
        make_minimal_draft(pdir)

        # 1. 手动 backup
        draft = Draft.open(project_dir=pdir)
        bak = draft.backup()
        assert bak.exists()
        print(f"✓ 手动备份: {bak.name}")

        # 2. save 自动备份（新建实例避免 _backup_done 状态）
        draft2 = Draft.open(project_dir=pdir)
        draft2.content["duration"] = 6_000_000  # 改一下
        draft2.save()
        baks = list(pdir.glob("draft_content.json.bak.*"))
        assert len(baks) >= 2, f"应有 ≥2 个备份，实际 {len(baks)}"
        print(f"✓ save 自动备份: 共 {len(baks)} 个备份")


if __name__ == "__main__":
    print("\n=== 测试 1: 解析 ===")
    test_parse()
    print("\n=== 测试 2: 切分 ===")
    test_split()
    print("\n=== 测试 3: 加字幕 ===")
    test_add_text()
    print("\n=== 测试 4: 备份 ===")
    test_backup()
    print("\n✅ 所有测试通过")
