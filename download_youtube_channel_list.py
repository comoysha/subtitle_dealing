#!/usr/bin/env python3
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys


def build_command(channel_url: str, limit: int | None) -> list[str]:
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--dump-single-json",
        channel_url,
    ]
    if limit is not None:
        cmd.extend(["--playlist-end", str(limit)])
    return cmd


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return ""
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    return f"{hours} 时 {minutes} 分"


def format_upload_date(upload_date: str | None) -> str:
    if not upload_date or len(upload_date) != 8:
        return ""
    return f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"


def parse_entries(payload: dict) -> list[dict]:
    entries = payload.get("entries") or []
    if payload.get("_type") == "url" and payload.get("url"):
        return [payload]
    if not entries and payload.get("webpage_url"):
        return [payload]
    return [entry for entry in entries if entry]


def load_existing(output_path: str) -> set[str]:
    if not os.path.exists(output_path):
        return set()
    existing: set[str] = set()
    with open(output_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0].strip().lower() == "title" and len(row) >= 5:
                continue
            url = row[4].strip() if len(row) >= 5 else ""
            if url:
                existing.add(url)
    return existing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a YouTube creator's video list and write URLs to CSV."
    )
    parser.add_argument(
        "--channel-url",
        required=True,
        help="YouTube channel URL (use /videos for the videos tab if needed).",
    )
    parser.add_argument(
        "--output",
        default="youtube_dump.csv",
        help="CSV file path to write video metadata.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to CSV instead of overwriting and avoid duplicates.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of videos to fetch.",
    )
    args = parser.parse_args()

    if not shutil.which("yt-dlp"):
        print("Error: yt-dlp is not installed or not in PATH.", file=sys.stderr)
        return 1

    cmd = build_command(args.channel_url, args.limit)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: yt-dlp failed to fetch the list.", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        return result.returncode

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error: failed to parse yt-dlp JSON output.", file=sys.stderr)
        return 1

    entries = parse_entries(payload)
    if not entries:
        print("No video entries found.", file=sys.stderr)
        return 1

    existing = load_existing(args.output) if args.append else set()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    write_mode = "a" if args.append else "w"
    need_header = (
        not args.append
        or not os.path.exists(args.output)
        or os.path.getsize(args.output) == 0
    )
    fieldnames = ["title", "duration", "upload_date", "view_count", "webpage_url"]
    written = 0
    with open(args.output, write_mode, encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if need_header:
            writer.writeheader()
        for entry in entries:
            url = entry.get("webpage_url") or entry.get("url") or entry.get("id")
            if not url:
                continue
            if not str(url).startswith("http"):
                url = f"https://www.youtube.com/watch?v={url}"
            if args.append and url in existing:
                continue
            writer.writerow(
                {
                    "title": entry.get("title") or "",
                    "duration": format_duration(entry.get("duration")),
                    "upload_date": format_upload_date(entry.get("upload_date")),
                    "view_count": entry.get("view_count") or "",
                    "webpage_url": url,
                }
            )
            written += 1

    print(f"Wrote {written} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
