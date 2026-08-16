# EP01 Final Lock: Durable Video Rules

- TTS text, canonical script, and visible caption text are independent sources.
- Captions preserve visual forms such as `7×24`, `5000U`, `7350U`, `AI`, `Codex`, `Claude Code`, and `Binance`; never derive their text from ASR.
- When a user-approved voice is found, retain provider, voice ID, model, speed, source version, and source hash in `voice-lock.json`. Do not silently fall back.
- Render system screen recordings with FIT/CONTAIN. Do not crop merely to fill the output canvas.
- Treat the source screen-recording sequence as the visual master timeline, except for an explicitly documented cold open.
- Keep system UI as the visual subject. Captions are supporting text, not title cards.
- Prefer loaded Binance/Testnet evidence over generated proof graphics. Show account, positions, and order evidence on the real exchange page.
- Preserve `Why No Trade` in the UI while narrating it naturally in Chinese as why an order was not opened.
- Require a scene map tying every important narration segment to an appropriate real screen state.
- Completion is the playable final MP4 and a visual review, not passing tests or workflow metadata.
