#!/usr/bin/env node
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { delimiter, resolve } from "node:path";
import process from "node:process";

function resolvePython() {
  const configured = process.env.AGENT_PYTHON;
  if (configured) {
    if (!existsSync(configured)) {
      console.error(`[FAIL] AGENT_PYTHON 不存在: ${configured}`);
      process.exit(1);
    }
    return configured;
  }
  return process.platform === "win32" ? "python" : "python3";
}

const root = resolve(import.meta.dirname, "..");
const python = resolvePython();
const env = {
  ...process.env,
  PYTHONPATH: [resolve(root, "src"), process.env.PYTHONPATH]
    .filter(Boolean)
    .join(delimiter),
};
const result = spawnSync(python, process.argv.slice(2), {
  cwd: root,
  env,
  stdio: "inherit",
});

if (result.error) {
  console.error(`[FAIL] 无法运行 Python: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 1);
