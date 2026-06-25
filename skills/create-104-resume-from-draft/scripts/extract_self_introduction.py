#!/usr/bin/env python3
"""Extract the exact 104 introduction body from a job-application Markdown file."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def extract_body(text: str) -> str:
    lines = text.splitlines()

    heading_index = next(
        (
            i
            for i, line in enumerate(lines)
            if line.startswith("# ")
            and ("Self Introduction" in line or "自我介紹" in line)
        ),
        None,
    )
    if heading_index is None:
        raise ValueError("No Self Introduction/自我介紹 heading found")

    separators = [
        i for i in range(heading_index + 1, len(lines)) if lines[i].strip() == "---"
    ]
    if len(separators) < 2:
        raise ValueError("Expected the introduction body between two '---' separators")

    body = "\n".join(lines[separators[0] + 1 : separators[1]]).strip()
    if not body:
        raise ValueError("The self-introduction body is empty")
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--max-chars", type=int, default=1000)
    args = parser.parse_args()

    try:
        source = args.path.expanduser().resolve()
        body = extract_body(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    count = len(body)
    if count > args.max_chars:
        print(
            f"error: introduction is {count} characters; limit is {args.max_chars}",
            file=sys.stderr,
        )
        return 2

    if args.as_json:
        print(
            json.dumps(
                {
                    "path": str(source),
                    "char_count": count,
                    "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    "text": body,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
