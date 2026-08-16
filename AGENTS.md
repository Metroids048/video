# Creator OS V2 — Agent Contract

This file is the highest-priority project operating contract for Codex and other coding/production agents working in this repository.

## 1. Product definition

Creator OS V2 turns real project material into content that can be published directly to Douyin or Xiaohongshu. Video is preferred when it is genuinely the strongest medium, but the system may select a carousel or text package.

The user is not expected to become an editor, voice actor, motion designer or social-media operator. The user supplies facts, source material, reference links, privacy boundaries and optional provider tokens. The system owns production quality.

**Hard definition of done:** if the user must reopen Jianying/CapCut and substantially repair the artifact, the episode is not complete. It is `BLOCKED`.

## 2. Read order for content-production tasks

Before doing work, read:
1. `AGENTS.md`;
2. `config/project.yaml`;
3. `config/creator-workflow.yaml`;
4. `config/content-formats.yaml`;
5. `config/reference-acquisition.yaml` when references are present;
6. `config/voice.yaml` for narration;
7. `config/quality.yaml` and `config/visual.yaml` for review;
8. `docs/video-plugin-routing.md` only when choosing an execution capability.

Do not use deleted V1 docs, deleted EP01 scripts or chat history as a competing contract.

## 3. Capability-resource freeze

Do not add, upgrade, remove, bulk-rewrite or replace plugin/Skill resources unless the user explicitly asks for a plugin/Skill change.

Protected capability paths include:
- `skills-src/`;
- `third_party_skills/`;
- `vendor/`;
- `.agents/skills/`;
- `.claude/skills/`;
- `skills.lock.json`;
- `tools-manifest.yaml`.

Existing capabilities are a toolbox, not a workflow. Never invoke a tool merely because it is installed.

## 4. Single creative authority

Exactly one Creative Contract controls each episode.

Only the Creative Director may choose/change:
- main story;
- primary conflict;
- primary Hook;
- viewer payoff;
- output format;
- target duration;
- reference-pattern selection;
- voice mode;
- visual direction.

After `CREATIVE_LOCKED`, downstream Skills execute bounded tasks. They may not quietly rewrite the concept. Story-level failure explicitly returns to the Creative Director and creates a new contract version.

The contract must validate against `schemas/creative-contract.schema.json`.

## 5. Fixed flow

Use this order:

1. **Input Hub** — normalize source material and privacy boundary.
2. **Reference Acquire** — resolve/cache accessible reference media; record honest degradation when inaccessible.
3. **Research & Evidence** — separate first-party facts from third-party style references; create Evidence Map and Reference Recipes.
4. **Creative Director** — freeze one Creative Contract.
5. **Format Router** — select `VIDEO`, `CAROUSEL` or `TEXT` from evidence and storytelling needs.
6. **Production** — invoke only capabilities required by the selected format.
7. **Creative QA** — inspect the actual rendered artifact, not only JSON/timeline metadata.
8. **Repair** — maximum 3 rounds by default; repair only the failing layer.
9. **Delivery & Learning** — emit the publish pack only after `READY_TO_PUBLISH`.

User-facing lifecycle:

`CREATED → INPUT_READY → RESEARCH_READY → CREATIVE_LOCKED → PRODUCING → REVIEWING → REPAIRING ↺ → READY_TO_PUBLISH`

Exceptional states: `WAITING_FOR_RESOURCE`, `BLOCKED`, `FAILED`.

The existing AVS engine may retain lower-level compatibility states internally. Map them through `config/workflow.yaml`; do not expose `DELIVERY_READY` as the product definition of success.

## 6. Input rules

Minimum useful Episode input:
- one concrete problem/conflict/project node;
- at least one verifiable fact source;
- a public/privacy boundary.

Accepted inputs include ideas, files/logs, GitHub/web URLs, images, screenshots, screen recordings, rough voice, local reference video, Douyin URL and published metrics.

### Douyin URLs

Douyin share/direct URLs are first-class references.

When technically/publicly accessible:
- resolve the share URL;
- cache the media once;
- record `source.json`;
- pass the local copy to existing reference analysis;
- produce transcript/word timestamps/frames/contact sheet/reference recipe where supported.

When acquisition is blocked:
- do not bypass login/access controls;
- store the source URL and page-level evidence;
- mark audiovisual evidence unavailable;
- continue with other usable references or original direction;
- never infer exact shots, timing, captions, music or delivery from a title/snippet.

Reference material may transfer structure, pacing, shot grammar and motion logic. Do not copy original wording, voice, footage, examples, data, title or cover.

## 7. Format Router

### VIDEO
Choose when real dynamic evidence/process materially improves the story.

Rules:
- 9:16 mobile-first;
- prefer real evidence in the first 3 seconds when available;
- no corporate-PPT/title/logo intro;
- no full landscape contain with black bars;
- use establish → ROI focus/zoom for desktop recordings;
- motion directs attention rather than decorates emptiness;
- non-trivial video requires a 20–30 second publication-quality Pilot before full render;
- Pilot uses final/locked voice direction, real evidence, real caption grammar and representative motion/SFX.

### CAROUSEL
Choose for structured explanations, comparisons, checklists, retrospectives or screenshot/chart-heavy evidence where time-based editing adds little.

Default: 6–9 pages, cover + one main message per page.

### TEXT
Choose for concise opinions, lessons, checklists or project notes where additional visual packaging has low value.

Do not switch a failed video to another format and call the original video successful. A format change after Creative Lock requires a new contract version.

## 8. Voice contract

Do not default to arbitrary Edge TTS or a new voice every episode.

Use a one-time audition against the same 15–20 second script:
- `HUMAN_ENHANCED`;
- `HYBRID_S2S`;
- `PREMIUM_TTS`.

Persist the approved result as `knowledge/voice/voice-profile.json` using `schemas/voice-profile.schema.json`.

For VIDEO:
- accepted final narration is the master clock;
- preserve natural pauses/emphasis when using human/hybrid modes;
- generate subtitle/word timing from the final narration audio;
- never allocate subtitle timing from text length/character count.

If no voice profile exists, create audition candidates before a full production rather than silently choosing a temporary voice for the final.

## 9. Visual contract

Evidence before decoration.

Hard rules:
- no empty technology cards used to cover missing evidence;
- no long static opening;
- no tiny full desktop UI centered in a vertical canvas;
- no subtitles covering balances/charts/orders/positions/primary proof;
- no generic full-screen architecture diagram unless the story truly needs it;
- screen shots longer than ~4 seconds must add information through ROI, cursor/action, callout, progressive reveal or meaningful cut;
- every visual treatment must remain readable in the 360×640 mobile preview.

HyperFrames/Remotion/Seedance/etc. are optional execution tools. FFmpeg remains the deterministic assembly fallback. Choose the simplest tool that produces the desired shot.

## 10. QA and repair

### Technical QA
Check decode/playback, resolution/fps, audio validity, clipping, black frames, subtitle bounds, missing assets/placeholders and output integrity.

### Creative QA
A reviewer must actually inspect the artifact/mobile preview and list inspected files. Evaluate at minimum:
- Hook;
- story clarity;
- pacing;
- evidence readability;
- visual design;
- human tone;
- audio;
- captions.

Null/unviewed/self-invented scores fail. A passing number cannot override contradictory evidence.

### Repair routing
- `VOICE_BAD` → audio only;
- `HOOK_WEAK` → Hook/Pilot only;
- `SCREEN_UNREADABLE` → screen composition/ROI only;
- `CAPTION_BLOCKING` → captions only;
- `FACT_UNSUPPORTED` → Evidence Map;
- `STORY_CONFUSED` → Creative Director/new contract version.

Maximum 3 repair rounds by default. If still below publish quality, return `BLOCKED` with the exact blocker; do not rebuild the whole platform.

## 11. Naming and delivery

Only `READY_TO_PUBLISH` artifacts may be named `FINAL.*`.

Before pass, use names such as:
- `pilot.mp4`;
- `candidate-v1.mp4`;
- `blocked-preview.mp4`.

Video delivery target:
- `FINAL.mp4`;
- optional `FINAL-clean.mp4`;
- `captions.srt`;
- `cover-A.png`;
- `cover-B.png`;
- `douyin.md`;
- `xiaohongshu.md`;
- `evidence-map.json`;
- `review.json`.

Do not produce “完成 75%”, “基本可用”, or “粗稿完成请用户再精修” as a successful delivery state.

## 12. Repository hygiene

Do not recreate:
- deleted quant-video completion/progress reports;
- `fixtures/golden-ai-quant`;
- `scripts/build_ep01_v*.py`;
- `scripts/build_ep01_final*.py`;
- random `final_final_new` style builders/artifacts.

Reusable logic belongs in `src/avs`, a bounded project Skill, renderer, schema or config. Episode-specific work belongs under that Episode and is not promoted into root-level scripts without a proven reusable need.

The local folder `第一期视频_7x24自动交易` is a protected source-material folder for the user’s retained first episode. Do not delete or mutate its original files.
