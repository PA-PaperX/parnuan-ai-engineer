"""Small command-line entry point for manual checks."""

import argparse
import json

from .parser import extract


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract transactions from Thai text.")
    parser.add_argument("text", nargs="?", help="Input message; omit it to read stdin.")
    args = parser.parse_args()

    text = args.text
    if text is None:
        text = input()

    result = extract(text)
    print(json.dumps(result.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    main()

