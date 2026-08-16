# Creator OS V2 — Video Capability Routing

This file routes **execution needs** to already-installed video Skills/plugins. It does not own the creative workflow.

Canonical production authority is `AGENTS.md` + the Episode Creative Contract. Existing capability resources under `skills-src/`, `third_party_skills/`, `vendor/`, `.agents/skills/` and `.claude/skills/` remain unchanged.

## Hard rules

1. Installed does not mean invoked. Select the smallest capability set that satisfies the locked Creative Contract.
2. No plugin may change story, Hook, output format, voice mode or visual direction by itself.
3. Every side-path artifact must return to the Episode work/output area and pass Creator Review.
4. `QA_PASSED`/`DELIVERY_READY` are engine compatibility states, not proof of product success. Only `READY_TO_PUBLISH` is publish success.
5. Never silently replace failed real evidence with decorative AI cards or generic stock footage.
6. Do not add/upgrade/remove vendor Skills during normal Episode production.

## Capability table

| Need | Preferred existing capability | Notes |
|---|---|---|
| deterministic probe/cut/mix/subtitle/transcode | `ffmpeg` + AVS | default assembly substrate |
| word timestamps / dialogue edit / EDL | `video-use` / faster-whisper | use final narration as timing source |
| small HTML/title/callout motion | HyperFrames | attention guidance, not PPT filler |
| reusable code-driven motion/composition | Remotion | only when it materially improves the shot |
| Jianying/CapCut project automation | `jianying-editor`, `cut-skill`, `capcut-david` | optional editable side path |
| logged-in cloud timeline editing | ChatCut | requires host login; never a completion shortcut |
| generative B-roll / short shot exploration | Seedance / `seedance-free` | only when evidence does not need to be real UI |
| shot-language / prompt planning | `ai-video-shot-prompt`, `ltx-prompt-director`, `video-shotcraft` | planning/reference capability |
| multi-pipeline montage | OpenMontage | use only when story benefits from it |
| theme-to-video side paths | MoneyPrinterTurbo / Pixelle-Video | candidate source only; must return to review |
| high-quality TTS / speech capability | ElevenLabs / Azure Speech / existing Jianying voices | only through the locked voice audition/profile |
| music/SFX | ElevenLabs SFX/music / Epidemic Sound when configured | duck under narration and record source |
| account/topic strategy | `ip-strategist` | may advise research; Creative Director keeps authority |

## Screen-recording rules

- Preserve original source media unchanged.
- A vertical publish render may use ROI crops/zooms. It does **not** need to show every desktop edge in every shot.
- Use a readable establishing shot when context matters, then crop/focus the exact evidence region.
- Never center a tiny full desktop screen inside 9:16 with black bars as the default.
- Important evidence (balances, orders, positions, charts, Why No Trade, logs, result states) must remain readable in a 360×640 review preview.
- If an ROI crop removes context needed to interpret the claim, add an establishing shot or alternate crop rather than shrinking the evidence.

## Voice routing

Do **not** default to Edge TTS or any provider merely because it is free.

Voice is selected once through `config/voice.yaml`:
1. `HUMAN_ENHANCED`;
2. `HYBRID_S2S`;
3. `PREMIUM_TTS`.

Use the same 15–20 second audition script, persist the approved `voice-profile.json`, and reuse it. Provider selection is subordinate to the approved mode/profile.

For video, the accepted final narration audio is the master clock. Generate word timestamps from that audio; character-count timing is forbidden.

## Motion routing

Use motion only to:
- reveal information;
- guide the eye to evidence;
- clarify before/after or cause/effect;
- emphasize a keyword/result;
- maintain pacing when the underlying evidence remains the same.

Do not use motion to disguise missing evidence. Full-screen generated cards are scarce and must obey `config/visual.yaml`.

## Failure behavior

A capability failure routes locally:
- renderer failure → choose another suitable renderer or deterministic assembly;
- voice failure → `VOICE_BAD`;
- unreadable screen → `SCREEN_UNREADABLE`;
- caption interference → `CAPTION_BLOCKING`.

Do not respond to a local capability failure by installing a new plugin, changing the account architecture or rebuilding the entire Episode unless the Creative Contract itself is invalid.

## Resource manifests

Use existing pinned resources and manifests:
- `skills.lock.json`
- `tools-manifest.yaml`
- `vendor/manifests/video-third-party.yaml`

Secrets remain local (`.env`/provider configuration) and are never committed.
