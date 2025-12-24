#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import re
import sys
import subprocess
import ssl
import urllib.request
from pathlib import Path


DEFAULT_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
DEFAULT_MODEL = "google/gemini-3-pro-preview"
DEFAULT_PROMPT = (
    "根据音频文件，生成转写的中文（要翻译源语言）字幕文件，用 SRT 文件格式。"
    "所有情绪词、语气词、填充词、停顿表达都必须保留，包括但不限于：“嗯”“啊”“哦”“呃”“呵”“哈”。"
    "仅输出 SRT 内容，不要额外说明。"
    "时间戳必须严格为 HH:MM:SS,mmm（小时/分钟/秒/毫秒），"
    "例如：00:00:12,345 --> 00:00:15,678。"
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:srt)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def request_srt(api_key: str, model: str, prompt: str, audio_path: Path, insecure: bool) -> str:
    audio_bytes = audio_path.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    audio_format = audio_path.suffix.lstrip(".").lower() or "mp3"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": audio_format}},
                ],
            }
        ],
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://subtitle_dealing",
            "X-Title": "subtitle_dealing",
        },
        method="POST",
    )

    context = None
    if insecure:
        context = ssl._create_unverified_context()

    with urllib.request.urlopen(req, context=context) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "choices" not in data or not data["choices"]:
        raise RuntimeError(f"Unexpected response: {data}")

    content = data["choices"][0]["message"].get("content", "")
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        content = "".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"Empty response content: {data}")

    return strip_code_fence(content)


def get_audio_duration_seconds(path: Path) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def fix_srt_hours_if_short(srt_text: str, duration_seconds: float | None) -> str:
    if duration_seconds is None or duration_seconds >= 3600:
        return srt_text

    timestamp_re = re.compile(
        r"^(?P<h1>\\d{2}):(?P<m1>\\d{2}):(?P<s1>\\d{2}),(?P<ms1>\\d{3})\\s*-->\\s*"
        r"(?P<h2>\\d{2}):(?P<m2>\\d{2}):(?P<s2>\\d{2}),(?P<ms2>\\d{3})$"
    )

    lines = srt_text.splitlines()
    has_hour = False
    for line in lines:
        m = timestamp_re.match(line.strip())
        if m and (m.group("h1") != "00" or m.group("h2") != "00"):
            has_hour = True
            break

    if not has_hour:
        return srt_text

    fixed_lines = []
    for line in lines:
        m = timestamp_re.match(line.strip())
        if m:
            fixed = (
                f"00:{m.group('m1')}:{m.group('s1')},{m.group('ms1')} --> "
                f"00:{m.group('m2')}:{m.group('s2')},{m.group('ms2')}"
            )
            fixed_lines.append(fixed)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in DEFAULT_AUDIO_EXTS


def iter_audio_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted([p for p in input_dir.iterdir() if is_audio_file(p)])


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio files to Chinese SRT subtitles via OpenRouter."
    )
    parser.add_argument("--input-dir", default="output_audio", help="Audio input directory")
    parser.add_argument("--input-file", help="Single audio file to transcribe")
    parser.add_argument("--output-dir", default="ai_srt", help="SRT output directory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model name")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt for transcription")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SRT files")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent
    load_dotenv(root / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment or .env", file=sys.stderr)
        return 2

    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    input_file = Path(args.input_file).expanduser() if args.input_file else None
    if input_file and not input_file.is_absolute():
        input_file = (root / input_file).resolve()
    if not input_dir.is_absolute():
        input_dir = root / input_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_file:
        if not input_file.exists():
            print(f"Error: input file not found: {input_file}", file=sys.stderr)
            return 2
        if not is_audio_file(input_file):
            print(f"Error: not an audio file: {input_file}", file=sys.stderr)
            return 2
        audio_files = [input_file]
    else:
        audio_files = iter_audio_files(input_dir)
    if not audio_files:
        print(f"No audio files found in: {input_dir}")
        return 0

    for audio_path in audio_files:
        stem = audio_path.stem
        out_path = output_dir / f"{stem}.srt"
        if out_path.exists() and not args.force:
            print(f"【跳过已存在任务】Skipping existing: {out_path}")
            continue

        print(f"【使用 ai 对音频生成 srt】Transcribing: {audio_path}")
        try:
            srt_text = request_srt(api_key, args.model, args.prompt, audio_path, args.insecure)
        except Exception as exc:
            print(f"Failed: {audio_path} ({exc})", file=sys.stderr)
            continue

        duration_seconds = get_audio_duration_seconds(audio_path)
        srt_text = fix_srt_hours_if_short(srt_text, duration_seconds)
        out_path.write_text(srt_text, encoding="utf-8")
        print(f"【srt 写入】Wrote: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
