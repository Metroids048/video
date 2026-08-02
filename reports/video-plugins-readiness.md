# Video Plugins Readiness

- generated_at: 2026-08-02T12:00:00+00:00
- chatcut_project: https://app.chatcut.io/editor/5f02e41f-5749-4548-bd40-7a706de4230c

## Automated results

| Step | OK | Notes |
|------|----|-------|
| vendor + overlays | PASS | third_party_skills + free overlays |
| hyperframes | PASS | 0.7.68 + browser |
| capcut-david | PASS | global CLI |
| chatcut-cli | PASS | `chatcut login` done by user |
| video-use + whisper | PASS | helpers + faster-whisper free default |
| remotion | PASS | skills vendored |
| seedance-free | PASS | FFmpeg Ken Burns adapter |
| openmontage | PASS | entry + AGENT_GUIDE |
| ip-strategist / cut-skill | PASS | skills present |

## Free substitutes (default)

| Paid | Free default | How |
|------|--------------|-----|
| ElevenLabs Scribe | faster-whisper | `helpers/transcribe.py --backend auto` → `scripts/free_providers/whisper_transcribe.py` |
| Seedance / Kie | seedance-free + OpenMontage + HyperFrames | `python scripts/free_providers/image_to_clip.py ...` |

## Optional paid upgrades

- ElevenLabs：仅当你要 Scribe 级说话人分离/更高准确率
- Kie Seedance：仅当你要生成式视频（非 Ken Burns）

## Re-run

```bash
npm run skills:ensure
```
