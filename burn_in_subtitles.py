#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys
from pathlib import Path


VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".m4v", ".webm", ".ts", ".mpeg", ".mpg"}


def ffmpeg_filter_escape_path(path: str) -> str:
    """
    Escape a path for use inside ffmpeg filter arguments (e.g. subtitles=...).
    This is not shell-escaping; it targets ffmpeg's filter-argument parser.
    """
    return (
        path.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("[", r"\[")
        .replace("]", r"\]")
        .replace(",", r"\,")
    )


def build_default_out_path(video_path: Path) -> Path:
    suffix = video_path.suffix if video_path.suffix else ".mp4"
    return video_path.with_name(f"{video_path.stem}_hardsub{suffix}")


def run_ffmpeg(video: Path, srt: Path, out: Path, crf: int, preset: str, force: bool) -> None:
    if out.exists() and not force:
        raise FileExistsError(f"Output already exists: {out} (use --force to overwrite)")

    out.parent.mkdir(parents=True, exist_ok=True)

    video_str = str(video)
    srt_str = str(srt)

    subtitles_filter = f"subtitles='{ffmpeg_filter_escape_path(srt_str)}':charenc=UTF-8"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y" if force else "-n",
        "-i",
        video_str,
        "-vf",
        subtitles_filter,
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(out),
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Burn (hardcode) an SRT subtitle file into a video using ffmpeg."
    )
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument("--srt", required=True, help="Path to .srt subtitle file")
    parser.add_argument("--out", help="Path to output video file (default: <video>_hardsub.<ext>)")
    parser.add_argument("--crf", type=int, default=18, help="x264 CRF quality (lower is better, default: 18)")
    parser.add_argument("--preset", default="medium", help="x264 preset (default: medium)")
    parser.add_argument("--force", action="store_true", help="Overwrite output if exists")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if not shutil_which("ffmpeg"):
        print("Error: ffmpeg not found. Please install ffmpeg and try again.", file=sys.stderr)
        return 127

    video = Path(args.video).expanduser().resolve()
    srt = Path(args.srt).expanduser().resolve()
    out = Path(args.out).expanduser().resolve() if args.out else build_default_out_path(video)

    if not video.exists():
        print(f"Error: video not found: {video}", file=sys.stderr)
        return 2
    if not srt.exists():
        print(f"Error: srt not found: {srt}", file=sys.stderr)
        return 2
    if video.suffix.lower() not in VIDEO_EXTS:
        print(f"Warning: video extension looks uncommon: {video.suffix}", file=sys.stderr)

    try:
        run_ffmpeg(video=video, srt=srt, out=out, crf=args.crf, preset=args.preset, force=args.force)
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3
    except subprocess.CalledProcessError as e:
        print(f"Error: ffmpeg failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode

    print(f"Done: {out}")
    return 0


def shutil_which(cmd: str) -> str | None:
    path = os.environ.get("PATH", "")
    for base in path.split(os.pathsep):
        candidate = Path(base) / cmd
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
