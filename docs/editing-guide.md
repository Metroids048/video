# 编辑说明

`delivery/` 是交给剪映或其他编辑器继续处理的自包含包，不是自动发布产物。

| 产物 | 用途 |
|---|---|
| `preview-clean.mp4` | 无字幕粗剪检查 |
| `preview-with-captions.mp4` | 字幕版粗剪检查 |
| `preview-with-motion.mp4` | 存在图文包装时的合成预览 |
| `captions.srt` | 可导入编辑器的字幕 |
| `timeline/timeline.json` 和 `.csv` | 可审查的镜头与时间线 |
| `assets-used/` | 成片实际使用的工作副本 |
| `qa-report.*`、`visual-review.md` | 质量证据和人工复核记录 |
| `edit-notes.md` | 占位卡、发布前检查和待补素材 |

发布前请完整播放并核对画面、音量、字幕安全区、事实、授权、标题和封面。替换所有占位卡后，由人手动发布；`REFERENCE_CLONE` 的交付包仅用于内部学习，禁止公开发布。
