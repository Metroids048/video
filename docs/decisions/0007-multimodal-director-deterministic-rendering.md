# ADR-0007: Multimodal Director and Deterministic Rendering

Status: Accepted

## Context

The legacy publish path selected the first asset in a storyboard scene and
rendered static contain/pad segments. It could produce a decodable MP4 without
proving that narration, product facts, source assets, and visible UI regions
matched.

## Decision

Publishable Episodes use one active path:

`create -> ingest -> analyze -> plan -> preview -> visual-review -> final-render -> qa -> approve -> deliver -> export`

`episode.json` remains the workflow state source and `timeline.json` remains
the renderer protocol. `work/input-manifest.json` records user intent and media
roles. Asset intelligence, the creative brief, reference selection, evidence
map, and shot plan are Episode artifacts, not a second state system.

The multimodal provider may understand screenshots and recordings, but it may
not generate replacement product evidence. FFmpeg renders deterministic shot
primitives. A publishable run fails closed when required input, concrete
reference pattern IDs, evidence bindings, semantic visual review, or current
human approval is missing.

Legacy timeline and rough-render commands remain available for internal filter
and compatibility tests. They cannot independently qualify an Active Episode
for delivery.

## Consequences

- Multiple bound assets expand into observable atomic shots.
- Horizontal recording proxies do not bake in contain letterboxing; original
  dimensions remain in the manifest for ROI planning.
- Audio roles come from the input manifest on the Active path.
- Approval binds the input, script, evidence map, shot plan, timeline, and final
  video fingerprint.
- Visual review samples the actual video and permits one targeted retry.
- Without a real vision provider, the Episode is BLOCKED and cannot be
  delivered.
