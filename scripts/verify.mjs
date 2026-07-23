#!/usr/bin/env node
/**
 * scripts/verify.mjs — 环境验证脚本
 * 用法：node scripts/verify.mjs
 * 或：   npm run verify
 *
 * 检查核心可执行文件和项目目录结构，返回 0 = 通过，1 = 失败。
 */
import { execSync } from "child_process";
import { existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const errors = [];
let checks = 0;

function check(label, fn) {
  checks++;
  try {
    fn();
    console.log(`[OK] ${label}`);
  } catch (e) {
    errors.push(`${label}: ${e.message}`);
    console.error(`[FAIL] ${label}: ${e.message}`);
  }
}

function requireFile(rel) {
  const p = join(ROOT, rel);
  if (!existsSync(p)) throw new Error(`不存在: ${rel}`);
}

function requireCmd(cmd) {
  execSync(cmd, { stdio: "pipe", cwd: ROOT });
}

// ── 文件存在性检查 ─────────────────────────────────────────────────
check("AGENTS.md",            () => requireFile("AGENTS.md"));
check("CLAUDE.md",            () => requireFile("CLAUDE.md"));
check("tools-manifest.yaml",  () => requireFile("tools-manifest.yaml"));
check("skills.lock.json",     () => requireFile("skills.lock.json"));
check(".gitignore",           () => requireFile(".gitignore"));
check("docs/architecture.md", () => requireFile("docs/architecture.md"));
check("docs/decisions/0001",  () => requireFile("docs/decisions/0001-python-cli.md"));
check("docs/decisions/0002",  () => requireFile("docs/decisions/0002-timeline-contract.md"));
check("docs/decisions/0003",  () => requireFile("docs/decisions/0003-hyperframes-boundary.md"));
check("docs/decisions/0004",  () => requireFile("docs/decisions/0004-agent-skill-layout.md"));
check("pyproject.toml",       () => requireFile("pyproject.toml"));
check("package.json",         () => requireFile("package.json"));

// ── CLI 可执行性检查 ────────────────────────────────────────────────
check("python -m avs --help", () => requireCmd("python -m avs --help"));
check("python -m avs doctor", () => requireCmd("python -m avs doctor"));

// ── Skills 检查 ────────────────────────────────────────────────────
check("skills:check", () => requireCmd("python scripts/sync_skills.py --check"));

console.log(`\n${checks - errors.length}/${checks} 项通过`);
if (errors.length > 0) {
  console.error(`\n[FAIL] ${errors.length} 项失败：`);
  errors.forEach((e) => console.error(`  - ${e}`));
  process.exit(1);
} else {
  console.log("[OK] 所有验证通过");
  process.exit(0);
}
