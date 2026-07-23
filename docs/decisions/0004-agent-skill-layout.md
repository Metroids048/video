# ADR-0004：Skills 单一编辑源与三 Agent 同步机制

- **状态**：已接受（Accepted）
- **日期**：2026-07-20
- **模块**：0（设计冻结）

---

## 背景

本项目需同时支持 Codex、Claude Code 和 Cursor 三种 Agent。三种 Agent 各有专属 Skills 目录（`.agents/skills/`、`.claude/skills/`），若直接在各目录独立维护，会造成 Skill 内容漂移、同一 Skill 出现多个不同版本、更新时需重复三处操作的问题。

同时，Windows 环境下符号链接需要管理员权限，无法作为默认同步机制。

---

## 决策

**项目自有 Skill 只在 `skills-src/` 中修改，由 `scripts/sync_skills.py` 复制（非符号链接）到各 Agent 目标目录。**

### 单一编辑源

```
skills-src/                        ← 唯一编辑源
├── create-episode/
│   └── SKILL.md
├── analyze-reference/
│   └── SKILL.md
├── write-video-script/
│   └── SKILL.md
├── create-storyboard/
│   └── SKILL.md
├── prepare-assets/
│   └── SKILL.md
├── create-rough-cut/
│   └── SKILL.md
├── revise-video/
│   └── SKILL.md
├── quality-review/
│   └── SKILL.md
└── create-publish-pack/
    └── SKILL.md
```

### 同步目标

```
.claude/skills/     ← Claude Code
.agents/skills/     ← Codex / 兼容 Agent
```

### 同步规则

1. `scripts/sync_skills.py` 执行全量复制，不依赖符号链接
2. Windows 默认复制模式，不要求管理员权限
3. 每次安装或更新第三方 Skill 后写入 `skills.lock.json`
4. `npm run skills:check` 检查 `skills-src/`、`.claude/skills/`、`.agents/skills/` 三处内容一致
5. 重复执行幂等：相同内容不重复写入

### 第三方 Skill（HyperFrames）

```bash
npx skills add heygen-com/hyperframes -a claude-code -a codex -a cursor --copy -y
```

- 使用 `--copy` 模式，避免 Windows 符号链接权限问题
- 安装后版本信息写入 `skills.lock.json` 的 `third_party_skills.hyperframes` 节
- 第三方 Skill 不在 `skills-src/` 中，不被 `sync_skills.py` 管理

### SKILL.md 必须字段

每个项目自有 Skill 的 `SKILL.md` 必须包含：

| 字段 | 说明 |
|------|------|
| 触发条件 | 何时调用此 Skill |
| 输入文件 | 必须存在的文件列表 |
| 不允许修改的文件 | 明确的只读文件列表 |
| 输出文件 | 产物路径（相对） |
| 执行命令 | 完整命令行示例 |
| 验证命令 | 如何确认执行成功 |
| 停止条件 | 何时停止执行 |
| 缺失输入时的行为 | 降级或报错方式 |
| 完成报告格式 | 必须包含的字段 |

Skill 只引用 `AGENTS.md` 和对应 Schema，不复制大量通用规则。

### V1 Agent 角色（最小集）

Claude Code 只创建三个 Subagent，不扩展：

| Agent | 职责 |
|-------|------|
| `content-worker` | 内容生成：脚本、分镜、发布文案 |
| `media-worker` | 媒体操作：素材准备、渲染、QA |
| `reviewer` | 只读审计：验证模块交付结果 |

---

## 原因

- Windows 环境下符号链接需要管理员权限，不可作为默认机制
- 单一编辑源确保三种 Agent 始终使用相同版本的 Skill
- `skills.lock.json` 提供版本可追溯性，便于排查 Agent 行为差异
- 最小 Agent 角色集（3个）避免过早过度拆分，模块9再评估是否需要扩展

---

## 后果

**正面：**
- Skill 更新只需修改 `skills-src/`，然后运行 `npm run skills:sync`
- 三种 Agent 使用完全相同的 Skill 内容，行为一致
- `skills:check` 可在 CI 中检测同步是否遗漏

**需注意：**
- 开发者不得直接修改 `.claude/skills/` 或 `.agents/skills/` 中的内容（改了会在下次 sync 时被覆盖）
- 第三方 Skill 升级需重新运行安装命令并更新 `skills.lock.json`

---

## 合规检测

若在 `.claude/skills/` 或 `.agents/skills/` 中发现与 `skills-src/` 不一致的内容，视为违反本 ADR，需运行 `npm run skills:sync` 修复。
