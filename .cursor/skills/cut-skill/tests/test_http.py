"""测试 HTTP API。

启动 Flask test client，验证所有路由。
"""
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).parent))

# 先确认 flask 已装
try:
    import flask
except ImportError:
    print("flask 未安装，跳过 HTTP API 测试")
    sys.exit(0)

from test_e2e import make_empty_draft, make_fake_video


def setup_project(tmp: Path):
    project_dir = tmp / "http_test"
    make_empty_draft(project_dir)
    return project_dir


def main():
    from cut.http_api import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    print("=== HTTP API 测试 ===\n")

    # [1] GET / 工具列表
    r = client.get("/")
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "cut-http-api"
    assert len(data["tools"]) == 14
    print(f"[1] GET /: {len(data['tools'])} tools")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        project_dir = setup_project(tmp_p)
        v = tmp_p / "v.mp4"
        make_fake_video(str(v))

        # [2] GET /state
        r = client.get("/state", query_string={
            "backend": "jianying", "dir": str(project_dir),
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["backend"] == "jianying"
        print(f"[2] GET /state: {data['duration_hms']}")

        # [3] GET /materials
        r = client.get("/materials", query_string={
            "backend": "jianying", "dir": str(project_dir),
        })
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)
        print(f"[3] GET /materials: []")

        # [4] GET /timeline
        r = client.get("/timeline", query_string={
            "backend": "jianying", "dir": str(project_dir),
        })
        assert r.status_code == 200
        tl = r.get_json()
        assert tl["duration_us"] == 0
        print(f"[4] GET /timeline: {len(tl['tracks'])} tracks")

        # [5] POST /import
        r = client.post("/import", json={
            "backend": "jianying", "project_dir": str(project_dir),
            "path": str(v), "mtype": "video", "alias": "clip1",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        mat_id = data["material_id"]
        print(f"[5] POST /import: id={mat_id[:8]}")

        # [6] 统一入口 POST /call/cut.get_state
        r = client.post("/call/cut.get_state", json={
            "backend": "jianying", "project_dir": str(project_dir),
        })
        assert r.status_code == 200
        print(f"[6] POST /call/cut.get_state: ok")

        # [7] POST /text
        r = client.post("/text", json={
            "backend": "jianying", "project_dir": str(project_dir),
            "content": "HTTP 字幕", "start_us": 0, "duration_us": 2000000,
        })
        assert r.status_code == 200
        assert r.get_json()["success"] is True
        print(f"[7] POST /text: ok")

        # [8] 验证素材池
        from cut.jianying.draft import Draft
        draft = Draft.open(project_dir=project_dir)
        draft.find_material(mat_id)["duration"] = 5_000_000
        from cut.jianying import materials
        materials.add_video_segment(draft, mat_id, start_us=0, duration_us=5_000_000)
        draft.save()

        # [9] POST /split
        r = client.post("/split", json={
            "backend": "jianying", "project_dir": str(project_dir),
            "track_index": 0, "at_us": 2500000,
        })
        assert r.status_code == 200
        assert r.get_json()["success"] is True
        print(f"[8] POST /split: ok")

        # [10] GET /materials 验证
        r = client.get("/materials", query_string={
            "backend": "jianying", "dir": str(project_dir),
        })
        mats = r.get_json()
        # 1 video + 1 text = 2
        assert len(mats) == 2
        print(f"[9] GET /materials: {len(mats)} items")

        # [11] POST /plan
        r = client.post("/plan", json={
            "backend": "jianying",
            "brief": "自动做一个60秒旅行vlog，适合抖音",
        })
        assert r.status_code == 200
        plan = r.get_json()
        assert plan["target_platform"] == "douyin"
        assert plan["qa_required"] is True
        print("[10] POST /plan: ok")

    # [11] 错误处理：未知 tool
    r = client.post("/call/cut.nonexistent", json={})
    # dispatch_tool 把 error 包在 JSON 里返回，HTTP 200 但 body 含 error
    data = r.get_json()
    assert "error" in data
    print(f"[11] error handling: 未知 tool → 返回 error 字段")

    print("\n✅ 所有 HTTP API 测试通过")


if __name__ == "__main__":
    main()
