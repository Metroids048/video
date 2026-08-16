# Creator OS V2 Fixed Workflow

## 0. Episode input packet

Provide as much as exists; do not require the user to pre-edit it.

```text
Topic / problem:
(optional if the material itself makes it obvious)

Facts / evidence:
project files, logs, GitHub URL, screenshots, results

Raw screen recordings:
unedited is acceptable

Rough voice:
optional; natural speech is preferred over presenter-style reading

References:
Douyin links or local videos

Privacy boundary:
what must be hidden / cannot be published

Special request:
optional
```

## 1. INPUT_READY

Normalize assets, preserve originals and create the input manifest. Missing decorative assets are not blockers; missing factual basis/privacy boundary is.

## 2. RESEARCH_READY

Build:
- Evidence Map from first-party facts;
- Reference Recipe(s) from references;
- source confidence/evidence level.

Douyin acquisition failure downgrades that reference to page-level evidence; it does not block the whole episode when other evidence is sufficient.

## 3. CREATIVE_LOCKED

Freeze one Creative Contract:
- one story;
- one primary conflict;
- one Hook;
- one viewer payoff;
- one selected format;
- evidence refs;
- reference pattern refs;
- voice mode;
- visual direction;
- definition of done.

Do not start production before this is coherent.

## 4. Format Router

### VIDEO
Use for temporal/process evidence. Build a real 20–30 second Pilot first for non-trivial work. The Pilot must use representative final voice, captions, evidence framing and motion grammar.

### CAROUSEL
Use for structured explanation/comparison. Default 6–9 pages and one main message per page.

### TEXT
Use for concise conclusions/lessons/checklists where extra visuals add little.

## 5. PRODUCING

Video order:

`final narration → timestamps → storyboard/evidence mapping → Pilot → Pilot review → full timeline → render`

Do not generate a full synthetic narration and then force unrelated screen footage to fit it. Do not time captions by character count.

Carousel order:

`outline → page contract → evidence selection → layout → mobile review → copy`

Text order:

`hook/title variants → structure → final body → platform variant → review`

## 6. REVIEWING

Technical checks first, then actual creative inspection.

For VIDEO the reviewer must inspect the rendered MP4/contact sheet/mobile preview and answer:
- Would the first 3 seconds be skipped?
- Is every important UI/evidence region readable on a phone?
- Does each visual prove or advance the narration?
- Does the voice feel natural enough for the account identity?
- Do captions cover evidence?
- Does the video feel like a creator post rather than a corporate PPT?

## 7. REPAIRING

Repair only the failed layer. Maximum 3 rounds by default. A localized failure must not trigger a new platform architecture or new plugin installation.

## 8. READY_TO_PUBLISH

Only after pass may the final artifact be named `FINAL.*` and the publish pack be generated.

If quality remains below the contract, return `BLOCKED` with an explicit failure code and best candidate. Never return “75% complete” as success.
