#!/usr/bin/env python3
import argparse
import csv
import os
import shutil
import subprocess
import sys


def read_urls(csv_path: str) -> list[str]:
    urls: list[str] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            url = row[0].strip()
            if not url or url.startswith("#"):
                continue
            urls.append(url)
    return urls


def run_yt_dlp(url: str, video_dir: str, srt_dir: str, download_video: bool) -> None:
    video_dir = os.path.abspath(video_dir)
    srt_dir = os.path.abspath(srt_dir)
    cmd = [
        "yt-dlp",
        "--write-subs",
        "--write-auto-subs",
        "--sub-format",
        "srt",
        "--paths",
        f"home:{video_dir}",
        "--paths",
        f"subtitle:{srt_dir}",
        url,
    ]
    if not download_video:
        cmd.insert(1, "--skip-download")

    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download YouTube videos from a CSV and save SRT subtitles."
    )
    parser.add_argument(
        "--csv",
        default="youtube_url.csv",
        help="CSV file path containing one URL per line.",
    )
    parser.add_argument(
        "--video-dir",
        default="input_video",
        help="Directory to save downloaded videos.",
    )
    parser.add_argument(
        "--srt-dir",
        default="download_srt",
        help="Directory to save downloaded SRT files.",
    )
    parser.add_argument(
        "--with-video",
        action="store_true",
        help="Download videos in addition to subtitles.",
    )
    args = parser.parse_args()

    if not shutil.which("yt-dlp"):
        print("Error: yt-dlp is not installed or not in PATH.", file=sys.stderr)
        return 1

    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}", file=sys.stderr)
        return 1

    os.makedirs(args.video_dir, exist_ok=True)
    os.makedirs(args.srt_dir, exist_ok=True)

    urls = read_urls(args.csv)
    if not urls:
        print("No URLs found in CSV.", file=sys.stderr)
        return 1

    for url in urls:
        try:
            run_yt_dlp(url, args.video_dir, args.srt_dir, args.with_video)
        except subprocess.CalledProcessError as exc:
            print(f"Failed: {url} (exit {exc.returncode})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
