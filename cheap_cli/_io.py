"""File and URL reading helpers with binary detection and stdin sentinel."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx


def is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def is_binary(path: Path, sample_size: int = 8192) -> bool:
    try:
        sample = path.read_bytes()[:sample_size]
    except OSError:
        return True
    return b"\x00" in sample


_SCRIPT_OR_STYLE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def html_to_text(html: str) -> str:
    """Cheap HTML → plain text. Strips script/style + tags, collapses whitespace.

    Good enough for static vendor docs and blog posts. SPA pages that render
    client-side will return mostly nav cruft — Claude's WebFetch is the right
    tool for those.
    """
    text = _SCRIPT_OR_STYLE.sub(" ", html)
    text = _TAG.sub(" ", text)
    return _WS.sub(" ", text).strip()


def fetch_url(url: str, timeout: int = 30) -> tuple[str, str]:
    """Fetch URL, return (label, content). HTML is stripped to plain text."""
    resp = httpx.get(
        url,
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": "cheap-cli/0.1 (+https://github.com/grayscaled-dev/cheap-cli)"},
    )
    resp.raise_for_status()
    body = resp.text
    ctype = resp.headers.get("content-type", "").lower()
    if "html" in ctype:
        body = html_to_text(body)
    return (url, body)


def read_inputs(paths: list[str]) -> list[tuple[str, str]]:
    """Read paths into (label, content) tuples.

    A path of '-' reads from stdin, labeled '<stdin>'.
    URLs (http://, https://) are fetched; HTML is stripped to plain text.
    Missing files and binary files are skipped with a stderr warning.
    """
    out: list[tuple[str, str]] = []
    for raw in paths:
        if raw == "-":
            out.append(("<stdin>", sys.stdin.read()))
            continue
        if is_url(raw):
            try:
                out.append(fetch_url(raw))
            except httpx.HTTPError as e:
                print(f"cheap-cli: fetch failed for {raw}: {e}", file=sys.stderr)
            continue
        p = Path(raw)
        if not p.exists():
            print(f"cheap-cli: file not found: {raw}", file=sys.stderr)
            continue
        if is_binary(p):
            print(f"cheap-cli: skipping binary file {raw}", file=sys.stderr)
            continue
        out.append((str(p), p.read_text(encoding="utf-8", errors="replace")))
    return out


def estimate_tokens(text: str) -> int:
    return len(text) // 4
