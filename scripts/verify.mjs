#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import process from "node:process";

const ROOT = join(import.meta.dirname, "..");
const python = process.env.AGENT_PYTHON || (process.platform === "win32" ? "python" : "python3");
const errors = [];
let checks = 0;

function check(label, fn) {
  checks += 1;
  try {
    fn();
    console.log(`[OK] ${label}`);
  } catch (error) {
    errors.push(`${label}: ${error.message}`);
    console.error(`[FAIL] ${label}: ${error.message}`);
  }
}

function requireFile(relative) {
  if (!existsSync(join(ROOT, relative))) throw new Error(`不存在: ${relative}`);
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    env: { ...process.env, PYTHONPATH: join(ROOT, "src") },
    encoding: "utf8",
  });
  if (result.status !== 0) {
    const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
    throw new Error(output.slice(-1200) || `exit ${result.status}`);
  }
}

const hyperframes = join(ROOT, "node_modules", "hyperframes", "bin", "hyperframes.mjs");

for (const file of [
  "AGENTS.md", "CLAUDE.md", "tools-manifest.yaml", "skills.lock.json",
  "requirements.lock.txt", ".gitignore", ".claude/settings.json",
  ".claude/agents/content-worker.md", ".claude/agents/media-worker.md",
  ".claude/agents/reviewer.md", "pyproject.toml", "package.json",
  "README.md", "docs/getting-started.md", "docs/input-guide.md",
  "docs/creator-os-v2.md", "docs/workflow-v2.md", "docs/troubleshooting.md",
  "config/content-formats.yaml", "config/reference-acquisition.yaml", "config/voice.yaml",
  "schemas/creative-contract.schema.json", "schemas/creator-review.schema.json",
  "schemas/voice-profile.schema.json", "scripts/validate_creator_os_v2.py",
]) {
  check(file, () => requireFile(file));
}

check("Creator OS V2 contract", () => run(python, ["scripts/validate_creator_os_v2.py"]));
check("Python compile", () => run(python, ["-m", "compileall", "-q", "src", "tests", "scripts"]));
check("AVS CLI", () => run(python, ["-m", "avs", "--help"]));
check("AVS workflow CLI", () => run(python, ["-m", "avs", "workflow", "--help"]));
check("AVS doctor", () => run(python, ["-m", "avs", "doctor"]));
check("Skills sync", () => run(python, ["scripts/sync_skills.py", "--check"]));
check("Ruff", () => run(python, ["-m", "ruff", "check", "src", "tests", "scripts"]));
check("Mypy", () => run(python, ["-m", "mypy", "src"]));
check("Pytest", () => run(python, ["-m", "pytest", "-q"]));
for (const component of ["HookTitle", "InfoCard", "EndCard"]) {
  check(`HyperFrames lint ${component}`, () =>
    run(process.execPath, [hyperframes, "lint", `renderers/hyperframes/components/${component}`]));
}
check("HyperFrames demo lint", () =>
  run(process.execPath, [hyperframes, "lint", "renderers/hyperframes"]));

console.log(`\n${checks - errors.length}/${checks} 项通过`);
if (errors.length) {
  console.error(`\n[FAIL] ${errors.length} 项失败`);
  process.exit(1);
}
console.log("[OK] 所有验证通过");
