#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
import sys
from pathlib import Path


VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".m4v", ".webm", ".ts", ".mpeg", ".mpg"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run video -> mp3 -> SRT -> burn-in pipeline.")
    parser.add_argument("--input-dir", default="input_video", help="Input video directory")
    parser.add_argument("--audio-dir", default="output_audio", help="Output audio directory")
    parser.add_argument("--srt-dir", default="ai_srt", help="Output SRT directory")
    parser.add_argument("--burn-dir", default="burn_video", help="Output burn-in video directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SRT/burn outputs")
    parser.add_argument("--stop-after-srt", action="store_true", help="Stop after SRT generation")
    return parser.parse_args(argv)


def run(cmd: list[str], cwd: Path) -> int:
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd))
    return result.returncode


def find_video_for_stem(processed_dir: Path, stem: str) -> Path | None:
    for ext in VIDEO_EXTS:
        candidate = processed_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent
    args = parse_args(argv)

    input_dir = (root / args.input_dir) if not Path(args.input_dir).is_absolute() else Path(args.input_dir)
    audio_dir = (root / args.audio_dir) if not Path(args.audio_dir).is_absolute() else Path(args.audio_dir)
    srt_dir = (root / args.srt_dir) if not Path(args.srt_dir).is_absolute() else Path(args.srt_dir)
    burn_dir = (root / args.burn_dir) if not Path(args.burn_dir).is_absolute() else Path(args.burn_dir)
    processed_dir = input_dir / "已处理"
    srt_processed_dir = srt_dir / "已处理"
    audio_processed_dir = audio_dir / "已处理"

    # Step 1: video -> mp3
    if run(["./video_to_mp3_batch.sh"], cwd=root) != 0:
        print("Step 1 failed: video_to_mp3_batch.sh", file=sys.stderr)
        return 1

    # Step 2: mp3 -> srt
    transcribe_cmd = [
        sys.executable,
        "transcribe_audio_to_srt_openrouter.py",
        "--input-dir",
        str(audio_dir),
        "--output-dir",
        str(srt_dir),
        "--insecure",
    ]
    if args.force:
        transcribe_cmd.append("--force")
    if run(transcribe_cmd, cwd=root) != 0:
        print("Step 2 failed: transcribe_audio_to_srt_openrouter.py", file=sys.stderr)
        return 1
    if args.stop_after_srt:
        print("Stopping after SRT generation (--stop-after-srt).")
        return 0

    # Step 3: burn-in
    burn_dir.mkdir(parents=True, exist_ok=True)
    srt_processed_dir.mkdir(parents=True, exist_ok=True)
    audio_processed_dir.mkdir(parents=True, exist_ok=True)
    srt_files = sorted([p for p in srt_dir.iterdir() if p.is_file() and p.suffix.lower() == ".srt"])
    if not srt_files:
        print(f"No SRT files found in: {srt_dir}")
        return 0

    for srt_path in srt_files:
        stem = srt_path.stem
        video_path = find_video_for_stem(processed_dir, stem)
        if not video_path:
            print(f"Skipping: no matching video for {srt_path}")
            continue

        out_path = burn_dir / f"{stem}_hardsub{video_path.suffix}"
        burn_cmd = [
            sys.executable,
            "burn_in_subtitles.py",
            "--video",
            str(video_path),
            "--srt",
            str(srt_path),
            "--out",
            str(out_path),
        ]
        if args.force:
            burn_cmd.append("--force")

        if run(burn_cmd, cwd=root) != 0:
            print(f"Burn failed: {video_path}", file=sys.stderr)
            continue

        audio_path = audio_dir / f"{stem}.mp3"
        if audio_path.exists():
            audio_path.replace(audio_processed_dir / audio_path.name)
        srt_path.replace(srt_processed_dir / srt_path.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
