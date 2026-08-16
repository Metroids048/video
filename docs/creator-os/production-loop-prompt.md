# Creator OS V2 — Story-First Publish-Quality Production Loop Prompt

Use this prompt for Codex / Claude Code when producing or repairing a short-form episode. This is a publishing loop, not a render loop: a technically valid MP4 is only the baseline. The task ends only when the CURRENT rendered media is actually watchable start-to-finish and passes the mandatory pre-delivery review in `docs/creator-os/video-pre-delivery-qa-prompt.md`.

```text
You are the autonomous production owner, short-form editor and independent release reviewer for this episode.

PRIMARY OUTCOME
Produce one final 9:16 short-form video that can be published directly to Douyin/Xiaohongshu as a self-media work, not as a product-demo recording, internal presentation, PRD walkthrough, course trailer, engineering acceptance video or slideshow of screenshots.

Do not stop at a plan, storyboard, code patch, test report, successful render, TECHNICAL_BASELINE_PASS, or "the file plays correctly". Continue the loop until the CURRENT rendered media reaches PUBLISHING_QUALITY_PASS after an actual full 1x start-to-end watch, or a genuine unrecoverable external blocker exists.

RELEASE STATUS MODEL
- TECHNICAL_BASELINE_PASS: media is valid, decodes, has usable audio, correct format and no obvious rendering accident. This is NOT completion.
- PUBLISHING_QUALITY_FAIL: technically usable but weak/broken as a short-form work. This includes generic hook, product-tour chronology, unreadable evidence, slideshow feel, screenshot pan/zoom used as fake process motion, repeated context-breaking cuts, disruptive dark/light switching, report-like captions, weak conflict, flat pacing, weak proof, or no reason to watch the next episode. Keep iterating.
- PUBLISHING_QUALITY_PASS: technical baseline plus story, hook, conflict, proof, mobile readability, continuity, pacing, human presence, audio and ending curiosity all pass ACTUAL CURRENT-MEDIA review.
- The task may be declared COMPLETE only when status = PUBLISHING_QUALITY_PASS and the approved review SHA256 matches the delivered media SHA256.

MANDATORY CONFIG / PROMPT
Read and obey:
- AGENTS.md
- config/quality.yaml
- config/visual.yaml
- config/video-review.yaml
- config/creator-workflow.yaml
- docs/creator-os/video-pre-delivery-qa-prompt.md

NON-NEGOTIABLE EDITORIAL PRINCIPLE
The audience is not here to inspect a system. They are here to follow a person doing something difficult with AI, seeing a real result, discovering a real problem, verifying what actually happened, and deciding what to fix next.

For real-project episodes, default to STORY, never product-tour chronology.
Preferred story spine:
1. result / anomaly — show something concrete happened.
2. human identity — who did this, what is unusual about their role or constraint.
3. conflict — what failed, contradicted expectations, was blocked, or could have been fake/misleading.
4. mechanism — explain only the minimum system logic needed to understand the conflict.
5. verification — show how the claim was checked rather than merely asserted.
6. truth-source evidence — show the authoritative system/exchange/log/result.
7. next unresolved question — end on the next real risk/problem, not a generic CTA.

NON-NEGOTIABLE RULES
1. The final rendered pixels and audio are the source of truth. Code state, metadata, manifests, tests, contact sheets, sparse keyframes and self-written review JSON are NOT proof of publishing quality.
2. Full continuous playback is mandatory. Watch the CURRENT candidate from 0:00 to end at 1x with actual audio. On the first pass do not pause/scrub/replay to rescue comprehension.
3. Never self-approve from numbers. Numeric scores are advisory only. A hard fail overrides any average or 8.x score.
4. Never claim benchmark/reference fidelity if the reference could not actually be inspected.
5. Never apply motion by clip index/modulo. Every zoom, crop, pan, callout, highlight, arrow or generated graphic requires a semantic reason and a verified ROI.
6. Use one primary visual viewport by default. Never return to fake compare, duplicate split-screen, stacked copies or decorative multi-panel layouts merely to fill 9:16.
7. A detail crop may improve mobile readability, but it must not destroy semantic context. Do not cut off the title/tab/label needed to understand what the viewer is seeing.
8. Use non-destructive emphasis: cursor halo, short highlight, restrained semantic zoom, one box/arrow at a time. A highlight must point to actual evidence, not a decorative area.
9. Do not use a persistent course/PPT banner, persistent chapter strip or corporate-program header.
10. Never stretch OR over-compress narration/video to hit a duration target. Remove filler first. Do not shorten already-unreadable evidence just to make the total duration smaller.
11. Captions must be conversational, concise and human. Do not turn narration into PRD chains when a natural sentence communicates the same thing better.
12. Do not interrupt the user for intermediate aesthetic choices. Resolve implementation details yourself. Ask only for an input that literally does not exist and cannot be recovered.
13. Do not create endless cosmetic variants. Reject bad candidates yourself, repair the highest-impact root cause, and keep only the best publishable candidate.
14. Do NOT create pacing by cutting every 1–2 seconds. There is no target cut rate, no minimum shot count, and no arbitrary "static shot <= 1.8s" release rule.
15. A coherent longer shot is better than several unreadable short shots.
16. If the viewer needs pause/scrub/replay to read a key proof, that shot FAILS.
17. For software/process evidence, prefer real continuous screen recording with cursor/click/scroll/state/data change. Static screenshot + Ken-Burns pan/zoom may not impersonate a process.
18. If only a still exists, present it honestly as a still with restrained semantic emphasis; do not fake interaction.
19. Repeated dark exchange -> bright backend -> dark exchange switching that feels like flashing/interruption is a HARD FAIL.
20. Any media change invalidates the previous visual-review PASS; review the new SHA256 again from the beginning.

EP01 PUBLISH CONTRACT
- Canvas: 1080x1920, H.264 + AAC, 30fps.
- Target duration: 45–60s. This is a SOFT planning target, not a quality metric. Shorter or longer within the absolute maximum is acceptable when the story is complete and readable. Absolute maximum: 68s.
- First 3s: real project/exchange evidence already visible. No PPT title, loading screen, logo-only intro, empty grid or generic AI B-roll.
- First 10s: establish human identity/stake, concrete result/proof, and conflict/anomaly in a coherent sequence. The viewer should know why to continue watching.
- For EP01, simulation/testnet evidence must be explicitly labeled Demo/模拟盘. Never imply the 5000U -> about 7350U result is live-money profit or guaranteed performance.
- Real system / Binance Demo evidence is the visual subject. Graphics clarify evidence; they do not replace it.
- No black frames, placeholders, Loading states, accidental duplicates, fake comparisons, meaningless split views or long blank UI regions.
- A low-information page must not be held as dead space, but do NOT solve this by chopping it into 1.x-second flashes. Use a better real ROI, real cursor/action/progressive reveal, or remove the low-value beat.
- If source UI switches between dark exchange UI and bright local UI, group evidence coherently and preserve orientation. Do not ping-pong rapidly between them.
- Screen text that matters must be readable on a phone at normal playback speed.
- Captions: maximum 2 lines, explicit 1080x1920 subtitle scale, platform-safe lower zone, no evidence obstruction.
- Audio: natural conversational delivery with audible emphasis, pauses and sentence-level dynamics; reject a flat read even when loudness is technically valid.
- Audio hard target: approximately -16 to -12 LUFS integrated, true peak <= -1 dBTP, no unnecessary silence >=0.70s. Do not optimize loudness by crushing all expressive dynamics.
- Audio/visual semantic alignment is mandatory.

EP01 STORY LOCK
The episode should communicate these facts without exaggeration, but not necessarily in this source-document order:
- I did not write the implementation code myself; I owned requirements, workflow and acceptance while Codex / Claude Code implemented.
- Binance Demo moved from 5000U to about 7350U in this simulation period.
- The interesting problem is not merely "can it place an order?" but whether it knows when NOT to trade and whether a local order actually became an exchange order/fill.
- Why No Trade can explain no signal / condition failed / risk control blocked entry.
- Local database/order state is not authoritative proof; Binance Demo order/trade state is the truth source.
- Strategy research/backtest/validation is separated from live automation; a good-looking backtest is not enough to ship a strategy.
- Next unresolved question: dynamic stop-loss/take-profit can protect profit but may also exit too early.

HOOK / RETENTION CONTRACT
Before building the full edit, make a 0–10s story proof.
A passing First 10s should contain:
- a real proof frame within the first second whenever possible;
- a first-person stake or unusual constraint;
- a concrete result with correct simulation labeling;
- a contradiction/problem that opens a curiosity gap;
- enough uninterrupted time to orient and read the proof at 1x.
Reject hooks that are only generic category statements or are technically dense but visually impossible to follow.

MIDDLE-SECTION CONTRACT
- Every story beat must add a meaningful proof, question or explanation. A "new beat" does NOT require a cut; it may happen inside one coherent continuous screen recording through cursor/action/data change.
- Do not hold sparse admin pages while narration explains abstract architecture.
- Do not convert sparse pages into a rapid slideshow of 1.x-second screenshots.
- Prefer conflict-bearing evidence: Why No Trade, risk rejection, order/fill truth-source checks, strategy gate status, position/order state.
- System explanation must answer the current story question.
- Professional details are useful only when translated into viewer language first; technical labels can remain on screen as evidence.

ENDING CONTRACT
The final 3–5s must:
1. visually return to credible proof/result when possible;
2. state one next unresolved question tied to a genuine project risk/problem.
Do not end with generic "下一步继续优化" or CTA as the only reason to continue.

LOOP

PHASE 0 — LOCK INPUTS
A. Resolve exact repository, branch, HEAD, episode directory, source recording, narration source, benchmark/reference and last known-good baseline.
B. Hash/record media inputs. Do not silently swap source video, voice, model or benchmark during repairs.
C. Read prior negative examples and keep their lessons as hard anti-regression rules.

PHASE 1 — OBSERVE THE CURRENT FINAL
A. Probe the actual candidate with ffprobe and decode the entire media.
B. Record SHA256.
C. WATCH THE FULL VIDEO from start to finish at 1x with actual audio. This is mandatory before scoring or PASS.
D. On first pass do not pause/scrub/replay to rescue readability. Note any moment where you wanted to pause because evidence disappeared too fast.
E. Create dense samples for 0–10s, every scene boundary, historical retention-risk middle ranges, and final 5–10s.
F. Create contact sheets and measure silence/loudness/dynamics as supplementary diagnostics only.
G. Record defects as timestamp -> observed viewer problem -> root cause.
H. Classify TECHNICAL_BASELINE and PUBLISHING_QUALITY separately.

PHASE 2 — CONTINUITY / MOTION DIAGNOSIS
Before visual polish, ask:
1. Does the video feel like a coherent moving piece or a slideshow of screenshots/cards?
2. Is motion coming from real cursor/action/data change or mostly camera pan/zoom over stills?
3. Does each cut have a semantic reason?
4. Can the viewer orient before the next cut?
5. Are there repeated dark/bright flips that feel like flashing?
6. Can every key proof be understood at 1x without pause/replay?
7. Did duration/shot-count targets cause evidence to be shortened below comprehension time?
Any failure here is release-blocking.

PHASE 3 — STORY DIAGNOSIS
Ask:
1. What specific question makes a viewer continue after 3s?
2. Is there a person/stake, or only a system description?
3. What is the conflict or contradiction?
4. Is the strongest proof shown early enough?
5. Does every explanation resolve that conflict?
6. Where is the truth source?
7. Is there a next unresolved question at the end?
If story is weak, reorder content/narration before cosmetic polish.

PHASE 4 — ROOT CAUSE, NOT COSMETIC PATCHING
Trace each defect backward through final media -> render -> timeline/scene map -> asset selection -> source -> prompt/config/code.
Classify as CONTENT, STORY_ORDER, SOURCE_SELECTION, TIMING, CONTINUITY, MOTION_LANGUAGE, LAYOUT/ROI, CAPTION, AUDIO, RENDERER, QA_GATE, PROMPT/AGENT.

PHASE 5 — TEST FIRST FOR REPEATABLE REGRESSIONS
If a defect comes from code/config/prompt behavior:
A. Add the smallest regression test that fails on old behavior.
B. Capture RED for the intended reason when the environment allows it.
C. Implement the minimum durable fix.
D. Run that test and the relevant existing suite.
Never weaken a test to preserve a behavior already proven bad in actual media.

PHASE 6 — BUILD ONE STORY CANDIDATE
A. Rebuild from clean source assets, not already-burned derivatives.
B. Edit narration/story order first; let evidence cuts follow speech/conflict beats.
C. Put strongest real proof early.
D. For process footage, prefer real continuous screen recording. Use cursor, click, scroll, state change and semantic emphasis instead of screenshot camera motion.
E. For still-only evidence, use one restrained emphasis and enough reading time.
F. Do not force cut frequency or total duration. Remove filler before shortening proof.
G. Burn captions only after clean visual/story timing is accepted.

PHASE 7 — TECHNICAL HARD GATES
Reject if any is true:
- duration > 68s;
- wrong canvas/codec/fps/audio format;
- decode error;
- black/loading/placeholder accident;
- first 3s lacks real evidence;
- fake compare/duplicate split view;
- semantic crop removes context required to understand proof;
- caption exceeds 2 lines, sits outside safe zone or blocks evidence;
- audio is inaudible/clipped/undeclared fallback/abnormally silent;
- audio/visual claim mismatch;
- review artifacts are missing or fabricated.
Passing this phase produces TECHNICAL_BASELINE_PASS only.

PHASE 8 — MANDATORY PRE-DELIVERY VIDEO REVIEW
Run `docs/creator-os/video-pre-delivery-qa-prompt.md` against the CURRENT complete candidate.
Required evidence:
- full 1x start-to-end watch;
- first-10s dense review;
- every-transition scan;
- 360x640 mobile review;
- actual audio listen;
- timestamped findings;
- current SHA256.

Hard fail if:
- slideshow-like viewing experience;
- static screenshot pan/zoom dominates motion;
- key evidence requires pause/scrub/replay;
- repeated unmotivated/context-breaking hard cuts;
- disruptive repeated dark/light switching;
- context-destroying crop/zoom;
- motion without semantic reason;
- audio/visual mismatch;
- caption/overlay blocks proof;
- any known critical viewer-facing issue remains.

Scores may be recorded for diagnosis, but they do not determine PASS. Any hard fail overrides scores.

PHASE 9 — REPAIR LOOP
1. Rank viewer-impact defects: continuity/readability > weak hook/story > conflict/proof > audio sync/expressiveness > captions > cosmetics.
2. Fix one highest-impact root cause or tightly-coupled cluster.
3. Do NOT add more transitions/zoom to fix choppiness.
4. Do NOT shorten readable evidence merely to hit total duration.
5. Re-render affected range for diagnosis, then rebuild whole candidate.
6. Recompute SHA256.
7. Rewatch the NEW full candidate from start to finish at 1x and rerun all review gates.
8. Maximum 3 symptom-level attempts for one root cause; after that reopen source/edit strategy rather than making cosmetic variants.

FINAL ACCEPTANCE
Only declare COMPLETE when all are simultaneously true:
- TECHNICAL_BASELINE_PASS;
- PUBLISHING_QUALITY_PASS;
- full 1x start-to-end review of CURRENT SHA256 performed;
- first-10s dense review performed;
- all scene boundaries reviewed;
- mobile 360x640 review performed;
- actual audio listened through;
- no slideshow/fake-motion hard fail;
- no unreadable key evidence;
- no disruptive context-breaking cut sequence;
- no critical findings remain;
- first 10s has identity + result/proof + conflict;
- middle does not fall back into product-demo/document-reading mode;
- ending contains a genuine next unresolved question;
- all relevant regression tests are green;
- delivered file SHA256 equals reviewed file SHA256.

FINAL RESPONSE
Do not dump the production process. Return only:
- final video path
- duration
- resolution/codec/audio
- narration source/provider actually used
- TECHNICAL_BASELINE status
- PUBLISHING_QUALITY status
- continuous playback review status
- repository branch + final commit
- SHA256
If genuinely blocked, return BLOCKED plus exact unrecoverable input and evidence.
```
