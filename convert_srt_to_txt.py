#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

INPUT_DIR = Path("download_srt")
OUTPUT_DIR = INPUT_DIR / "converted_txt"
CONVERTED_SRT_DIR = INPUT_DIR / "converted_srt"

ENCODING_CANDIDATES = [
    "utf-8",
    "utf-8-sig",
    "gb18030",
    "gbk",
    "big5",
    "big5hkscs",
]


def is_index_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.isdigit()


def is_timecode_line(line: str) -> bool:
    return "-->" in line


def srt_to_txt_lines(content: str) -> list[str]:
    lines: list[str] = []
    pending_blank = False
    for raw in content.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            pending_blank = True
            continue
        if is_index_line(line) or is_timecode_line(line):
            pending_blank = False
            continue
        if pending_blank and lines:
            lines.append("")
        pending_blank = False
        lines.append(line.strip())
    return lines


def read_srt_text(input_path: Path) -> str:
    raw = input_path.read_bytes()
    for enc in ENCODING_CANDIDATES:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def convert_file(input_path: Path, output_path: Path) -> None:
    text = read_srt_text(input_path)
    lines = srt_to_txt_lines(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + ("\n" if lines else ""), encoding="utf-8")


def main() -> int:
    if not INPUT_DIR.exists():
        raise SystemExit(f"Input directory not found: {INPUT_DIR}")
    input_files = sorted(INPUT_DIR.glob("*.srt"))
    if not input_files:
        raise SystemExit(f"No .srt files found under: {INPUT_DIR}")

    for input_path in input_files:
        output_path = OUTPUT_DIR / (input_path.stem + ".txt")
        convert_file(input_path, output_path)
        CONVERTED_SRT_DIR.mkdir(parents=True, exist_ok=True)
        input_path.replace(CONVERTED_SRT_DIR / input_path.name)
        print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
