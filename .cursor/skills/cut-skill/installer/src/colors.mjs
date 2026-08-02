// colors.mjs — 终端着色（无第三方依赖）
// 仅在 TTY 输出时着色，管道/重定向时自动禁用

const isTTY = process.stdout.isTTY;
const NO_COLOR = process.env.NO_COLOR;

function colorize(code) {
  if (!isTTY || NO_COLOR) return (s) => String(s);
  return (s) => `\x1b[${code}m${s}\x1b[0m`;
}

function colorizeBold(code) {
  if (!isTTY || NO_COLOR) return (s) => String(s);
  return (s) => `\x1b[1m\x1b[${code}m${s}\x1b[0m`;
}

export const bold = isTTY && !NO_COLOR ? (s) => `\x1b[1m${s}\x1b[0m` : (s) => String(s);
export const dim = colorize(2);
export const red = colorize(31);
export const green = colorize(32);
export const yellow = colorize(33);
export const cyan = colorize(36);
