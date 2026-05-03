"""File reading helpers with binary detection and stdin sentinel."""
from __future__ import annotations

import sys
from pathlib import Path


def is_binary(path: Path, sample_size: int = 8192) -> bool:
    try:
        sample = path.read_bytes()[:sample_size]
    except OSError:
        return True
    return b"\x00" in sample


def read_inputs(paths: list[str]) -> list[tuple[str, str]]:
    """Read paths into (label, content) tuples.

    A path of '-' reads from stdin, labeled '<stdin>'.
    Missing files and binary files are skipped with a stderr warning.
    """
    out: list[tuple[str, str]] = []
    for raw in paths:
        if raw == "-":
            out.append(("<stdin>", sys.stdin.read()))
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
