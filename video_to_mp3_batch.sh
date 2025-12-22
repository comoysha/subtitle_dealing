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

INPUT_DIR="$(resolve_dir "${1:-input_video}")"
OUTPUT_DIR="$(resolve_dir "${2:-output_audio}")"
PROCESSED_DIR="${INPUT_DIR}/已处理"

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
while IFS= read -r -d '' in_file; do
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

  if [[ -f "$out_file" ]]; then
    i=1
    while [[ -f "${OUTPUT_DIR}/${stem} (${i}).mp3" ]]; do
      i=$((i + 1))
    done
    out_file="${OUTPUT_DIR}/${stem} (${i}).mp3"
  fi

  echo "【mp3转换中】Converting: $in_file -> $out_file"
  if ffmpeg -hide_banner -loglevel error -y -i "$in_file" -vn -c:a libmp3lame -q:a 2 "$out_file"; then
    echo "【移动已处理文件】Moving processed video to: $PROCESSED_DIR/"
    mv -f "$in_file" "$PROCESSED_DIR/"
  else
    echo "Failed to convert (kept in place): $in_file" >&2
  fi
done < <(find "$INPUT_DIR" -maxdepth 1 -type f -print0)

if [[ "$has_files" -eq 0 ]]; then
  echo "No files found in '$INPUT_DIR' (processed files are expected in '$PROCESSED_DIR')."
fi
