# 排障

| 现象 | 检查与处理 |
|---|---|
| `WAITING_FOR_INPUT` | 补充 `input/` 中缺少的文本或媒体，再运行 `avs ingest <ID>` |
| `workflow resume` 停在 `agent` | 使用 `write-video-script`、`create-storyboard`，随后运行 `avs content validate` 和 `avs content approve` |
| 停在 `human` 的 assets | 检查 `missing-assets.md`、素材权利和版式，再运行 `avs assets approve` |
| `reference analyze` 找不到参考 | 只支持放入 `input/reference/` 的本地视频；URL 仅作来源记录，不会下载 |
| HyperFrames 失败 | 基础 FFmpeg 粗剪必须保留；运行 `npm run doctor`、`npx hyperframes lint renderers/hyperframes` 检查 |
| QA 未通过 | 阅读 `delivery/qa-report.md` 和联系表，修正素材/时间线后按需使用 `--force` 重建 |
| 状态为 `FAILED` | 阅读 `episode.json` 的 `last_error`，修复原因后使用受限的 `avs episode reset --to <状态> --force` |

不要手工修改 `episode.json` 来跳过状态，也不要覆盖 `input/` 原始媒体。若需要重新生成已有产物，显式使用对应命令的 `--force`。
