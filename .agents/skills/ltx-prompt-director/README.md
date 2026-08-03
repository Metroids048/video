# LTX-2.3 Prompt Director

LTX-2.3 Prompt Director is a Codex skill for creating, rewriting, routing, and diagnosing production-ready prompts for **LTX-2.3** and its ComfyUI ecosystem.

It works as a director, not a keyword decorator: it classifies the shot, chooses the right generation mode, writes a chronological English model prompt, and separates native prompt control from official workflow controls and community/experimental graphs.

## What It Is For

- Text-to-video (T2V) shot prompts
- Image-to-video (I2V) motion prompts that respect the starting frame
- Audio-to-video (A2V) and custom-audio driven performance
- Video-to-video, retake, inpaint, outpaint, restyle, and preserve/edit briefs
- Prompt Relay multi-beat timing
- First/Last and First/Middle/Last frame workflows
- Multi-person dialogue, talking avatars, Lipdub, TTS, reference audio, and Foley
- Multi-reference identity, pose/depth/edge/camera control
- Long-video extension, loops, music video, product ads, cinematic and social video
- Failure diagnosis when a generation drifts, freezes, or desyncs

## Core Philosophy

An LTX prompt is a **chronological shot description**, not a tag pile.

Prefer:

```text
A woman walks through rain-soaked neon streets at night. She pauses under a red awning, looks left, then continues past a glass storefront as reflections slide across the frame. Handheld medium shot follows from behind and slightly to the side. Soft rain, wet asphalt sheen, distant traffic ambience, and light footsteps stay synchronized with the motion.
```

Avoid dumping unrelated tags without time order, camera plan, or audio alignment.

Default model prompt language is **English**, even when the user brief is Chinese. Spoken dialogue keeps its target language and can be labeled with language/accent when needed.

## Capability Layers

The skill deliberately distinguishes three layers:

1. **Native prompt control** — subject, action, camera, lighting, dialogue, ambience, Foley, music, temporal order
2. **Official model/workflow control** — image conditioning, keyframes, A2V, V2V, extension, LoRA/IC-LoRA, pose/depth/edge/camera, retake, lipdub, upscaling
3. **Community/experimental control** — Prompt Relay implementations, multi-speaker packs, first-middle-last guiders, long-loop graphs, multi-reference identity stacks, specialized effect LoRAs

Workflow-dependent features are labeled as such and never promised as guaranteed native model behavior.

## Typical Routing

| User intent | Preferred route |
|---|---|
| One coherent shot from text | T2V single prompt |
| Animate a still image | I2V motion prompt |
| Drive visuals from audio | A2V / custom-audio workflow |
| Several timed actions in one clip | Prompt Relay |
| Exact open and end composition | First/Last Frame |
| Preserve a midpoint composition too | First/Middle/Last Frame |
| Two or more speaking characters | Prompt Relay + speaker blocking; add TTS/reference audio when exact voice/lips matter |
| Translate/rephrase an existing performance | Lipdub |
| Keep a specific person across shots | Reference image + face-ID/ID-LoRA or trained identity LoRA |

## Output Shape

Depending on the request, the skill can return:

- Final English production prompt
- Prompt Relay segmented fields
- Workflow route recommendation
- Preserve / change / control notes
- Parameter hints when useful
- Bilingual explanation
- Failure diagnosis and repair rewrite

It can also run structural checks through `scripts/ltx_prompt_lint.py`.

## Included Files

### Codex skill core

- `SKILL.md` — main Codex skill instructions and routing
- `agents/openai.yaml` — Codex agent display metadata
- `references/model-and-workflow-map.md` — mode and workflow matrix
- `references/prompt-construction-playbook.md` — shot writing rules
- `references/prompt-relay.md` — multi-beat / Prompt Relay guidance
- `references/dialogue-audio-lipsync.md` — dialogue, TTS, lip sync, audio routing
- `references/scenario-library.md` — common production scenarios
- `references/troubleshooting-and-qa.md` — failure diagnosis
- `references/source-map.md` — source and capability boundaries
- `scripts/ltx_prompt_lint.py` — lightweight prompt lint helper
- `manifest.txt` — package file list

### Complete pack extras

- `INSTALL.md` — Codex and generic LLM install notes
- `LTX-2.3-Prompt-Director-Core-SKILL.md` — core skill export
- `LTX-2.3-Prompt-Director-Universal-SKILL.md` — full universal skill document for non-Codex hosts
- `LTX-2.3-Prompt-Director-Universal-System-Prompt.txt` — paste-ready system/developer prompt

## Install

### Codex

Clone or copy into your Codex skills directory:

```powershell
git clone https://github.com/AI-KSK/ltx-2-3-prompt-director.git "$env:CODEX_HOME/skills/ltx-2-3-prompt-director"
```

If your Codex home is customized:

```powershell
Copy-Item -Recurse . "C:\Users\KSK\.codex-bianyiwang\skills\ltx-2-3-prompt-director"
```

Start a new Codex turn, then invoke explicitly when needed:

```text
Use $ltx-2-3-prompt-director to convert this brief into an LTX-2.3 production prompt.
```

### Generic LLM / project knowledge

Use either:

- `LTX-2.3-Prompt-Director-Universal-SKILL.md` as project knowledge
- `LTX-2.3-Prompt-Director-Universal-System-Prompt.txt` as a system/developer/custom instruction

Recommended opening instruction:

```text
Read and follow the attached LTX-2.3 Prompt Director instructions. Treat the Core Skill Instructions as mandatory and consult the embedded reference chapters based on the requested workflow.
```

## Safety And Accuracy Boundary

This skill does **not** promise:

- exact text or logo fidelity from prompt alone
- perfect multi-person lip sync without the right audio/lip workflow
- unlimited long-video consistency without extension/loop graphs
- community node features as native model guarantees

It produces the smallest prompt and workflow specification that can reliably express the intended shot.

## 中文说明

这是一个面向 **LTX-2.3** 的视频提示词导演技能，用来把中文/英文 brief 整理成可直接生产的英文镜头提示词，并自动判断该走 T2V、I2V、A2V、V2V、Prompt Relay、首尾帧、对话口型、长视频扩展等哪条路线。

它不是堆标签工具，而是按时间顺序写镜头：主体动作、镜头运动、光线环境、同步音频、需要保留/修改的内容都会分清楚。同时会区分：

- 模型原生提示词能力
- 官方工作流控制项
- 社区/实验节点能力

适合 ComfyUI、RunningHub、本地 LTX 工作流，以及需要把创意压力测试、广告、对话数字人、音乐视频等 brief 转成可执行生产提示词的场景。
