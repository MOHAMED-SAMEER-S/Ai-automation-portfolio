"""One small AI layer for both projects. Plain HTTP (httpx) with a hard timeout, so it
works with Claude, OpenAI or any OpenAI-compatible API (Gemini, Groq...) and never hangs.

If no key is set, or the API fails, the caller's own rule-based `fallback` runs instead,
so the automation never stops because an AI service is down.
"""
import json
import re

import httpx

from . import config


def real_provider() -> str | None:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        return "anthropic"
    if config.LLM_PROVIDER == "openai" and config.OPENAI_API_KEY:
        return "openai"
    return None


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"no JSON in AI output: {text[:120]!r}")
    return json.loads(match.group(0))


def _anthropic(system: str, user: str) -> str:
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
        json={"model": config.ANTHROPIC_MODEL, "max_tokens": 700, "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=config.LLM_TIMEOUT)
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def _openai_compatible(system: str, user: str, json_mode: bool) -> str:
    url = (config.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}
    body = {"model": config.OPENAI_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    r = None
    if json_mode:
        r = httpx.post(url, headers=headers, json={**body, "response_format": {"type": "json_object"}},
                       timeout=config.LLM_TIMEOUT)
    if r is None or r.status_code >= 400:   # some free providers have no JSON mode -> plain call
        r = httpx.post(url, headers=headers, json=body, timeout=config.LLM_TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call(provider: str, system: str, user: str, json_mode: bool) -> str:
    return _anthropic(system, user) if provider == "anthropic" else _openai_compatible(system, user, json_mode)


def ask_json(system: str, user: str, fallback) -> dict:
    """AI answer parsed as a dict, or fallback() if there is no key / the API fails.
    The result always has '_source': anthropic | openai | mock | mock (API failed)."""
    provider = real_provider()
    if provider:
        try:
            data = parse_json(_call(provider, system, user, True))
            data["_source"] = provider
            return data
        except Exception as exc:
            print(f"[ai] falling back to rules: {type(exc).__name__}: {exc}")
            data = fallback()
            data["_source"] = "mock (API failed)"
            return data
    data = fallback()
    data["_source"] = "mock"
    return data


def ask_text(system: str, user: str, fallback) -> tuple[str, str]:
    """Free-text AI answer -> (text, source)."""
    provider = real_provider()
    if provider:
        try:
            text = _call(provider, system, user, False).strip()
            if text:
                return text, provider
        except Exception as exc:
            print(f"[ai] falling back to template: {type(exc).__name__}: {exc}")
            return fallback(), "mock (API failed)"
    return fallback(), "mock"
