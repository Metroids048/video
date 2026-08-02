"""cut.http_api — Flask HTTP API。

适合长任务、Web 集成、跨进程协作。
启动：
    python -m cut.http_api --port 8765

或环境变量 CUT_API_PORT=8765。
"""
from __future__ import annotations

import os
import sys

try:
    from flask import Flask, request, jsonify
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    Flask = None

from .mcp_server import dispatch_tool, TOOLS


def create_app():
    if not HAS_FLASK:
        print("Flask 未安装。请运行: pip install flask", file=sys.stderr)
        sys.exit(1)

    app = Flask(__name__)

    # ---- 工具元数据 ----
    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "name": "cut-http-api",
            "version": "1.0.0",
            "tools": [{"name": t.name, "description": t.description, "schema": t.inputSchema}
                      for t in TOOLS],
        })

    # ---- 统一调用入口 ----
    @app.route("/call/<tool_name>", methods=["POST"])
    def call_tool_route(tool_name: str):
        """统一调用入口。

        POST /call/cut.get_state
        {"backend": "jianying", "project": "my_vlog"}
        """
        body = request.get_json(silent=True) or {}
        # 把 snake_case 转回 args 用的 key
        # MCP schema 用 snake_case，body 也接收 snake_case
        try:
            result = dispatch_tool(tool_name, body)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ---- 便捷端点 ----
    @app.route("/state", methods=["GET"])
    def state():
        backend = request.args.get("backend", "jianying")
        project = request.args.get("project")
        project_dir = request.args.get("dir") or request.args.get("project_dir")
        return jsonify(dispatch_tool("cut.get_state", {"backend": backend, "project": project, "project_dir": project_dir}))

    @app.route("/materials", methods=["GET"])
    def materials():
        backend = request.args.get("backend", "jianying")
        project = request.args.get("project")
        project_dir = request.args.get("dir") or request.args.get("project_dir")
        mtype = request.args.get("type")
        return jsonify(dispatch_tool("cut.list_materials", {"backend": backend, "project": project, "project_dir": project_dir, "mtype": mtype}))

    @app.route("/timeline", methods=["GET"])
    def timeline():
        backend = request.args.get("backend", "jianying")
        project = request.args.get("project")
        project_dir = request.args.get("dir") or request.args.get("project_dir")
        return jsonify(dispatch_tool("cut.get_timeline", {"backend": backend, "project": project, "project_dir": project_dir}))

    @app.route("/import", methods=["POST"])
    def import_media():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.import_media", body))

    @app.route("/split", methods=["POST"])
    def split():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.split", body))

    @app.route("/trim", methods=["POST"])
    def trim():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.trim", body))

    @app.route("/text", methods=["POST"])
    def add_text():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.add_text", body))

    @app.route("/transition", methods=["POST"])
    def add_transition():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.add_transition", body))

    @app.route("/effect", methods=["POST"])
    def add_effect():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.add_effect", body))

    @app.route("/audio", methods=["POST"])
    def set_audio():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.set_audio", body))

    @app.route("/export", methods=["POST"])
    def export():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.export", body))

    @app.route("/plan", methods=["POST"])
    def create_plan():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.create_plan", body))

    @app.route("/qa", methods=["POST"])
    def quality_check():
        body = request.get_json(silent=True) or {}
        return jsonify(dispatch_tool("cut.quality_check", body))

    return app


def main():
    port = int(os.environ.get("CUT_API_PORT", "8765"))
    host = os.environ.get("CUT_API_HOST", "127.0.0.1")
    app = create_app()
    print(f"cut HTTP API 启动于 http://{host}:{port}")
    print("  GET  /                工具列表")
    print("  GET  /state           读取项目状态")
    print("  GET  /materials       列出素材")
    print("  GET  /timeline        读取时间轴")
    print("  POST /import          导入素材")
    print("  POST /split           切分片段")
    print("  POST /trim            调整入出点")
    print("  POST /text            添加文字")
    print("  POST /transition      添加转场")
    print("  POST /effect          添加特效")
    print("  POST /audio           音频操作")
    print("  POST /export          导出渲染")
    print("  POST /plan            生成专业剪辑执行计划")
    print("  POST /qa              导出后质量验收")
    print("  POST /call/<tool>     统一调用入口（与 MCP 同 schema）")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
