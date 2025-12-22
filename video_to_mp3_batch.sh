#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

resolve_dir() {
  local dir="$1"
  if [[ "$dir" = /* ]]; then
    printf '%s\n' "$dir"
  else
    printf '%s\n' "${SCRIPT_DIR}/${dir}"
  fi
}

INPUT_DIR="input_video"
OUTPUT_DIR="output_audio"
PROCESSED_DIR=""
INPUT_FILE=""
FORCE=0

usage() {
  cat <<'USAGE'
Usage:
  video_to_mp3_batch.sh [--input-dir DIR] [--output-dir DIR] [--processed-dir DIR] [--input-file FILE] [--force]

Notes:
  - Relative paths are resolved from the script directory.
  - If --input-file is provided, only that file is processed.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input-dir)
      INPUT_DIR="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --processed-dir)
      PROCESSED_DIR="$2"
      shift 2
      ;;
    --input-file)
      INPUT_FILE="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

INPUT_DIR="$(resolve_dir "$INPUT_DIR")"
OUTPUT_DIR="$(resolve_dir "$OUTPUT_DIR")"
if [[ -n "$PROCESSED_DIR" ]]; then
  PROCESSED_DIR="$(resolve_dir "$PROCESSED_DIR")"
else
  PROCESSED_DIR="${INPUT_DIR}/已处理"
fi
if [[ -n "$INPUT_FILE" ]]; then
  if [[ "$INPUT_FILE" != /* ]]; then
    INPUT_FILE="${SCRIPT_DIR}/${INPUT_FILE}"
  fi
fi

mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$PROCESSED_DIR"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Error: ffmpeg not found. Please install ffmpeg and try again." >&2
  exit 127
fi

shopt -s nullglob

is_video_file() {
  local path="$1"
  local name ext
  name="$(basename "$path")"
  ext="${name##*.}"
  [[ "$name" != "$ext" ]] || return 1
  ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  case "$ext" in
    mp4|mkv|mov|avi|flv|wmv|m4v|webm|ts|mpeg|mpg) return 0 ;;
    *) return 1 ;;
  esac
}

has_files=0
echo "Input dir:  $INPUT_DIR"
echo "Output dir: $OUTPUT_DIR"

if [[ -n "$INPUT_FILE" ]]; then
  if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: input file not found: $INPUT_FILE" >&2
    exit 2
  fi
  files=("$INPUT_FILE")
else
  mapfile -d '' files < <(find "$INPUT_DIR" -maxdepth 1 -type f -print0)
fi

for in_file in "${files[@]}"; do
  if ! is_video_file "$in_file"; then
    echo "【跳过非视频文件】Skipping non-video file: $in_file"
    continue
  fi
  if [[ ! -f "$in_file" ]]; then
    echo "Skipping missing file: $in_file"
    continue
  fi

  has_files=1

  base_name="$(basename "$in_file")"
  stem="${base_name%.*}"
  out_file="${OUTPUT_DIR}/${stem}.mp3"
  skip_convert=0

  if [[ -f "$out_file" ]]; then
    if [[ "$FORCE" -eq 1 ]]; then
      :
    elif [[ -n "$INPUT_FILE" ]]; then
      echo "【跳过已存在输出】Output exists: $out_file"
      skip_convert=1
    else
      i=1
      while [[ -f "${OUTPUT_DIR}/${stem} (${i}).mp3" ]]; do
        i=$((i + 1))
      done
      out_file="${OUTPUT_DIR}/${stem} (${i}).mp3"
    fi
  fi

  if [[ "$skip_convert" -eq 1 ]]; then
    echo "【移动已处理文件】Moving processed video to: $PROCESSED_DIR/"
    mv -f "$in_file" "$PROCESSED_DIR/"
  else
    echo "【mp3转换中】Converting: $in_file -> $out_file"
    if ffmpeg -hide_banner -loglevel error -y -i "$in_file" -vn -c:a libmp3lame -q:a 2 "$out_file"; then
      echo "【移动已处理文件】Moving processed video to: $PROCESSED_DIR/"
      mv -f "$in_file" "$PROCESSED_DIR/"
    else
      echo "Failed to convert (kept in place): $in_file" >&2
    fi
  fi
done

if [[ "$has_files" -eq 0 ]]; then
  echo "No files found in '$INPUT_DIR' (processed files are expected in '$PROCESSED_DIR')."
fi
