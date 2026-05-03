"""write-cheap: generate boilerplate to stdout."""
from __future__ import annotations

import argparse
import sys

from . import _client, _config, _prompts


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="write-cheap",
        description="Generate boilerplate code/text via cheap LLM. Output goes to stdout.",
    )
    parser.add_argument("description", help="What to generate")
    parser.add_argument("--lang", help="Optional language hint (e.g. python, fish, sql)")
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

    user = args.description
    if args.lang:
        user = f"Language: {args.lang}\n\n{args.description}"

    args_hash = _client.hash_args(args.description, args.lang or "")

    try:
        for chunk in _client.stream_chat(
            cfg,
            _client.build_messages(_prompts.WRITE, user),
            tool="write-cheap",
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
