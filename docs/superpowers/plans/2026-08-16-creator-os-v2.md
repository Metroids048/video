# Creator OS V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old Agent Video Studio/V1 production contract with Creator OS V2, remove obsolete quant-video production residue, and preserve existing plugin/Skill resources.

**Architecture:** Keep the existing media engine and capability resources as the execution substrate, while replacing the product/control contract above them. V2 introduces one Creative Contract, a VIDEO/CAROUSEL/TEXT format router, explicit voice audition policy, publish-grade QA, and a READY_TO_PUBLISH product state without requiring a risky rewrite of every low-level renderer in the same migration.

**Tech Stack:** Python 3.11+, YAML/JSON contracts, FFmpeg/HyperFrames/Remotion and existing vendored Skills/providers.

## Global Constraints

- Do not add, upgrade, remove or rewrite plugin/Skill/vendor resources in this migration.
- Preserve `skills-src/`, `third_party_skills/`, `vendor/`, `.agents/skills`, `.claude/skills`, `skills.lock.json` and `tools-manifest.yaml`.
- Preserve the generic reference knowledge library.
- Remove quant/EP01 historical reports, fixtures and one-off builders.
- User-facing success is `READY_TO_PUBLISH`; manually unfinished work is `BLOCKED`.
- Douyin URLs are first-class reference inputs; acquisition failure must degrade honestly rather than fabricate audiovisual analysis.
- The selected narration master is the timing authority for VIDEO.
- Repair loops are localized and capped at 3 rounds by default.

---

### Task 1: Repository cleanup

**Files:**
- Delete quant-specific root reports and historical progress/fix reports.
- Delete root one-off video generation helpers tied to the failed quant episode.
- Delete `fixtures/golden-ai-quant/`.
- Delete `docs/retros/`.
- Delete obsolete V1 design/prompt/overnight implementation documents.
- Delete EP01-specific builders/audition scripts under `scripts/`.

**Interfaces:**
- Consumes: current `main` tree.
- Produces: a lean tree in which capability resources and generic engine/test assets are intact.

- [ ] **Step 1:** Remove only the explicitly identified historical roots/subtrees.
- [ ] **Step 2:** Verify protected capability paths still exist and keep their original tree SHA where no project-rule update is required.
- [ ] **Step 3:** Verify `fixtures/reference-adapt-demo` and `fixtures/screen-explainer-demo` remain available.
- [ ] **Step 4:** Verify `fixtures/golden-ai-quant` and all `scripts/build_ep01_*` paths are absent.

### Task 2: Freeze Creator OS V2 project contract

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `config/project.yaml`
- Modify: `config/creator-workflow.yaml`
- Modify: `config/workflow.yaml`
- Create: `config/content-formats.yaml`
- Create: `config/reference-acquisition.yaml`
- Create: `config/voice.yaml`
- Modify: `src/avs/config.py`

**Interfaces:**
- Consumes: existing Config loader and engine states.
- Produces: single project contract and new configuration surfaces for format routing/reference acquisition/voice audition.

- [ ] **Step 1:** Rename project/product contract to Creator OS V2 while retaining `python -m avs` as the execution engine.
- [ ] **Step 2:** Rewrite creator workflow around Input Hub → Research & Evidence → Creative Director → Format Router → Production → Creative QA → Delivery & Learning.
- [ ] **Step 3:** Keep low-level execution transitions compatible, but add an explicit public lifecycle mapping ending in READY_TO_PUBLISH.
- [ ] **Step 4:** Add VIDEO/CAROUSEL/TEXT routing rules.
- [ ] **Step 5:** Add Douyin reference acquisition/fallback policy.
- [ ] **Step 6:** Add HUMAN_ENHANCED/HYBRID_S2S/PREMIUM_TTS audition policy and final-narration timing rule.
- [ ] **Step 7:** Extend `Config` required files/properties so missing V2 config is detectable.

### Task 3: Add machine-readable V2 contracts

**Files:**
- Create: `schemas/creative-contract.schema.json`
- Create: `schemas/format-decision.schema.json`
- Create: `schemas/voice-profile.schema.json`
- Create: `schemas/creator-review.schema.json`

**Interfaces:**
- Consumes: V2 config vocabulary.
- Produces: stable JSON contracts usable by Codex/Claude/other agents without relying on chat memory.

- [ ] **Step 1:** Define Creative Contract fields and immutable decision scope.
- [ ] **Step 2:** Define format decision with VIDEO/CAROUSEL/TEXT and reason/evidence fields.
- [ ] **Step 3:** Define persistent voice profile and audition evidence.
- [ ] **Step 4:** Define publish review with inspected artifacts, failure codes, repair target and READY_TO_PUBLISH/BLOCKED decision.

### Task 4: Replace V1 documentation with concise V2 operating docs

**Files:**
- Create: `docs/creator-os-v2.md`
- Create: `docs/workflow-v2.md`
- Modify: `docs/getting-started.md`
- Modify: `docs/input-guide.md`
- Preserve: `docs/video-plugin-routing.md`, `docs/compatibility.md`, reference research and durable ADRs.

**Interfaces:**
- Consumes: spec/config contracts.
- Produces: human-readable onboarding consistent with machine-readable configuration.

- [ ] **Step 1:** Document exact responsibilities and the single-authority rule.
- [ ] **Step 2:** Document the fixed per-episode input packet and Douyin URL behavior.
- [ ] **Step 3:** Document the publish-grade Pilot/review/repair loop.
- [ ] **Step 4:** Remove language that describes “rough draft + user finishes 10–30%” as the target outcome.

### Task 5: Add guarded local cleanup tooling

**Files:**
- Create: `scripts/cleanup_creator_os_v2_local.ps1`

**Interfaces:**
- Consumes: local repository root on Windows.
- Produces: removal of recognized historical output/media while preserving core resources and `第一期视频_7x24自动交易`.

- [ ] **Step 1:** Resolve repository root and require the preserve directory to exist.
- [ ] **Step 2:** Define protected project/resource directories and historical root paths.
- [ ] **Step 3:** Default to dry-run; require `-Apply` for destructive deletion.
- [ ] **Step 4:** Delete old generated media/output folders and known historical report/build files outside protected areas.
- [ ] **Step 5:** Print preserved path, deleted paths, skipped protected paths and final manual-check reminder.

### Task 6: Verification

**Files:**
- Read-only verification of changed branch.

**Interfaces:**
- Produces: evidence that migration scope matches the design.

- [ ] **Step 1:** Compare `main...agent/creator-os-v2` and inspect changed filenames.
- [ ] **Step 2:** Confirm protected plugin/Skill trees were not deleted or modified by this migration.
- [ ] **Step 3:** Confirm old quant reports, `golden-ai-quant` and EP01 builders are absent.
- [ ] **Step 4:** Confirm README/AGENTS/config use the same V2 terminology, lifecycle and output contract.
- [ ] **Step 5:** Confirm all YAML/JSON written in this migration is syntactically valid by inspection; runtime execution is separately reported because this environment has no direct access to the user's Windows checkout or its installed dependencies.
