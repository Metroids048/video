---
name: create-motion-graphics
description: Create, patch, or place direct-authored Motion Graphic JSX through the Codex ChatCut tool surface.
---

# Create Motion Graphics

Codex's ChatCut workbench uses direct-authored Motion Graphics. It exposes `create_motion_graphic_from_code` instead of the paid `submit_motion_graphic` generator, so do not load or imitate the generator-only `motion-graphic-gen` workflow.

Before authoring, establish the content, intended timeline span, overlay versus full-frame role, and visual direction. Check the active Design Style and relevant composed frame when available. If style is unspecified and materially affects the result, use the `widget-forms` host adapter to align first.

Use `create_motion_graphic_from_code` for a new asset and `edit_asset` for existing JSX. Pass source inline through the tool; do not stage JSX in repository files, temporary files, local servers, or guessed backend workspaces. Follow the current tool descriptions for the full direct-authoring, natural-box, editable-property, and visual-mechanism constraints.

Keep visible text, colors, fonts, numbers, and media references editable when users may reasonably change them. Use renderer-supported fonts and project asset properties rather than hardcoded local fonts or media URLs. Give overlays a natural asset box; use timeline dimensions only when the design intentionally spans the frame.

Place or update timeline instances with `edit_item`. Re-read the affected item and inspect composed settled frames before claiming the graphic looks correct. A successful asset or timeline mutation is not visual proof.

For batches, make one representative graphic first unless the user already confirmed an active Design Style, preset, or accepted role anchor. Reuse an asset only for an intentionally recurring component with the same viewer task and information structure; shared palette or typography alone is not a reason to reuse one asset.
