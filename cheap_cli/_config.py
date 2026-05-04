"""Resolve configuration from CLI flags > env vars > OS keystore > defaults."""
from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_LOG_PATH = "~/.local/share/cheap-cli/usage.jsonl"
DEFAULT_TIMEOUT = 120
DEFAULT_KEYCHAIN_SERVICE = "openrouter"
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


def _keystore_lookup(args: list[str]) -> str | None:
    """Run a subprocess that prints the secret to stdout. Returns None on any failure."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _try_keychain() -> str | None:
    """OS keystore fallback. Returns None on Windows or any failure.

    macOS uses the system Keychain via `security`. Linux uses libsecret via
    `secret-tool` (gnome-keyring, KWallet, or any Secret Service provider).
    Windows is not auto-detected — set OPENROUTER_API_KEY explicitly.

    Service name defaults to 'openrouter' (override with CHEAP_KEYCHAIN_SERVICE).
    Account name is the current user (override with CHEAP_KEYCHAIN_ACCOUNT).
    """
    service = os.environ.get("CHEAP_KEYCHAIN_SERVICE", DEFAULT_KEYCHAIN_SERVICE)
    account = os.environ.get("CHEAP_KEYCHAIN_ACCOUNT") or os.environ.get("USER", "")
    if not account:
        return None
    system = platform.system()
    if system == "Darwin":
        return _keystore_lookup(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"]
        )
    if system == "Linux":
        return _keystore_lookup(
            ["secret-tool", "lookup", "service", service, "account", account]
        )
    return None


def resolve(
    *,
    cli_api_key: str | None = None,
    cli_model: str | None = None,
    cli_reasoning: str | None = None,
) -> Config:
    api_key = (
        cli_api_key
        or os.environ.get("OPENROUTER_API_KEY")
        or _try_keychain()
    )
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
