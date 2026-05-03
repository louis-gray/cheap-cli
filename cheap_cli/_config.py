"""Resolve configuration from CLI flags > env vars > defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_LOG_PATH = "~/.local/share/cheap-cli/usage.jsonl"
DEFAULT_TIMEOUT = 120
VALID_REASONING = ("low", "medium", "high", "xhigh")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    reasoning: str | None
    log_path: str | None
    timeout: int


def resolve(
    *,
    cli_api_key: str | None = None,
    cli_model: str | None = None,
    cli_reasoning: str | None = None,
) -> Config:
    api_key = cli_api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ConfigError("OPENROUTER_API_KEY not set")

    model = cli_model or os.environ.get("CHEAP_MODEL") or DEFAULT_MODEL

    reasoning = cli_reasoning or os.environ.get("CHEAP_REASONING") or None
    if reasoning is not None and reasoning not in VALID_REASONING:
        raise ConfigError(f"invalid reasoning level: {reasoning}")

    log_env = os.environ.get("CHEAP_LOG", DEFAULT_LOG_PATH)
    log_path = None if log_env == "off" else os.path.expanduser(log_env)

    timeout = int(os.environ.get("CHEAP_TIMEOUT", DEFAULT_TIMEOUT))

    return Config(
        api_key=api_key,
        model=model,
        reasoning=reasoning,
        log_path=log_path,
        timeout=timeout,
    )
