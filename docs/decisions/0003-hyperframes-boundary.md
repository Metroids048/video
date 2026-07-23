# ADR-0003：HyperFrames 边界——仅负责动效片段

- **状态**：已接受（Accepted）
- **日期**：2026-07-20
- **模块**：0（设计冻结）

---

## 背景

HyperFrames 是一个基于 HTML/CSS 的确定性视频动效框架，支持 preview、lint 和 render CLI 命令。早期方案存在将整个制作流程（包括 Episode 状态、输入管理、参考分析）写入 HyperFrames 组件的风险，这会造成框架越权、降级路径缺失、核心流程对 HyperFrames 产生硬依赖。

---

## 决策

**HyperFrames 只负责动效片段的渲染，其边界严格限定如下。**

### HyperFrames 负责

| 组件 | 用途 |
|------|------|
| `HookTitle` | 开头钩子标题动效（V1 必须实现） |
| `InfoCard` | 关键信息展示卡（V1 必须实现） |
| `EndCard` | 结尾引导关注/点赞卡（V1 必须实现） |
| `KeywordCaption` | 关键词高亮字幕动效（V1 可选） |
| `ScreenRecordingFrame` | 录屏强调框（V1 可选） |
| `RankingCard` | 排行榜卡片（V1 可选） |
| `BeforeAfter` | 前后对比（V1 可选） |
| 其他可复用解释动画 | 后续迭代添加 |

### HyperFrames 不负责

- Episode 状态读写
- `input/` 目录管理
- 参考视频语义分析
- 完整业务时间线管理
- 发布动作
- 事实判断

### 集成架构

```
timeline.json（唯一真相来源）
    │
    ├── FFmpeg 渲染：视频主轨 + 音频 + 静态字幕
    │
    └── HyperFrames 渲染：动效片段（独立 MP4 或可合成素材）
               │
               ▼
           FFmpeg 合成 → preview-with-captions.mp4
```

### 数据输入规范

HyperFrames 组件必须从以下来源获取参数：
1. `timeline.json` 中标记为 `"renderer": "hyperframes"` 的 Clip 条目，或
2. 独立 motion manifest 文件

HyperFrames 组件不得直接读取聊天上下文或 Episode JSON。

### 降级路径（必须实现）

```
HyperFrames 失败原因                降级行为
─────────────────────────────────   ──────────────────────────────
HyperFrames CLI 未安装              FFmpeg 静态文字卡替代
npx hyperframes lint 失败           FFmpeg 静态文字卡替代 + warning
npx hyperframes render 失败         FFmpeg 静态文字卡替代 + warning
渲染超时                            FFmpeg 静态文字卡替代 + warning
输出文件损坏                        FFmpeg 静态文字卡替代 + warning
```

任何降级情况均记录到 Episode 日志和 `qa-report.md`，但不阻止基础粗剪交付。

---

## 原因

- 防止核心流程对 HyperFrames 产生硬依赖——这是规范明确要求的可降级设计
- HyperFrames 在 Windows 环境下可能遇到 Chromium/Puppeteer 安装问题，必须有干净的降级路径
- 边界清晰后，HyperFrames 组件开发者可独立测试组件，无需了解 Episode 业务逻辑
- 与 ADR-0002 配合：HyperFrames 从 `timeline.json` 读参数，通过 FFmpeg 合成，形成闭环

---

## 后果

**正面：**
- 模块 6 可以在没有 HyperFrames 的情况下完整验收（基础粗剪）
- 模块 7 的失败不影响模块 6 的成果
- HyperFrames 组件单元测试独立，可在隔离环境运行

**需注意：**
- 模块 7 必须实现三个最小组件（HookTitle、InfoCard、EndCard）并通过 doctor/lint/render
- 降级路径必须生成可播放的 FFmpeg 静态卡片，不得生成损坏视频

---

## 合规检测

若在 `renderers/hyperframes/` 中发现 Episode 状态操作、输入文件访问或发布调用，视为违反本 ADR，需立即重构。
