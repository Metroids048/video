# Creator OS V2

Creator OS V2 is a creator-production operating system for turning real project work into publish-ready content for **Douyin** and **Xiaohongshu**.

The product is no longer “an automatic video editor”. The user supplies real source material, references and optional provider tokens; the system owns research, creative direction, format choice, production, review, repair and the publish pack.

## What goes in

- one idea/problem/project node;
- project files, logs or GitHub/web links;
- screenshots and screen recordings;
- optional rough voice recording;
- local reference videos or Douyin reference URLs;
- privacy/redaction boundaries.

## What comes out

Creator OS chooses the strongest format:

- `VIDEO` — publish-ready vertical video + covers + platform copy;
- `CAROUSEL` — 6–9 page visual post + cover + Xiaohongshu copy;
- `TEXT` — title variants + final post + tags/topics.

A file may be named `FINAL.*` only after the Creator Review returns `READY_TO_PUBLISH`. If the user would still need to reopen Jianying/CapCut to make it acceptable, the status is `BLOCKED`, not “mostly finished”.

## Fixed production flow

`Input Hub → Research & Evidence → Creative Director → Format Router → Production → Creative QA → localized Repair → Delivery & Learning`

The Creative Director is the only authority allowed to choose the story, Hook, output format, voice mode and visual direction. Skills/plugins are execution capabilities; installed does not mean automatically invoked.

## Reference videos

Douyin links are first-class reference inputs. When media can be acquired through existing lawful/public access, it is cached locally and passed to reference analysis. If acquisition fails, the system records page-level evidence only and must not pretend it inspected shots, pacing or audio.

## Voice

One-time audition compares available variants of the same 15–20 second script:

1. `HUMAN_ENHANCED` — clean/master the user’s real voice;
2. `HYBRID_S2S` — preserve the user’s performance while improving/replacing timbre through an authorized speech-to-speech route;
3. `PREMIUM_TTS` — locked high-quality TTS fallback.

The winner is persisted in a voice profile and reused. For video, final narration is the master clock; subtitles use real timestamps, never character-count timing.

## Repository boundaries

Capability resources remain intact:

- `skills-src/`
- `third_party_skills/`
- `vendor/`
- `.agents/skills/`
- `.claude/skills/`
- `skills.lock.json`
- `tools-manifest.yaml`

Historical quant-video reports, EP01 one-off builders and `fixtures/golden-ai-quant` are intentionally removed from the V2 branch.

## Start here

1. Read `AGENTS.md`.
2. Read `docs/creator-os-v2.md` and `docs/workflow-v2.md`.
3. Run `python -m avs doctor` in a local checkout.
4. Run `python scripts/validate_creator_os_v2.py` to verify the V2 contract.
5. Put new source material into a new Episode; do not revive deleted EP01 build scripts.

The existing `python -m avs` engine remains the deterministic execution substrate. Creator OS V2 is the product/control contract above it.
