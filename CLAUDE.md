# Claude Code project instructions

The canonical project contract is `AGENTS.md`. Read and follow it before any content-production or project-modification task.

Key rules:
- Product is **Creator OS V2**, not Agent Video Studio V1.
- Existing Skills/plugins/vendor resources are frozen unless the user explicitly asks to change them.
- One Creative Director/Creative Contract owns story, Hook, format, voice mode and visual direction.
- Output format is `VIDEO | CAROUSEL | TEXT`.
- Douyin URLs are first-class reference inputs with honest acquisition fallback.
- For video, locked narration is the timing authority; never use character-count subtitle timing.
- VIDEO cannot be approved, named FINAL, packaged, or delivered until the exact current MP4 has passed `config/video-review.yaml` and the validated `work/qa/video-release-review.json` is `READY_TO_PUBLISH` for the current SHA256.
- The reviewer must actually watch the current MP4 start-to-end at 1x with audio, densely inspect the first second/first 10 seconds, scan every transition, and check the 360x640 mobile view. Contact sheets, sparse keyframes, ffprobe, metadata, cut counts, test success, or self-authored PASS JSON never substitute for that viewing.
- Slideshow/Ken-Burns screenshot motion, unreadable short-dwell evidence, discontinuous opening, repeated dark/light flashing, unmotivated hard cuts, or any key proof that needs pause/replay are hard failures and route to REPAIRING.
- After any repair/rerender, old approval is stale: recompute SHA256 and repeat the full release review. Maximum default repair rounds: 3, then `BLOCKED` with the unresolved reason.
- Only `READY_TO_PUBLISH` is success; if manual re-edit is required, return `BLOCKED`.
- Do not recreate deleted EP01/quant one-off builders or historical completion reports.

Before delivering VIDEO, read `docs/creator-os/video-pre-delivery-qa-prompt.md`, write `work/qa/video-release-review.input.json`, and run:

```bash
python scripts/validate_video_release_review.py <episode-dir>
```

A non-zero exit blocks approval and delivery.

Read `docs/creator-os-v2.md` and `docs/workflow-v2.md` for the concise architecture and workflow.
