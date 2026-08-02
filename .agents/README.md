# Codex Project Skills

项目 Skill 的唯一编辑源是 `skills-src/`。运行 `npm run skills:sync` 后，Codex 从 `.agents/skills/` 读取同步副本。不要直接编辑同步目标。

第三方视频 Skills 的可提交副本在 `third_party_skills/`，由 `npm run skills:vendor` 同步到 `.agents/skills/` 与 `.claude/skills/`。路由表见 `docs/video-plugin-routing.md`。
