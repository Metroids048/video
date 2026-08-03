# Third-party video skills (vendored copies)

Do not hand-edit unless fixing a pin. Regenerate with:

```bash
npm run skills:vendor
npm run skills:ensure   # vendor + overlays + CLI/deps smoke
```

Source of truth for URLs/commits: `vendor/manifests/video-third-party.yaml`.
Forced routing: `docs/video-plugin-routing.md`.

## Packages (selection)

| Dir | Role |
|-----|------|
| `hyperframes`, `hyperframes-cli` | 动效卡 |
| `remotion*`, `remotion-best-practices` | 代码驱动成片 |
| `video-use` | 对话式粗剪 / EDL |
| `seedance`, `seedance-free` | 即梦提示词 / 免费 Ken Burns |
| `chatcut/` | ChatCut MCP Skills |
| `capcut-david`, `cut-skill` | CapCut/剪映 CLI 链路 |
| `jianying-editor` | 剪映 JyWrapper（与 cut-skill 分流） |
| `ffmpeg` | FFmpeg 命令库 Skill |
| `azure-speech` | Azure Speech 知识 Skill |
| `elevenlabs`, `text-to-speech`, `music`, `sound-effects` | ElevenLabs 官方 Skills |
| `ai-video-shot-prompt` | 镜头脚本 |
| `ltx-prompt-director` | LTX-2.3 提示词导演 |
| `epidemic-sound` | Epidemic Sound MCP 薄入口（无上游 Skill 仓） |
| `moneyprinterturbo` | MPT Agent Skill（仅 `docs/skill` sparse） |
| `pixelle-video` | Pixelle 主题一键短视频（sparse docs + curated 入口） |
| `ip-strategist`, `openmontage` | 选题策略 / 多管线制片 |
| `video-shotcraft` | 镜头语法参考（`reference_only`） |
