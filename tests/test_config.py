import os
import pytest
from cheap_cli._config import resolve, Config, ConfigError, DEFAULT_MODEL


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY not set"):
        resolve()


def test_env_only_uses_defaults(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.delenv("CHEAP_MODEL", raising=False)
    monkeypatch.delenv("CHEAP_REASONING", raising=False)
    monkeypatch.delenv("CHEAP_LOG", raising=False)
    cfg = resolve()
    assert cfg.api_key == "sk-test"
    assert cfg.model == DEFAULT_MODEL
    assert cfg.reasoning is None
    assert cfg.log_path.endswith("/cheap-cli/usage.jsonl")
    assert cfg.timeout == 120


def test_cli_flag_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-env")
    monkeypatch.setenv("CHEAP_MODEL", "from-env")
    cfg = resolve(cli_model="from-flag")
    assert cfg.model == "from-flag"


def test_log_off_disables_logging(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("CHEAP_LOG", "off")
    cfg = resolve()
    assert cfg.log_path is None


def test_invalid_reasoning_raises(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    with pytest.raises(ConfigError, match="invalid reasoning"):
        resolve(cli_reasoning="ultra")


def test_valid_reasoning_levels(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    for level in ("low", "medium", "high", "xhigh"):
        cfg = resolve(cli_reasoning=level)
        assert cfg.reasoning == level
