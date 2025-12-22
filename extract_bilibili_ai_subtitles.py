#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

DEFAULT_INPUT_DIR = Path("bilibili_subtitle_json_downloaded")
DEFAULT_OUTPUT_DIR = Path("bilibili_json_subtitle_to_txt")


def iter_contents(data: object) -> Iterable[str]:
    if isinstance(data, dict) and isinstance(data.get("body"), list):
        body = data["body"]
    elif isinstance(data, list):
        body = data
    else:
        body = []

    for item in body:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if content is None:
            continue
        line = str(content).strip("\n").strip()
        if not line:
            continue
        yield line


def convert_file(input_path: Path, output_path: Path) -> int:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    lines = list(iter_contents(data))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        if lines:
            f.write("\n".join(lines) + "\n")
        else:
            f.write("")
    return len(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract Bilibili AI subtitle JSON body[].content into .txt files. "
            f"Defaults: in-dir={DEFAULT_INPUT_DIR}, out-dir={DEFAULT_OUTPUT_DIR}"
        )
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Input .json file path(s) or filenames under in-dir (default: process all .json in in-dir).",
    )
    parser.add_argument(
        "--in-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing input .json files (default: subtitle_json).",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write output .txt files to (default: output_txt).",
    )
    parser.add_argument(
        "-o",
        "--out",
        help="Output .txt path override (only valid when there is exactly 1 input).",
    )
    return parser.parse_args()


def resolve_input_path(raw: str, in_dir: Path) -> Path:
    candidate = Path(raw)
    if candidate.exists():
        return candidate
    fallback = in_dir / raw
    if fallback.exists():
        return fallback
    return candidate


def main() -> int:
    args = parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)

    if args.inputs:
        input_paths = [resolve_input_path(p, in_dir) for p in args.inputs]
    else:
        if not in_dir.exists():
            raise SystemExit(f"Input directory not found: {in_dir}")
        input_paths = sorted(in_dir.glob("*.json"))
        if not input_paths:
            raise SystemExit(f"No .json files found under: {in_dir}")

    if args.out and len(input_paths) != 1:
        raise SystemExit("--out can only be used with exactly 1 input file.")

    for input_path in input_paths:
        if not input_path.exists():
            raise SystemExit(f"Input file not found: {input_path}")
        if input_path.suffix.lower() != ".json":
            raise SystemExit(f"Input file must be .json: {input_path}")

        output_path = (
            Path(args.out) if args.out else (out_dir / input_path.name).with_suffix(".txt")
        )
        line_count = convert_file(input_path, output_path)
        print(f"Wrote {output_path} ({line_count} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
