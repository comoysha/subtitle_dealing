#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

TARGETS=(
  "output_audio/已处理"
  "input_video/已处理"
  "ai_srt/已处理"
)

for rel in "${TARGETS[@]}"; do
  dir="${ROOT_DIR}/${rel}"
  if [[ -d "$dir" ]]; then
    echo "Clearing: $dir"
    rm -rf "${dir:?}/"*
  else
    echo "Skip (not found): $dir"
  fi
done
