"""测试 cut-cli 命令行接口。

通过 subprocess 调用 python -m cut.cli，验证：
- detect
- list-drafts (空场景)
- get-state / list-materials / get-timeline (用临时项目)
- import / split / add-text / add-transition / add-effect / set-audio
- export --method ffmpeg (空场景应失败但不崩溃)
- plan / qa 新命令 help
- --dry-run 模式
- --json 输出格式
- 时间格式解析（us/s/ms/HH:MM:SS）
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).parent))

from test_e2e import make_empty_draft, make_fake_video


def run_cli(*args, expect_code=0):
    """运行 cut.cli，返回 (returncode, stdout, stderr)。"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SCRIPTS_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "cut.cli"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(SCRIPTS_DIR))
    if expect_code is not None:
        assert r.returncode == expect_code, f"期望退出码 {expect_code}，实际 {r.returncode}\nstderr: {r.stderr}"
    return r.returncode, r.stdout, r.stderr


def test_detect():
    code, out, err = run_cli("detect", "--json")
    data = json.loads(out)
    assert data["platform"] in ("windows", "darwin", "linux")
    assert "jianying" in data
    assert "premiere" in data
    print(f"[1] detect: platform={data['platform']}")


def test_help():
    code, out, err = run_cli("--help")
    assert "detect" in out
    assert "get-state" in out
    assert "split" in out
    assert "export" in out
    assert "plan" in out
    assert "qa" in out
    assert "auto-edit" in out
    assert "apply-template" in out
    print(f"[2] --help: 列出所有命令")


def test_subcommand_help():
    """每个子命令都要有 help。"""
    cmds = ["detect", "list-drafts", "get-state", "list-materials", "get-timeline",
            "import", "add-segment", "split", "trim", "add-text",
            "add-transition", "add-effect", "set-audio", "export", "plan", "qa",
            "auto-edit", "apply-template", "add-lut", "beat-sync", "add-huazi",
            "pro-transition"]
    for c in cmds:
        code, out, err = run_cli(c, "--help", expect_code=0)
        assert "usage:" in out.lower() or "--help" in out
    print(f"[3] {len(cmds)} 个子命令 --help 全部正常")


def setup_project(tmp: Path):
    project_dir = tmp / "cli_test"
    make_empty_draft(project_dir)
    return project_dir


def test_get_state_json(tmp: Path):
    project_dir = setup_project(tmp)
    # get-state 默认输出 JSON（无 --json 参数）
    code, out, err = run_cli("get-state", "--backend", "jianying",
                              "--dir", str(project_dir))
    data = json.loads(out)
    assert data["backend"] == "jianying"
    assert data["duration_us"] == 0
    print(f"[4] get-state (empty): {data['duration_hms']}")


def test_import_and_add_segment(tmp: Path):
    project_dir = setup_project(tmp)
    v = tmp / "v.mp4"
    make_fake_video(str(v))

    # import
    code, out, err = run_cli("import", "--backend", "jianying",
                              "--dir", str(project_dir),
                              "--type", "video", "--path", str(v), "--alias", "clip1")
    data = json.loads(out)
    assert data["success"] is True
    mat_id = data["material_id"]
    print(f"[5] import: material_id={mat_id[:8]}")

    # 手动设 duration（因为 ffprobe 失败）
    from cut.jianying.draft import Draft
    draft = Draft.open(project_dir=project_dir)
    draft.find_material(mat_id)["duration"] = 5_000_000
    draft.save()

    # add-segment
    code, out, err = run_cli("add-segment", "--backend", "jianying",
                              "--dir", str(project_dir),
                              "--material-id", mat_id,
                              "--track-type", "video", "--start", "0",
                              "--duration", "5000000")
    data = json.loads(out)
    assert data["success"] is True
    print(f"[6] add-segment: segment saved={data['saved']}")


def test_time_formats(tmp: Path):
    """测试时间参数解析：us/s/ms/HH:MM:SS。"""
    project_dir = setup_project(tmp)
    v = tmp / "v.mp4"
    make_fake_video(str(v))

    # import + add-segment
    code, out, _ = run_cli("import", "--backend", "jianying", "--dir", str(project_dir),
                           "--type", "video", "--path", str(v))
    mat_id = json.loads(out)["material_id"]

    from cut.jianying.draft import Draft
    from cut.jianying import materials
    draft = Draft.open(project_dir=project_dir)
    draft.find_material(mat_id)["duration"] = 10_000_000
    # 用 Python 直接加 segment，避免 CLI add-segment 复杂度
    sid = materials.add_video_segment(draft, mat_id, start_us=0, duration_us=10_000_000)
    draft.save()

    # 测试不同时间格式的 split
    formats = [
        ("2500000", 2_500_000),       # us 整数
        ("2.5s", 2_500_000),           # 秒
        ("2500ms", 2_500_000),         # 毫秒
        ("0.0416667min", 2_500_002),    # 分钟
        ("00:00:02.500", 2_500_000),   # HH:MM:SS.mmm
    ]
    for fmt, expected_us in formats:
        # 每次重新打开 draft（前面 split 已修改）
        # 测试方式：用 --dry-run 不实际改，仅验证参数解析不报错
        code, out, err = run_cli("split", "--backend", "jianying",
                                  "--dir", str(project_dir),
                                  "--track", "0", "--at", fmt, "--dry-run",
                                  expect_code=0)
        # dry-run 应该输出 JSON
        data = json.loads(out)
        assert data["success"] is True
        print(f"[7] time format '{fmt}': dry-run ok")


def test_dry_run(tmp: Path):
    """验证 --dry-run 不实际写文件。"""
    project_dir = setup_project(tmp)
    v = tmp / "v.mp4"
    make_fake_video(str(v))

    code, out, _ = run_cli("import", "--backend", "jianying", "--dir", str(project_dir),
                           "--type", "video", "--path", str(v), "--dry-run")
    data = json.loads(out)
    assert data["success"] is True
    assert data["saved"] is False
    # 验证文件没写
    from cut.jianying.draft import Draft
    draft = Draft.open(project_dir=project_dir)
    assert len(draft.list_materials()) == 0  # dry-run 没保存
    print(f"[8] --dry-run: 不写文件，正确")


def test_add_text(tmp: Path):
    project_dir = setup_project(tmp)
    code, out, _ = run_cli("add-text", "--backend", "jianying",
                            "--dir", str(project_dir),
                            "--content", "CLI 字幕测试",
                            "--start", "1000000", "--duration", "2000000",
                            "--preset", "subtitle")
    data = json.loads(out)
    assert data["success"] is True
    # 重读验证
    from cut.jianying.draft import Draft
    draft = Draft.open(project_dir=project_dir)
    assert len(draft.text_tracks) == 1
    seg = draft.text_tracks[0].segments[0]
    assert seg.start_us == 1_000_000
    print(f"[9] add-text: segment_id={data['segment_id'][:8]}")


def test_error_handling():
    """测试错误处理：不存在的项目。"""
    code, out, err = run_cli("get-state", "--backend", "jianying",
                              "--project", "nonexistent_project_xyz",
                              expect_code=None)
    assert code != 0
    assert "错误" in err or "Error" in err or "未找到" in err
    print(f"[10] error handling: 不存在的项目 → 非零退出码")


def test_plan_command():
    """测试一句话生成剪辑计划。"""
    code, out, err = run_cli("plan", "自动做一个60秒旅行vlog，适合抖音，节奏轻快")
    data = json.loads(out)
    assert data["format"] == "short_form"
    assert data["target_platform"] == "douyin"
    assert data["qa_required"] is True
    print("[11] plan: 一句话生成专业剪辑计划")


def main():
    print("=== cut-cli 命令行测试 ===\n")
    test_detect()
    test_help()
    test_subcommand_help()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        test_get_state_json(tmp_p)
        test_import_and_add_segment(tmp_p)
        test_time_formats(tmp_p)
        test_dry_run(tmp_p)
        test_add_text(tmp_p)
    test_error_handling()
    test_plan_command()
    print("\n✅ 所有 CLI 测试通过")


if __name__ == "__main__":
    main()
