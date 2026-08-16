# Creator OS V2

Creator OS V2 是面向真实创作者生产的多格式内容生产系统。它把文本、录屏、图片、音频、参考视频与事实材料组织成可发布的内容，并以 `READY_TO_PUBLISH` 作为唯一成功交付状态。

## 当前分支

V2 工作分支：`agent/creator-os-v2`。

本地迁移只采用一种方式：**使用经过 CI 验证的完整 V2 项目包替换旧 `video` 文件夹**。不再维护本地清理脚本，也不要求从旧目录逐项搬运历史文件。

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

历史 `main` 从未跟踪这批原始二进制媒体，所以 V2 在 Git 中锁定 `第一期视频_7x24自动交易/source-manifest.json`；完整本地项目包负责携带真实 `原始录屏.mp4` 与最终交付物。不要再从旧 `main` 的历史草稿目录复制文件回来。

## 验证

```bash
python scripts/validate_creator_os_v2.py
python -m pytest -q
```

GitHub Actions：`.github/workflows/creator-os-v2-verify.yml`。只有合同校验和完整测试都通过后，CI 才会打包 verified project snapshot。

## 能力资源

以下能力资产继续保留并复用：

- `skills-src/`
- `third_party_skills/`
- `.agents/skills/`
- `.claude/skills/`
- `vendor/`
- `skills.lock.json`

插件和 Skills 不是 V2 重构的删除目标；V2 收口的是项目配置、工作流、质量门禁和历史作品残留。
