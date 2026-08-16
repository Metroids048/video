# Creator OS V2 Troubleshooting

| Symptom | Check / action |
|---|---|
| `WAITING_FOR_RESOURCE` / engine `WAITING_FOR_INPUT` | Supply the missing factual source, privacy boundary, inaccessible required asset or provider credential. Do not manufacture filler evidence. |
| Douyin reference cannot be acquired | Keep the URL/source metadata, mark it page-only, and continue with other usable references/original direction. Never infer audiovisual details that were not inspected. |
| Reference analysis has a local video but fails | Check decode/ffprobe/transcription dependencies, then rerun only reference analysis. |
| No voice profile exists | Run the one-time 15–20s audition for HUMAN_ENHANCED / HYBRID_S2S / PREMIUM_TTS. Do not silently choose a random final voice. |
| Voice sounds synthetic or unnatural | Return `VOICE_BAD` and repair audio only; keep the Creative Contract unless the story itself failed. |
| Desktop recording is unreadable on mobile | Return `SCREEN_UNREADABLE`; use establish → ROI focus/zoom or screen-stack. Do not use full 16:9 contain with black bars. |
| Captions cover balances/charts/orders/primary proof | Return `CAPTION_BLOCKING`; change segmentation/position only. |
| Hook is weak | Repair the Hook/Pilot before full rerender. Do not rebuild the whole workflow. |
| Story is confusing | Return `STORY_CONFUSED`; create a new Creative Contract version before further production. |
| HyperFrames/Remotion/other optional renderer fails | Use another appropriate execution route or deterministic FFmpeg assembly; record the failure. Never convert renderer failure into fake publish success. |
| Technical QA fails | Fix the deterministic media problem and rerun the affected render/review stage. |
| Three repair rounds are exhausted | Return `BLOCKED` with exact failure code and best candidate. Do not install more plugins or rebuild architecture as a reflex. |
| Engine state is `FAILED` | Read `episode.json:last_error`; use supported reset/recovery commands. Never hand-edit state to skip gates. |

Original Episode input media is immutable. Derived crops, redactions, audio processing and renders belong in work/output locations, never overwriting the source.
