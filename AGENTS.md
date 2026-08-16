# Creator OS V2 — Agent Contract

This file is the highest-priority project operating contract for Codex and other coding/production agents working in this repository.

## 0. FINAL VIDEO RELEASE CONTRACT — OVERRIDES ANY CONFLICTING OLDER RULE

For VIDEO, **source fidelity and human-viewing continuity come before canvas fill, pacing metrics, technical metadata, or self-scoring**.

The following rules are absolute project-wide gates:

1. **SOURCE -> FINAL comparison is mandatory before release.** Identify the actual source artifacts used in important final sections, record Episode-relative path + SHA256, inspect the source, then compare it with the CURRENT final render.
2. **Landscape software/screen recordings default to `fit_full_frame` / `contain`.** Preserving the complete source page is more important than filling a 9:16 canvas. Unused vertical space is allowed.
3. **Destructive crop is forbidden by default.** `screen_focus`, `roi_crop`, `cover`, `screen_stack`, or any equivalent crop/reframe may only be used when `allow_destructive_crop=true` is explicit and the full-page context has already been established. Missing authorization must fall back to full-frame.
4. **A stable frame is not automatically a complete frame.** A render that is technically stable but only shows a center strip of a 1920x1080 source is a HARD FAIL.
5. **Spatial continuity is mandatory.** The viewer must understand where each ROI sits within the original page; do not force the viewer to mentally stitch left/center/right fragments together.
6. **Temporal continuity is mandatory.** Preserve meaningful source action/state order. Do not jump A -> C when omitted B is necessary to understand what happened.
7. **Frame zero must be intentional.** The opening cannot begin on an unexplained partial crop, loading state, mid-action, mid-scroll, or contextless fragment.
8. **The CURRENT candidate must be watched start-to-end at 1x.** First pass cannot use pause/scrub/replay to rescue comprehension. First 10 seconds require dense review; every transition requires inspection; actual audio must be listened to end-to-end.
9. **User opinion does not override the gate.** Positive feedback cannot turn a hard fail into PASS. Negative feedback must trigger independent reproduction and evidence logging, not automatic agreement.
10. **Metrics are diagnostic only.** ffprobe, LUFS, black-frame counts, scene counts, contact sheets, sparse frames, duration, shot counts, JSON self-reviews and numeric scores cannot prove publish quality.
11. **Any source/final change invalidates prior review.** `video-release-review.json` must match the CURRENT final MP4 SHA256 and all declared source SHA256 values.
12. **Mobile 360x640 is QA-only.** Do not deliver it as a second final video. Formal video delivery is one 1080x1920 master.
13. **Any hard fail routes to REPAIRING.** Repair only the failing layer, rerender, re-run source->final comparison and full 1x review. Maximum 3 rounds for the same symptom; unresolved defects become BLOCKED, never knowingly delivered.

If any older documentation says landscape `contain` is forbidden, that older rule is superseded by this section and `config/visual.yaml` / `config/video-review.yaml`.

## 1. Product definition

Creator OS V2 turns real project material into content that can be published directly to Douyin or Xiaohongshu. Video is preferred when it is genuinely the strongest medium, but the system may select a carousel or text package.

The user is not expected to become an editor, voice actor, motion designer or social-media operator. The user supplies facts, source material, reference links, privacy boundaries and optional provider tokens. The system owns production quality.

**Hard definition of done:** if the user must reopen Jianying/CapCut and substantially repair the artifact, the episode is not complete. It is `BLOCKED`.

For VIDEO, a technically valid MP4 is only a baseline. A video may not be delivered until the CURRENT rendered file has passed source-to-final fidelity review plus a full start-to-end 1x playback review under `config/video-review.yaml`.

## 2. Read order for content-production tasks

Before doing work, read:
1. `AGENTS.md`;
2. `config/project.yaml`;
3. `config/creator-workflow.yaml`;
4. `config/content-formats.yaml`;
5. `config/reference-acquisition.yaml` when references are present;
6. `config/voice.yaml` for narration;
7. `config/quality.yaml`, `config/visual.yaml` and `config/video-review.yaml` for review;
8. `docs/creator-os/video-pre-delivery-qa-prompt.md` before delivering any VIDEO;
9. `docs/video-plugin-routing.md` only when choosing an execution capability.

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
7. **Source Inventory + Fidelity Review** — VIDEO only: identify actual source artifacts, bind source SHA256 values, compare source to final for frame integrity, spatial continuity, temporal continuity and opening context.
8. **Creative QA** — inspect the actual rendered artifact, not only JSON/timeline metadata.
9. **Continuous Video Review** — VIDEO only: watch CURRENT candidate start-to-end at 1x, inspect first 10s densely, scan every transition, review 360×640 QA readability and listen to the actual mix.
10. **Repair** — mandatory when any source-fidelity or publish-quality hard fail remains; repair only the failing layer, rerender, then repeat source->final comparison and full review on the new SHA256.
11. **Delivery & Learning** — emit the publish pack only after `READY_TO_PUBLISH`.

User-facing lifecycle:

`CREATED → INPUT_READY → RESEARCH_READY → CREATIVE_LOCKED → PRODUCING → REVIEWING → REPAIRING ↺ → READY_TO_PUBLISH`

Exceptional states: `WAITING_FOR_RESOURCE`, `BLOCKED`, `FAILED`.

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
- 9:16 mobile-first output canvas;
- landscape desktop/screen recordings default to full-frame proportional fit, even if vertical space remains;
- destructive ROI crop is explicit/temporary only and requires `allow_destructive_crop=true`;
- prefer real evidence in the first 3 seconds when available;
- no corporate-PPT/title/logo intro;
- establish complete context before ROI focus;
- motion directs attention rather than decorates emptiness;
- non-trivial video requires a 20–30 second publication-quality Pilot before full render;
- process footage should prefer real continuous screen recording with cursor/click/scroll/state change over still screenshot camera motion;
- do not force extra cuts, minimum shot counts or arbitrary short shot caps to make the video feel faster;
- a coherent longer shot is better than several unreadable fragments.

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

## 9. Visual contract

Evidence before decoration. Source fidelity before canvas fill.

Hard rules:
- preserve the complete landscape source by default;
- never auto-upscale a 1920×1080 recording to 1920 high and center-crop it merely to fill 1080×1920;
- no tiny unreadable UI: use full-frame context plus one explicitly authorized semantic ROI when needed;
- no subtitles covering balances/charts/orders/positions/primary proof;
- no long static opening;
- no slideshow-like sequence where screenshots/cards are the whole motion language;
- no repeated Ken-Burns pan/zoom over UI stills to fake a process;
- no repeated dark exchange → bright backend → dark exchange hard-cut sequence that breaks viewer orientation;
- no cut whose only purpose is duration, shot-count or visual-change metrics;
- key proof must remain understandable at 1x without pause/scrub/replay;
- establish context before ROI detail and retain page identity;
- preserve meaningful source action order.

HyperFrames/Remotion/Seedance/etc. are optional execution tools. FFmpeg remains the deterministic assembly fallback.

## 10. QA and repair

### Gate A — Source fidelity
Before judging polish, compare actual source artifacts to the final render. Verify source hashes, full-frame integrity, spatial continuity, temporal continuity and opening context. Any unauthorized crop/context loss/teleport jump is a hard fail.

### Gate B — Continuous viewer experience
Watch CURRENT final from 0:00 to end at 1x with actual audio. First pass no pause/scrub/replay. Inspect 0–10s densely and every transition. Review 360×640 as QA only.

### Gate C — Technical QA
Only after Gates A/B: check decode, resolution/fps, audio validity, clipping, black/blank frames, subtitle bounds, missing assets/placeholders and output integrity.

The following do **not** count as release proof by themselves:
- contact sheets;
- sparse frame samples;
- ffprobe/codec/duration output;
- timeline/scene JSON;
- automatic cut counts;
- self-written PASS JSON;
- numeric scores;
- user saying the video is fine.

### Historical anti-regressions from EP01
These are project-wide hard lessons:
- A technically stable frame can still be a failure if the original page was destructively cropped.
- Do not confuse “no loading flash” with “opening is complete and understandable.”
- Do not confuse “fewer cuts” with “continuous experience.”
- Do not infer source fidelity from final frames; compare the actual source.
- A 1920×1080 source reduced proportionally inside 1080×1920 is acceptable; filling the canvas is not a quality requirement.
- Screenshot push/zoom as the main motion language is a release failure.
- Repeated 1.x-second evidence flashes are a release failure.
- Repeated dark/bright page flipping is a release failure.
- Shorter duration never justifies destroying evidence readability or continuity.
- If a normal viewer cannot understand key proof at 1x, FAIL.

### Repair routing
- `SOURCE_FIDELITY_FAIL` / `DESTRUCTIVE_CROP` → layout/transform only;
- `SPATIAL_CONTINUITY_BROKEN` → composition/context/ROI only;
- `TEMPORAL_CONTINUITY_BROKEN` / `OPENING_MID_ACTION` → cut structure/source sequence only;
- `VOICE_BAD` → audio only;
- `HOOK_WEAK` → Hook/Pilot only;
- `SCREEN_UNREADABLE` → screen composition/ROI/timing only;
- `SLIDESHOW_FEEL` → replace fake screenshot motion with real continuous process footage or honest still treatment;
- `RAPID_DARK_LIGHT_SWITCHING` → regroup evidence into coherent visual blocks;
- `CAPTION_BLOCKING` → captions only;
- `FACT_UNSUPPORTED` → Evidence Map;
- `STORY_CONFUSED` → Creative Director/new contract version.

Maximum 3 repair rounds for the same symptom. If still below publish quality, return `BLOCKED`; never deliver a known bad video.

## 11. Naming and delivery

Only `READY_TO_PUBLISH` artifacts may be named `FINAL.*`.

Before pass, use names such as `pilot.mp4`, `candidate-v1.mp4`, `blocked-preview.mp4`.

Formal VIDEO delivery target:
- one `FINAL.mp4` 1080×1920 master;
- optional `FINAL-clean.mp4` only when explicitly useful;
- captions/publish copy/evidence/review artifacts as needed.

`360x640` mobile media is QA-only and must not be treated as a second final video.

A VIDEO delivery is invalid if final SHA256 or any declared source SHA256 differs from the files that passed the current release review.

## 12. Repository hygiene

Do not recreate:
- deleted quant-video completion/progress reports;
- `fixtures/golden-ai-quant`;
- `scripts/build_ep01_v*.py`;
- `scripts/build_ep01_final*.py`;
- random `final_final_new` style builders/artifacts.

Reusable logic belongs in `src/avs`, a bounded project Skill, renderer, schema or config. Episode-specific work belongs under that Episode.

The local folder `第一期视频_7x24自动交易` is a protected source-material folder. Do not delete or mutate its original files.
