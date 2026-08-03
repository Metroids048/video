# Prompt Relay for LTX-2.3

Prompt Relay is an inference-time conditioning technique implemented through community ComfyUI nodes. It assigns different text segments to different temporal regions. Treat it as **workflow-dependent and evolving**, not as a native text syntax universally understood by every LTX interface.

## 1. When to use it

Use Prompt Relay for:

- multi-step action in one continuous shot,
- alternating dialogue,
- product reveal with timed phases,
- transformation stages,
- music-video beats,
- planned camera phases,
- a short narrative with several events,
- custom audio where visual actions must align to time blocks.

Do not use it to force many unrelated locations and hard cuts into one shot. Generate separate shots when the narrative is truly multi-scene.

## 2. Supported syntax families

Pick one syntax per prompt. Do not mix them.

### Inline pipe-separated syntax

Equal timing:

```text
Static opening description | First change | Second change | Final change
```

Weighted timing:

```text
Static opening description [0-20] | First action [20-55] | Dialogue reaction [55-85] | Final hold [85-100]
```

The ranges are relative spans, not literal frame numbers. A plain weight such as `[30]` can also be used in implementations that support it.

### Block/header syntax

Equal timing:

```text
Scene 1:
Static opening description
Scene 2:
First change
Scene 3:
Second change
```

Proportional timing:

```text
Scene 0-20:
Static opening description
Scene 20-55:
First action
Scene 55-85:
Dialogue reaction
Scene 85-100:
Final hold
```

Header words can usually be `Scene`, `Part`, `Shot`, `Beat`, `Segment`, or similar; the parser relies on the number/range and colon.

## 3. Global anchor vs local changes

The most important rule:

- Segment 1/global prompt contains the **persistent, static state**: subject identity, wardrobe, location, composition, lighting baseline, visual style.
- Later segments contain **only what changes**: action, gaze, speaker turn, camera phase, prop movement, light transition, audio event.

This reduces semantic re-introduction and identity drift. Do not rewrite the entire scene in every segment.

### Global anchor example

```text
A cinematic medium two-shot in a quiet late-night diner. The same woman in a cream trench coat sits on camera left, and the same man in a dark green jacket sits on camera right. A rain-streaked window glows behind them; warm tungsten light, realistic live action, restrained film grain, stable spatial positions.
```

### Local beats

```text
Beat 1:
Both remain silent; the woman turns a coffee cup slowly while the man watches her hands. The camera is locked.

Beat 2:
The woman on camera left raises her eyes and says in Mandarin, “你跟踪我多久了？” Her voice is controlled and quiet; the man remains silent.

Beat 3:
The man on camera right leans back, exhales, and replies in Mandarin, “从你上车开始。” A subtle rack focus moves from her to him.

Beat 4:
Neither speaks. A truck passes outside, throwing a band of white light across both faces; the woman stops turning the cup.
```

## 4. Beat design

Each beat should have one dominant purpose:

- one speaker,
- one action,
- one emotional/physical cue,
- one camera implication,
- one key sound event.

This is a heuristic for clarity, not a parser requirement. A segment can contain more than one item, but crowded segments reduce temporal ownership.

## 5. Timing allocation

Allocate time by what must be legible, not by sentence length alone:

- Static establishing anchor: 10–20%.
- Simple movement: 15–25%.
- Short spoken line: estimate from actual speech duration; give room for articulation and a reaction.
- Fast impact/action: 10–20%, but provide anticipation and recovery in neighboring beats.
- Final hero hold: 10–20%.

When exact audio exists, derive segment ranges from the waveform/transcript timestamps rather than guessing.

### Example for a 10-second dialogue

```text
0.0–1.5 s: establish both characters and silence
1.5–4.3 s: speaker A line
4.3–5.2 s: listener reaction/pause
5.2–8.2 s: speaker B line
8.2–10.0 s: shared reaction/final hold
```

Translate those durations into relative weights or actual timeline fields supported by the node.

## 6. Transition controls

Community Prompt Relay nodes may expose variants of:

- `epsilon`: boundary softness/sharpness.
- video window/strength or conditioning scale.
- audio epsilon/strength/window.
- explicit segment lengths in frames or seconds.
- token-normalized distribution.

General practice:

- Lower epsilon/sharper boundaries: clearer ownership, higher risk of abrupt semantic change.
- Higher epsilon/softer boundaries: smoother transition, higher risk of bleed between actions/speakers.
- Start near the node default. Change only after diagnosing boundary bleed or abrupt cuts.
- Do not invent a universal numeric optimum; node versions and workflows differ.

## 7. Prompt Relay for multi-person dialogue

### Rules

1. Lock character positions in the global anchor.
2. Use unique labels repeatedly: “woman on camera left,” “man on camera right.”
3. One active speaker per segment.
4. Explicitly state that non-speakers keep their mouths closed and react silently when necessary.
5. Keep each line short enough for the segment.
6. Add a pause/reaction segment between lines when lip ownership bleeds.
7. For exact voices/lips, use separate TTS/reference audio and an appropriate multi-character/lipdub workflow.

### Two-person inline example

```text
A locked medium two-shot of the same two detectives in a dim evidence room, woman on camera left and man on camera right, cool overhead light, realistic live action, stable identities and positions [0-15] | The woman on camera left leans over the table and says in Mandarin, “照片不是昨晚拍的。” The man remains silent with his mouth closed [15-42] | The man studies the photograph, lifts one eyebrow, and remains silent while the woman waits [42-55] | The man on camera right answers in Mandarin, “那就有人改了时间。” The woman keeps her mouth closed and watches him [55-83] | Both fall silent as the fluorescent lamp flickers; the camera slowly pushes toward the photograph [83-100]
```

### Three-person strategy

Do not ask all three to speak in rapid succession without pauses. Use:

- a wider establishing anchor,
- one speaker per beat,
- listener reaction beats,
- spatial labels (left/center/right),
- longer total duration or separate shots,
- external audio tracks for exact speaker identity.

## 8. Product reveal example

```text
Scene 0-15:
A polished macro commercial shot of a matte black wireless earbud case centered on wet obsidian, cool cyan rim light, dark background, stable product geometry.
Scene 15-40:
A narrow highlight sweeps across the lid while the camera slides slowly from left to right; droplets tremble but remain attached.
Scene 40-68:
The lid opens with precise mechanical motion and a soft magnetic click; both earbuds rise slightly into view as a low electronic pulse begins.
Scene 68-88:
The camera performs a controlled ten-degree orbit; cyan light shifts to a warm white hero light, revealing the surface texture.
Scene 88-100:
The product settles into a stable frontal hero composition; music resolves, leaving clean negative space for post-produced text.
```

## 9. Transformation example

```text
Scene 0-20:
The reference woman stands motionless in the same studio pose and clothing; neutral white background, locked full-body camera.
Scene 20-45:
Fine silver threads grow from the hem of her dress and travel upward across the fabric; her body and face remain unchanged.
Scene 45-72:
The threads weave into reflective metallic panels while she slowly turns one quarter toward camera right; the camera begins a gentle push-in.
Scene 72-90:
The final futuristic dress locks into place, catching sharp highlights; loose particles collapse into the seams rather than floating away.
Scene 90-100:
She faces the camera and holds a stable fashion pose; the camera stops and the studio falls silent.
```

## 10. Music-video example

Build segments from beat markers or lyric timestamps:

```text
Beat 0-12:
Establish performer, stage, costume and palette; minimal movement before the downbeat.
Beat 12-35:
First phrase: one clear body gesture repeated with rhythm; slow push-in.
Beat 35-60:
Chorus: stronger dance phrase; lateral track; lighting pulses on major beats.
Beat 60-82:
Bridge: performer becomes still while background motion continues; close-up.
Beat 82-100:
Final hit: decisive pose and lighting change; hold for edit.
```

If the workflow accepts custom audio, map the real timestamps rather than using arbitrary percentages.

## 11. First-frame treatment in I2V Relay

The first segment should describe only the static visible state of the provided image. Do not add motion or infer hidden details. Later segments describe only changes. This is especially important when a VLM drafts the segments from the input image.

## 12. Failure modes

| Symptom | Likely cause | Repair |
|---|---|---|
| Actions happen in the wrong order | Segments overlap semantically; each repeats multiple actions | One dominant change per segment; sharpen boundaries slightly |
| Identity drifts at every beat | Full subject re-described differently | Move stable identity/style to global anchor; use reference/ID-LoRA |
| Both characters talk | Pronouns and speaker ownership ambiguous | Spatial labels; one speaker per segment; silent listener instructions; separate audio |
| Abrupt visual jump | Local prompt introduces a new location/style | Keep scene continuity or generate a separate shot; soften transition |
| Prompt bleed | Boundary too soft or local prompts share verbs | Reduce semantic overlap; adjust epsilon/window conservatively |
| No action in early clip | First segment allocated too much time | Shorten static anchor after validating identity |
| Final frame never settles | No final hold segment | Add a 10–20% stable ending beat |
| Audio and video disagree | Generated dialogue conflicts with custom audio | Remove invented dialogue; anchor to supplied timestamps |

## 13. Output package for Codex

When creating relay prompts, return:

1. Mode and assumed duration.
2. Global anchor.
3. Smart prompt in the exact selected syntax.
4. Segment timing table.
5. Speaker/audio routing.
6. Recommended node-level adjustments only if the user requested them.
7. A warning when the workflow is experimental or version-sensitive.
