"""summarize-cheap: compress a file/stream into a short summary."""
from __future__ import annotations

import argparse
import sys

from . import _client, _config, _io, _prompts


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="summarize-cheap",
        description="Summarise files or stdin via cheap LLM.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="File paths, '-' for stdin, or no args (= stdin)",
    )
    parser.add_argument("--bullets", type=int, help="Output as N bullet points")
    parser.add_argument("--max-words", type=int, help="Cap output at N words")
    parser.add_argument("--model", help="Override CHEAP_MODEL")
    parser.add_argument(
        "--reasoning",
        choices=["low", "medium", "high", "xhigh"],
        help="Reasoning effort (default: off)",
    )
    args = parser.parse_args()

    try:
        cfg = _config.resolve(cli_model=args.model, cli_reasoning=args.reasoning)
    except _config.ConfigError as e:
        print(f"cheap-cli: {e}", file=sys.stderr)
        return 1

    paths = args.files or ["-"]
    inputs = _io.read_inputs(paths)
    if not inputs:
        print("cheap-cli: no readable input", file=sys.stderr)
        return 1

    instructions = []
    if args.bullets:
        instructions.append(f"Reply as exactly {args.bullets} bullet points.")
    if args.max_words:
        instructions.append(f"Use at most {args.max_words} words total.")
    instructions.append("Content follows:")
    body = ["\n".join(instructions), ""]
    for label, content in inputs:
        body.append(f"=== {label} ===")
        body.append(content)
        body.append("")
    user = "\n".join(body)

    estimated = _io.estimate_tokens(user)
    context_limit = 1_000_000 if "v4" in cfg.model else 128_000
    if estimated > context_limit * 0.9:
        print(
            f"cheap-cli: input ~{estimated // 1000}k tokens, exceeds model "
            f"context ({context_limit // 1000}k). Split input or pass fewer files.",
            file=sys.stderr,
        )
        return 3

    args_hash = _client.hash_args(*(label for label, _ in inputs))

    try:
        for chunk in _client.stream_chat(
            cfg,
            _client.build_messages(_prompts.SUMMARIZE, user),
            tool="summarize-cheap",
            args_hash=args_hash,
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        sys.stdout.write("\n")
    except _client.APIError as e:
        print(f"cheap-cli: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
