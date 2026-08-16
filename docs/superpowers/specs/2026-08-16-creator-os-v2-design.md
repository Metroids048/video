# Creator OS V2 Design

## 1. Goal

Creator OS V2 turns real project material into publish-ready creator content for Douyin and Xiaohongshu. The user supplies raw evidence, screen recordings, reference links and optional rough voice; the system owns research, creative direction, production, review, repair and the publish pack.

The project is no longer defined as “automatic video editing”. Video is preferred when the evidence supports it, but the system may route an episode to a Xiaohongshu carousel or text package when that format is stronger.

## 2. Frozen product contract

### User owns
- Real facts, project files, logs, screenshots and screen recordings.
- Reference URLs, especially Douyin share URLs.
- Optional rough voice/performance recording.
- API keys/tokens needed by optional providers.
- Privacy/redaction boundary.
- Final decision to publish.

### System owns
- Topic/story selection from supplied material.
- Reference acquisition and analysis when technically accessible.
- Fact/evidence mapping.
- Script and storyboard.
- Voice processing or synthesis according to the locked voice profile.
- Motion, visual treatment, subtitles, music/SFX and editing.
- Cover, title, copy and platform-specific publish pack.
- Technical QA, creative QA and targeted repair loops.

The system must not hand the user a “75% complete” artifact and call it complete. If manual editing is still required, the episode is BLOCKED rather than READY_TO_PUBLISH.

## 3. Architecture

Creator OS V2 has six product layers. Existing Skills/plugins remain capability resources underneath these layers; they do not own the workflow.

1. **Input Hub** — normalizes ideas, files, GitHub/web URLs, screen recordings, screenshots, rough voice and reference URLs.
2. **Research & Evidence** — separates first-party facts from third-party reference patterns. It produces an Evidence Map and Reference Recipes.
3. **Creative Director** — owns the single Creative Contract: audience, story, hook, promise, format, evidence, reference patterns, voice mode and visual direction.
4. **Production Engine** — routes to VIDEO, CAROUSEL or TEXT and invokes only the Skills/providers needed for the chosen format.
5. **Creative QA** — technical QA + actual visual/semantic review + comparison against approved golden baselines.
6. **Delivery & Learning** — emits a publish pack and records review/learning without changing the production contract retroactively.

## 4. Single-authority rule

Only the Creator OS orchestrator/Creative Director may choose or change:
- story;
- primary hook;
- output format;
- target duration;
- reference pattern selection;
- voice mode;
- visual direction.

Individual Skills may execute a bounded task but must not redesign the episode. Plugin availability never justifies calling a plugin; a production need must justify it.

## 5. Input contract

An episode may begin with any combination of:
- idea/question;
- local project files/logs;
- GitHub URL;
- webpage URL;
- screenshots/images;
- raw screen recording;
- rough voice/audio;
- local reference video;
- Douyin reference URL;
- prior performance metrics.

Minimum useful input is:
1. one concrete problem/conflict/project node;
2. one verifiable fact source;
3. public/privacy boundary.

### Douyin reference URL
Douyin URLs are first-class reference inputs. The acquisition adapter must:
1. resolve the share URL without bypassing platform access controls;
2. acquire/cache the publicly accessible media when possible;
3. persist source metadata;
4. pass a local copy into the existing reference-analysis pipeline;
5. degrade honestly to page-level evidence when acquisition fails.

A failed download must never be represented as if the full audiovisual reference was inspected.

## 6. Creative Contract

Every production freezes one machine-readable Creative Contract before asset production. Required fields:
- episode_id;
- target_platforms;
- audience;
- one-sentence story;
- primary conflict;
- hook;
- viewer payoff;
- selected format: VIDEO | CAROUSEL | TEXT;
- evidence refs;
- reference recipe refs;
- voice mode;
- visual direction;
- privacy/redaction rules;
- definition of done.

After CREATIVE_LOCKED, downstream Skills cannot rewrite this contract. A story-level failure explicitly returns to Creative Director; visual/audio failures only return to their failing layer.

## 7. Format Router

### VIDEO
Use when real screen/video evidence and temporal storytelling materially improve the content.

Preferred output:
- 9:16;
- mobile-readable evidence;
- real evidence in the first 3 seconds when available;
- motion used to direct attention, not decorate empty frames;
- 20–30 second publication-quality Pilot before full render for non-trivial videos.

### CAROUSEL
Use when the value is structural, explanatory or comparison-heavy and video adds little.

Preferred output:
- 6–9 pages;
- cover + one message per page;
- real screenshots/charts where useful;
- platform copy and topic tags.

### TEXT
Use when the idea is strongest as a concise opinion, lesson, checklist or project note without enough meaningful visual evidence.

The Router may select a non-video format proactively. It must not use CAROUSEL/TEXT as a disguised failure fallback after claiming a video is complete.

## 8. Voice strategy

Creator OS V2 separates voice performance from voice timbre.

Three audition modes are supported:
1. HUMAN_ENHANCED — user rough recording cleaned and mastered.
2. HYBRID_S2S — user performance/prosody retained while timbre is converted using an authorized speech-to-speech/voice-conversion provider.
3. PREMIUM_TTS — locked high-quality TTS voice used only after audition approval.

A one-time Audio Audition compares the same 15–20 second script across available modes/providers. The chosen profile is persisted and reused; each episode must not silently choose a new voice.

For VIDEO, the accepted narration master is the timing authority. Subtitle timing must come from real timestamps/transcription of the final narration, not character-count estimates.

## 9. Review and repair

QA has three independent layers:

### Technical QA
Playback, resolution, frame/audio validity, black frames, clipping, subtitle bounds, missing assets and deterministic export checks.

### Creative QA
A reviewer must genuinely inspect the rendered artifact/mobile preview. It judges hook, story clarity, evidence readability, visual design, pacing, human tone, audio quality, caption interference and whether the artifact feels publishable.

### Golden baseline comparison
New content is compared against approved good examples/style profiles. Numeric self-scores without inspected artifacts are not sufficient evidence.

### Repair loop
Maximum 3 repair rounds by default. Repairs are localized:
- VOICE_BAD → audio only;
- HOOK_WEAK → hook/Pilot only;
- SCREEN_UNREADABLE → ROI/screen composition only;
- CAPTION_BLOCKING → subtitle layout only;
- STORY_CONFUSED → return to Creative Director.

## 10. Public lifecycle

The user-facing lifecycle is:

CREATED → INPUT_READY → RESEARCH_READY → CREATIVE_LOCKED → PRODUCING → REVIEWING → REPAIRING ↺ → READY_TO_PUBLISH

Exceptional states:
- WAITING_FOR_RESOURCE;
- BLOCKED;
- FAILED.

The existing low-level Episode engine may retain compatibility states internally while V2 is introduced, but all documentation, orchestration and final delivery decisions must map to this lifecycle. Only READY_TO_PUBLISH may emit files named FINAL.*.

## 11. Delivery contract

### Video package
- `FINAL.mp4`
- optional `FINAL-clean.mp4`
- `captions.srt`
- `cover-A.png`
- `cover-B.png`
- `douyin.md`
- `xiaohongshu.md`
- `evidence-map.json`
- `review.json`

### Carousel package
- `01-cover.png` … numbered pages;
- `xiaohongshu.md`;
- `review.json`.

### Text package
- title candidates;
- final body;
- tags/topics;
- comment/CTA suggestion;
- `review.json`.

Candidate artifacts before the gate must use names such as `pilot.mp4`, `candidate-v1.mp4` or `blocked-preview.mp4`.

## 12. Repository slimming policy

### Preserve unchanged
- `.agents/skills` and related skill resources;
- `.claude/skills` and related skill resources;
- `.cursor` skill/rule resources unless a project rule must point to the V2 contract;
- `skills-src/`;
- `third_party_skills/`;
- `vendor/`;
- `skills.lock.json`;
- plugin/provider installation manifests and generic diagnostics;
- core `src/avs`, schemas, renderers, generic tests and reusable templates;
- generic reference knowledge/library.

### Remove
- old quant-video completion/progress/fix reports;
- EP01/quant one-off build scripts;
- obsolete V1 implementation prompts/specs and old episode retrospectives;
- quant-specific golden fixtures;
- committed draft/final artifacts from failed historical attempts;
- duplicated “final/final_final/vN” production paths.

### Local-only cleanup
The repository contains ignored/untracked media that GitHub cannot delete. A guarded PowerShell cleanup script will preserve exactly `第一期视频_7x24自动交易` while removing recognized historical output/media locations outside core resource directories. It must abort if the preserve folder does not exist.

## 13. Acceptance criteria for this V2 migration

The migration is complete when:
1. a dedicated branch contains the V2 contract;
2. Skills/plugins/vendor resources remain intact;
3. quant-specific reports, golden fixtures and EP01 one-off builders are absent;
4. README/AGENTS/config agree on Creator OS V2 and the same workflow;
5. Douyin URL is documented as a first-class reference input with honest acquisition fallback;
6. VIDEO/CAROUSEL/TEXT routing is explicit;
7. voice audition modes and timestamp authority are explicit;
8. READY_TO_PUBLISH is the only publish-success concept at product level;
9. local cleanup tooling protects `第一期视频_7x24自动交易` and core resources;
10. no new plugin/Skill dependency is introduced by the migration.
