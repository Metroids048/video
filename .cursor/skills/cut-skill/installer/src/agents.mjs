// agents.mjs — 各家 agent 的检测、路径定义、安装逻辑
//
// 每个 agent 定义：
// - name: 显示名
// - detect(): 返回本机是否安装了该 agent 工具
// - skillDir(scope): 返回 skill 应该安装到的目录
// - install(sourceDir, scope): 把 skill 文件复制到目标位置
// - uninstall(scope): 删除 skill 文件
// - isInstalled(scope): 检测是否已安装
// - updateConfig?(skillDir, scope): 可选，更新 agent 的配置文件（Kimi 需要）

import { existsSync, mkdirSync, cpSync, rmSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { execSync } from 'node:child_process';

const HOME = homedir();

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------

function safeRead(path) {
  try {
    return readFileSync(path, 'utf-8');
  } catch {
    return null;
  }
}

function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
}

function copySkill(sourceDir, targetDir) {
  // 复制 SKILL.md、references/、scripts/、agents/、examples/、tests/、*.md
  // 排除 installer/ 自身（避免递归）、.git、node_modules、__pycache__
  ensureDir(targetDir);
  const items = [
    'SKILL.md', 'README.md', 'README.en.md', 'LICENSE', 'CHANGELOG.md',
    'CONTRIBUTING.md', '.gitignore',
    'references', 'scripts', 'agents', 'examples', 'tests',
  ];
  const excludes = new Set(['.git', 'node_modules', '__pycache__', 'installer', '.venv']);
  for (const item of items) {
    const src = join(sourceDir, item);
    if (existsSync(src)) {
      cpSync(src, join(targetDir, item), { recursive: true, filter: (s) => {
        const parts = s.split(/[/\\]/);
        return !parts.some(p => excludes.has(p));
      }});
    }
  }
}

// ---------------------------------------------------------------------------
// Agent 定义
// ---------------------------------------------------------------------------

export const AGENTS = {
  // ---- Codex CLI ----
  codex: {
    name: 'Codex CLI',
    detect() {
      // Codex/OpenAI agent skills use .agents/skills at project or user scope.
      // 检测 codex 命令是否存在
      try {
        execSync('codex --version', { stdio: 'ignore' });
        return true;
      } catch {
        return false;
      }
    },
    skillDir(scope) {
      if (scope === 'project') return join(process.cwd(), '.agents', 'skills', 'cut');
      return join(HOME, '.agents', 'skills', 'cut');
    },
    install(sourceDir, scope) {
      const dir = this.skillDir(scope);
      copySkill(sourceDir, dir);
      return dir;
    },
    uninstall(scope) {
      const dir = this.skillDir(scope);
      if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
    },
    isInstalled(scope) {
      return existsSync(join(this.skillDir(scope), 'SKILL.md'));
    },
  },

  // ---- Claude Code ----
  claude: {
    name: 'Claude Code',
    detect() {
      try {
        execSync('claude --version', { stdio: 'ignore' });
        return true;
      } catch {
        // macOS Claude Desktop 也算
        return existsSync('/Applications/Claude.app') ||
               existsSync(join(HOME, 'Applications', 'Claude.app'));
      }
    },
    skillDir(scope) {
      if (scope === 'project') return join(process.cwd(), '.claude', 'skills', 'cut');
      return join(HOME, '.claude', 'skills', 'cut');
    },
    install(sourceDir, scope) {
      const dir = this.skillDir(scope);
      copySkill(sourceDir, dir);
      return dir;
    },
    uninstall(scope) {
      const dir = this.skillDir(scope);
      if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
    },
    isInstalled(scope) {
      return existsSync(join(this.skillDir(scope), 'SKILL.md'));
    },
  },

  // ---- OpenCode ----
  opencode: {
    name: 'OpenCode',
    detect() {
      try {
        execSync('opencode --version', { stdio: 'ignore' });
        return true;
      } catch {
        return existsSync(join(HOME, '.config', 'opencode')) ||
               existsSync(join(HOME, '.opencode'));
      }
    },
    skillDir(scope) {
      if (scope === 'project') return join(process.cwd(), '.opencode', 'skills', 'cut');
      return join(HOME, '.config', 'opencode', 'skills', 'cut');
    },
    install(sourceDir, scope) {
      const dir = this.skillDir(scope);
      copySkill(sourceDir, dir);
      return dir;
    },
    uninstall(scope) {
      const dir = this.skillDir(scope);
      if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
    },
    isInstalled(scope) {
      return existsSync(join(this.skillDir(scope), 'SKILL.md'));
    },
  },

  // ---- Kimi Code ----
  kimi: {
    name: 'Kimi Code',
    detect() {
      try {
        execSync('kimi --version', { stdio: 'ignore' });
        return true;
      } catch {
        return existsSync(join(HOME, '.kimi'));
      }
    },
    skillDir(scope) {
      // Kimi 始终用用户级目录，配置文件指向它
      return join(HOME, '.kimi', 'skills', 'cut');
    },
    install(sourceDir, scope) {
      const dir = this.skillDir(scope);
      copySkill(sourceDir, dir);
      this.updateConfig(dir);
      return dir;
    },
    uninstall(scope) {
      const dir = this.skillDir(scope);
      if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
      this.removeFromConfig();
    },
    isInstalled(scope) {
      return existsSync(join(this.skillDir(scope), 'SKILL.md'));
    },
    configPath() {
      return join(HOME, '.kimi', 'skills.yaml');
    },
    updateConfig(skillDir) {
      const cfgPath = this.configPath();
      ensureDir(dirname(cfgPath));
      let content = safeRead(cfgPath) || '';
      // 简单 YAML 追加：如果已存在 cut 条目则更新 path，否则追加
      const entry = `  - name: cut\n    path: ${skillDir}\n    description: 视频剪辑操控（剪映 + Premiere）\n    triggers: [剪映, CapCut, Premiere, 视频剪辑, 字幕, 转场, 特效]\n    entry: SKILL.md\n`;
      if (/^skills:\s*$/m.test(content) && /^  - name: cut$/m.test(content)) {
        // 已存在，替换 path
        content = content.replace(
          /(^  - name: cut\n(?:    [^\n]+\n)*)/,
          entry
        );
      } else if (/^skills:\s*$/m.test(content)) {
        // 有 skills: 但没 cut，追加
        content = content.replace(/(^skills:\s*\n)/, `$1${entry}`);
      } else {
        // 没有 skills: 节，新建
        content = `skills:\n${entry}`;
      }
      writeFileSync(cfgPath, content, 'utf-8');
    },
    removeFromConfig() {
      const cfgPath = this.configPath();
      const content = safeRead(cfgPath);
      if (!content) return;
      // 删除 cut 条目（从 `  - name: cut` 到下一个 `  - name:` 或文件末尾）
      const newContent = content.replace(
        /  - name: cut\n(?:    [^\n]+\n)+/g,
        ''
      );
      if (newContent !== content) {
        writeFileSync(cfgPath, newContent, 'utf-8');
      }
    },
  },

  // ---- Qwen Code ----
  qwen: {
    name: 'Qwen Code',
    detect() {
      try {
        execSync('qwen --version', { stdio: 'ignore' });
        return true;
      } catch {
        return existsSync(join(HOME, '.qwen'));
      }
    },
    skillDir(scope) {
      if (scope === 'project') return join(process.cwd(), '.qwen', 'skills', 'cut');
      return join(HOME, '.qwen', 'skills', 'cut');
    },
    install(sourceDir, scope) {
      const dir = this.skillDir(scope);
      copySkill(sourceDir, dir);
      return dir;
    },
    uninstall(scope) {
      const dir = this.skillDir(scope);
      if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
    },
    isInstalled(scope) {
      return existsSync(join(this.skillDir(scope), 'SKILL.md'));
    },
  },

  // ---- GLM Code ----
  glm: {
    name: 'GLM Code',
    detect() {
      try {
        execSync('glm --version', { stdio: 'ignore' });
        return true;
      } catch {
        return existsSync(join(HOME, '.glm'));
      }
    },
    skillDir(scope) {
      if (scope === 'project') return join(process.cwd(), 'skills', 'cut');
      return join(HOME, '.glm', 'skills', 'cut');
    },
    install(sourceDir, scope) {
      const dir = this.skillDir(scope);
      copySkill(sourceDir, dir);
      return dir;
    },
    uninstall(scope) {
      const dir = this.skillDir(scope);
      if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
    },
    isInstalled(scope) {
      return existsSync(join(this.skillDir(scope), 'SKILL.md'));
    },
  },
};

// ---------------------------------------------------------------------------
// 公开 API
// ---------------------------------------------------------------------------

export const AGENT_KEYS = Object.keys(AGENTS);

export function detectInstalledAgents() {
  const installed = [];
  for (const key of AGENT_KEYS) {
    if (AGENTS[key].detect()) {
      installed.push(key);
    }
  }
  return installed;
}

export function parseAgentList(str) {
  if (!str) return [];
  return str.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
}
