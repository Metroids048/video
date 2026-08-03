# Troubleshooting and QA

## 1. Diagnostic order

Diagnose in this order to avoid random parameter changes:

1. Wrong workflow family?
2. Prompt asks for too much in the duration?
3. Identity/reference/control conflict?
4. Temporal order or speaker ownership ambiguous?
5. Camera instructions conflict?
6. Audio route contradicts prompt?
7. Denoise/control/LoRA strength inappropriate?
8. Checkpoint/quantization/node version limitation?
9. Upscale/interpolation introduced the artifact?

Change one variable at a time.

## 2. Symptom matrix

| Symptom | Likely prompt cause | Prompt repair | Workflow repair |
|---|---|---|---|
| Little or no motion | Verbs vague; I2V only redescribes image | State initial motion, trajectory and end state | Increase compatible motion/denoise carefully; verify frame conditioning |
| Chaotic motion | Too many actors/actions/camera moves | One principal action per beat | Pose/motion control; split shot |
| Wrong action order | Non-chronological prose | Use explicit connectors or Relay | Segment timeline |
| Camera ignored | “dynamic camera” or action dominates | Name one physical move early | Camera-control LoRA/path |
| Camera jumps | Conflicting moves/cuts | One continuous camera plan | Lower edit strength; use separate shots |
| Face changes | Repeated/conflicting identity details | Simplify identity language | Reference image, face-ID/ID-LoRA, trained LoRA |
| Clothes/background change in I2V | Prompt invents new appearance | State preserve contract; prompt motion only | Lower denoise/edit strength; masks |
| Hands fail | Complex hand/object interaction | Simplify and stage interaction | Pose/hand reference; retake/inpaint |
| Extra people appear | Crowd/subject count ambiguous | State exact visible subject roles | Mask/reference; shorter shot |
| Both people speak | Pronouns/turns ambiguous | Spatial labels, one speaker/beat | Prompt Relay, separate audio/masks |
| Dialogue truncated | Line too long for duration | Shorten line or extend beat | Retimed TTS/reference audio |
| Lip sync weak | Prompt-only exact timing expected | Add physical speech cues, remove competing actions | A2V/lipdub/talking-avatar workflow |
| Audio muddy | Too many layers | Prioritize dialogue, sparse ambience | Mix externally; clean stems |
| Foley unsynced | Events not ordered | List visible events chronologically | Timestamped Foley/custom audio workflow |
| Prompt Relay bleed | Local prompts overlap; soft boundary | One change per segment | Adjust epsilon/window; separate reaction beat |
| Relay transition snaps | New scene/style introduced abruptly | Maintain continuity | Soften boundary or generate separate shot |
| First/last frame not reached | No transition/end easing | Describe bridge and final settling | Increase endpoint conditioning; FML guider |
| Loop seam visible | End state differs from start | Match pose/camera/light/audio phase | Loop graph, crossfade or latent overlap |
| Long extension drifts | Every extension reinterprets identity/style | Prompt only next action; continuity ledger | Stable reference/LoRA; shorter shot units |
| V2V changes everything | No preserve list | Explicit “preserve/change only” contract | Mask, lower strength, retake route |
| Inpaint boundary flickers | Replacement ignores lighting/occlusion | Describe blend, shadow, perspective | Better mask feather/temporal mask |
| Style inconsistent | Mixed media terms | One visual grammar | Style LoRA and fixed workflow |
| Text/logo garbled | Asking diffusion model for typography | Reserve blank area | Composite exact text/logo in post |
| Output looks oversharpened | Excess quality/detail adjectives or enhancer stack | Remove “ultra sharp” pile | Reduce detail/upscale strength |
| Flicker after upscale | Base frames unstable | Fix base generation first | Change temporal/spatial upscale path |

## 3. Prompt load test

Count these units:

- subjects,
- major actions,
- speaker lines,
- camera changes,
- location/style transitions,
- control requirements.

For a short shot, if more than two categories contain several independent units, split or segment the task.

## 4. Contradiction audit

Flag pairs such as:

- static camera / handheld orbit,
- slow motion / frantic real-time pacing,
- bright noon / dark moonlit scene at the same moment,
- preserve source outfit / transform into new outfit,
- silent clip / generated dialogue,
- custom audio exact / different quoted dialogue,
- single continuous take / rapid hard cuts,
- keep exact composition / large viewpoint change.

Resolve them chronologically only when the transition is intentional.

## 5. Identity audit

For each named subject, verify:

- stable label,
- stable left/right/center position if multi-person,
- consistent clothing/age/hair,
- no contradictory facial description,
- reference or LoRA route when exact identity matters,
- no repeated full re-description in local Relay segments.

## 6. Audio audit

- Is the audio native, supplied, TTS, lipdub or preserved source?
- Does the prompt add competing speech?
- Are dialogue lines feasible in the segment duration?
- Are non-speakers explicitly silent where needed?
- Are Foley events visibly caused?
- Is music necessary, and should it duck under speech?

## 7. Endpoint audit

Required for FLF/FML, continuation, transitions and loops:

- final camera position,
- subject final pose/gaze,
- object final location,
- lighting state,
- motion velocity/easing,
- audio tail or loop phase.

## 8. A/B test protocol

1. Save workflow JSON and model/LoRA versions.
2. Fix seed or seed list.
3. Fix duration, resolution, fps and references.
4. Generate baseline.
5. Change one prompt variable.
6. Score 1–5:
   - prompt adherence,
   - identity,
   - motion physics,
   - camera,
   - temporal order,
   - audio sync,
   - dialogue ownership,
   - artifact severity.
7. Keep the shortest prompt that wins reliably, not the longest prompt that wins once.

## 9. Repair rewrite pattern

When asked to fix a failed prompt, respond with:

```text
Failure: [observable defect]
Cause: [one or two highest-probability causes]
Prompt change: [specific wording change]
Workflow change: [only if needed]
Rewritten prompt: [complete prompt]
```

Do not dump a long generic parameter list when the defect is clearly semantic.

## 10. Lint script

Use:

```bash
python scripts/ltx_prompt_lint.py prompt.txt --mode t2v --duration 10
python scripts/ltx_prompt_lint.py relay.txt --mode relay --duration 10 --json
```

The script is heuristic. A clean report does not guarantee visual success; warnings identify common prompt-structure risks.
