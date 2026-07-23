# HyperFrames 动效组件

本目录包含 Agent Video Studio V1 使用的 HyperFrames 动效组件。

## 组件清单

| 组件 | 用途 | 时长 | 尺寸 |
|------|------|------|------|
| `HookTitle` | 开头钩子标题动效 | 3s | 1080×1920 |
| `InfoCard` | 关键信息展示卡 | 4s | 1080×1920 |
| `EndCard` | 结尾引导关注卡 | 3s | 1080×1920 |

## 使用方式

### 1. 安装 HyperFrames（可选）

```bash
npm install -g hyperframes
```

### 2. 本地预览

```bash
cd renderers/hyperframes/components/HookTitle
npx hyperframes preview index.html
```

### 3. 渲染输出

```bash
npx hyperframes render index.html --output ../../output/hook-title.mp4
```

### 4. 通过 AVS CLI 自动调用

```bash
# HyperFrames 成功时自动合成动效；失败时降级到 FFmpeg 静态卡片
python -m avs render rough <ID>
```

## 数据输入

HyperFrames 组件从以下来源获取参数：
1. `timeline.json` 中标记为 `"renderer": "hyperframes"` 的 Clip
2. URL query params：`?title=xxx&subtitle=yyy`
3. `window.HYPERFRAMES_DATA` 全局变量（优先级最低）

**禁止**直接从聊天上下文或 `episode.json` 读取数据。

## 降级路径

当 HyperFrames 失败时（CLI 未安装、lint 失败、render 超时、输出损坏），AVS 自动降级到 FFmpeg 静态卡片，确保基础粗剪仍可交付。

降级行为在 `src/avs/render/ffmpeg.py` 中实现，HyperFrames 组件无需关心降级逻辑。

## 开发规范

- 所有组件使用 1080×1920 画布
- 字体：优先使用系统安装的中文字体（Microsoft YaHei / PingFang SC）
- 动画时长：控制在 0.5–1.0s 进入 + 静态展示 + 0.3–0.5s 退出
- 测试：本地预览时检查中文渲染、动效流畅度、边界情况

## 参考

- HyperFrames 官方文档：https://hyperframes.dev
- AVS 时间线协议：`docs/decisions/0002-timeline-contract.md`
- HyperFrames 边界：`docs/decisions/0003-hyperframes-boundary.md`
