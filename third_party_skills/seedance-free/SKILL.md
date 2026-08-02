---
name: seedance-free
description: >
  【免费 Seedance 平替】不调用 Kie/付费 Seedance API。
  用本机 FFmpeg Ken Burns 把参考图做成竖屏短镜头；需要真实动态素材时改走 OpenMontage 纪录片蒙太奇；
  需要 HTML 动效时走 HyperFrames。仍可用原 seedance skill 只写提示词给即梦网页免费额度。
trigger: 免费图生视频、不用付费 Seedance、Ken Burns、无 API Key 出片
inputs: []
read_only:
  - input/
outputs: []
run: "python scripts/free_providers/image_to_clip.py <images> -o <out> --size 1080x1920"
verify: "输出 MP4 可被 ffprobe 解码"
stop_when: "用户停止或素材缺失"
on_missing_input: "列出缺口；不调用付费 API"
report_format: "命令、退出码、产物路径、已知限制"
---

# Seedance 免费平替

付费路径（Kie Seedance ≈ $0.165/秒）**不是必须的**。默认走本 skill。

## 平替矩阵

| 需求 | 免费做法 | 命令 / Skill |
|------|----------|--------------|
| 参考图 → 运动短镜头 | FFmpeg Ken Burns | `python scripts/free_providers/image_to_clip.py img.jpg -o out.mp4` |
| 多图成片竖屏 | 上式批量 + AVS/FFmpeg 拼接 | 同上 `-o outdir/` |
| 真实动态 B-roll | OpenMontage 纪录片蒙太奇（免费素材库） | `openmontage` |
| 标题/信息卡动效 | HyperFrames | `hyperframes` |
| 只要提示词（去即梦网页免费额度） | 原 `seedance` skill **只写 prompt，不调 Kie** | `seedance` |

## 示例

```bash
python scripts/free_providers/image_to_clip.py references/shot1.jpg -o work/clip1.mp4 --duration 4 --size 1080x1920
```

产物挂到 Episode `work/` / `output/`，再进 `timeline.json` / 粗剪。

## 限制

- Ken Burns 是镜头运动，不是 Seedance 级生成视频。
- 本地开源大模型（Wan/LTX/Hunyuan）需高显存，本仓库不默认安装；需要时另开模块。
- 即梦网页免费额度仍属厂商活动，与 Kie 付费 API 无关。
