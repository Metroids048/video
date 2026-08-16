# EP-20260812-01 V1 negative fixture

This fixture intentionally captures the rejected V1. It is a regression target,
not a publishable asset. The full 76.9s render and 184s source stay local; the
fixture keeps only the first 10s, compact frames, a phone preview, labels, and
hashes of the complete local evidence set.

Expected regression failures:

- title/PPT card in the first three seconds;
- blank pale-green grid and static runs;
- landscape UI reduced below mobile readability;
- captions becoming the visual subject and obscuring evidence;
- generated card overuse and underuse of real Binance evidence.

The inspection timestamps are `0`, `0.5`, `1`, `2`, `3`, `5`, then every second
through `10`, matching the failure retrospective.
