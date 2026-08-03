# Agent Video Studio V1 — 项目规范（索引副本）

> 原始文件：[docx/Agent_Video_Studio_V1_项目规范.md](../docx/Agent_Video_Studio_V1_项目规范.md)  
> 版本：1.0 | 日期：2026-07-20 | 状态：已冻结

本文件是规范的入口索引，包含最关键的决策摘要。各 Agent 开发时应直接读取原始文件全文。

---

## 快速参考

| 章节 | 内容 | 重要性 |
|------|------|-------|
| §1 项目结论 | 系统定位与交付标准 | 必读 |
| §3 范围 | V1 支持的输入/输出类型 | 必读 |
| §4 架构原则 | 单一真相、确定性/生成式分离 | 必读 |
| §5 技术基线 | 必需与推荐工具版本 | 必读 |
| §7 统一 CLI | `python -m avs` 命令完整列表 | 必读 |
| §8 目录结构 | 完整目录树 | 必读 |
| §9 Episode 工作目录 | 每期视频文件结构 | 必读 |
| §10 状态机 | 9+3 个状态和转换规则 | 必读 |
| §11 数据合同 | 8 个 JSON Schema 字段定义 | 实现时读 |
| §12 Provider 设计 | 转写/TTS/LLM 接口 | 实现时读 |
| §13 HyperFrames 边界 | 动效组件列表和集成方式 | 模块7读 |
| §14 项目 Skills | 9 个 Skill 名称和职责 | 各模块读 |
| §15 开发模块与依赖顺序 | 模块0–9 交付与验收 | 每模块读 |
| §16 测试策略 | 测试层级与完成声明 | 必读 |
| §17 Git 策略 | 提交/忽略规则 | 必读 |

---

## V1 边界

仍不得自行扩展到：

- 自动发布（抖音/小红书）
- 自动登录、评论、私信、多账号矩阵（ChatCut MCP 登录除外，凭证不入库）
- 数字人和声音克隆
- 云端分布式渲染
- 自动下载第三方平台视频

已放宽（ADR-0006）：Remotion、CapCut/剪映草稿工具、ChatCut、video-use、Seedance、OpenMontage、Pixelle-Video、IP Strategist，以及 JianyingEditor / FFmpeg / Azure Speech / ElevenLabs / 镜头脚本 / Epidemic Sound / MoneyPrinterTurbo 可进入正式链路，**必须**按 [video-plugin-routing.md](video-plugin-routing.md) 路由调用。

---

## 画布规格

- 分辨率：1080×1920（竖屏）
- 帧率：30fps
- 视频编码：H.264（libx264）
- 音频编码：AAC
- 像素格式：yuv420p
- 目标平台：抖音、小红书

---

## 核心合规规则

1. 唯一业务 CLI：`python -m avs`（见 ADR-0001）
2. `timeline.json` 是渲染器共享协议（见 ADR-0002）
3. HyperFrames 仅负责动效片段（见 ADR-0003）；其它渲染器见 ADR-0006
4. Skills 单一编辑源：自有 `skills-src/`（ADR-0004）；第三方 `third_party_skills/` + `npm run skills:vendor`
5. 原始素材不可变：`input/` 目录只读
6. 任何阶段失败保留已完成产物
7. 不自动发布，不存储密钥/Cookie
8. 未运行验证命令，不得声称完成
9. 视频任务强制路由：`docs/video-plugin-routing.md`

---

*阅读完整规范请打开 [docx/Agent_Video_Studio_V1_项目规范.md](../docx/Agent_Video_Studio_V1_项目规范.md)*
