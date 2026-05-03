"""OpenRouter streaming client + usage logging."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import httpx

from ._config import Config

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class APIError(Exception):
    pass


def build_messages(system: str, user: str) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def hash_args(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


def log_usage(
    *,
    log_path: str,
    tool: str,
    model: str,
    usage: dict,
    args_hash: str,
) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": tool,
        "model": model,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost_usd": usage.get("cost", 0.0),
        "args_hash": args_hash,
    }
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def stream_chat(
    cfg: Config,
    messages: list[dict],
    *,
    tool: str,
    args_hash: str,
) -> Iterator[str]:
    """Stream assistant content from OpenRouter. Yields content chunks.

    On completion, appends a usage entry to cfg.log_path (if set).
    Raises APIError on non-recoverable failures.
    """
    payload: dict = {
        "model": cfg.model,
        "messages": messages,
        "stream": True,
        "usage": {"include": True},
    }
    if cfg.reasoning:
        payload["reasoning"] = {"effort": cfg.reasoning}

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/grayscaled-dev/cheap-cli",
        "X-Title": "cheap-cli",
    }

    last_usage: dict | None = None
    succeeded = False

    for attempt in range(2):  # one retry on transient failure
        try:
            with httpx.Client(timeout=cfg.timeout) as client:
                with client.stream(
                    "POST", OPENROUTER_URL, json=payload, headers=headers
                ) as resp:
                    if resp.status_code == 401:
                        raise APIError("auth failed (401)")
                    if resp.status_code in (429,) or resp.status_code >= 500:
                        if attempt == 0:
                            time.sleep(2)
                            continue
                        body = b"".join(resp.iter_bytes()).decode(
                            "utf-8", errors="replace"
                        )[:500]
                        kind = "rate-limited, try later" if resp.status_code == 429 else f"provider error: {body}"
                        raise APIError(kind)
                    if resp.status_code >= 400:
                        body = b"".join(resp.iter_bytes()).decode(
                            "utf-8", errors="replace"
                        )[:500]
                        raise APIError(f"provider error: {body}")

                    for line in resp.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        usage = chunk.get("usage")
                        if usage:
                            last_usage = usage
                        for choice in chunk.get("choices", []):
                            delta = choice.get("delta", {}) or {}
                            content = delta.get("content")
                            if content:
                                yield content
            succeeded = True
            break
        except httpx.TimeoutException:
            if attempt == 0:
                continue
            raise APIError(f"timeout after {cfg.timeout}s")
        except httpx.HTTPError as e:
            raise APIError(str(e))

    if succeeded and last_usage and cfg.log_path:
        log_usage(
            log_path=cfg.log_path,
            tool=tool,
            model=cfg.model,
            usage=last_usage,
            args_hash=args_hash,
        )
