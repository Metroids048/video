# Claude Code project instructions

The canonical project contract is `AGENTS.md`. Read and follow it before any content-production or project-modification task.

Key rules:
- Product is **Creator OS V2**.
- Existing Skills/plugins/vendor resources are frozen unless the user explicitly asks to change them.
- One Creative Director/Creative Contract owns story, Hook, format, voice mode and visual direction.
- Output format is `VIDEO | CAROUSEL | TEXT`.
- Douyin URLs are first-class reference inputs with honest acquisition fallback.
- For video, locked narration is the timing authority; never use character-count subtitle timing.
- Landscape software/screen recordings default to `fit_full_frame` / `contain`. Preserving the complete source page outranks filling the 9:16 canvas.
- `screen_focus`, `roi_crop`, `cover`, `screen_stack`, or equivalent destructive crop require explicit `allow_destructive_crop=true`; otherwise fall back to full-frame.
- VIDEO cannot be approved, named FINAL, packaged, or delivered until the actual source artifacts have been compared against the exact CURRENT final MP4 and the validated `work/qa/video-release-review.json` is `READY_TO_PUBLISH` for the current final SHA256 **and current source SHA256 values**.
- Source-to-final review must verify full-frame integrity, page/context identity, spatial continuity, temporal/action continuity, and intentional opening context.
- The reviewer must then watch the current MP4 start-to-end at 1x with audio, densely inspect frame zero/first 10 seconds, scan every transition, and check the temporary 360x640 QA view.
- Contact sheets, sparse keyframes, ffprobe, metadata, cut counts, test success, user opinion, or self-authored PASS JSON never substitute for source fidelity + actual viewing.
- Unauthorized destructive crop, source context loss, spatial/temporal discontinuity, mid-action/partial opening, slideshow/Ken-Burns motion, unreadable evidence, repeated dark/light flashing, unmotivated hard cuts, or key proof needing pause/replay are hard failures and route to REPAIRING.
- After any source change or rerender, old approval/release review is stale: recompute affected SHA256 values and repeat source-to-final review plus the full release review.
- Maximum default repair rounds: 3, then `BLOCKED` with the unresolved reason.
- 360x640 is QA-only; formal video delivery is one 1080x1920 master.
- Only `READY_TO_PUBLISH` is success; if manual re-edit is required, return `BLOCKED`.
- Do not recreate deleted EP01/quant one-off builders or historical completion reports.

Before delivering VIDEO, read `docs/creator-os/video-pre-delivery-qa-prompt.md`, write `work/qa/video-release-review.input.json`, and run:

```bash
python scripts/validate_video_release_review.py <episode-dir>
```

A non-zero exit blocks approval and delivery.

Read `docs/creator-os-v2.md` and `docs/workflow-v2.md` for the concise architecture and workflow.
