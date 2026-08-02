# ADR-0006：视频第三方渲染器与 Skills 并存

- **状态**：已接受（Accepted）
- **日期**：2026-08-02
- **模块**：跨模块（Skills / 渲染边界修订）

---

## 背景

V1 初版将 Remotion 主渲染与剪映草稿逆向列为延后项。业务需要将 HyperFrames、Remotion、video-use、Seedance、ChatCut、CapCut（原 cut-motion）、IP Strategist、OpenMontage 等 Skills **本地化**，并在视频任务中强制按场景路由调用。

用户确认：

- **B**：放宽 V1，允许 Remotion / ChatCut / CapCut 进入正式链路（非仅 reference_only）。
- **C**：ChatCut 与 CapCut/cut-motion 继任工具同时纳入。

## 决策

1. 第三方 Skills 以 `third_party_skills/` 为可提交副本，由 `scripts/vendor_video_skills.py` 从上游浅克隆/sparse 同步；大仓工作副本在 `vendor/repos/`（gitignore）。
2. 强制路由表见 [docs/video-plugin-routing.md](../video-plugin-routing.md)；`AGENTS.md` / `CLAUDE.md` / Cursor rules 必须引用该表。
3. `python -m avs` 仍是 Episode 状态机唯一入口；旁路渲染器不得伪造完成状态。
4. `timeline.json` 仍为共享协议；`renderer` 可扩展为 `ffmpeg` / `hyperframes` / `remotion` / `auto`（具体 CLI 子命令可后续模块实现）。
5. Remotion **允许**作为正式渲染器（`remotion_primary_renderer: true` 登记在 `skills.lock.json` 的 remotion 条目）；默认粗剪仍可为 FFmpeg，由路由决定是否启用 Remotion。
6. CapCut/剪映草稿工具（`capcut-david`、`cut-skill`）允许用于草稿生成与动效，产物须回挂 Episode。

## 后果

- 需维护 `vendor/manifests/video-third-party.yaml` 与 `npm run skills:vendor`。
- doctor 对 Remotion/ChatCut/CapCut/video-use 以 optional WARNING 检测，不阻断纯 FFmpeg 路径。
- OpenMontage AGPL-3.0 合规由使用者确认。

## 不做

- 本 ADR 不要求本轮实现完整 `avs render remotion`。
- 不将 Remotion monorepo / 完整 OpenMontage 提交进 git。
