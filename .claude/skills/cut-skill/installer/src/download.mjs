// download.mjs — 从 GitHub 下载 cut.skill 仓库
//
// 支持镜像回退：用户指定镜像 → 直连 → 公共镜像 gh-proxy.com
// 优先用 git clone，失败则用 HTTPS zip 下载
//
// 环境变量 CUT_MIRROR 可指定镜像前缀（如 https://gh-proxy.com/）

import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, writeFileSync, unlinkSync, readdirSync, renameSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const HOME = homedir();

// 公共镜像列表（按顺序尝试）
const MIRRORS = [
  '',  // 直连
  'https://gh-proxy.com/',
];

// ---------------------------------------------------------------------------
// 构造 git clone URL（带镜像）
// ---------------------------------------------------------------------------

function buildGitUrls(repo, mirror) {
  // 返回候选 URL 数组
  const urls = [];
  if (mirror) {
    urls.push(`${mirror}https://github.com/${repo}.git`);
  }
  urls.push(`https://github.com/${repo}.git`);
  // 如果用户没指定镜像，加入公共镜像回退
  if (!mirror) {
    for (const m of MIRRORS) {
      if (m && !urls.includes(`${m}https://github.com/${repo}.git`)) {
        urls.push(`${m}https://github.com/${repo}.git`);
      }
    }
  }
  return urls;
}

// ---------------------------------------------------------------------------
// 方法 1: git clone（首选，支持镜像回退）
// ---------------------------------------------------------------------------

export function downloadViaGit(repo, ref = 'main', mirror = '') {
  const tmpDir = mkdtempSync(join(HOME, '.cut-skill-tmp-'));
  const urls = buildGitUrls(repo, mirror);

  let lastErr = null;
  for (const url of urls) {
    try {
      process.stderr.write(`  尝试: ${url}\n`);
      execSync(
        `git clone --depth 1 --branch ${ref} "${url}" "${tmpDir}"`,
        { stdio: 'pipe' }
      );
      if (!existsSync(join(tmpDir, 'SKILL.md'))) {
        throw new Error('下载的仓库不包含 SKILL.md');
      }
      rmSync(join(tmpDir, '.git'), { recursive: true, force: true });
      process.stderr.write(`  ✓ 下载成功\n`);
      return tmpDir;
    } catch (e) {
      lastErr = e;
      process.stderr.write(`  ⚠ 失败，尝试下一个\n`);
      rmSync(tmpDir, { recursive: true, force: true });
    }
  }

  throw new Error(
    `所有 git clone 源都失败。\n` +
    `  最后错误: ${lastErr?.message}\n` +
    `  建议：\n` +
    `    1. 用 --mirror 指定镜像：npx github:ygtec/cut.skill/installer install --all --mirror https://gh-proxy.com/\n` +
    `    2. 设环境变量：export CUT_MIRROR=https://gh-proxy.com/\n` +
    `    3. 手动 clone 后用 --source 指定本地路径`
  );
}

// ---------------------------------------------------------------------------
// 方法 2: HTTPS + unzip（备选，也支持镜像）
// ---------------------------------------------------------------------------

export async function downloadViaHttps(repo, ref = 'main', mirror = '') {
  const tmpDir = mkdtempSync(join(HOME, '.cut-skill-tmp-'));
  const zipPath = join(tmpDir, 'repo.zip');

  // 候选 URL：镜像 + 直连
  const urls = [];
  if (mirror) {
    urls.push(`${mirror}https://api.github.com/repos/${repo}/zipball/${ref}`);
  }
  urls.push(`https://api.github.com/repos/${repo}/zipball/${ref}`);
  if (!mirror) {
    for (const m of MIRRORS) {
      if (m) urls.push(`${m}https://api.github.com/repos/${repo}/zipball/${ref}`);
    }
  }

  let lastErr = null;
  for (const url of urls) {
    try {
      process.stderr.write(`  尝试: ${url}\n`);
      const res = await fetch(url, {
        headers: { 'User-Agent': 'cut-skill-installer' },
        redirect: 'follow',
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const buf = Buffer.from(await res.arrayBuffer());
      writeFileSync(zipPath, buf);

      // 解压
      const platform = process.platform;
      let extractCmd;
      if (platform === 'win32') {
        extractCmd = `powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${tmpDir}' -Force"`;
      } else {
        extractCmd = `unzip -q '${zipPath}' -d '${tmpDir}'`;
      }
      execSync(extractCmd, { stdio: 'pipe' });

      try { unlinkSync(zipPath); } catch {}

      // GitHub zipball 解压后有顶层目录，移到根
      const entries = readdirSync(tmpDir, { withFileTypes: true })
        .filter(d => d.isDirectory());
      const topLevelDir = entries.find(d => d.name !== '__MACOSX');
      if (topLevelDir) {
        const inner = join(tmpDir, topLevelDir.name);
        const items = readdirSync(inner);
        for (const item of items) {
          renameSync(join(inner, item), join(tmpDir, item));
        }
        rmSync(inner, { recursive: true, force: true });
      }

      if (!existsSync(join(tmpDir, 'SKILL.md'))) {
        throw new Error('下载的仓库不包含 SKILL.md');
      }
      process.stderr.write(`  ✓ 下载成功\n`);
      return tmpDir;
    } catch (e) {
      lastErr = e;
      process.stderr.write(`  ⚠ 失败，尝试下一个\n`);
      rmSync(tmpDir, { recursive: true, force: true });
    }
  }

  throw new Error(`HTTPS 下载失败: ${lastErr?.message}`);
}

// ---------------------------------------------------------------------------
// 统一入口：优先 git，失败回退 HTTPS
// ---------------------------------------------------------------------------

export async function downloadSkill(repo = 'ygtec/cut.skill', ref = 'main', mirror = '') {
  // 优先从环境变量读取镜像
  const m = mirror || process.env.CUT_MIRROR || '';

  try {
    return downloadViaGit(repo, ref, m);
  } catch (gitErr) {
    process.stderr.write(`  git clone 全部失败，回退到 HTTPS 下载\n`);
    try {
      return await downloadViaHttps(repo, ref, m);
    } catch (httpsErr) {
      throw new Error(
        `下载失败。\n` +
        `  git clone: ${gitErr.message}\n` +
        `  HTTPS: ${httpsErr.message}\n` +
        `请检查网络，或手动 clone 后用 --source 指定本地路径。`
      );
    }
  }
}

// ---------------------------------------------------------------------------
// 从本地路径加载（用户已 clone 的情况）
// ---------------------------------------------------------------------------

export function downloadFromLocal(localPath) {
  if (!existsSync(localPath)) {
    throw new Error(`本地路径不存在: ${localPath}`);
  }
  if (!existsSync(join(localPath, 'SKILL.md'))) {
    throw new Error(`路径不包含 SKILL.md，可能不是有效的 cut.skill 仓库: ${localPath}`);
  }
  return localPath;
}
