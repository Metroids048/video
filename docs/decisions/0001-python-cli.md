# ADR-0001：唯一业务 CLI 为 python -m avs

- **状态**：已接受（Accepted）
- **日期**：2026-07-20
- **模块**：0（设计冻结）

---

## 背景

项目早期方案存在 Python CLI 与 npm 命令分别实现业务逻辑的风险。如果两套接口各自独立实现，会导致：行为不一致、测试重复、维护负担加倍、Agent 调用路径分叉。

项目服务于 Codex、Claude Code 和 Cursor 三种 Agent，以及开发者直接命令行使用，需要一个所有调用方都认可的权威入口。

---

## 决策

**唯一业务 CLI 为 `python -m avs`**。

所有业务逻辑（状态机、媒体处理、FFmpeg 调用、QA、交付）均在此 CLI 中实现。

`package.json` 中的 npm 命令只作为薄包装，调用同一个 Python CLI 或脚本，绝不另立独立业务逻辑。

### 权威命令列表

```bash
python -m avs doctor
python -m avs episode create <ID>
python -m avs episode status <ID>
python -m avs episode validate <ID>
python -m avs episode fail <ID> --reason "..."
python -m avs episode reset <ID> --to <state> --force
python -m avs ingest <ID>
python -m avs assets list <ID>
python -m avs assets validate <ID>
python -m avs reference analyze <ID>
python -m avs reference validate <ID>
python -m avs timeline build <ID>
python -m avs timeline validate <ID>
python -m avs subtitles build <ID>
python -m avs render rough <ID>
python -m avs qa <ID>
python -m avs deliver <ID>
python -m avs run <ID>
```

### npm 包装（仅便捷入口）

```bash
npm run bootstrap       # 调用 scripts/bootstrap.ps1 或 bootstrap.sh
npm run doctor          # 调用 python -m avs doctor
npm run demo            # 调用 python -m avs run EP-DEMO-*
npm run verify          # 调用 scripts/verify.mjs
npm run skills:install  # 调用 scripts/install_skills.mjs
npm run skills:sync     # 调用 python scripts/sync_skills.py
npm run skills:check    # 校验 skills.lock.json 一致性
```

---

## 原因

- **Python** 拥有 FFmpeg 绑定（subprocess）、JSON Schema 校验（jsonschema）、媒体处理生态和跨平台路径支持。
- **Node/npm** 在此项目中的优势是生态工具（HyperFrames CLI、npx skills），而非业务逻辑。
- 单一入口使得任何 Agent 均可通过相同命令驱动流程，无需维护两套文档和测试。
- CLI 退出码稳定，可在脚本、CI 和 Agent 任务中可靠检测成功/失败。

---

## 后果

**正面：**
- 零 CLI 重复；一处修改，所有调用方生效
- 测试只需覆盖 Python 路径
- Agent 指令可直接使用命令行示例，无歧义

**需注意：**
- npm 脚本作者必须确保每条命令最终调用 `python -m avs` 或 `python scripts/…`，不得绕过
- Windows 环境需确保 Python 在 PATH 中，bootstrap 脚本负责验证

---

## 违规检测

任何在 `package.json` 的 `scripts` 中直接实现业务逻辑（而非调用 Python CLI）的做法，均视为违反本 ADR，需立即重构。
