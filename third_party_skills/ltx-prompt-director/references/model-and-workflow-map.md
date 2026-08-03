# LTX-2.3 Model and Workflow Map

Last verified: 2026-07-23.

This document separates **native/official capabilities** from **community workflow compositions**. A workflow's existence does not guarantee perfect results for every checkpoint, quantization, node version, resolution, or hardware profile.

## 1. Model identity

LTX-2.3 is a joint audio-video diffusion-transformer family designed to generate synchronized visual and audio content. The official model card lists a full 22B development checkpoint, distilled variants, a distilled LoRA, and spatial/temporal upscalers. The development model is the flexible route for high-control workflows and training; distilled models prioritize low-step iteration.

### Practical checkpoint routing

| Goal | Typical checkpoint route | Prompt implication |
|---|---|---|
| Maximum control, LoRA stacking, advanced workflows | 22B dev or supported dev derivative | Can tolerate richer conditioning; still avoid overloaded prompts |
| Fast previews and iteration | 22B distilled / distilled 1.1 | Keep prompt decisive; use workflow controls rather than verbal overconstraint |
| Fast draft then high-quality finish | Distilled preview → dev/multiscale/detail/upscale pass | Preserve the same core prompt and references across passes |
| Low-memory local execution | Quantized/community packaging | Test prompt adherence and audio separately; quantization/workflow can change behavior |

Do not encode sampler, CFG, steps, resolution, or model filename inside prose unless the user explicitly wants a reproducibility record. Those belong in workflow metadata.

## 2. Capability tiers

### Tier A — official/native model family

- Text-to-video.
- Image-to-video.
- Joint generation of video and synchronized audio.
- Audio-to-video / custom-audio conditioning in supported workflows.
- Multiple keyframe conditioning.
- Forward and backward video extension.
- Video-to-video transformations.
- LoRA and IC-LoRA customization.
- Pose, depth, edge/canny, motion/structure and camera-oriented control through supported models/workflows.
- Spatial and temporal upscaling/multiscale rendering.
- Lipdub and audio-oriented workflows in the official ecosystem.
- Native portrait output and generative reframing/outpainting in the 2.3 ecosystem.

### Tier B — official ecosystem compositions

These combine the model with official or maintained nodes/models:

- Single-stage and two-stage T2V/I2V.
- Union control using pose/depth/edge signals.
- Motion tracking/reference control.
- HDR conditioning.
- Pixel/detail upscaling.
- Text-to-audio or audio-conditioned video.
- Retake, colorization, deblur, decompression, day-to-night, in/outpainting and specialized effects where an appropriate LoRA/IC-LoRA is available.

### Tier C — community/experimental workflows

Treat these as powerful but version-sensitive:

- Prompt Relay and timeline editors.
- Multi-sequence movie-maker graphs.
- Prompt Relay with custom audio.
- Dual-character or multi-character lip-sync packs.
- First-middle-last-frame guiders.
- Multi-reference character sheets and multi-subject reference stacks.
- Long-video loop and repeated extension graphs.
- Music-video creators with segment export/merge/interpolation.
- Just-Talk masked speech injection.
- Cross-view viewpoint change.
- EditAnything add/remove/replace/restyle pipelines.
- Community Foley, style transition, audio-reactive, water, ingredient, shave, cross-eye and other effect LoRAs.

## 3. Workflow router

### Text-to-video

Use when no reference visual is required. Best for establishing shots, concepts, environments, stylized animation, product concepts, and short narrative shots. Prompt must carry appearance, blocking, camera, lighting and sound.

### Image-to-video

Use when the user has a good first frame or character/product reference. The image already encodes identity, wardrobe, composition and palette. Prompt only the motion trajectory, camera behavior, environment reaction, sound and desired ending.

### Audio-to-video / custom audio

Use when dialogue, song, speech rhythm, or sound design should dictate the timing. Audio is the temporal anchor. Prompt the visual interpretation and performance. For exact speech content, do not ask the model to invent a competing line.

### Video-to-video

Use when source timing, motion, performance, or camera should be retained. Decide whether the task is:

- global restyle,
- local inpaint,
- object/person add/remove/replace,
- viewpoint change,
- outpaint/reframe,
- audio insertion/Foley,
- lipdub,
- retake,
- extension,
- shot-to-shot transition,
- restoration/detail/HDR.

### Prompt Relay

Use when the clip has distinguishable time blocks: sequential actions, alternating dialogue, product reveal, transformation stages, music beats, or camera phases. Prompt Relay is not a substitute for scene editing when the user actually wants hard cuts between unrelated locations.

### First/Last Frame and First/Middle/Last Frame

Use when endpoint composition matters more than free generation. Good for morphs, match transitions, entrances/exits, product assembly, pose transitions, and constrained camera moves. The prompt explains the continuous bridge between anchors.

### Long video and extension

Generate in shot units. Preserve identity/style through reference frames, LoRA/ID-LoRA, keyframes and a continuity ledger. Repeated extension accumulates drift; write prompts that describe only the next shot segment and preserve the last stable frame.

### Loop

The final state must reconnect to the first: same camera position, subject pose family, lighting phase, moving-object phase, and audio cadence. Avoid irreversible actions unless the loop visually hides the reset.

### Multi-reference identity

Choose by production need:

- One-off: strong first-frame image.
- Several angles: character sheet/multiple references.
- Repeated series: ID-LoRA or trained character LoRA.
- Multiple subjects: separate references and unambiguous spatial labels; reduce simultaneous complex actions.

### Control reference

- Pose: body skeleton, dance, action blocking.
- Depth: spatial layout, camera-space structure.
- Edge/canny: silhouettes, object boundaries, architectural form.
- Motion tracking: trajectory and movement transfer.
- Camera-control LoRA/path: dolly, jib, static, or referenced camera motion.

When control is active, prompt appearance and performance; do not re-specify incompatible geometry.

## 4. Prompt vs workflow responsibility

| Requirement | Prompt owns | Workflow/control owns |
|---|---|---|
| Character behavior | action, gaze, expression, rhythm | identity reference/LoRA for exact person |
| Camera | semantic move and composition intent | exact path/pose/depth/camera LoRA when precision matters |
| Speech | line, tone, language, pause | TTS/reference audio/lipdub for exact timing and voice |
| Multiple speakers | blocking and turn-taking | segmented audio, masks, dual/multi-character workflow for exact lips |
| Style | medium, lighting, texture, palette | style LoRA for repeatability |
| Start/end | transition description | keyframes/FLF/FML for exact endpoints |
| Edit region | desired appearance | mask/retake/inpaint for spatial restriction |
| Long continuity | next-shot continuity text | references, LoRA, saved frames, extension graph |
| Resolution | detail intent | latent/spatial/temporal upscalers and render settings |
| Text/logo | placement intent only | compositing/post-production for exact typography |

## 5. Production recommendations

1. Draft at a lower-cost setting, but validate motion and speaker ownership before upscaling.
2. Lock identity references, seed strategy, model/checkpoint, LoRA stack and key prompt phrases before batch comparisons.
3. Change one variable at a time when diagnosing: prompt, seed, control strength, denoise, LoRA strength, timing, or sampler—not all simultaneously.
4. For multi-character scenes, use spatial names such as “the woman on camera left” and “the man on camera right,” then keep those labels stable.
5. For product ads and UI/text shots, generate the visual plate and composite exact labels afterward.
6. Treat community workflow names as routing hints; inspect the actual graph and node versions before execution.
