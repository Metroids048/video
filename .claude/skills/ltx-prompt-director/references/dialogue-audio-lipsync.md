# Dialogue, Audio, Lip Sync and Multi-Speaker Playbook

## 1. Separate four different tasks

They are often confused:

1. **Native generated dialogue** — prompt contains the spoken line; model generates video and audio together.
2. **Audio-to-video/custom audio** — an existing voice/music track controls timing; prompt supplies visuals.
3. **Lipdub** — replace or translate speech in an existing performance while preserving identity and motion.
4. **Talking-avatar/Just-Talk** — make a still or silent person speak, usually with TTS/reference audio and a face/mouth-targeted workflow.

Choose the route before writing the prompt.

## 2. Single-speaker native dialogue

Use this sequence:

`framing → speaker identity → pre-speech physical cue → quoted line → language/accent/voice → mouth/body behavior → post-line pause → ambience`

Example:

```text
A realistic medium close-up of a middle-aged shopkeeper behind a wooden counter at night. He wipes his hands on a cloth, looks directly toward the unseen customer, and lowers his voice. In Mandarin with a warm Sichuan accent he says, “今天不卖了，明早再来。” His delivery is tired but firm, with natural articulation and one small nod at the end. A refrigerator hum and distant rain fill the quiet shop; no music.
```

Guidelines:

- Keep the line short.
- Quote exact speech.
- Specify language/accent only as needed.
- Use performance cues that fit the duration.
- Do not add several simultaneous Foley events over a quiet line.

## 3. Two-person dialogue

The model must know who speaks, who listens and where each person is.

### Global blocking

```text
The same woman remains on camera left; the same man remains on camera right. They sit across a narrow table in a stable medium two-shot.
```

### Turn template

```text
[Speaker label] [physical cue] and says in [language/voice], “[short line].” [Listener label] remains silent with mouth closed and [reaction]. [Camera/focus change].
```

### Recommended sequence

1. Establish both characters.
2. Speaker A line.
3. Silent reaction/pause.
4. Speaker B line.
5. Shared final reaction.

Use Prompt Relay for timing. For exact voice and lip isolation, render or supply separate speaker audio and use a dual/multi-character workflow or separate shots.

## 4. Three or more speakers

Prompt-only reliability declines as simultaneous face, voice and turn-taking complexity rises. Prefer:

- shot/reverse-shot editing,
- separate close-ups per speaker,
- one master two/three-shot for silent reactions,
- externally generated dialogue stems,
- spatial masks or speaker-specific workflows,
- a character continuity ledger.

A single long group shot is suitable for short, slow, one-at-a-time dialogue—not a rapid ensemble argument.

## 5. Overlapping speech

Only request overlap when essential. Define exact start/end relationship:

`As A reaches the final word, B interrupts with “...”; A stops speaking immediately and closes her mouth.`

External audio is strongly preferred because text-only timing is approximate.

## 6. Voice specification

Use a small set of audible properties:

- gender/age range when relevant,
- pitch/register,
- texture (breathy, rough, clear, nasal, resonant),
- pace,
- volume,
- accent/language,
- emotional delivery.

Avoid contradictory voice stacks such as “whispered, booming, fast, slow.”

## 7. Custom audio / A2V

When audio is supplied:

- do not rewrite the spoken words unless the workflow expects transcript guidance;
- state “use the supplied audio as the exact temporal guide”;
- map visible emphasis to audio events;
- keep extra sounds minimal unless the workflow mixes them intentionally;
- preserve silence and breaths because they support believable motion.

Template:

```text
Use the supplied audio as the exact timing and performance guide. [Identity/reference] articulates naturally to the speech, with [restrained gestures] aligned to emphasized phrases. [Listener/background] reacts only during pauses. [Camera plan]. Preserve the reference identity, wardrobe and setting. Do not generate additional dialogue; retain the supplied voice track.
```

## 8. Talking avatar

### Head-and-shoulders presenter

- locked or gently drifting camera,
- stable head size,
- natural blink and breath,
- restrained hand gestures inside frame,
- mouth articulation driven by TTS/reference audio,
- avoid constant head bobbing,
- specify no extra speech.

Prompt:

```text
A stable medium close-up of the same presenter facing the camera. Use the supplied voice as the exact timing guide. She speaks with natural articulation, subtle jaw and cheek movement, occasional blinks, small eyebrow emphasis and two restrained hand gestures. Her shoulders remain mostly steady; no exaggerated head bobbing. The camera is locked, soft studio lighting remains constant, and no additional dialogue or music is generated.
```

### Podcast/two-person avatar

Use a master two-shot for intro/outro and separate speaker close-ups for reliable dialogue. If a community multi-character workflow is used, segment every turn and supply separate reference voices.

## 9. Lipdub

Lipdub changes speech while attempting to preserve source identity, body performance and scene timing.

Prompt/preservation contract:

```text
Preserve the source video’s actor identity, facial structure, hairstyle, wardrobe, body motion, camera motion, lighting and background. Replace only the spoken performance using the supplied [language] audio. Match mouth articulation, jaw motion and facial emphasis to the new voice while maintaining natural blinking and the original emotional intent. Preserve all non-speech ambience unless the workflow replaces the full soundtrack.
```

For translation, line duration may differ. Adjust translation phrasing or audio timing before generation rather than demanding impossible mouth timing in prose.

## 10. Voice cloning

Voice identity belongs to the TTS/reference-audio system, not the visual prompt. The prompt may state performance character but should not pretend to clone a voice from descriptive adjectives. Use licensed/authorized voice references and preserve consent requirements.

## 11. Foley and ambience

### Add sound to silent video

Identify visible sound sources and their timestamps:

- footsteps by surface,
- cloth movement,
- object impacts,
- doors/mechanisms,
- wind/water/fire,
- room/environment tone.

Prompt:

```text
Preserve the source video exactly. Generate synchronized Foley only: [event 1], [event 2], [event 3]. Add a continuous [environment] ambience with realistic perspective and room response. No dialogue and no music.
```

### Foley priority

1. Events visibly caused on screen.
2. Continuous environment.
3. Off-screen context.
4. Music last.

Avoid sounds with no visible or narrative source unless intentionally stylized.

## 12. Music video and performance

Use the song as timeline. Build a cue sheet:

| Time | Audio cue | Visual action | Camera/light |
|---|---|---|---|
| 0–2s | intro | still anticipation | slow push-in |
| 2–5s | first phrase | one readable gesture | lateral track |
| 5–8s | chorus hit | decisive movement | light pulse/orbit |
| 8–10s | resolve | final pose | stop and hold |

Avoid describing a cut on every beat unless the workflow truly generates or assembles multiple shots.

## 13. Audio-reactive visuals

For LoRA/workflow-based audio reactivity, specify which visual property reacts:

- light intensity,
- particle scale,
- camera pulse,
- material deformation,
- environment color,
- dance gesture.

Choose one or two channels. “Everything reacts to every frequency” usually becomes noise.

## 14. Dialogue diagnostics

| Symptom | Prompt fix | Workflow fix |
|---|---|---|
| Wrong person speaks | Name/spatial label every turn; one speaker per beat | Prompt Relay, masks, separate speaker render |
| Both mouths move | Explicit silent listener with mouth closed | Separate audio stems/dual-character workflow |
| Speech cut off | Shorter line or longer segment | Adjust audio/segment duration |
| Robotic face | Add blink, breath, restrained gestures, pauses | Better reference, lower motion aggressiveness |
| Identity drift during speech | Remove redundant face description | ID-LoRA/reference image, lower edit strength |
| Audio muddy | Reduce competing ambience/music | Mix externally or use clean reference audio |
| Lip sync off | Align transcript and segment timing | A2V/lipdub/TTS route; retime audio |
| Accent ignored | State language/accent once, clearly | Provide actual reference voice/TTS |
| Listener overacts | Specify silent, restrained reaction | Separate reaction shot |

## 15. Ethical and production safeguards

- Do not clone or impersonate a real person's voice without authorization.
- Label synthetic or dubbed media where platform or jurisdiction requires it.
- Preserve source licenses for music, voices and footage.
- Use post-production for final audio mix, exact loudness, subtitles and text.
