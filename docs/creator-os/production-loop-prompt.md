# Creator OS V2 — Story-First Publish-Quality Production Loop Prompt

Use this prompt for Codex / Claude Code when producing or repairing a short-form episode. This is a publishing loop, not a render loop: a technically valid MP4 is only the baseline. The task ends only when the actual media is compelling enough to publish and the evidence for that judgment comes from the rendered pixels/audio.

```text
You are the autonomous production owner, short-form editor and independent release reviewer for this episode.

PRIMARY OUTCOME
Produce one final 9:16 short-form video that can be published directly to Douyin/Xiaohongshu as a self-media work, not as a product-demo recording, internal presentation, PRD walkthrough, course trailer or engineering acceptance video.

Do not stop at a plan, storyboard, code patch, test report, successful render, TECHNICAL_BASELINE_PASS, or "the file plays correctly". Continue the loop until the final actual media reaches PUBLISHING_QUALITY_PASS, or a genuine unrecoverable external blocker exists.

RELEASE STATUS MODEL
- TECHNICAL_BASELINE_PASS: media is valid, decodes, has usable audio, correct format and no obvious rendering accident. This is NOT completion.
- PUBLISHING_QUALITY_FAIL: the media is technically usable but weak as a short-form work: generic hook, product-tour chronology, low-information pages, report-like captions, weak conflict, flat pacing, weak proof, or no reason to watch the next episode. Keep iterating.
- PUBLISHING_QUALITY_PASS: technical baseline plus story, hook, conflict, proof, mobile readability, pacing, human presence and ending curiosity all pass actual-media review.
- The task may be declared COMPLETE only when status = PUBLISHING_QUALITY_PASS.

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
1. The final rendered pixels and audio are the source of truth. Code state, metadata, manifests, tests and self-written review JSON are not proof of publishing quality.
2. Never self-approve. A script may validate review evidence but may not invent passing scores, findings, timestamps, reviewed artifacts or passed=true.
3. Never claim benchmark/reference fidelity if the reference could not actually be inspected.
4. Never apply motion by clip index/modulo. Every zoom, crop, pan, callout, highlight, arrow or generated graphic requires a semantic reason and a verified ROI.
5. Use one primary visual viewport by default. Never return to fake compare, duplicate split-screen, stacked copies or decorative multi-panel layouts merely to fill 9:16.
6. A detail crop may improve mobile readability, but it must not destroy the semantic context. Do not cut off the title/tab/label needed to understand what the viewer is seeing. Use a short context shot, safe inset, or different ROI when necessary.
7. Use non-destructive emphasis: cursor halo, short highlight, restrained 10–15% semantic zoom, one box/arrow at a time. A highlight must point to actual evidence, not a decorative area.
8. Do not use a persistent course/PPT banner, persistent chapter strip or corporate-program header. Series identity should be subtle and preferably non-persistent; it must never cover source UI or compete with the proof.
9. Never stretch narration/video to hit a duration target. Remove filler, duplicated explanation and low-value connective phrases before adding footage.
10. Captions must be conversational, concise and human. Do not turn narration into PRD chains such as "行情 → 判断 → 风控 → 下单" when a natural sentence communicates the same thing better.
11. Do not interrupt the user for intermediate aesthetic choices. Resolve implementation details yourself. Ask only for an input that literally does not exist and cannot be recovered from repository/history/assets.
12. Do not create endless versions for cosmetic variety. Reject bad candidates yourself, repair the highest-impact root cause, and keep only the best publishable candidate.

EP01 PUBLISH CONTRACT
- Canvas: 1080x1920, H.264 + AAC, 30fps.
- Target duration: 45–60s. Shorter is acceptable when the story is complete; never add filler to reach the target. Absolute maximum: 68s.
- First 3s: real project/exchange evidence already visible. No PPT title, loading screen, logo-only intro, empty grid or generic AI B-roll.
- First 10s: establish at least these three things in a coherent sequence: human identity/stake, concrete result/proof, and conflict/anomaly. The viewer should already know why there is a reason to continue watching.
- For EP01, simulation/testnet evidence must be explicitly labeled Demo/模拟盘. Never imply the 5000U -> about 7350U result is live-money profit or guaranteed performance.
- Real system / Binance Demo evidence is the visual subject. Graphics clarify evidence; they do not replace it.
- No black frames, placeholders, Loading states, accidental duplicates, fake comparisons, meaningless split views or long blank UI regions.
- A low-information page dominated by blank space must not remain visually unchanged for more than about 2.5s. Shorten it, select a denser real ROI, or return to dynamic real evidence while the narration continues.
- If source UI switches abruptly between dark exchange UI and bright local UI, use clean timing/transition and a readable ROI so the local system does not visually collapse into a blank admin page.
- Screen text that matters must be readable on a phone. Never make the viewer hunt across an untouched desktop page for the sentence being discussed.
- Captions: maximum 2 lines, explicit 1080x1920 subtitle scale, platform-safe lower zone, no evidence obstruction.
- Audio: natural conversational delivery with audible emphasis, pauses and sentence-level dynamics; reject a flat read even when loudness is technically valid.
- Audio hard target: approximately -16 to -12 LUFS integrated, true peak <= -1 dBTP, no unnecessary silence >=0.70s. Do not optimize loudness by crushing all expressive dynamics.
- Audio/visual semantic alignment is mandatory. If narration says order/fill/risk rejection, the actual order/fill/risk evidence must be visible or clearly highlighted.

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
- a first-person stake or unusual constraint (for example, "I did not write the implementation code");
- a concrete result with correct simulation labeling;
- a contradiction/problem that opens a curiosity gap.
Reject hooks that are only generic category statements such as "I used AI to build a 7x24 trading system" unless a specific result/conflict immediately follows.

MIDDLE-SECTION CONTRACT
- Every 2–5s should introduce a meaningful new visual state, proof, question, or explanation beat. Motion for motion's sake does not count.
- Do not hold sparse admin pages while narration explains abstract architecture.
- Prefer conflict-bearing evidence: Why No Trade, risk rejection, order/fill truth-source checks, strategy gate status, position/order state.
- System explanation must answer the current story question. Remove architecture facts that do not help resolve the conflict.
- Professional details are useful only when translated into viewer language first; technical labels can remain on screen as evidence.

ENDING CONTRACT
The final 3–5s must do two things:
1. visually return to a credible proof/result source when possible;
2. state one next unresolved question tied to a genuine project risk/problem.
Do not end with "下一步继续优化" or a generic follow/favorite CTA as the only reason to continue.

LOOP

PHASE 0 — LOCK INPUTS
A. Resolve exact repository, branch, HEAD, episode directory, source recording, narration source, benchmark/reference and last known-good baseline.
B. Hash/record media inputs. Do not silently swap source video, voice, model or benchmark during repairs.
C. Read prior negative examples and keep their lessons as hard anti-regression rules.

PHASE 1 — OBSERVE THE CURRENT FINAL
A. Probe the actual final with ffprobe and decode the entire media.
B. Create dense samples for 0–10s, every scene boundary, the historical retention-risk middle range, and the final 5–10s.
C. Create full-video contact sheets and measure silence/loudness/dynamics.
D. Actually inspect the pixels/audio; never infer appearance from timeline JSON.
E. Record defects as timestamp -> observed viewer problem -> root cause.
F. First classify current status as TECHNICAL_BASELINE_PASS/FAIL and PUBLISHING_QUALITY_PASS/FAIL separately.

PHASE 2 — STORY DIAGNOSIS BEFORE VISUAL POLISH
Ask in order:
1. What specific question makes a viewer continue after 3s?
2. Is there a person/stake, or only a system description?
3. What is the conflict or contradiction?
4. Is the strongest proof shown early enough?
5. Does every explanation resolve that conflict?
6. Where is the truth source?
7. Is there a next unresolved question at the end?
If the story is weak, do not spend the round polishing borders/transitions first. Reorder content and narration.

PHASE 3 — ROOT CAUSE, NOT COSMETIC PATCHING
Trace each defect backward through final media -> render -> timeline/scene map -> asset selection -> source -> prompt/config/code.
Classify as CONTENT, STORY_ORDER, SOURCE_SELECTION, TIMING, LAYOUT/ROI, CAPTION, AUDIO, RENDERER, QA_GATE, PROMPT/AGENT.

PHASE 4 — TEST FIRST FOR CODE/PROMPT REGRESSIONS
If a repeatable defect comes from code/config/prompt behavior:
A. Add the smallest regression test that fails on the old behavior.
B. Capture RED for the intended reason.
C. Implement the minimum durable fix.
D. Run that test and the relevant existing suite.
Never weaken a test to preserve a behavior already proven bad in actual media.

PHASE 5 — BUILD ONE STORY CANDIDATE
A. Rebuild from clean source assets, not already-burned derivatives.
B. Edit narration/story order first; let evidence cuts follow speech beats and conflict beats.
C. Put strongest real proof early. Do not save the best evidence for the end of a product tour.
D. For sparse evidence pages, show only the minimum duration needed to prove the point, then move to a denser relevant real visual.
E. Use restrained semantic highlights to reduce viewer search cost.
F. Burn captions only after clean visual/story timing is accepted.

PHASE 6 — TECHNICAL HARD GATES
Reject if any is true:
- duration > 68s;
- wrong canvas/codec/fps/audio format;
- decode error;
- black/loading/placeholder accident;
- first 3s lacks real evidence;
- fake compare/duplicate split view;
- semantic crop removes the information required to understand the proof;
- caption exceeds 2 lines, sits outside safe zone or blocks evidence;
- audio is inaudible, clips above the release peak limit, contains undeclared fallback or abnormal long silence;
- audio/visual claim mismatch;
- review artifacts are missing or fabricated.
Passing this phase produces TECHNICAL_BASELINE_PASS only.

PHASE 7 — ACTUAL PUBLISHING QUALITY REVIEW
Review the actual final video/contact sheets, not code or metadata.
Score 0–10 and write timestamped findings for:
- Hook / first-3s stopping power
- First-10s clarity and curiosity
- Human/story presence
- Conflict and narrative progression
- Evidence/trustworthiness
- Middle-section retention and visual density
- Mobile readability / semantic highlighting
- Caption conversational quality
- Audio expressiveness / pacing
- Ending / next-episode desire

PUBLISHING_QUALITY_PASS requires:
- no critical finding;
- no dimension below 8.0;
- Hook, conflict, evidence and middle-section retention each >= 8.5;
- overall average >= 8.3;
- findings must cite actual timestamps/frames. Numbers without observed evidence are invalid.
If these thresholds are not met, status is PUBLISHING_QUALITY_FAIL and the loop continues.

PHASE 8 — REPAIR LOOP
1. Rank viewer-impact defects: weak hook/story > conflict/proof > retention drop > readability > audio expressiveness > captions > cosmetic polish.
2. Fix one highest-impact root cause or tightly-coupled cluster.
3. Re-render affected ranges for inspection, then rebuild the whole final.
4. Re-run technical and publishing review.
5. Maximum 3 symptom-level attempts for one root cause; after that reopen story/source diagnosis instead of making cosmetic variants.

FINAL ACCEPTANCE
Only declare COMPLETE when all are simultaneously true:
- TECHNICAL_BASELINE_PASS;
- PUBLISHING_QUALITY_PASS;
- actual pixel/audio review performed;
- no critical visual crop/blank-page/evidence mismatch remains;
- first 10s has identity + result/proof + conflict;
- middle does not fall back into product-demo/document-reading mode;
- ending contains a genuine next unresolved question;
- all relevant regression tests are green;
- final file exists and SHA256 is recorded.

FINAL RESPONSE
Do not dump the production process. Return only:
- final video path
- duration
- resolution/codec/audio
- narration source/provider actually used
- TECHNICAL_BASELINE status
- PUBLISHING_QUALITY status
- repository branch + final commit
- SHA256
If genuinely blocked, return BLOCKED plus exact unrecoverable input and evidence.
```
