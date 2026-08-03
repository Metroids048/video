# ADR-0008: Creator Operating System Above Episode

Status: Accepted

## Context

The project can already produce one Episode, but a creator account is not one
project. The account needs a stable promise, multiple real projects, repeatable
input rules, a monetization hypothesis, and a feedback loop. Without an account
layer, each video starts from zero and the system optimizes rendering details
before proving that the topic is useful to a viewer.

## Decision

Add an account-level creator contract in `config/creator-workflow.yaml` and a
human-readable SOP in `docs/creator-video-workflow.md`.

The account layer owns:

- positioning, audience, content pillars, series rules, and monetization stages;
- the minimum input package and reference-video evidence requirements;
- the skill routing order and quality gates for a publishable post;
- the collaboration contract and post-publication experiment loop.

The account layer does **not** own runtime state. `episode.json` remains the
single state machine for one piece of content, and `timeline.json` remains the
shared renderer protocol. All account-level outputs that belong to a post are
stored under that Episode's `work/` or `delivery/` directories.

Reference URLs may be recorded as research sources, but exact visual and pacing
claims require a local authorized copy plus deterministic inspection artifacts.
The project must never claim to have fully watched or reproduced a remote video
when only a page or title was available.

## Consequences

- One account can cover many projects while preserving one recognizable promise.
- The agent can own roughly 90% of production; the user only supplies facts,
  permissions, final approval, publication, and platform metrics.
- Monetization is tested in stages (free proof -> low-ticket template ->
  diagnosis -> delivery service) instead of being promised before evidence.
- A missing local reference, voice, music license, vision provider, or human
  approval blocks the relevant gate instead of being silently replaced.
- Existing renderers and third-party Skills remain optional routed capabilities;
  they cannot create or bypass Episode completion.

## Verification

- `tests/test_config.py` validates the account contract is loaded by `Config`.
- `npm run skills:check` validates the project Skill is synchronized.
- `npm run verify` remains the repository acceptance gate.
