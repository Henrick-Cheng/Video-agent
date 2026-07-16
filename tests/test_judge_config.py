"""Judge endpoint resolution — the dual-judge (qwen daily / gpt final) switch.

A gpt-* JUDGE_MODEL alone must select the OpenAI endpoint and fall back to
OPENAI_API_KEY, while leaving the default (no env) path on the DashScope
config; explicit JUDGE_BASE_URL/JUDGE_API_KEY must still win. Guards against
the footgun of sending an OpenAI key to the DashScope endpoint.
"""
from __future__ import annotations

from src.eval.run_benchmark import _judge_client, _judge_model


def test_default_judge_uses_active_llm_config(monkeypatch):
    for var in ("JUDGE_MODEL", "JUDGE_BASE_URL", "JUDGE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    from src.config import get_settings
    cfg = get_settings()
    client = _judge_client()
    assert _judge_model() == cfg.active_llm.model_name
    assert str(client.base_url).rstrip("/") == cfg.active_llm.base_url.rstrip("/")


def test_gpt_judge_model_selects_openai_profile(monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", "gpt-4-turbo")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.delenv("JUDGE_BASE_URL", raising=False)
    monkeypatch.delenv("JUDGE_API_KEY", raising=False)
    client = _judge_client()
    assert "api.openai.com" in str(client.base_url)
    assert client.api_key == "sk-test-openai"


def test_explicit_judge_env_overrides_gpt_profile(monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", "gpt-4o")
    monkeypatch.setenv("JUDGE_BASE_URL", "https://proxy.example.com/v1")
    monkeypatch.setenv("JUDGE_API_KEY", "sk-proxy")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    client = _judge_client()
    assert "proxy.example.com" in str(client.base_url)
    assert client.api_key == "sk-proxy"
