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
import {
  cpSync,
  existsSync,
  readdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "fs";
import { createHash } from "crypto";
import { homedir } from "os";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const LOCK_FILE = join(ROOT, "skills.lock.json");

function readLock() {
  try {
    return JSON.parse(readFileSync(LOCK_FILE, "utf8"));
  } catch {
    return {};
  }
}

function writeLock(lock, packageKey, details) {
  lock.third_party_skills = lock.third_party_skills || {};
  const current = lock.third_party_skills[packageKey] || {};
  const unchanged = Object.entries(details).every(
    ([key, value]) => JSON.stringify(current[key]) === JSON.stringify(value)
  );
  if (unchanged) return;
  lock.third_party_skills[packageKey] = {
    ...current,
    ...details,
    installed_at: new Date().toISOString(),
  };
  writeFileSync(LOCK_FILE, JSON.stringify(lock, null, 2), "utf8");
}

function hashTree(root) {
  const hash = createHash("sha256");
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
      a.name.localeCompare(b.name)
    )) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else {
        hash.update(entry.name);
        hash.update(readFileSync(path));
      }
    }
  };
  walk(root);
  return hash.digest("hex");
}

function findBundledSkills() {
  const projectBundle = join(ROOT, "node_modules", "hyperframes", "dist", "skills");
  if (existsSync(join(projectBundle, "hyperframes", "SKILL.md"))) return projectBundle;
  const candidates = [];
  const npmCache = process.env.npm_config_cache || join(homedir(), "AppData", "Local", "npm-cache");
  const npxRoot = join(npmCache, "_npx");
  if (!existsSync(npxRoot)) return null;
  for (const entry of readdirSync(npxRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const skills = join(npxRoot, entry.name, "node_modules", "hyperframes", "dist", "skills");
    if (existsSync(join(skills, "hyperframes", "SKILL.md"))) candidates.push(skills);
  }
  candidates.sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
  return candidates[0] || null;
}

function installBundledSkills() {
  const sourceRoot = findBundledSkills();
  if (!sourceRoot) return null;
  const destinations = [
    join(homedir(), ".codex", "skills"),
    join(homedir(), ".claude", "skills"),
    join(homedir(), ".cursor", "skills"),
  ];
  const installed = [];
  for (const name of ["hyperframes", "hyperframes-cli"]) {
    const source = join(sourceRoot, name);
    if (!existsSync(source)) continue;
    for (const destinationRoot of destinations) {
      const destination = join(destinationRoot, name);
      cpSync(source, destination, { recursive: true, force: true });
      installed.push(destination);
    }
  }
  return {
    sourceRoot,
    source: sourceRoot.startsWith(join(ROOT, "node_modules"))
      ? "node_modules/hyperframes/dist/skills"
      : "npm-cache/_npx/*/node_modules/hyperframes/dist/skills",
    destinations: installed.map((path) => path.replace(homedir(), "~").replaceAll("\\", "/")),
    sourceSha256: hashTree(sourceRoot),
  };
}

function installHyperframesSkills() {
  const bundled = installBundledSkills();
  if (bundled) {
    const packageJson = JSON.parse(
      readFileSync(join(dirname(dirname(bundled.sourceRoot)), "package.json"), "utf8")
    );
    console.log(`[OK] 安装官方 HyperFrames npm 包内置 Skills：${bundled.sourceRoot}`);
    return { success: true, version: packageJson.version || null, offline: bundled };
  }
  const cmd = "npx --yes hyperframes skills";
  console.log(`[INSTALL] ${cmd}`);
  try {
    execSync(cmd, { cwd: ROOT, encoding: "utf8", stdio: "inherit" });
    execSync("npx --yes hyperframes skills check", {
      cwd: ROOT,
      encoding: "utf8",
      stdio: "inherit",
    });
    const versionOutput = execSync("npx --yes hyperframes --version", {
      cwd: ROOT,
      encoding: "utf8",
    });
    const version = versionOutput.match(/(\d+\.\d+\.\d+)/)?.[1] ?? null;
    console.log("[OK] HyperFrames 官方 Skills 安装成功");
    return { success: true, version };
  } catch (err) {
    console.error(`[WARN] HyperFrames 网络安装失败：${err.message}`);
    const offline = installBundledSkills();
    if (!offline) {
      console.error("[FAIL] 未找到 npm 缓存中的官方 HyperFrames Skills");
      return { success: false, version: null };
    }
    console.log(`[OK] 使用官方 npm 缓存离线包：${offline.sourceRoot}`);
    return { success: true, version: "0.7.68", offline };
  }
}

const lock = readLock();
const result = installHyperframesSkills();

if (!result.success) {
  process.exit(1);
} else {
  writeLock(lock, "hyperframes", {
    status: result.offline ? "installed_offline_bundle" : "installed",
    version: result.version || null,
    source: result.offline?.source || "npx hyperframes skills",
    destinations: result.offline?.destinations || [],
    source_sha256: result.offline?.sourceSha256 || null,
  });
  console.log("\n[OK] 所有第三方 Skills 安装完成。");
}
