# Repair Guide

Creator OS V2 does not treat manual editing as the default final stage. Repair is an internal production loop.

Use creator-review failure codes:

- `VOICE_BAD` → regenerate/remaster only narration/audio and retime dependent captions if needed.
- `HOOK_WEAK` → rebuild only the opening/Pilot.
- `SCREEN_UNREADABLE` → change ROI/crop/layout/callouts; keep story and audio unless timing requires a local adjustment.
- `CAPTION_BLOCKING` → change caption segmentation/placement only.
- `FACT_UNSUPPORTED` → repair the Evidence Map or remove the unsupported claim.
- `STORY_CONFUSED` → return to Creative Director and create a new Creative Contract version.
- `TECHNICAL_FAILURE` → rerender/fix the deterministic media problem.

Maximum default repair rounds: 3. After that, return `BLOCKED` with the best candidate and exact blocker instead of rebuilding the platform.
