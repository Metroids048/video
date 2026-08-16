# 视频第三方插件 / Skills 强制路由

> 任何视频相关任务开始前，Agent **必须**阅读本文件，并按场景加载对应 Skill（位于 `third_party_skills/`，已同步到 `.claude/skills/` 与 `.agents/skills/`）。
>
> 重新拉取上游：`npm run skills:vendor`  
> 锁文件：`skills.lock.json` → `third_party_skills`  
> 清单：`vendor/manifests/video-third-party.yaml`

## 硬规则

1. 不得跳过本路由表直接「自由发挥」剪辑/渲染。
2. `python -m avs` 仍是 Episode 状态机与交付包主入口。
3. Remotion / ChatCut / CapCut / OpenMontage / Pixelle-Video / MoneyPrinterTurbo / JianyingEditor 产出必须落到对应 Episode 的 `work/` 或 `output/`，不得伪造 `QA_PASSED`。
4. FFmpeg 只可降级为可检查的确定性装配，不能把“静态卡 + 长字幕”伪装成可发布成片；其它渲染器失败 → 非零退出并报告，禁止静默成功。
5. ChatCut 需本机 MCP 登录；Epidemic Sound 需官方 MCP；脚本只 vendoring Skills，不代登、不存密钥。

### 录屏像素完整性（P0）

1. 录屏须在时间线中明确标注全页建立场景或 ROI Screen Focus。ROI 只能服务于当前口播证据，不能成为全局 `cover`、自动重构图或裁掉真实页面边界的默认。
2. 全页镜头用于建立场景，ROI 镜头用于余额、订单、仓位、历史等证据可读性；目标比例不同时不得把横屏缩成黑边细条。
3. 在交付前，至少抽取源视频与输出的对应帧，确认原始左边界、右边界、顶部导航和底部内容仍可见。
   任一边界内容在输出中缺失时，必须报 `FAIL_SOURCE_FRAME_CROPPED` 并停止交付。

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
| **剪映 JyWrapper 自动化**（智能配音字幕、录屏变焦、云端素材） | **jianying-editor**（与 cut-skill **并存分流**） | `third_party_skills/jianying-editor` |
| FFmpeg 探测/裁切/混音/字幕烧录/转码 | **ffmpeg**（先读 Skill，再走 AVS 主链） | `third_party_skills/ffmpeg` |
| Azure 神经语音 TTS/STT | **azure-speech**（需 Azure 凭证；默认仍优先免费平替） | `third_party_skills/azure-speech` |
| ElevenLabs 高表现配音 / SFX / 音乐 | **elevenlabs**（入口同 `text-to-speech`；需 API Key） | `third_party_skills/elevenlabs`、`text-to-speech` |
| 镜头脚本 / 分镜提示词 | **ai-video-shot-prompt** | `third_party_skills/ai-video-shot-prompt` |
| LTX-2.3 镜头/生产提示词路由 | **ltx-prompt-director** | `third_party_skills/ltx-prompt-director` |
| 版权音乐 / Epidemic Sound 曲库 | **epidemic-sound**（官方 MCP；无账号则标缺口） | `third_party_skills/epidemic-sound` |
| 主题一键短视频旁路 | **moneyprinterturbo**（产物回挂 Episode） | `third_party_skills/moneyprinterturbo` |
| **主题一键短视频旁路（ComfyUI/直连 API）** | **pixelle-video**（产物回挂 Episode） | `third_party_skills/pixelle-video` |
| 账号定位 / 选题 / 口播策略（不碰剪辑） | ip-strategist | `third_party_skills/ip-strategist` |
| 多管线 Agent 制片、纪录片蒙太奇 | openmontage（再读 `vendor/repos/openmontage/AGENT_GUIDE.md`） | `third_party_skills/openmontage` |
| 镜头语法 / 节奏 / 声音设计参考（非主渲染） | **video-shotcraft**（`usage: reference_only`） | `third_party_skills/video-shotcraft` |

镜头语法/节奏参考使用已 pin 的 `video-shotcraft`（`usage: reference_only`），不替代上表渲染器。

### 剪映分流

- **JyWrapper / 智能配音字幕 / 录屏变焦 / 云端素材进草稿** → `jianying-editor`
- **统一 CLI、Premiere、既有 AVS CapCut 草稿链路** → `cut-skill` + `capcut-david`

### 配音优先级

1. 默认免费平替（Edge TTS / 项目 Whisper 转写等）
2. 用户明确要求 Azure → `azure-speech`
3. 用户明确要求 ElevenLabs 高表现 → `elevenlabs` / `text-to-speech`

### 真人口播录屏专题（强制组合）

1. 先调用 `video-use` / Whisper，复用 VCI 中已有的转写与词级时间戳；生成语义切分 SRT 和 EDL。
2. 有本机 ChatCut 登录时，优先用 ChatCut 处理口播删句、停顿与可视时间线；无登录时用 FFmpeg 仅做确定性装配。
3. Remotion / HyperFrames 只可为 SRT 关键词加微动效，不能替代真实录屏证据或制造整屏 PPT。
4. 没有“新口播逐句同步录屏”不构成阻塞；使用原始录屏和参考成片的真实镜头池按语义重新映射。

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
| JianyingEditor（JyWrapper） | https://github.com/luoluoluo22/jianying-editor-skill |
| FFmpeg Skill | https://github.com/ychoi-kr/claude-ffmpeg-skill |
| Azure Speech Skill | https://github.com/MicrosoftDocs/Agent-Skills（`skills/azure-speech`） |
| ElevenLabs Skills | https://github.com/elevenlabs/skills |
| 镜头脚本 Shots | https://github.com/Wayhhow/ai-video-shot-prompt-skill |
| LTX Prompt Director | https://github.com/AI-KSK/ltx-2-3-prompt-director |
| Epidemic Sound MCP | https://www.epidemicsound.com/a/mcp-service/mcp |
| MoneyPrinterTurbo | https://github.com/harry0703/MoneyPrinterTurbo（仅 vendor `docs/skill`） |
| Pixelle-Video | https://github.com/AIDC-AI/Pixelle-Video（仅 sparse README/docs/config） |
| IP Strategist | https://github.com/erduo1998-cell/ip-strategist |
| 开放蒙太奇 | https://github.com/calesthio/OpenMontage |
| video-shotcraft（参考库） | https://github.com/Vincentwei1021/video-shotcraft |

## 与 AVS 主链的关系

```
Episode 状态机 (python -m avs)
        │
        ├── FFmpeg 粗剪（默认；先读 ffmpeg Skill）
        ├── HyperFrames 动效片段
        ├── Remotion（代码驱动成片，按路由启用）
        ├── video-use / ChatCut / CapCut / JianyingEditor（剪辑旁路，产物回挂 Episode）
        ├── Azure / ElevenLabs / Epidemic Sound（音轨旁路，需密钥或 MCP）
        ├── MoneyPrinterTurbo / Pixelle-Video（主题短视频旁路，产物回挂 Episode）
        └── OpenMontage（多 pipeline，产物回挂 Episode）
```

共享协议仍是 `timeline.json`（见 ADR-0002）。旁路渲染器写入的片段应可被时间线引用或在交付说明中标明。

## 已知限制

- OpenMontage 仅 sparse vendor（skills / pipeline_defs / AGENT_GUIDE）；完整 700+ skill 不进 git。
- Pixelle-Video 仅 sparse README/docs/config；完整 ComfyUI/workflows/模型不进 `third_party_skills/`。
- Remotion monorepo 不整仓入库；运行时按需 `npm` 安装。
- MoneyPrinterTurbo **仅** sparse `docs/skill`；禁止把整仓复制进 `third_party_skills/`。
- Epidemic Sound **无**公开 SKILL.md 仓；项目内为 curated 入口，依赖官方 MCP 与账号。
- Azure / ElevenLabs / Epidemic Sound / MoneyPrinterTurbo / Pixelle-Video 云端能力需要本机密钥或登录；密钥只进 `.env`，永不入库。
- **付费 API 已有免费默认平替**：转写 → `faster-whisper`（`scripts/free_providers/whisper_transcribe.py`）；Seedance 出片 → `seedance-free` / OpenMontage / HyperFrames；TTS → Edge TTS。ElevenLabs / Kie / Azure 仅为可选升级。
- ChatCut 示例项目：https://app.chatcut.io/editor/5f02e41f-5749-4548-bd40-7a706de4230c
- OpenMontage 为 AGPL-3.0，正式商用前需合规确认。
- JianyingEditor 自动导出依赖 Windows + 剪映 ≤5.9；与 `cut-skill` 不要互相覆盖草稿而不备份。
