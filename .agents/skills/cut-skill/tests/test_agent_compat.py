"""Agent compatibility and skill metadata regression tests."""
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_skill_frontmatter_is_portable():
    text = read("SKILL.md")
    front = text.split("---", 2)[1]
    keys = []
    for line in front.splitlines():
        if line and not line.startswith(" ") and ":" in line:
            keys.append(line.split(":", 1)[0])
    allowed = {"name", "description", "license", "allowed-tools", "metadata"}
    assert set(keys) <= allowed, f"unexpected frontmatter keys: {set(keys) - allowed}"
    assert "name" in keys
    assert "description" in keys


def test_openai_skill_metadata_exists():
    meta = ROOT / "agents" / "openai.yaml"
    assert meta.exists(), "agents/openai.yaml should describe the skill for Codex/OpenAI UIs"
    text = meta.read_text(encoding="utf-8")
    assert "display_name:" in text
    assert "short_description:" in text
    assert "default_prompt:" in text


def test_agent_docs_use_real_tool_names():
    docs = [
        "agents/OPENCODE.md",
        "agents/GLM.md",
        "references/agent-integration.md",
    ]
    for rel in docs:
        text = read(rel)
        assert "cut.detect" not in text, f"{rel} references non-existent MCP tool cut.detect"
    assert "cut.list_backends" in read("agents/GLM.md")


def test_agent_install_paths_match_current_skill_conventions():
    installer = read("installer/src/agents.mjs")
    shell_installer = read("installer/install.sh")
    opencode_doc = read("agents/OPENCODE.md")
    qwen_doc = read("agents/QWEN.md")

    assert "'.agents', 'skills', 'cut'" in installer
    assert '$HOME/.agents/skills/cut' in shell_installer
    assert ".agents/skills/cut" in read("references/agent-integration.md")

    assert "'.config', 'opencode', 'skills', 'cut'" in installer
    assert "'.opencode', 'skills', 'cut'" in installer
    assert '$HOME/.config/opencode/skills/cut' in shell_installer
    assert './.opencode/skills/cut' in shell_installer
    assert "~/.config/opencode/skills/cut" in opencode_doc
    assert ".opencode/skills/" in opencode_doc

    assert "~/.qwen/skills/cut" in qwen_doc
    assert "'.qwen', 'skills', 'cut'" in installer
    assert "skills.json 加载 skill" not in qwen_doc


def main():
    test_skill_frontmatter_is_portable()
    print("[1] SKILL.md frontmatter portable")
    test_openai_skill_metadata_exists()
    print("[2] agents/openai.yaml exists")
    test_agent_docs_use_real_tool_names()
    print("[3] Agent docs use real MCP tool names")
    test_agent_install_paths_match_current_skill_conventions()
    print("[4] Agent install paths match current conventions")
    print("\nOK Agent compatibility tests passed")


if __name__ == "__main__":
    main()
