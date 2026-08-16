"""Probe the configured Codex relay for OpenAI-compatible speech, without logging secrets."""
from __future__ import annotations

import json
import subprocess
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"
OUT = ROOT / "episodes" / "active" / "EP-20260812-01-V2" / "work" / "audio"
MODELS = ["gpt-4o-mini-tts-2025-12-15", "gpt-4o-mini-tts", "tts-1-hd", "tts-1"]
VOICE = "cedar"
SPEED = 1.08
PROBE_TEXT = "这是一次语音接口测试。"
INSTRUCTIONS = "使用自然的中国大陆普通话。像一个二三十岁的年轻男性，正常跟朋友介绍自己最近做的项目。轻松、自然、有一点兴奋感，但不要夸张。禁止播音腔、新闻腔、纪录片腔、客服腔、广告腔、短剧腔、故意压低声音、过度磁性、一句一句机械朗读。整体连贯，语速稍快，像真实口语。"


def safe_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def load_config() -> tuple[str, str, str, str]:
    config = tomllib.loads((CODEX_HOME / "config.toml").read_text(encoding="utf-8"))
    provider_name = str(config["model_provider"])
    provider = config["model_providers"][provider_name]
    base_url = safe_base_url(str(provider["base_url"]))
    auth = json.loads((CODEX_HOME / "auth.json").read_text(encoding="utf-8"))
    token = str(auth.get("OPENAI_API_KEY") or provider.get("experimental_bearer_token") or "")
    if not token:
        raise RuntimeError("No configured Codex credential")
    return str(provider.get("name", provider_name)), base_url, str(provider.get("wire_api", "")), token


def request(url: str, token: str, data: dict | None = None) -> tuple[int, bytes, str]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body is not None else "GET")
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        # Do not preserve or write response text; relays sometimes include account details.
        return exc.code, b"", exc.headers.get("Content-Type", "")
    except urllib.error.URLError:
        return 0, b"", ""


def is_audio(path: Path) -> bool:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "default=nk=1:nw=1", str(path)], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return False
    return "audio" in result.stdout


def main() -> int:
    provider, base_url, wire_api, token = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    models_status, _, _ = request(f"{base_url}/models", token)
    results = []
    success_model = None
    probe = OUT / "relay-tts-probe.wav"
    for model in MODELS:
        if success_model:
            break
        status, audio, content_type = request(f"{base_url}/audio/speech", token, {
            "model": model, "voice": VOICE, "speed": SPEED, "input": PROBE_TEXT,
            "response_format": "wav", "instructions": INSTRUCTIONS,
        })
        available = status == 200 and len(audio) > 44
        if available:
            probe.write_bytes(audio)
            available = is_audio(probe)
            if not available:
                probe.unlink(missing_ok=True)
        results.append({"model": model, "http_status": status, "valid_audio": available, "content_type": content_type.split(";", 1)[0]})
        if available:
            success_model = model
    final_supported = success_model in {"gpt-4o-mini-tts-2025-12-15", "gpt-4o-mini-tts"}
    report = {
        "provider": provider,
        "base_url": base_url,
        "wire_api": wire_api,
        "authentication_source": "Codex auth.json (in-memory only)",
        "models_http_status": models_status,
        "attempts": results,
        "successful_model": success_model,
        "ccswitch_tts_supported": final_supported,
        "status": "CCSWITCH_TTS_SUPPORTED" if final_supported else "BLOCKED_CCSWITCH_TTS_UNSUPPORTED",
    }
    (OUT / "ccswitch-tts-probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if final_supported else 2


if __name__ == "__main__":
    raise SystemExit(main())
