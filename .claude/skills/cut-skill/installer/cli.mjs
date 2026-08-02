#!/usr/bin/env node

// cut-skill — cut.skill 安装器 CLI
//
// 用法（推荐 npx 从 GitHub 直接跑，无需安装）：
//   npx github:ygtec/cut.skill/installer install [--agent <name>] [--all] [--user|--project] [--source <path>] [--repo <github>]
//   npx github:ygtec/cut.skill/installer uninstall [--agent <name>] [--all]
//   npx github:ygtec/cut.skill/installer list
//   npx github:ygtec/cut.skill/installer update
//   npx github:ygtec/cut.skill/installer detect
//
// 或本地 clone 后运行：
//   git clone https://github.com/ygtec/cut.skill.git
//   cd cut.skill/installer
//   node cli.mjs install --all --source ..
//
// 或 curl 一键安装（不需要 Node.js）：
//   curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

import { parseArgs } from 'node:util';
import { existsSync, rmSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';
import { bold, green, red, yellow, cyan, dim } from './src/colors.mjs';
import { AGENTS, AGENT_KEYS, detectInstalledAgents, parseAgentList } from './src/agents.mjs';
import { downloadSkill, downloadFromLocal } from './src/download.mjs';

const VERSION = '1.2.0';
const HOME = homedir();

// ---------------------------------------------------------------------------
// 帮助文本
// ---------------------------------------------------------------------------

const HELP = `${bold('cut-skill')} v${VERSION} — cut.skill 安装器

${bold('用法：')}
  npx github:ygtec/cut.skill/installer <command> [options]

  ${dim('# 或本地 clone 后运行：')}
  node cli.mjs <command> [options]

${bold('命令：')}
  ${cyan('install')}     安装 cut.skill 到指定 agent
  ${cyan('uninstall')}   卸载 cut.skill
  ${cyan('list')}        列出已安装的位置
  ${cyan('update')}      更新到最新版
  ${cyan('detect')}      检测本机已安装的 agent 工具

${bold('install 选项：')}
  ${yellow('--agent <name>')}      目标 agent（可逗号分隔多个），可选值：
                          ${AGENT_KEYS.join(', ')}
  ${yellow('--all')}               安装到所有支持的 agent
  ${yellow('--user')}              安装到用户级目录（默认）
  ${yellow('--project')}           安装到当前项目目录
  ${yellow('--source <path>')}     用本地已下载的仓库，不联网下载
  ${yellow('--repo <github>')}     自定义 GitHub 仓库（默认 ygtec/cut.skill）
  ${yellow('--ref <git-ref>')}     自定义分支/tag（默认 main）
  ${yellow('--mirror <url>')}      git clone 镜像前缀（国内可用 https://gh-proxy.com/）
  ${yellow('--force')}             覆盖已存在的安装

${bold('示例：')}
  ${dim('# 一键安装到所有检测到的 agent')}
  npx github:ygtec/cut.skill/installer install

  ${dim('# 安装到指定 agent')}
  npx github:ygtec/cut.skill/installer install --agent claude
  npx github:ygtec/cut.skill/installer install --agent codex,glm

  ${dim('# 强制安装到全部 6 家 agent（即使没检测到）')}
  npx github:ygtec/cut.skill/installer install --all

  ${dim('# 安装到当前项目（而非用户目录）')}
  npx github:ygtec/cut.skill/installer install --agent claude --project

  ${dim('# 用本地已下载的仓库安装（离线）')}
  node cli.mjs install --all --source /path/to/cut.skill

  ${dim('# 卸载')}
  npx github:ygtec/cut.skill/installer uninstall --agent claude

  ${dim('# 查看已安装位置')}
  npx github:ygtec/cut.skill/installer list

${bold('不需要 Node.js 时用 curl 一键安装：')}
  curl -fsSL https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

${bold('国内网络不稳定时用镜像：')}
  # 方式 A：用镜像下载脚本
  curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ygtec/cut.skill/main/installer/install.sh | bash

  # 方式 B：指定镜像让 git clone 走代理
  npx github:ygtec/cut.skill/installer install --all --mirror https://gh-proxy.com/

  # 方式 C：设环境变量（一劳永逸）
  export CUT_MIRROR=https://gh-proxy.com/
  npx github:ygtec/cut.skill/installer install --all

${bold('文档：')}https://github.com/ygtec/cut.skill
`;

// ---------------------------------------------------------------------------
// 参数解析
// ---------------------------------------------------------------------------

function parseCliArgs(argv) {
  const command = argv[0];
  if (!command || command.startsWith('-')) {
    return { command: null, options: {}, args: [] };
  }
  const rest = argv.slice(1);
  try {
    const { values, tokens } = parseArgs({
      args: rest,
      options: {
        agent: { type: 'string' },
        all: { type: 'boolean', default: false },
        user: { type: 'boolean', default: false },
        project: { type: 'boolean', default: false },
        source: { type: 'string' },
        repo: { type: 'string', default: 'ygtec/cut.skill' },
        ref: { type: 'string', default: 'main' },
        mirror: { type: 'string', default: '' },
        force: { type: 'boolean', default: false },
        help: { type: 'boolean', short: 'h', default: false },
        version: { type: 'boolean', short: 'v', default: false },
      },
      allowPositionals: true,
      tokens: true,
    });
    return { command, options: values, args: tokens };
  } catch (e) {
    console.error(red(`参数解析失败: ${e.message}`));
    process.exit(1);
  }
}

// ---------------------------------------------------------------------------
// 命令实现
// ---------------------------------------------------------------------------

function cmdDetect() {
  console.log(bold('检测本机已安装的 agent 工具：\n'));
  const installed = detectInstalledAgents();
  for (const key of AGENT_KEYS) {
    const agent = AGENTS[key];
    const ok = installed.includes(key);
    const mark = ok ? green('✓') : red('✗');
    console.log(`  ${mark} ${agent.name.padEnd(15)} ${dim(`(${key})`)}`);
  }
  if (installed.length === 0) {
    console.log(yellow('\n  未检测到任何 agent 工具。可以用 --all 强制安装到全部。'));
  } else {
    console.log(green(`\n  检测到 ${installed.length} 个 agent：${installed.join(', ')}`));
  }
}

async function cmdInstall(opts) {
  // 1. 确定目标 agent 列表
  let targets;
  if (opts.all) {
    targets = [...AGENT_KEYS];
    console.log(cyan('目标：全部 6 家 agent'));
  } else if (opts.agent) {
    targets = parseAgentList(opts.agent);
    // 校验
    const invalid = targets.filter(t => !AGENT_KEYS.includes(t));
    if (invalid.length) {
      console.error(red(`未知的 agent: ${invalid.join(', ')}`));
      console.error(dim(`可选值: ${AGENT_KEYS.join(', ')}`));
      process.exit(1);
    }
    console.log(cyan(`目标：${targets.join(', ')}`));
  } else {
    // 自动检测
    targets = detectInstalledAgents();
    if (targets.length === 0) {
      console.error(yellow('未检测到任何 agent 工具。'));
      console.error(dim('请用 --agent <name> 指定，或 --all 强制安装到全部。'));
      console.error(dim(`可选 agent: ${AGENT_KEYS.join(', ')}`));
      process.exit(1);
    }
    console.log(cyan(`自动检测到：${targets.join(', ')}`));
  }

  // 2. 确定安装范围
  const scope = opts.project ? 'project' : 'user';
  console.log(cyan(`范围：${scope === 'project' ? '当前项目' : '用户级'}`));

  // 3. 获取 skill 源文件
  let sourceDir;
  if (opts.source) {
    const src = resolve(opts.source);
    console.log(cyan(`从本地路径加载：${src}`));
    try {
      sourceDir = downloadFromLocal(src);
    } catch (e) {
      console.error(red(e.message));
      process.exit(1);
    }
  } else {
    const mirrorInfo = opts.mirror ? ` (mirror: ${opts.mirror})` : '';
    console.log(cyan(`从 GitHub 下载：${opts.repo}@${opts.ref}${mirrorInfo}`));
    try {
      sourceDir = await downloadSkill(opts.repo, opts.ref, opts.mirror);
    } catch (e) {
      console.error(red(e.message));
      process.exit(1);
    }
  }
  console.log(green('✓ 下载完成'));

  // 4. 逐个安装到目标 agent
  console.log(bold('\n安装到各 agent：'));
  const results = [];
  for (const key of targets) {
    const agent = AGENTS[key];
    try {
      // 检查是否已安装
      if (agent.isInstalled(scope) && !opts.force) {
        console.log(yellow(`  ⚠ ${agent.name}: 已安装（用 --force 覆盖）`));
        results.push({ agent: key, status: 'skipped' });
        continue;
      }
      // 卸载旧版
      if (agent.isInstalled(scope)) {
        agent.uninstall(scope);
      }
      // 安装
      const dir = agent.install(sourceDir, scope);
      console.log(green(`  ✓ ${agent.name}: ${dir}`));
      results.push({ agent: key, status: 'installed', dir });
    } catch (e) {
      console.error(red(`  ✗ ${agent.name}: ${e.message}`));
      results.push({ agent: key, status: 'failed', error: e.message });
    }
  }

  // 5. 清理临时目录（仅当是下载的）
  if (!opts.source && sourceDir && sourceDir.startsWith(join(HOME, '.cut-skill-tmp-'))) {
    try {
      rmSync(sourceDir, { recursive: true, force: true });
    } catch {}
  }

  // 6. 汇总
  const succeeded = results.filter(r => r.status === 'installed').length;
  const skipped = results.filter(r => r.status === 'skipped').length;
  const failed = results.filter(r => r.status === 'failed').length;
  console.log(bold(`\n汇总：`));
  console.log(green(`  ✓ 成功: ${succeeded}`));
  if (skipped) console.log(yellow(`  ⚠ 跳过: ${skipped}（已安装）`));
  if (failed) console.log(red(`  ✗ 失败: ${failed}`));

  if (succeeded > 0) {
    console.log(bold('\n下一步：'));
    console.log(dim('  • 重启你的 agent 工具让它加载新 skill'));
    console.log(dim('  • 验证安装：npx github:ygtec/cut.skill/installer list'));
    console.log(dim('  • 试用：在 agent 中说"检测一下我电脑上有什么视频剪辑软件"'));
  }

  if (failed > 0) process.exit(1);
}

function cmdUninstall(opts) {
  let targets;
  if (opts.all) {
    targets = [...AGENT_KEYS];
  } else if (opts.agent) {
    targets = parseAgentList(opts.agent);
  } else {
    // 卸载所有已安装的
    targets = AGENT_KEYS.filter(k => {
      const agent = AGENTS[k];
      return agent.isInstalled('user') || agent.isInstalled('project');
    });
    if (targets.length === 0) {
      console.log(yellow('未找到已安装的 cut.skill'));
      return;
    }
  }

  const scope = opts.project ? 'project' : 'user';
  console.log(bold(`从 ${scope} 范围卸载：${targets.join(', ')}\n`));

  for (const key of targets) {
    const agent = AGENTS[key];
    try {
      if (agent.isInstalled(scope)) {
        agent.uninstall(scope);
        console.log(green(`  ✓ ${agent.name}: 已卸载`));
      } else {
        console.log(dim(`  - ${agent.name}: 未安装`));
      }
    } catch (e) {
      console.error(red(`  ✗ ${agent.name}: ${e.message}`));
    }
  }
}

function cmdList() {
  console.log(bold('cut.skill 安装位置：\n'));
  let found = false;
  for (const key of AGENT_KEYS) {
    const agent = AGENTS[key];
    // 对 scope 不敏感的 agent（kimi 始终用固定目录）只显示一次
    const scopes = (key === 'kimi')
      ? ['user']
      : ['user', 'project'];
    for (const scope of scopes) {
      if (agent.isInstalled(scope)) {
        const dir = agent.skillDir(scope);
        const scopeLabel = (key === 'kimi') ? 'user' : scope;
        console.log(green(`  ✓ ${agent.name.padEnd(15)} [${scopeLabel}] ${dim(dir)}`));
        found = true;
      }
    }
  }
  if (!found) {
    console.log(yellow('  未找到任何安装。运行 install 命令开始安装。'));
  }
}

async function cmdUpdate(opts) {
  console.log(cyan('更新 cut.skill 到最新版...\n'));
  // update = uninstall + install
  // 找到已安装的位置，对应重装
  const installed = AGENT_KEYS.filter(k => {
    const agent = AGENTS[k];
    return agent.isInstalled('user') || agent.isInstalled('project');
  });
  if (installed.length === 0) {
    console.log(yellow('未找到已安装的 cut.skill。运行 install 命令开始安装。'));
    return;
  }
  // 卸载后重装
  for (const key of installed) {
    const agent = AGENTS[key];
    for (const scope of ['user', 'project']) {
      if (agent.isInstalled(scope)) {
        opts.agent = key;
        opts.user = scope === 'user';
        opts.project = scope === 'project';
        opts.force = true;
        await cmdInstall(opts);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// 主入口
// ---------------------------------------------------------------------------

async function main() {
  const argv = process.argv.slice(2);
  const { command, options } = parseCliArgs(argv);

  if (options.help || command === 'help' || !command) {
    console.log(HELP);
    process.exit(0);
  }

  if (options.version || command === 'version') {
    console.log(`cut-skill v${VERSION}`);
    process.exit(0);
  }

  switch (command) {
    case 'install':
      await cmdInstall(options);
      break;
    case 'uninstall':
    case 'remove':
      cmdUninstall(options);
      break;
    case 'list':
    case 'ls':
      cmdList();
      break;
    case 'update':
    case 'upgrade':
      await cmdUpdate(options);
      break;
    case 'detect':
      cmdDetect();
      break;
    default:
      console.error(red(`未知命令: ${command}`));
      console.error(dim('运行 --help 查看可用命令'));
      process.exit(1);
  }
}

main().catch(e => {
  console.error(red(`\n错误: ${e.message}`));
  process.exit(1);
});
