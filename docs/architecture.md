# Creator OS V2 Architecture

## Control plane

- Input Hub
- Research & Evidence
- Creative Director
- Format Router
- Creator Review / Repair Router
- Delivery & Learning

These components decide **what** is being made and whether it is publishable.

## Execution plane

Existing AVS/media components decide **how** bounded work is executed:
- ingest/transcription/reference analysis;
- script/storyboard/evidence helpers;
- FFmpeg timeline/rendering;
- HyperFrames/Remotion and other optional motion/render capabilities;
- voice/audio providers;
- deterministic QA and delivery helpers.

## Capability plane

Existing project and third-party Skills/plugins remain frozen resources under `skills-src`, `.agents/.claude` mirrors, `third_party_skills` and `vendor`.

No capability is allowed to become a competing orchestrator. The Creative Contract is the single production authority.

## Data contracts

V2 adds:
- `creative-contract.schema.json`;
- `format-decision.schema.json`;
- `voice-profile.schema.json`;
- `creator-review.schema.json`.

Existing episode/timeline/reference/evidence schemas remain useful execution contracts.

## State model

The low-level AVS engine retains compatibility states to avoid a broad renderer rewrite in the migration. `config/workflow.yaml` maps them into the public Creator OS lifecycle ending in `READY_TO_PUBLISH`.

## Design principle

Prefer fewer, well-defined contracts over more Agents/Skills. When quality fails, fix the failing layer; do not expand architecture as a substitute for creative judgment.
