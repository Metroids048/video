# HyperFrames 动效组件

本目录包含 Agent Video Studio V1 的三种可复用动效。组件只接收
`timeline.json` graphic clip 转换出的 variables，不读取 Episode 状态、原始
`input/` 或聊天上下文。

## 组件

| 组件 | 用途 | 默认时长 | 尺寸 |
|------|------|----------|------|
| `HookTitle` | 开头钩子标题 | 3s | 1080×1920 |
| `InfoCard` | 关键信息卡 | 4s | 1080×1920 |
| `EndCard` | 结尾引导卡 | 3s | 1080×1920 |

`compositions/demo/` 和根 `index.html` 将三个组件顺序组合为 10 秒验收片。

## 离线资源

`package.json` 锁定 GSAP 3.14.2。每个组件的 `assets/gsap.min.js` 是独立渲染所需
的本地副本，项目级 `assets/gsap.min.js` 供 Demo 子组合使用。HTML 不依赖 CDN。

## 验证与渲染

```bash
npm ci
npx hyperframes doctor
npx hyperframes check renderers/hyperframes --samples 8
npx hyperframes render renderers/hyperframes --quality standard \
  --output output/hyperframes-demo.mp4
```

若 HyperFrames 固定版 Chrome 无法启动，可设置项目级环境变量指向本机 Chrome：

```powershell
$env:HYPERFRAMES_BROWSER_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

AVS CLI 在 Windows 会自动探测该路径：

```bash
python -m avs motion render <ID>
```

## 数据和降级

`avs motion render` 读取 timeline graphic 轨并生成：

- `delivery/motion-graphics/*.mp4`
- `work/motion-manifest.json`
- `renders/preview-with-motion.mp4`
- `logs/hyperframes-render-<ID>.log`

CLI 未安装、lint 失败、render 失败、超时或输出损坏时，单个片段会降级成 FFmpeg
静态卡。基础 `preview-clean.mp4` 和 `preview-with-captions.mp4` 永远保留。

## 约束

- 画布固定为 1080×1920、30fps。
- 组件通过 variables 获取文案，不读取 `episode.json`。
- HyperFrames 不修改 Episode 状态。
- 组件使用本地中文字体声明，并通过 motion sidecar 验证寻址动画。

参考：

- `docs/decisions/0002-timeline-contract.md`
- `docs/decisions/0003-hyperframes-boundary.md`
