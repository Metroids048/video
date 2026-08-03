# LTX-2.3 Prompt Director — Installation Guide

## A. Codex installation

Copy the entire `codex-skill` folder into one of these locations:

Windows custom Codex home:

```text
%CODEX_HOME%\skills\ltx-2-3-prompt-director
```

Default Windows location when `CODEX_HOME` is not customized:

```text
%USERPROFILE%\.codex\skills\ltx-2-3-prompt-director
```

Linux / WSL / macOS:

```text
~/.codex/skills/ltx-2-3-prompt-director
```

For the user's existing environment, the likely target is:

```text
C:\Users\KSK\.codex-bianyiwang\skills\ltx-2-3-prompt-director
```

Restart Codex after copying. Invoke it explicitly with:

```text
Use $ltx-2-3-prompt-director to convert this brief into an LTX-2.3 production prompt.
```

## B. Generic LLM installation

Use either file:

- `LTX-2.3-Prompt-Director-Universal-SKILL.md`: upload as a project knowledge/instruction file.
- `LTX-2.3-Prompt-Director-Universal-System-Prompt.txt`: paste into a system prompt, developer prompt, custom instructions, Gem, Project, Agent, or assistant configuration.

Recommended opening instruction:

```text
Read and follow the attached LTX-2.3 Prompt Director instructions. Treat the Core Skill Instructions as mandatory and consult the embedded reference chapters based on the requested workflow.
```

## C. Included capabilities

T2V, I2V, A2V, V2V, Prompt Relay, multi-person dialogue, TTS, reference audio, Lipdub, Foley, first/last and first/middle/last frames, long-video extension, loops, multi-reference identity, pose/depth/edge/camera controls, retake, inpaint, outpaint, restyle, advertising, cinematic scenes, music video, social video, and failure diagnosis.

## D. Safety and accuracy boundary

The skill distinguishes native model prompting from official workflow controls and community/experimental node graphs. Workflow-dependent capabilities must not be represented as guaranteed native behavior.
