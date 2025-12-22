#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="subtitle_json"

if [[ ! -d "${INPUT_DIR}" ]]; then
  echo "Input directory not found: ${INPUT_DIR}" >&2
  exit 1
fi

python3 extract_bilibili_ai_subtitles.py --in-dir "${INPUT_DIR}"
