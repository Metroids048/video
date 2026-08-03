# Video Plugins Readiness

- generated_at: 2026-08-03T01:20:53.332240+00:00

## Automated results

| Step | OK | Notes |
|------|----|-------|
| vendor | PASS | [vendor] hyperframes ... [vendor] remotion ... [vendor] video-use ... [vendor] seedance ... [vendor] chatcut ... [vendor |
| hyperframes | PASS | hyperframes version rc=0 0.7.68 browser ensure rc=0 T  hyperframes browser ensure [?25l| o  Browser found [?25h    Sou |
| capcut-david | PASS | C:\Users\Windows11\AppData\Local\Programs\nodejs\capcut-david.CMD capcut-david — CapCut/JianYing draft CLI (fork of capc |
| chatcut-cli | PASS | chatcut on PATH: C:\Users\Windows11\AppData\Local\Programs\nodejs\chatcut.CMD |
| video-use-deps | PASS |   Stored in directory: C:\Users\Windows11\AppData\Local\Temp\pip-ephem-wheel-cache-c7q2sxpe\wheels\35\8d\e3\6e879919282a |
| remotion | PASS | @remotion/cli install rc=0 up to date, audited 365 packages in 10s  81 packages are looking for funding   run `npm fund` |
| cut-skill | PASS | skill present; pymiere pip rc=0 sts>=2.25->pymiere) (2026.6.17)  [notice] A new release of pip is available: 24.0 -> 26. |
| seedance | PASS | skill OK; tools_dir=True |
| free-providers | PASS | faster-whisper import rc=0 ok |
| openmontage | PASS | guide=True entry=True |
| ip-strategist | PASS | present=True |
| batch-manifest-skills | PASS | 11 skill trees present; mpt_agent.py OK |

## Needs user action

- （可选付费升级）ElevenLabs：仅当免费 Whisper 不够用时再配 ELEVENLABS_API_KEY
- （可选付费升级）Seedance/Kie：仅当需要生成式视频时再配 KIE_API_KEY；默认用 seedance-free（FFmpeg Ken Burns）或 OpenMontage
- （可选）Azure Speech：仅当明确要求神经语音时再配 Azure 凭证；默认 Edge TTS / Whisper
- （可选）Epidemic Sound：配置官方 MCP 并登录账号；无账号则标素材缺口，不伪造曲库
- ChatCut：若已 `chatcut login` 成功可忽略；Claude Code MCP 插件路径仍需 marketplace install 后新会话

## Re-run

```bash
npm run skills:ensure
```
