# Creator OS V2

Creator OS V2 是面向真实创作者生产的多格式内容生产系统。它把文本、录屏、图片、音频、参考视频与事实材料组织成可发布的内容，并以 `READY_TO_PUBLISH` 作为唯一成功交付状态。

## 当前分支

本项目的 V2 工作分支为 `agent/creator-os-v2`。

## 核心生产链

```text
Input / Evidence
→ Research & Evidence
→ Creative Director
→ Format Router
→ Production
→ Creative QA
→ Repair
→ READY_TO_PUBLISH
```

默认优先真实素材和真实证据。对于录屏纪录片类内容：

- 首 3 秒必须出现真实证据；
- 不使用企业 PPT 式片头；
- 横屏录屏必须通过移动端可读的 ROI / 局部聚焦呈现；
- 旁白音轨是字幕、镜头切换和节奏的主时钟；
- 成片必须实际观看后才能通过 Creative Gate；
- 若还需要用户进入剪映继续补救，则状态必须保持 `BLOCKED`，不能标成完成。

## 第一期保留素材

V2 只保留第一期“7×24 自动交易”作为 Golden Episode 素材来源；旧量化视频草稿、一次性构建脚本、旧完成报告和失败版本不再属于 V2。

> 注意：历史 main 分支中这批原始媒体没有提交到 GitHub，因此 V2 会把已恢复的核心素材重新归档到 `第一期视频_7x24自动交易/`。不要再从旧 main 的历史草稿目录复制文件回来。

## 验证

```bash
python scripts/validate_creator_os_v2.py
python -m pytest -q
```

GitHub Actions：`.github/workflows/creator-os-v2-verify.yml`。

## 能力资源

以下能力资产继续保留并复用：

- `skills-src/`
- `third_party_skills/`
- `.agents/skills/`
- `.claude/skills/`
- `vendor/`
- `skills.lock.json`

插件和 Skills 不是 V2 这次重构的删除目标；V2 主要收口项目配置、工作流、质量门禁和作品目录。
