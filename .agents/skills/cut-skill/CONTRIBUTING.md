# 贡献指南 | Contributing Guide

感谢你对 cut.skill 的兴趣！欢迎提交 Issue 和 Pull Request。

## 开发环境设置 | Development Setup

```bash
git clone https://github.com/<your-username>/cut.skill.git
cd cut.skill/scripts
pip install -e ".[all]"
```

## 运行测试 | Running Tests

```bash
cd cut.skill
python tests/run_all.py
```

测试套件覆盖：
- `test_draft.py` — Draft 解析与基本操作
- `test_e2e.py` — 端到端工作流（20 步）
- `test_mcp.py` — MCP 12 工具 dispatch 验证
- `test_cli.py` — CLI 14 命令验证
- `test_http.py` — HTTP API 14 路由验证
- `test_regression.py` — Bug 修复回归测试（13 项）

所有测试不依赖剪映/Premiere 实际运行，纯 Python 验证 draft 操控逻辑。

## 代码风格 | Code Style

- Python 3.9+
- 用 `pyflakes` 检查（应无任何警告）
- 用 `autoflake --remove-all-unused-imports` 自动清理未使用 import
- 4 空格缩进，行宽 100
- 函数/类有 docstring
- 类型注解完整

```bash
# 检查
python -m pyflakes scripts/cut/

# 自动清理
python -m autoflake --in-place --remove-all-unused-imports scripts/cut/*.py
```

## 提交规范 | Commit Convention

使用 Conventional Commits：

```
<type>(<scope>): <subject>

type: feat | fix | docs | style | refactor | test | chore
scope: jianying | premiere | cli | mcp | http | docs | test
```

示例：
- `feat(jianying): 支持 4.x draft schema`
- `fix(segments): split 时关键帧 ID 重复`
- `docs: 更新中英文 README`

## 报告 Bug | Reporting Bugs

请用 GitHub Issues，包含：
1. 复现步骤
2. 期望行为 vs 实际行为
3. 操作系统与剪映/Premiere 版本
4. 相关日志/错误堆栈

## 贡献新功能 | Contributing Features

1. 先开 Issue 讨论设计
2. Fork → 新分支 → 提交 PR
3. PR 必须通过所有测试
4. 新功能需补测试用例

## 项目结构 | Project Structure

```
cut/
├── SKILL.md              # skill 主入口
├── scripts/cut/          # Python 核心包
│   ├── jianying/         # 剪映 draft 操控
│   ├── premiere/         # Premiere pymiere 封装
│   ├── cli.py            # 命令行
│   ├── mcp_server.py     # MCP Server
│   └── http_api.py       # Flask HTTP API
├── references/           # 参考文档
├── agents/               # 各家 agent 集成入口
├── examples/             # 示例脚本
└── tests/                # 测试套件
```

## 许可证 | License

MIT License. 见 [LICENSE](LICENSE).
