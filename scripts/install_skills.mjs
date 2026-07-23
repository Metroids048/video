#!/usr/bin/env node
/**
 * scripts/install_skills.mjs — 安装第三方 Skills（HyperFrames 等）
 *
 * 用法：node scripts/install_skills.mjs
 * 或：   npm run skills:install
 *
 * 规则：
 * - 使用 --copy 模式（避免 Windows 符号链接权限问题）
 * - 安装完成后更新 skills.lock.json
 * - 安装失败时给出明确提示，不崩溃整个 bootstrap
 */
import { execSync } from "child_process";
import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const LOCK_FILE = join(ROOT, "skills.lock.json");

// 第三方 Skills 安装清单（与 skills.lock.json 同步）
const THIRD_PARTY_SKILLS = [
  {
    package: "heygen-com/hyperframes",
    agents: ["claude-code", "codex", "cursor"],
    key: "hyperframes",
  },
];

function readLock() {
  try {
    return JSON.parse(readFileSync(LOCK_FILE, "utf8"));
  } catch {
    return {};
  }
}

function writeLock(lock, packageKey, version) {
  lock.third_party_skills = lock.third_party_skills || {};
  lock.third_party_skills[packageKey] = {
    ...lock.third_party_skills[packageKey],
    status: "installed",
    installed_at: new Date().toISOString(),
    version: version || null,
  };
  writeFileSync(LOCK_FILE, JSON.stringify(lock, null, 2), "utf8");
}

function installSkill(skill) {
  const agentFlags = skill.agents.map((a) => `-a ${a}`).join(" ");
  const cmd = `npx skills add ${skill.package} ${agentFlags} --copy -y`;
  console.log(`[INSTALL] ${cmd}`);

  try {
    const out = execSync(cmd, { cwd: ROOT, encoding: "utf8", stdio: "pipe" });
    console.log(`[OK] ${skill.package} 安装成功`);

    // 尝试读取版本
    const verMatch = out.match(/(\d+\.\d+\.\d+)/);
    const version = verMatch ? verMatch[1] : null;
    return { success: true, version };
  } catch (err) {
    console.error(`[WARN] ${skill.package} 安装失败：${err.message}`);
    console.error(
      `  手动安装命令：npx skills add ${skill.package} ${agentFlags} --copy -y`
    );
    return { success: false, version: null };
  }
}

const lock = readLock();
let hasError = false;

for (const skill of THIRD_PARTY_SKILLS) {
  const result = installSkill(skill);
  if (result.success) {
    writeLock(lock, skill.key, result.version);
  } else {
    hasError = true;
  }
}

if (hasError) {
  console.warn("\n[WARN] 部分 Skills 安装失败。运行 npm run skills:install 重试。");
  process.exit(0); // 不阻断 bootstrap，只是 WARN
} else {
  console.log("\n[OK] 所有第三方 Skills 安装完成。");
}
