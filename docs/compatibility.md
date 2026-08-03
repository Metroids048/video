# 兼容性

| 项目 | 要求/行为 |
|---|---|
| Python | 3.11+，项目命令通过 `scripts/run-python.mjs` 使用当前环境 |
| Node.js | 22+ |
| 媒体工具 | FFmpeg / FFprobe；`avs doctor` 会检查 |
| 动效 | 锁定 HyperFrames `0.7.68`；失败时保留 FFmpeg 粗剪 |
| 镜头知识库 | 项目 vendor `third_party_skills/video-shotcraft` commit `d491544`（Apache-2.0，`reference_only`），仅作镜头语法/节奏/声音设计参考；其 Remotion 实现不进入 AVS 主渲染链 |
| 输出 | 1080×1920、30fps、H.264、AAC；两份 MP4 和 SRT |
| 平台 | 抖音、小红书竖屏交付，实际发布均由人完成 |
| 编辑器 | 交付 MP4、SRT、时间线 JSON/CSV 和素材副本，可导入或手工重建；不生成剪映工程草稿 |
| 参考链接 | 仅作为来源记录；第三方远程视频不自动下载 |

不同机器的编码输出不要求逐像素一致。验证比较元数据、可解码性和 QA 结果，而不是二进制完全相同。
