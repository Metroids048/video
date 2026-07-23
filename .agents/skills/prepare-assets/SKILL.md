---
trigger: "用户提供了输入素材，需要接收并标准化这些素材"
inputs:
  - "episodes/active/<ID>/input/（任意支持类型的文件）"
  - "episodes/active/<ID>/episode.json（状态必须为 CREATED 或 INGESTED）"
read_only:
  - "AGENTS.md"
  - "schemas/asset-manifest.schema.json"
  - "episodes/active/<ID>/input/（只读，绝不修改原始文件）"
outputs:
  - "episodes/active/<ID>/work/asset-manifest.json"
  - "episodes/active/<ID>/work/prepared/（标准化工作副本）"
  - "episodes/active/<ID>/logs/ingest.log"
run: |
  python -m avs ingest <ID>
verify: |
  python -m avs assets validate <ID>
  python -m avs episode status <ID>
stop_when: |
  asset-manifest.json 通过 Schema 校验，
  Episode 状态为 INGESTED，
  原始文件 SHA-256 与 ingest 前完全相同
on_missing_input: |
  input/ 为空时：创建空 manifest，Episode 进入 WAITING_FOR_INPUT，
  提示用户将文件放入 input/ 后重新运行
report_format: |
  - 识别的文件列表（类型、路径、大小）
  - FFprobe 摘要（时长、尺寸、fps、音轨）
  - 损坏文件清单（如有）
  - 横屏素材代理生成情况
  - 原始文件 SHA-256 校验结果
  - 命令与返回码
  - Episode 最终状态
---

# prepare-assets Skill

安全识别、校验和标准化用户放入 `input/` 的文件，生成 `asset-manifest.json`。

## 支持的输入类型

- 文本：`.txt`, `.md`
- 图片：`.png`, `.jpg`, `.webp`
- 视频：`.mp4`, `.mov`, `.mkv`, `.webm`
- 音频：`.wav`, `.mp3`, `.m4a`
- 链接：`links.txt`（每行一个 URL）

## 约束

- **原始文件绝不修改、重命名或移动**
- 所有加工使用工作副本（`work/prepared/`）
- 横屏素材必须明确选择 contain / cover，不能静默拉伸
- 损坏文件标记为 `status: "corrupt"`，不进入下游
- 幂等：文件未变化时复用已处理结果
- `--force` 可强制重新处理
