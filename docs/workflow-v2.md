# Creator OS V2 Fixed Workflow

## 0. Episode input packet

Provide as much as exists; do not require the user to pre-edit it.

```text
Topic / problem:
(optional if the material itself makes it obvious)

Facts / evidence:
project files, logs, GitHub URL, screenshots, results

Raw screen recordings:
unedited is acceptable

Rough voice:
optional; natural speech is preferred over presenter-style reading

References:
Douyin links or local videos

Privacy boundary:
what must be hidden / cannot be published

Special request:
optional
```

## 1. INPUT_READY

Normalize assets, preserve originals and create the input manifest. Missing decorative assets are not blockers; missing factual basis/privacy boundary is.

## 2. RESEARCH_READY

Build:
- Evidence Map from first-party facts;
- Reference Recipe(s) from references;
- source confidence/evidence level.

Douyin acquisition failure downgrades that reference to page-level evidence; it does not block the whole episode when other evidence is sufficient.

## 3. CREATIVE_LOCKED

Freeze one Creative Contract:
- one story;
- one primary conflict;
- one Hook;
- one viewer payoff;
- one selected format;
- evidence refs;
- reference pattern refs;
- voice mode;
- visual direction;
- definition of done.

Do not start production before this is coherent.

## 4. Format Router

### VIDEO
Use for temporal/process evidence. Build a real 20–30 second Pilot first for non-trivial work. The Pilot must use representative final voice, captions, evidence framing and motion grammar.

For landscape software/screen recordings, the default visual treatment is `fit_full_frame` / `contain`. Preserving the complete page and source context is more important than filling the 9:16 canvas. A destructive ROI crop is allowed only when explicitly authorized after full-page context has already been established.

### CAROUSEL
Use for structured explanation/comparison. Default 6–9 pages and one main message per page.

### TEXT
Use for concise conclusions/lessons/checklists where extra visuals add little.

## 5. PRODUCING

Video order:

`final narration → timestamps → storyboard/evidence mapping → Pilot → Pilot review → full timeline → render`

Do not generate a full synthetic narration and then force unrelated screen footage to fit it. Do not time captions by character count.

Do not crop a landscape source merely to make it fill a vertical frame. Do not convert continuous screen recording into disconnected left/center/right fragments. Do not remove an intermediate source state when that state is needed to understand how the action progressed.

Carousel order:

`outline → page contract → evidence selection → layout → mobile review → copy`

Text order:

`hook/title variants → structure → final body → platform variant → review`

## 6. REVIEWING — FAIL-CLOSED VIDEO ORDER

For VIDEO, review in this exact order. Do **not** start from technical metadata and infer publishing quality.

### 6.1 Source inventory
Identify the actual source artifacts used by important final sections. Record Episode-relative path, role and SHA256.

### 6.2 Source → final fidelity
Compare the real source directly with the current render.

Required checks:
- complete source frame preserved by default;
- page identity/navigation/context remains understandable;
- no unauthorized destructive crop;
- spatial continuity: each ROI can be mapped back to the full page;
- temporal continuity: meaningful source action/state order is preserved;
- frame zero is intentional, not a partial crop/loading state/mid-action fragment.

A stable frame is not necessarily a complete frame. A technically clean center strip of a wider source is still a hard failure.

### 6.3 Full 1× continuous watch
Watch the current candidate from 0:00 to end at normal speed with actual final audio. The first pass may not rely on pause, scrub or replay to rescue comprehension.

### 6.4 Dense opening / transitions / mobile
- inspect frame zero and the first 10 seconds densely;
- inspect every transition and ±0.5 seconds around it;
- check key proof at 360×640 as an internal QA view only;
- key proof must be understandable without pause/replay;
- reject slideshow/Ken-Burns fake process motion, flash-like dark/light switching, unmotivated cuts and context loss.

### 6.5 Audio / captions
Listen end-to-end. Check intelligibility, natural phrasing, cut-off words, semantic sync and evidence obstruction.

### 6.6 Technical checks — last
Only after fidelity and viewing gates:
- decode;
- resolution/fps/codec;
- audio validity/peak/silence;
- black/blank frames;
- subtitle bounds;
- missing assets/placeholders;
- output integrity.

Technical PASS cannot override a source-fidelity or viewer-experience FAIL. Contact sheets, sparse keyframes, scene counts, duration, ffprobe data, self-authored PASS JSON, numeric scores or user opinion cannot independently unlock release.

The canonical VIDEO release record must bind the current final MP4 SHA256 and the declared source SHA256 values.

## 7. REPAIRING

Repair only the failed layer. Maximum 3 rounds by default. A localized failure must not trigger a new platform architecture or new plugin installation.

Repair priority:
1. source fidelity / full-frame integrity;
2. spatial and temporal continuity;
3. evidence readability;
4. story/evidence alignment;
5. audio;
6. captions;
7. cosmetic polish.

After any source change, timeline/layout change or rerender:
- old release review becomes stale;
- recompute affected SHA256 values;
- repeat source → final comparison;
- rewatch the complete new candidate at 1×;
- rerun opening, transition, mobile, audio and technical checks.

## 8. READY_TO_PUBLISH

Only after the validated current release review passes may the final artifact be named `FINAL.*` and the publish pack be generated.

Formal VIDEO delivery is one 1080×1920 master. A 360×640 render is QA-only and is not a second final deliverable.

If quality remains below the contract, return `BLOCKED` with an explicit failure code and best candidate. Never return “75% complete” as success.
