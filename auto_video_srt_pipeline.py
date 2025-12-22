#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    parser.add_argument("--jobs", type=int, default=0, help="Max parallel tasks (default: auto)")
    return parser.parse_args(argv)


def run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def is_video_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTS


def iter_videos(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted([p for p in input_dir.iterdir() if is_video_file(p)])


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

    burn_dir.mkdir(parents=True, exist_ok=True)
    srt_processed_dir.mkdir(parents=True, exist_ok=True)
    audio_processed_dir.mkdir(parents=True, exist_ok=True)

    videos = iter_videos(input_dir)
    if not videos:
        print(f"未找到视频文件：{input_dir}")
        return 0

    max_workers = args.jobs if args.jobs > 0 else max(1, min(4, os.cpu_count() or 2))
    total = len(videos)
    print(f"共发现 {total} 个视频文件，开始并行处理（并发数：{max_workers}）")

    def process_one(video_path: Path, index: int) -> None:
        stem = video_path.stem
        print(f"[{index}/{total}] 开始处理：{video_path.name}")

        print(f"[{index}/{total}] 1/3 提取音频")
        mp3_cmd = [
            "./video_to_mp3_batch.sh",
            "--input-file",
            str(video_path),
            "--output-dir",
            str(audio_dir),
            "--processed-dir",
            str(processed_dir),
        ]
        if args.force:
            mp3_cmd.append("--force")
        code, out, err = run(mp3_cmd, cwd=root)
        if code != 0:
            details = err.strip() or out.strip()
            print(f"[{index}/{total}] 音频提取失败：{video_path.name}\n{details}", file=sys.stderr)
            return

        mp3_path = audio_dir / f"{stem}.mp3"
        if not mp3_path.exists():
            print(f"[{index}/{total}] 未找到输出音频：{mp3_path}", file=sys.stderr)
            return

        print(f"[{index}/{total}] 2/3 生成 SRT")
        srt_cmd = [
            sys.executable,
            "transcribe_audio_to_srt_openrouter.py",
            "--input-file",
            str(mp3_path),
            "--output-dir",
            str(srt_dir),
            "--insecure",
        ]
        if args.force:
            srt_cmd.append("--force")
        code, out, err = run(srt_cmd, cwd=root)
        if code != 0:
            details = err.strip() or out.strip()
            print(f"[{index}/{total}] SRT 生成失败：{mp3_path.name}\n{details}", file=sys.stderr)
            return
        if args.stop_after_srt:
            print(f"[{index}/{total}] 已生成 SRT，按参数停止后续步骤")
            return

        srt_path = srt_dir / f"{stem}.srt"
        if not srt_path.exists():
            print(f"[{index}/{total}] 未找到输出字幕：{srt_path}", file=sys.stderr)
            return

        processed_video = processed_dir / video_path.name
        if not processed_video.exists():
            print(f"[{index}/{total}] 未找到已处理视频：{processed_video}", file=sys.stderr)
            return

        print(f"[{index}/{total}] 3/3 烧录字幕")
        out_path = burn_dir / f"{stem}_hardsub{video_path.suffix}"
        burn_cmd = [
            sys.executable,
            "burn_in_subtitles.py",
            "--video",
            str(processed_video),
            "--srt",
            str(srt_path),
            "--out",
            str(out_path),
        ]
        if args.force:
            burn_cmd.append("--force")
        code, out, err = run(burn_cmd, cwd=root)
        if code != 0:
            details = err.strip() or out.strip()
            print(f"[{index}/{total}] 烧录失败：{processed_video.name}\n{details}", file=sys.stderr)
            return

        if mp3_path.exists():
            mp3_path.replace(audio_processed_dir / mp3_path.name)
        if srt_path.exists():
            srt_path.replace(srt_processed_dir / srt_path.name)

        print(f"[{index}/{total}] 完成：{video_path.name}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_one, v, i + 1) for i, v in enumerate(videos)]
        for future in as_completed(futures):
            future.result()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
