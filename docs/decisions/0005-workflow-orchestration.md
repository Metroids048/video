# ADR-0005: Codex Full-Chain Workflow Orchestration

- Status: Accepted
- Date: 2026-07-31
- Module: 10 (V1.1 orchestration and operational documentation)

## Context

V1 already has a reliable production back half: `timeline.json`, FFmpeg rough cuts,
HyperFrames packaging, QA, and editable delivery.  Its front half is intentionally
agent-assisted: ingest, reference analysis, content brief, script, storyboard, and
asset review are separate commands.  This makes a real episode easy to start but
too easy to stall or to run stages in the wrong order.

The supplied Douyin references reinforce four applicable ideas:

1. audio/timing must inform storyboard and timeline;
2. a reference analysis must become reusable written guidance, not a one-off prompt;
3. preview, captions, timeline, source assets, and editorial notes must be handed
   off together;
4. AI output remains a rough draft that needs human editorial review.

The project boundary rules prohibit automatic publishing, downloading third-party
platform videos, or creating/reverse-engineering Jianying drafts.  Therefore an
orchestrator must make the existing workflow easier to run without hiding those
boundaries or inventing a second state store.

## Decision

Add a `python -m avs workflow` command group backed by a small, pure workflow
inspection module.

- `workflow status <ID>` reports the current state and the exact next action.
- `workflow next <ID>` reports only the actionable next step, including whether it
  is deterministic, agent-assisted, human approval, input collection, recovery, or
  complete.
- `workflow resume <ID>` repeatedly runs only deterministic commands that are
  already part of the canonical CLI (`ingest`, `reference analyze`, `content init`,
  and the existing `run` back-half command).  It stops successfully at a human or
  agent gate and never changes state merely to look complete.

The source of truth remains `episode.json`; `timeline.json` remains the rendering
contract.  The inspector derives its answer from these files and the existing
episode workspace.  It does not create a workflow database, queue, or hidden
checkpoint.

Reference URLs remain provenance input in `input/links.txt`.  The application does
not fetch or download third-party platform video.  A browser-reviewed reference
registry records the resolved page, evidence level, and transferable,
non-copyrightable workflow ideas for all 18 supplied references.

The audited Apache-2.0 `video-shotcraft` Skill is pinned and installed globally as
a reference library.  AVS may reuse its shot vocabulary, pacing, and sound-design
guidance, but does not adopt its Remotion renderer.  `timeline.json`, FFmpeg, and
HyperFrames remain the canonical V1 rendering path.

## Consequences

- A Codex Skill can now take an episode from creation through deterministic stages
  with one command, then state exactly what an agent or editor must do next.
- The project stays usable without a Codex plugin because all operational behavior
  is available through `python -m avs`.
- `workflow resume` is deliberately not an autonomous content generator.  The
  content Skill creates the brief/script/storyboard and the editor performs the
  explicit approval commands.
- Delivery remains an editable package (`MP4`, `SRT`, `timeline.json`, assets,
  QA report, editing notes), not a Jianying draft and not a publishing action.
- Third-party Skills with no auditable source or incompatible required dependencies
  are not installed merely because a social post names them.

## Implementation Plan

1. Add pure inspection and resume helpers with unit tests covering every workflow
   state and idempotent stopping points.
2. Register the command group in the existing CLI, with JSON output for agents.
3. Add `orchestrate-video-production` under `skills-src/` and sync it using the
   existing Skill mechanism.
4. Add an evidence-graded Douyin reference registry and user-facing operating,
   input, editing, compatibility, and troubleshooting documentation.
5. Make `scripts/verify.mjs` reject missing required documentation, stale Skill
   synchronization, missing workflow command availability, and stale roadmap text.
6. Run the full verification suite plus real demos and HyperFrames doctor/lint/render.

## Rejected Alternatives

### A second workflow database or task queue

Rejected because it duplicates `episode.json`, complicates resume semantics, and
would violate the project's single-source-of-truth rule.

### Automatically generate content, approve assets, or publish

Rejected because those operations involve factual/editorial judgment and are outside
the V1 safety boundary.

### Download, transcribe, or clone every social-platform reference automatically

Rejected because it is unnecessary for the core CLI, creates rights/platform risk,
and conflicts with the no-third-party-download rule.  Local reference files can
still be analyzed through the existing approved pipeline.
