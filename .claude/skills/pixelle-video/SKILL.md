---
name: pixelle-video
description: >
  【Pixelle-Video】AI 全自动短视频引擎入口。
  主题一键：文案 → AI 配图/视频 → TTS → BGM → 成片。
  基于 ComfyUI / RunningHub / 直连 API；产物必须回挂 Episode。
trigger: Pixelle、Pixelle-Video、主题一键短视频、ComfyUI 短视频引擎
inputs: []
read_only:
  - input/
outputs: []
run: "参阅 vendor/repos/pixelle-video/README.md 与 docs/；按官方方式生成后回挂 Episode"
verify: "确认 MP4 落入 Episode work/ 或 output/，且未伪造 QA_PASSED"
stop_when: "缺 LLM/ComfyUI/API 凭证或用户停止"
on_missing_input: "列出服务/密钥缺口并停止，不伪造成片"
report_format: "命令、退出码、产物路径、已知限制"
---

# Pixelle-Video 入口

Sparse checkout at `vendor/repos/pixelle-video` (README / docs / config.example).

上游：https://github.com/AIDC-AI/Pixelle-Video

文档站：https://aidc-ai.github.io/Pixelle-Video/zh

## 必读

1. `vendor/repos/pixelle-video/README.md`（或 `README_EN.md`）
2. `vendor/repos/pixelle-video/docs/`（安装、工作流、API）
3. `vendor/repos/pixelle-video/config.example.yaml`（本机配置模板；真实密钥只进 `.env` / 本机配置，永不入库）

## 硬规则

1. **禁止**把完整 ComfyUI 模型仓或整仓 Python 包复制进 `third_party_skills/`。
2. 旁路生成的成片必须落到对应 Episode 的 `work/` 或 `output/`。
3. 不得跳过 AVS 状态机或伪造 `QA_PASSED`。
4. LLM / RunningHub / DashScope 等密钥只放本机 `.env`，不写入仓库。

## 与 AVS 的关系

- Episode 状态机仍由 `python -m avs` 管理。
- Pixelle-Video 是主题一键短视频旁路（与 `moneyprinterturbo` 类似），不是默认主链替代。
- 共享协议仍是 `timeline.json`；旁路产物在交付说明中标明来源。

## Agent 操作（摘要）

1. 确认用户要「主题 → 成片」且同意走 Pixelle 旁路。
2. 检查本机是否已按官方文档安装（Windows 整合包或源码 + uv）。
3. 缺凭证时一次性列出缺口；有凭证则按 README/API 生成竖屏短视频。
4. 将最终 MP4 复制/挂载到当前 Episode 工作目录并报告路径。
