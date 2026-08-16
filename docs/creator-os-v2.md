# Creator OS V2

## Purpose

Creator OS V2 is a production operating system for a creator who has real projects but does not want to manually learn scriptwriting, editing, motion design, voice production, covers and platform copy.

The system converts real source material into the strongest publishable format for Douyin/Xiaohongshu: video, carousel or text.

## Six layers

### 1. Input Hub
Normalizes ideas, project files/logs, GitHub/web URLs, images, screen recordings, rough voice and reference URLs while preserving original source artifacts.

### 2. Research & Evidence
First-party evidence becomes an Evidence Map. Third-party references become Reference Recipes. These two evidence types are never mixed.

### 3. Creative Director
Creates one Creative Contract and owns story, Hook, viewer payoff, format, voice mode and visual direction.

### 4. Production Engine
Routes to VIDEO/CAROUSEL/TEXT and invokes only the capabilities required for that decision.

For VIDEO, source fidelity is part of production, not a cosmetic preference. Landscape software/screen recordings default to proportional full-frame fit (`fit_full_frame` / `contain`). The system may leave unused vertical space rather than discard meaningful source context. Destructive crop/ROI is explicit-only and never the default way to fill a 9:16 canvas.

### 5. Source Fidelity + Creative QA
VIDEO review begins by identifying the actual source artifacts and comparing source → current final render. It verifies full-frame integrity, page/context identity, spatial continuity, temporal/action continuity and opening context before judging polish.

Only after that does the reviewer perform a full 0:00→end 1× watch with actual audio, dense first-10-second review, every-transition inspection and 360×640 mobile QA. Technical checks come last. A timeline, contact sheet, sparse frame set, ffprobe output, cut count, numeric score, self-authored PASS JSON or user opinion cannot substitute for these gates.

The release review is content-addressed to both the exact final MP4 SHA256 and the actual source artifact SHA256 values. A source change or rerender invalidates the previous pass.

### 6. Delivery & Learning
Creates the publish pack only after `READY_TO_PUBLISH`, then stores performance/learning for future content without retroactively rewriting the episode facts.

For VIDEO, formal delivery is one 1080×1920 master. The 360×640 render is an internal QA artifact only, not a second final output.

## Video release invariants

These are hard project-level invariants:

- Source fidelity outranks filling the vertical canvas.
- A stable frame is not automatically a complete frame.
- A 1920×1080 source may be proportionally reduced inside 1080×1920; unused vertical space is acceptable.
- `screen_focus`, `roi_crop`, `cover`, `screen_stack` or equivalent destructive reframing requires explicit authorization and established full-page context.
- Meaningful source edges, labels/navigation and page identity may not silently disappear.
- A viewer must be able to map an ROI back to the full source page.
- Meaningful action/state order must remain understandable; no unexplained A→C teleport edits.
- Frame zero may not begin on an unexplained partial crop, loading state or mid-action fragment.
- Key proof must be understandable at normal 1× playback without pause/replay.
- Screenshot/Ken-Burns motion cannot masquerade as software process footage.
- User feedback triggers review but cannot flip a release verdict without the same independent evidence.
- Any known hard failure routes to `REPAIRING`; unresolved failure after the configured repair limit becomes `BLOCKED`, not delivered.

## Capability boundary

`python -m avs`, FFmpeg, HyperFrames, Remotion, ChatCut, Jianying/CapCut integrations, voice providers, video analysis tools and all installed Skills remain execution resources. They are selected by production need; none of them owns the end-to-end workflow.

## Why this replaces V1

V1 optimized for a valid rough cut and expected final manual editing. That contract allowed technically valid but aesthetically weak drafts to be described as completed work. V2 changes the product definition: publishable quality is the completion gate, and a failed gate stays BLOCKED.

The later source-fidelity gate further closes a failure class discovered during EP01: technically stable, low-cut-count, correctly encoded video can still be unusable when the source page is destructively cropped or meaningful source continuity is lost. Technical cleanliness is therefore never treated as proof of viewer-quality.

## Voice direction

The preferred compromise is to separate performance from timbre. The user can record a natural rough performance; HUMAN_ENHANCED or HYBRID_S2S keeps its pacing/emphasis while improving audio quality or timbre. PREMIUM_TTS remains a locked fallback after audition.

## Reference direction

A Douyin link is valid input. When public media acquisition works, the system builds a local analysis package. When it does not, the evidence level is downgraded rather than fabricated.

## Protected first-episode source

On the user’s Windows checkout, `第一期视频_7x24自动交易` is the only historical first-episode source folder explicitly retained. It is source material, not proof that old final drafts were good. Old builds/reports do not define the new baseline.
