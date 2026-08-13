"""Small command-line entry point for manual checks."""

import argparse
import json
import sys

from .client import OpenRouterClient
from .parser import extract, extract_with_provider


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract transactions from Thai text.")
    parser.add_argument("text", nargs="?", help="Input message; omit it to read stdin.")
    parser.add_argument("--model", help="OpenRouter model; defaults to MODEL_NAME.")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip the network and return the offline fallback contract.",
    )
    args = parser.parse_args()

    text = args.text
    if text is None:
        text = sys.stdin.read()

    if args.offline:
        result = extract(text)
    else:
        outcome = extract_with_provider(text, OpenRouterClient(model=args.model))
        result = outcome.response
        if outcome.status != "ok":
            print(f"status={outcome.status}", file=sys.stderr)

    print(json.dumps(result.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    main()

