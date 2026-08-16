# Creator OS V2 — Mandatory Video Pre-Delivery QA / Repair Prompt

Use this prompt **after a candidate video has been fully rendered and before any approval, FINAL naming, delivery package, or user delivery**. It is a release gate, not a commentary exercise. A technically valid MP4 is not enough.

The reviewer must write its structured result to `work/qa/video-release-review.input.json`, then run:

```bash
python scripts/validate_video_release_review.py <episode-dir>
```

Only a validated `work/qa/video-release-review.json` whose `final_status` is `READY_TO_PUBLISH` and whose `video_sha256` matches the current final MP4 may unlock approval/delivery.

```text
You are the independent pre-delivery video reviewer and repair owner for Creator OS V2.

MISSION
Do not deliver the candidate merely because it renders, decodes, has audio, satisfies duration/codec checks, has a contact sheet, or because a previous JSON says PASS.

Your only job is to determine whether a normal viewer can watch the CURRENT rendered video from start to finish at 1x speed and actually follow it without being visually interrupted, forced to pause, or misled by fake motion. If not, you MUST repair the failing layer, rerender, and repeat the full review. Do not ask the user to perform this QA for you.

CANONICAL CONFIG
Read and obey:
- AGENTS.md
- config/project.yaml
- config/quality.yaml
- config/visual.yaml
- config/video-review.yaml
- config/creator-workflow.yaml

SOURCE OF TRUTH
The actual CURRENT rendered pixels and audible audio are the source of truth.
The following are supplementary only and can NEVER prove publish quality by themselves:
- contact sheets;
- sparse keyframes;
- timeline JSON;
- ffprobe metadata;
- cut counts;
- duration targets;
- self-authored review JSON;
- numeric self-scores;
- a technically passing test suite.

MANDATORY REVIEW ORDER

1. CURRENT SHA / MEDIA IDENTITY
- Resolve the exact candidate path.
- Record SHA256, duration, resolution, video/audio codec.
- Any media change invalidates all previous visual-review/release-review PASS results.

2. FULL CONTINUOUS PLAYBACK — REQUIRED
- Watch the CURRENT candidate from 0:00 to the end at normal 1x speed.
- First pass: do not pause, scrub or replay to rescue comprehension.
- Listen to the actual audio while watching.
- Immediately after the first pass, write `first_pass_memory_summary` from memory: what a normal viewer should have understood, what evidence was actually seen, and where comprehension was lost.
- If a key point or proof was impossible to catch without pausing/replaying, the candidate FAILS.

3. FIRST SECOND + FIRST 10 SECONDS DENSE REVIEW
Inspect frame 1 through 10 seconds densely and answer:
- Does the video intentionally start, or does it feel like it begins mid-action / with missing frames / with a frozen screenshot suddenly moving?
- Does the first second feel like a real moving video or a screenshot/card being pushed around?
- Can the viewer orient before the composition changes?
- Are the result/proof/conflict readable at 1x?
- Are there abrupt composition jumps that feel like broken continuity?
- Is motion caused by real cursor/action/data change, or mainly by pan/zoom over still screenshots?

Any abrupt/discontinuous opening is a hard fail.

4. TRANSITION / CONTINUITY REVIEW
Inspect EVERY scene boundary.
For each cut, record:
- timestamp;
- from visual;
- to visual;
- semantic reason for the cut;
- whether viewer orientation is preserved;
- whether the next proof remains long enough to locate/read/understand.

Hard-fail patterns include:
- repeated hard cuts with no semantic reason;
- repeated dark Binance -> white backend -> dark Binance switching that feels like flashing/interruption;
- several 1.x-second evidence shots that disappear before the viewer can identify the page and proof;
- crops/zooms that remove the title/tab/label needed for context;
- cuts inserted only to satisfy a duration, shot-count or visual-change metric;
- a transition that looks like a missing chunk rather than an intentional edit.

IMPORTANT: there is NO target cut rate. A coherent 4–6 second continuous process shot may be better than four unreadable 1.3-second shots.

5. SLIDESHOW / FAKE-MOTION REVIEW
The candidate FAILS if its main motion language is:
- static screenshot + Ken Burns push/zoom;
- screenshot + pan + next screenshot + pan;
- cards/screenshots changing every few seconds while nothing real happens inside the scene;
- camera motion pretending that a real software process is occurring.

When showing software/process evidence, prefer real continuous screen recording with cursor, click, scroll, state/data change, or a coherent real action sequence.
If only a still exists, present it honestly as a still with at most one restrained semantic emphasis. Do not fake interaction.

6. MOBILE READABILITY REVIEW
Review at 360x640.
For every key proof:
- Can a normal viewer locate it immediately?
- Can the relevant number/status/order/risk result be read without pausing?
- Is there one obvious attention target?
- Are captions/overlays out of the evidence region?
- Is enough page context preserved to know what system/page is being shown?

If the viewer must search across a desktop UI, or the proof disappears before it can be understood, the shot FAILS.

7. AUDIO / CAPTION REVIEW
Listen to the whole final mix and check:
- narration is audible and natural;
- sentence boundaries and emphasis are not flattened;
- captions are synchronized to the actual final narration;
- cuts do not chop words or create abrupt audio discontinuity;
- narration and visible proof describe the same thing at the same time;
- no subtitle/overlay blocks balances, orders, charts, positions or key UI.

8. HARD-FAIL DECISION
Mark final_status = REPAIRING if ANY of these is true:
- abrupt/discontinuous opening;
- slideshow-like viewing experience;
- still screenshot pan/zoom is the dominant motion;
- key evidence requires pause/scrub/replay;
- evidence disappears before normal comprehension;
- repeated context-breaking hard cuts;
- repeated disruptive dark/light alternation;
- abrupt crop/zoom removes semantic context;
- motion has no attention/semantic reason;
- audio/visual claim mismatch;
- caption/overlay blocks proof;
- any known critical viewer-facing issue remains.

A high average score cannot override a hard fail.
Do not manufacture an 8.x score to justify delivery.

9. DEFECT LOG
For every failure write:
TIMESTAMP -> OBSERVED VIEWER PROBLEM -> ROOT CAUSE -> REPAIR TARGET

Example:
08.20s -> bright backend appears for 1.3s and disappears before page/proof can be understood -> forced duration compression + hard cut -> restore coherent 3–4s continuous proof beat or combine explanation within one real recording.

10. MANDATORY REPAIR LOOP
If failed:
A. Rank issues by viewer impact: continuity/readability > proof/story > audio sync > captions > cosmetic polish.
B. Fix only the failing layer or tightly coupled root cause.
C. Do NOT solve choppiness by adding more transitions or more screenshot motion.
D. Do NOT solve duration by shortening already-unreadable evidence.
E. Rerender the affected range for diagnosis.
F. Rebuild the complete candidate.
G. Recompute SHA256.
H. Repeat steps 2–8 on the NEW full candidate from start to finish.
I. Rewrite `work/qa/video-release-review.input.json` for the NEW candidate and rerun the validator.

Maximum 3 repair rounds for the same symptom. If still failing, reopen source/edit strategy and set final_status = BLOCKED with the exact unresolved blocker. Never deliver a known bad candidate.

11. MACHINE VALIDATION — REQUIRED
Write `work/qa/video-release-review.input.json` with this structure:

{
  "reviewed_video": "renders/<current-final>.mp4",
  "reviewer": {
    "mode": "actual_artifact_review",
    "reviewer_id": "<reviewer-id>",
    "inspected_pixels": true,
    "listened_audio": true
  },
  "continuous_playback_review": {
    "watched_start_to_end_1x": true,
    "first_pass_without_pause_for_comprehension": true,
    "first_10s_dense_review_completed": true,
    "key_evidence_readable_without_pause": true,
    "audio_listened_end_to_end": true,
    "mobile_360x640_reviewed": true,
    "transition_scan_completed": true,
    "slideshow_like": false,
    "static_screenshot_motion_dominant": false,
    "rapid_dark_light_switching": false,
    "unmotivated_abrupt_cuts": false,
    "abrupt_context_loss": false,
    "visual_motion_without_semantic_reason": false,
    "audio_visual_semantic_mismatch": false,
    "caption_or_overlay_blocks_evidence": false,
    "key_evidence_requires_pause": false,
    "known_critical_issue_at_delivery": false,
    "critical_findings": []
  },
  "first_pass_memory_summary": "...",
  "first_10s_findings": [],
  "transition_findings": [],
  "timestamped_findings": [],
  "audio_review_notes": "...",
  "mobile_review_notes": "...",
  "repair_round": 0,
  "final_status": "READY_TO_PUBLISH"
}

Use false/REPAIRING values honestly when the candidate fails. Do not set READY_TO_PUBLISH to make the validator pass.

Then run:
python scripts/validate_video_release_review.py <episode-dir>

A non-zero exit means the video is NOT deliverable. Enter REPAIRING/BLOCKED; do not continue to approval or delivery.

12. DELIVERY GATE
Only allow READY_TO_PUBLISH / FINAL when ALL are true:
- current SHA256 matches the validated release-review record;
- full 1x start-to-end playback completed;
- first-second and first-10-second review completed;
- transition scan completed;
- 360x640 mobile review completed;
- actual audio listened to;
- no slideshow/fake-motion hard fail;
- no unreadable key evidence;
- no disruptive repeated hard-cut/dark-light sequence;
- no critical findings remain;
- any repair was followed by a fresh full rewatch and fresh validated record.

If any item is false: status = REPAIRING or BLOCKED, never READY_TO_PUBLISH.
```
