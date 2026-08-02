"""测试 MCP Server 的 dispatch_tool 逻辑。

不启动真正的 MCP server（需要 stdio），而是直接调用 dispatch_tool
验证所有工具的参数解析与执行。
"""
import json
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from cut.mcp_server import dispatch_tool, TOOLS
from test_e2e import make_empty_draft, make_fake_video
from cut.jianying.draft import Draft


def setup_test_project(tmp: Path):
    """准备测试项目：1 视频 + 1 字幕。"""
    project_dir = tmp / "mcp_test"
    make_empty_draft(project_dir)
    v1 = tmp / "v.mp4"
    make_fake_video(str(v1))

    draft = Draft.open(project_dir=project_dir)
    mid = draft.add_material("video", {
        "id": "mat-v1", "type": "video", "path": str(v1),
        "duration": 5_000_000, "width": 1920, "height": 1080,
        "material_name": "v1",
    })
    from cut.jianying import materials
    sid = materials.add_video_segment(draft, mid, start_us=0, duration_us=5_000_000)
    draft.save()
    return project_dir, mid, sid


def test_tool_list():
    """验证所有工具定义合法。"""
    print(f"[1] 工具数: {len(TOOLS)}")
    names = [t.name for t in TOOLS]
    expected = [
        "cut.list_backends", "cut.get_state", "cut.list_materials",
        "cut.get_timeline", "cut.import_media", "cut.split", "cut.trim",
        "cut.add_text", "cut.add_transition", "cut.add_effect",
        "cut.set_audio", "cut.export", "cut.create_plan", "cut.quality_check",
    ]
    for n in expected:
        assert n in names, f"缺少工具: {n}"
    # 每个 tool 必须有 inputSchema
    for t in TOOLS:
        assert t.inputSchema is not None
        assert "type" in t.inputSchema
        assert t.inputSchema["type"] == "object"
    print(f"    所有 {len(expected)} 个工具定义合法")


def test_list_backends():
    """测试 cut.list_backends。"""
    r = dispatch_tool("cut.list_backends", {})
    assert "platform" in r
    print(f"[2] list_backends: platform={r['platform']}")


def test_get_state(tmp: Path):
    """测试 cut.get_state。"""
    project_dir, _, _ = setup_test_project(tmp)
    r = dispatch_tool("cut.get_state", {
        "backend": "jianying",
        "project": "mcp_test",
        "project_dir": str(project_dir),  # 优先于 project
    })
    assert r["backend"] == "jianying"
    assert r["duration_us"] == 5_000_000
    print(f"[3] get_state: {r['duration_hms']}")


def test_list_materials(tmp: Path):
    project_dir, mid, _ = setup_test_project(tmp)
    r = dispatch_tool("cut.list_materials", {
        "backend": "jianying", "project_dir": str(project_dir),
        "mtype": "video",
    })
    assert len(r) == 1
    assert r[0]["id"] == "mat-v1"
    print(f"[4] list_materials: {len(r)} video")


def test_get_timeline(tmp: Path):
    project_dir, _, _ = setup_test_project(tmp)
    r = dispatch_tool("cut.get_timeline", {
        "backend": "jianying", "project_dir": str(project_dir),
    })
    assert r["duration_us"] == 5_000_000
    assert len(r["tracks"]) >= 1
    print(f"[5] get_timeline: {len(r['tracks'])} tracks")


def test_split(tmp: Path):
    project_dir, mid, sid = setup_test_project(tmp)
    r = dispatch_tool("cut.split", {
        "backend": "jianying", "project_dir": str(project_dir),
        "track_index": 0, "at_us": 2_500_000,
    })
    assert r["success"] is True
    assert len(r["splits"]) == 1
    # 重读验证
    draft = Draft.open(project_dir=project_dir)
    assert len(draft.video_tracks[0].segments) == 2
    print(f"[6] split: left={r['splits'][0]['left'][:8]} right={r['splits'][0]['right'][:8]}")


def test_trim(tmp: Path):
    project_dir, mid, sid = setup_test_project(tmp)
    r = dispatch_tool("cut.trim", {
        "backend": "jianying", "project_dir": str(project_dir),
        "track_index": 0, "clip_index": 0,
        "new_start_us": 1_000_000, "new_end_us": 4_000_000,
    })
    assert r["success"] is True
    draft = Draft.open(project_dir=project_dir)
    seg = draft.video_tracks[0].segments[0]
    assert seg.start_us == 1_000_000
    assert seg.end_us == 4_000_000
    print(f"[7] trim: [{seg.start_us}-{seg.end_us}]")


def test_add_text(tmp: Path):
    project_dir, _, _ = setup_test_project(tmp)
    r = dispatch_tool("cut.add_text", {
        "backend": "jianying", "project_dir": str(project_dir),
        "content": "Hello MCP", "start_us": 0, "duration_us": 2_000_000,
        "preset": "subtitle",
    })
    assert r["success"] is True
    draft = Draft.open(project_dir=project_dir)
    assert len(draft.text_tracks) == 1
    assert draft.text_tracks[0].segments[0].start_us == 0
    print(f"[8] add_text: segment_id={r['segment_id'][:8]}")


def test_add_transition(tmp: Path):
    project_dir, _, _ = setup_test_project(tmp)
    # 先加第二个 segment 才能加转场
    draft = Draft.open(project_dir=project_dir)
    from cut.jianying import materials
    mid2 = draft.add_material("video", {
        "id": "mat-v2", "type": "video", "path": "/tmp/v2.mp4",
        "duration": 3_000_000, "width": 1920, "height": 1080,
    })
    materials.add_video_segment(draft, mid2, start_us=5_000_000, duration_us=3_000_000)
    draft.save()

    r = dispatch_tool("cut.add_transition", {
        "backend": "jianying", "project_dir": str(project_dir),
        "track_index": 0, "clip_index": 0, "preset": "fade",
        "duration_us": 500_000,
    })
    assert r["success"] is True
    print(f"[9] add_transition: id={r['transition_id'][:8]}")


def test_add_effect(tmp: Path):
    project_dir, _, sid = setup_test_project(tmp)
    r = dispatch_tool("cut.add_effect", {
        "backend": "jianying", "project_dir": str(project_dir),
        "track_index": 0, "clip_index": 0,
        "preset": "vignette", "intensity": 0.8,
    })
    assert r["success"] is True
    print(f"[10] add_effect: id={r['effect_segment_id'][:8]}")


def test_set_audio(tmp: Path):
    project_dir, _, _ = setup_test_project(tmp)
    # 加一个 audio segment
    draft = Draft.open(project_dir=project_dir)
    from cut.jianying import materials
    am_id = draft.add_material("audio", {
        "id": "mat-a1", "type": "audio", "path": "/tmp/a.mp3",
        "duration": 5_000_000,
    })
    a_sid = materials.add_audio_segment(draft, am_id, start_us=0, duration_us=5_000_000)
    draft.save()

    # 找到 audio track index
    tracks = draft.all_tracks()
    audio_track_idx = next(i for i, t in enumerate(tracks) if t.type == "audio")

    # 测试 volume
    r = dispatch_tool("cut.set_audio", {
        "backend": "jianying", "project_dir": str(project_dir),
        "track_index": audio_track_idx, "clip_index": 0,
        "action": "volume", "value": 0.5,
    })
    assert r["success"] is True
    draft2 = Draft.open(project_dir=project_dir)
    assert draft2.audio_tracks[0].segments[0].volume == 0.5
    print(f"[11] set_audio volume: 0.5")

    # 测试 fade_in
    r = dispatch_tool("cut.set_audio", {
        "backend": "jianying", "project_dir": str(project_dir),
        "track_index": audio_track_idx, "clip_index": 0,
        "action": "fade_in", "duration_us": 500_000,
    })
    assert r["success"] is True
    print(f"[12] set_audio fade_in: ok")


def test_import_media(tmp: Path):
    project_dir, _, _ = setup_test_project(tmp)
    v_path = tmp / "new.mp4"
    make_fake_video(str(v_path))
    r = dispatch_tool("cut.import_media", {
        "backend": "jianying", "project_dir": str(project_dir),
        "path": str(v_path), "mtype": "video", "alias": "新视频",
    })
    assert r["success"] is True
    assert "material_id" in r
    print(f"[13] import_media: id={r['material_id'][:8]}")


def test_unknown_tool():
    """测试未知工具的容错。"""
    r = dispatch_tool("cut.nonexistent", {})
    assert "error" in r
    print(f"[14] unknown_tool: error='{r['error']}'")


def test_create_plan():
    r = dispatch_tool("cut.create_plan", {
        "brief": "自动做一个60秒旅行vlog，适合抖音",
        "backend": "jianying",
        "assets": [{"path": "a.mp4", "duration_us": 10_000_000}],
    })
    assert r["format"] == "short_form"
    assert r["target_platform"] == "douyin"
    assert r["qa_required"] is True
    print("[15] create_plan: ok")


def test_quality_check_missing_file():
    r = dispatch_tool("cut.quality_check", {"output": "missing-output-file.mp4"})
    assert r["success"] is False
    assert r["findings"][0]["code"] == "probe_failed"
    print("[16] quality_check: missing file error ok")


def main():
    print("=== MCP dispatch_tool 测试 ===\n")
    test_tool_list()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        test_list_backends()
        test_get_state(tmp_p)
        test_list_materials(tmp_p)
        test_get_timeline(tmp_p)
        test_split(tmp_p)
        test_trim(tmp_p)
        test_add_text(tmp_p)
        test_add_transition(tmp_p)
        test_add_effect(tmp_p)
        test_set_audio(tmp_p)
        test_import_media(tmp_p)
        test_create_plan()
        test_quality_check_missing_file()
    test_unknown_tool()
    print("\n✅ 所有 MCP 测试通过")


if __name__ == "__main__":
    main()
