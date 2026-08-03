---
name: ltx-2-3-prompt-director
description: Create, rewrite, diagnose, and route production-ready prompts for LTX-2.3 and its ComfyUI ecosystem. Use for text-to-video, image-to-video, audio-to-video, video-to-video, Prompt Relay, first/last or first/middle/last frame, multi-person dialogue, talking avatars, lipdub, custom audio, Foley, music video, long-video extension, loops, multi-reference identity, pose/depth/edge/camera control, retake, inpaint, outpaint, restyle, product ads, cinematic shots, social video, and prompt troubleshooting. Accept Chinese or English briefs; produce model-ready English prompts by default and distinguish official model capabilities from community or experimental workflows.
---

# LTX-2.3 Prompt Director

Use this skill as a **director, prompt architect, workflow router, and failure diagnostician** for LTX-2.3. Do not merely decorate the user's words. Determine the generation mode, temporal structure, identity/audio/control requirements, then write the smallest prompt and workflow specification that can reliably express the intended shot.

## Core operating rules

1. Treat an LTX prompt as a **chronological shot description**, not a tag pile.
2. Use **present tense**, observable physical actions, explicit camera behavior, lighting, environment, and synchronized audio.
3. Default to an **English model prompt**, even when the brief is Chinese. Keep requested spoken dialogue in its target language and label the language/accent when relevant.
4. Distinguish three layers:
   - **Native prompt control:** subject, action, camera, lighting, dialogue, ambience, Foley, music, temporal order.
   - **Official model/workflow control:** image conditioning, multiple keyframes, A2V, V2V, video extension, LoRA/IC-LoRA, pose/depth/edge/camera controls, retake, lipdub, upscaling.
   - **Community/experimental control:** Prompt Relay implementations, multi-speaker packs, first-middle-last guiders, long-loop graphs, multi-reference identity stacks, specialized effect LoRAs. Label these as workflow-dependent rather than guaranteed model behavior.
5. Never promise exact text rendering, exact logo fidelity, exact multi-person lip synchronization, or unlimited long-video consistency from prompt text alone.
6. For I2V, describe **what begins moving and what happens next**. Do not waste tokens redescribing static details already visible in the input image.
7. For A2V, treat the supplied audio as the timing backbone. Describe the visual performance, subject identity, camera, environment, and reactions that should align to it.
8. For V2V/editing, specify **what must remain unchanged**, what may change, where the change occurs, and whether motion/timing/camera should be preserved.
9. Use Prompt Relay only when one flowing prompt cannot clearly allocate different actions, speakers, or camera beats across time.
10. Prefer one decisive camera plan. Multiple incompatible camera instructions often reduce adherence.

## First classify the request

Determine these fields before writing:

- `mode`: T2V, I2V, A2V, V2V, Lipdub, Talking Avatar, Prompt Relay, FLF/FML, Control, Retake/Edit, Long/Loop, Music Video, or Multi-reference.
- `duration`: seconds and, when known, frame count/fps.
- `aspect`: landscape, portrait, square, or source-preserving.
- `subject_count`: one, two, or crowd.
- `identity_requirement`: loose, reference-image, face-ID/ID-LoRA, character sheet, or trained LoRA.
- `dialogue_requirement`: none, single speaker, alternating speakers, overlap, voice clone, translation/dubbing.
- `audio_source`: native generated audio, reference audio, TTS, music track, silent, or preserve source audio.
- `temporal_complexity`: one action, chained action, multi-beat, multi-scene, or continuation.
- `control_requirement`: pose, depth, edge/canny, motion track, camera path, masks, keyframes, or none.
- `preserve`: subject, wardrobe, background, composition, motion, timing, camera, audio, or selected regions.
- `deliverable`: final prompt only, bilingual explanation, Prompt Relay fields, workflow recommendation, parameter hints, or failure repair.

When important values are missing, infer conservative defaults and state them briefly. Ask questions only when the missing information makes the requested result materially impossible; otherwise produce a usable draft immediately.

## Route to the right workflow family

Use `references/model-and-workflow-map.md` for the full matrix. Apply these defaults:

| User intent | Preferred route |
|---|---|
| One coherent shot from text | T2V single prompt |
| Animate a supplied still | I2V motion prompt |
| Drive visuals from an audio clip | A2V/custom-audio workflow |
| Several timed actions in one clip | Prompt Relay |
| Exact opening and ending composition | First/Last Frame |
| Preserve a midpoint composition too | First/Middle/Last Frame guider |
| Two or more speaking characters | Prompt Relay + speaker blocking; add TTS/reference audio or dual-character workflow when exact voice/lips matter |
| Translate/rephrase an existing performance | Lipdub workflow |
| Add speech to an existing silent person | Just-Talk / masked V2V talking workflow |
| Preserve a specific person across shots | Reference image + face-ID/ID-LoRA; trained identity LoRA for repeated production |
| Transfer body motion or camera motion | Pose/motion/camera control workflow |
| Change only part of a video | V2V inpaint/retake with mask |
| Add/remove/replace/restyle content | EditAnything/V2V editing route |
| Reframe landscape ↔ portrait | Outpaint/reframing IC-LoRA |
| Continue beyond one generation | Forward/backward extension; render in controlled shot units |
| Seamless repetition | Loop workflow with end-state matching |
| Music-driven cuts or performance | Music-video workflow + beat-based Prompt Relay |
| Improve resolution/details | Multiscale, spatial/temporal upscaler, or detailer route; do not encode “4K” as a substitute for workflow settings |

## Build the prompt with the SHOT-AUDIO sequence

Construct a single-shot prompt in this order. It should normally read as one flowing paragraph:

1. **Shot and medium** — cinematic/live action/animation, framing, lens feel, viewpoint.
2. **Hero subject** — only identity-defining visible attributes necessary for this shot.
3. **Opening state** — where the subject is, posture, gaze, object relationships.
4. **Ordered action** — “At first… then… as… finally…”; use physical cues rather than abstract emotion labels.
5. **Camera execution** — one primary move and, at most, one compatible secondary adjustment.
6. **Environment reaction** — cloth, hair, particles, reflections, props, background movement.
7. **Lighting and visual finish** — motivated light, contrast, palette, texture, medium/style.
8. **Audio timeline** — dialogue in quotes, voice quality, pauses, Foley, ambience, music, and silence.
9. **Ending state** — final pose/composition when continuity or looping matters.

### Physicalize emotions

Replace abstract directions with visible behavior:

- Weak: “She is anxious.”
- Better: “Her shoulders tighten, she draws a shallow breath, glances toward the door, and grips the paper until its edge bends.”

- Weak: “He speaks confidently.”
- Better: “He holds steady eye contact, keeps his chin level, and delivers the line without hesitation.”

### Keep temporal density realistic

These are production heuristics, not hard model limits:

- 3–5 seconds: one principal action, optionally one reaction.
- 6–10 seconds: two to four clear beats; use Prompt Relay if timing matters.
- 10–20 seconds: a controlled continuous shot with several simple beats, or Prompt Relay/keyframes. Avoid writing a full screenplay into one generation.
- Longer narratives: divide into shots and maintain continuity through references, LoRAs, keyframes, and extension workflows.

## Mode-specific writing

### T2V

Describe subject, setting, chronological action, camera, lighting, and audio. Start with the most visually consequential information. Avoid mutually exclusive art directions.

### I2V

Assume the source image supplies appearance and composition. Write:

`[initial motion] → [main action] → [camera response] → [secondary environmental motion] → [audio] → [ending state]`

Do not invent a different outfit, face, location, or composition unless the user explicitly requests transformation.

### A2V/custom audio

Treat audio timing as fixed. Identify who performs, the style of performance, mouth/body behavior, camera response, and environmental reaction. Do not include a second contradictory dialogue script when reference audio already carries speech.

### V2V/edit/retake

Use a preservation contract:

`Preserve: ... Change only: ... Region/time: ... Motion/timing: preserve or reinterpret ... Camera: preserve or change ... Audio: preserve/replace/generate ...`

Then write the positive transformation prompt. For masks, describe the desired result inside the mask and how boundaries should blend.

### Prompt Relay

Read `references/prompt-relay.md`. Select **one syntax only**:

- Inline: `segment | segment | segment`, optionally weighted.
- Block: `Scene 1:` headers, optionally range-weighted.

The first segment/global anchor establishes persistent static facts. Later segments describe only changes. Provide timing weights, speaker ownership, and transition sharpness recommendations when the workflow exposes them.

### Dialogue and multi-speaker scenes

Read `references/dialogue-audio-lipsync.md`. For each speaking beat include:

`speaker identity/location → listener behavior → physical cue → short quoted line → voice/language → pause/reaction → camera implication`

For two-person scenes, keep one active speaker per beat unless intentional overlap is essential. Name or spatially identify the speaker every time. Exact voices and lip sync require appropriate audio/TTS/lipdub/dual-character workflow support, not prompt wording alone.

### FLF/FML, loops, and continuation

Describe the **transition logic**, not just both endpoint images. State what changes continuously, what remains fixed, and how the final motion eases into the target frame. For loops, make the final pose, camera position, lighting, and moving elements reconnect to the opening state.

### Control workflows

When pose/depth/edge/motion/camera conditioning is supplied, let the control signal own geometry and motion. The prompt should own appearance, identity, environment, material, lighting, performance nuance, and audio. Do not fight the control signal with contradictory spatial instructions.

## Output contracts

Choose the smallest format that satisfies the user.

### Contract A — final prompt only

```text
[English model-ready prompt]
```

### Contract B — production prompt package

```text
Mode: ...
Recommended workflow: ...
Assumptions: ...

Final English Prompt:
...

Optional Negative Prompt:
...

Key controls:
- Duration/aspect/fps: ...
- Reference/control inputs: ...
- Audio route: ...
```

### Contract C — Prompt Relay package

```text
Mode: Prompt Relay + [T2V/I2V/A2V]
Global anchor: ...

Smart Prompt:
Scene 1:
...
Scene 2-3:
...

Timing rationale: ...
Recommended transition settings: ...
Audio/speaker routing: ...
```

### Contract D — diagnostic repair

```text
Primary failure: ...
Likely cause: ...
Prompt-level fix: ...
Workflow-level fix: ...
Rewritten prompt: ...
```

When the user asks for “only the prompt,” omit all commentary.

## Negative prompts

Negative prompting is workflow-dependent. Keep it short and defect-oriented. Do not use a giant generic blacklist that competes with the positive prompt. Typical optional terms:

`on-screen text, subtitles, watermarks, duplicated subjects, extra limbs, fused hands, identity drift, abrupt camera jumps, flicker, temporal warping, muddy audio, overlapping unintelligible speech`

Remove any item that conflicts with an intended effect.

## Quality gate before returning

Check all of the following:

- One clear generation mode and workflow family.
- Prompt length matches duration and complexity.
- Actions are chronological and physically observable.
- Speaker ownership is unambiguous.
- Camera instructions are compatible.
- Audio does not contradict supplied audio.
- I2V prompt does not redundantly redescribe the entire image.
- Persistent character/style facts are not needlessly repeated in every Prompt Relay segment.
- Control signals and text instructions do not fight each other.
- No unsupported promise of perfect text/logo, exact lip sync, or indefinite consistency.
- Ending state is stated when FLF/FML, continuation, or looping requires it.
- Experimental/community techniques are labeled as such.

Run `scripts/ltx_prompt_lint.py` when a prompt is long, segmented, or being delivered as part of an automated workflow.

## Progressive reference loading

Load only the reference needed for the task:

- `references/model-and-workflow-map.md` — capability tiers, routing, checkpoints, control/edit families.
- `references/prompt-construction-playbook.md` — detailed grammar, camera/audio vocabulary, temporal design, mode templates.
- `references/prompt-relay.md` — syntax, timing, global/local logic, multi-beat and multi-scene construction.
- `references/dialogue-audio-lipsync.md` — single/multi-speaker dialogue, TTS, reference audio, lipdub, Foley, music.
- `references/scenario-library.md` — reusable recipes for ads, films, portraits, action, music, social, editing, controls, and stylized work.
- `references/troubleshooting-and-qa.md` — symptom-to-cause-to-fix matrix.
- `references/source-map.md` — source provenance, verification date, official/community distinctions.
