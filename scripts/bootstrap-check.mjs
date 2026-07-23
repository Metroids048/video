#!/usr/bin/env node
/**
 * scripts/bootstrap-check.mjs — 引导前检查
 * 验证 Node.js 版本是否满足要求，为 npm run bootstrap 提供入口
 */
const major = parseInt(process.version.replace("v", "").split(".")[0], 10);
if (major < 22) {
  console.error(`[FAIL] 需要 Node.js 22+，当前 ${process.version}`);
  process.exit(1);
}
console.log(`[OK] Node.js ${process.version}`);
