# Source Map and Evidence Levels

Last verified: 2026-07-23.

This file records the research basis used to build the skill. Re-check sources before claiming that a rapidly changing community node, workflow or model filename is still current.

## Evidence labels

- **Official:** Lightricks/LTX documentation, model card, repository or research paper.
- **Maintainer:** repository documentation from the node/workflow maintainer.
- **Community:** popular workflow collections/tutorials; useful for routing, not a guarantee.
- **Heuristic:** production recommendation inferred from model behavior and common failure patterns.

## Official LTX sources

1. **LTX-2.3 Prompt Guide — Official**  
   https://ltx.io/blog/ltx-2-3-prompt-guide  
   Basis for long/detailed shot descriptions, chronological action, present tense, physical cues, camera language, dialogue/audio construction, T2V/I2V/A2V distinctions, and common prompting mistakes.

2. **LTX-2.3 Model Page — Official**  
   https://ltx.io/model/ltx-2-3  
   Basis for improved prompt adherence, image-to-video, camera control, audio-to-video, native portrait/reframing, identity/style customization and LoRA support.

3. **LTX-2.3 Model Card — Official**  
   https://huggingface.co/Lightricks/LTX-2.3  
   Basis for joint audio-video architecture and checkpoint families including 22B dev, distilled variants, distilled LoRA and upscalers.

4. **LTX-Video Official Repository — Official**  
   https://github.com/Lightricks/LTX-Video  
   Basis for supported families such as synchronized audio/video, image-to-video, multi-keyframes, extension, video-to-video, LoRA/IC-LoRA, controls, upscalers and training tools.

5. **LTX-2 Research Paper — Official research**  
   https://arxiv.org/abs/2601.03233  
   Basis for the joint audio-visual foundation model description, dual streams and synchronized semantic/audio behavior.

## Prompt Relay source

6. **ComfyUI-PromptRelay — Maintainer**  
   https://github.com/kijai/ComfyUI-PromptRelay  
   Basis for inline `|` syntax, relative weights/ranges, block headers, global/static first segment, local-change-only later segments, timing options and the warning that the project is work in progress.

## Community workflow coverage

7. **RuneXX LTX-2.3 Workflows — Community**  
   https://huggingface.co/RuneXX/LTX-2.3-Workflows/tree/main  
   Used to survey active workflow categories: 3-pass, control reference, custom audio, first/last frame, long video, movie maker, multi-reference character sheet, music video, talking avatar/TTS, V2V, Foley, lipdub, retake, outpainting, transitions and editing.

8. **LTX-2.3 Prompt Relay workflow discussion — Community**  
   https://huggingface.co/Kijai/LTX2.3_comfy/discussions/51  
   Evidence that creators use Prompt Relay for multi-event temporal control and per-segment prompts/lengths; explicitly described as work in progress.

9. **RunComfy Prompt Relay workflow page — Community commercial catalog**  
   https://www.runcomfy.com/comfyui-workflows/ltx-2-3-prompt-relay-in-comfyui-image-to-video-workflow  
   Supporting evidence for segmented I2V, VLM-assisted beat drafting and optional LoRA workflow composition. Do not treat marketing claims as model guarantees.

10. **Multi-character Prompt Relay tutorials — Community**  
    Community tutorials published in 2026 demonstrate one-speaker-per-segment patterns. This skill adopts that pattern as a heuristic, while recommending custom audio/dual-character workflows for exact lip ownership.

## Codex skill format

11. **OpenAI Skills Catalog and Skill Creator — Official OpenAI**  
    https://github.com/openai/skills  
    https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md  
    Basis for the required `SKILL.md`, YAML `name` and `description`, recommended `agents/openai.yaml`, progressive disclosure and optional `references/` and `scripts/` resources.

## Important boundary statements

- Prompt Relay syntax is not a universal native LTX prompt format; it belongs to compatible nodes/workflows.
- Multi-person exact lip sync is workflow-dependent and remains more fragile than single-speaker generation.
- “Long video” community workflows usually chain or extend generation; continuity can degrade across repeated extensions.
- Specialized LoRA workflows can appear, change names or disappear rapidly. Inspect current graph dependencies and licenses.
- Native model capability, ComfyUI implementation capability and a specific downloaded workflow's capability are not identical.
