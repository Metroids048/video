# 视频第三方插件 / Skills 强制路由

> 任何视频相关任务开始前，Agent **必须**阅读本文件，并按场景加载对应 Skill（位于 `third_party_skills/`，已同步到 `.claude/skills/` 与 `.agents/skills/`）。
>
> 重新拉取上游：`npm run skills:vendor`  
> 锁文件：`skills.lock.json` → `third_party_skills`  
> 清单：`vendor/manifests/video-third-party.yaml`

## 硬规则

1. 不得跳过本路由表直接「自由发挥」剪辑/渲染。
2. `python -m avs` 仍是 Episode 状态机与交付包主入口。
3. Remotion / ChatCut / CapCut / OpenMontage 产出必须落到对应 Episode 的 `work/` 或 `output/`，不得伪造 `QA_PASSED`。
4. HyperFrames 失败 → FFmpeg 静态卡降级；其它渲染器失败 → 非零退出并报告，禁止静默成功。
5. ChatCut 需本机 MCP 登录；脚本只 vendoring Skills，不代登、不存密钥。

## 场景 → Skill

| 场景 | 必须调用的 Skill / 插件 | 本地路径 |
|------|-------------------------|----------|
| 动效标题、信息卡、结尾卡、HTML 动效 | HyperFrames（先读 `hyperframes`，CLI 用 `hyperframes-cli`） | `third_party_skills/hyperframes` |
| React/代码驱动成片、可复用模板片 | Remotion（入口 `remotion-best-practices` / `remotion`） | `third_party_skills/remotion*` |
| 即梦 / Seedance 提示词与分镜 | seedance（可只写 prompt） | `third_party_skills/seedance` |
| **免费**图生短镜头（不付 Kie） | **seedance-free**（FFmpeg Ken Burns） | `third_party_skills/seedance-free` |
| 对话式粗剪、转写切条、EDL | video-use（**默认免费 Whisper**；可选 ElevenLabs） | `third_party_skills/video-use` |
| 云端可编辑时间线、ChatCut 项目 | ChatCut（先读 `chatcut/chatcut-plugin-basics-claude`；动效用 `create-motion-graphics`） | `third_party_skills/chatcut/` |
| CapCut/剪映草稿 Ken Burns、关键帧、成片草稿（原 cut-motion） | `capcut-david` + `cut-skill` | `third_party_skills/capcut-david`、`cut-skill` |
| 账号定位 / 选题 / 口播策略（不碰剪辑） | ip-strategist | `third_party_skills/ip-strategist` |
| 多管线 Agent 制片、纪录片蒙太奇 | openmontage（再读 `vendor/repos/openmontage/AGENT_GUIDE.md`） | `third_party_skills/openmontage` |

镜头语法/节奏参考仍可使用已 pin 的 `video-shotcraft`（`usage: reference_only`），不替代上表渲染器。

## 上游仓库

| 能力 | 仓库 |
|------|------|
| HyperFrames | https://github.com/heygen-com/hyperframes |
| Remotion 框架 | https://github.com/remotion-dev/remotion |
| Remotion Skills | https://github.com/remotion-dev/skills |
| video-use | https://github.com/browser-use/video-use |
| Seedance | https://github.com/automatorsplus/seedance-skill |
| ChatCut | https://github.com/ChatCut-Inc/agent-plugin |
| CapCut CLI（cut-motion 继任） | https://github.com/Davidb-2107/capcut-cli-david |
| 剪映/CapCut 统一操控 | https://github.com/ygtec/cut.skill |
| IP Strategist | https://github.com/erduo1998-cell/ip-strategist |
| 开放蒙太奇 | https://github.com/calesthio/OpenMontage |

## 与 AVS 主链的关系

```
Episode 状态机 (python -m avs)
        │
        ├── FFmpeg 粗剪（默认）
        ├── HyperFrames 动效片段
        ├── Remotion（代码驱动成片，按路由启用）
        ├── video-use / ChatCut / CapCut（剪辑旁路，产物回挂 Episode）
        └── OpenMontage（多 pipeline，产物回挂 Episode）
```

共享协议仍是 `timeline.json`（见 ADR-0002）。旁路渲染器写入的片段应可被时间线引用或在交付说明中标明。

## 已知限制

- OpenMontage 仅 sparse vendor（skills / pipeline_defs / AGENT_GUIDE）；完整 700+ skill 不进 git。
- Remotion monorepo 不整仓入库；运行时按需 `npm` 安装。
- **付费 API 已有免费默认平替**：转写 → `faster-whisper`（`scripts/free_providers/whisper_transcribe.py`）；Seedance 出片 → `seedance-free` / OpenMontage / HyperFrames。ElevenLabs / Kie 仅为可选升级。
- ChatCut 示例项目：https://app.chatcut.io/editor/5f02e41f-5749-4548-bd40-7a706de4230c
- OpenMontage 为 AGPL-3.0，正式商用前需合规确认。
