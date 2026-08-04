#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 'renders/turntable/frame_%04d.png' output.mp4 [fps] [start_frame]" >&2
  exit 2
fi

PATTERN="$1"
OUTPUT="$2"
FPS="${3:-30}"
START_FRAME="${4:-1}"

ffmpeg -y \
  -framerate "$FPS" -start_number "$START_FRAME" -i "$PATTERN" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
  -movflags +faststart "$OUTPUT"

