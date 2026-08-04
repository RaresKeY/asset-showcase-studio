#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-turntable}"
OUTPUT="${2:-recordings/${MODE}_$(date -u +%Y%m%dT%H%M%SZ).mp4}"
FPS="${3:-30}"
RESOLUTION="${4:-1920x1080}"
DURATION="${5:-}"
ASSET_PATH="${6:-}"

case "$MODE" in
  turntable)
    SCENE="$ROOT/scenes/showcase_studio.tscn"
    DURATION="${DURATION:-20}"
    ;;
  flythrough)
    SCENE="$ROOT/scenes/flythrough_showcase.tscn"
    DURATION="${DURATION:-12}"
    ;;
  *)
    echo "Usage: $0 [turntable|flythrough] [output.mp4] [fps] [WIDTHxHEIGHT] [seconds] [res://asset.glb]" >&2
    exit 2
    ;;
esac

if [[ ! "$FPS" =~ ^[1-9][0-9]*$ ]] || \
   [[ ! "$RESOLUTION" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]] || \
   [[ ! "$DURATION" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "FPS must be an integer, resolution like 1920x1080, and duration numeric." >&2
  exit 2
fi

GODOT="${GODOT_BIN:-}"
if [[ -z "$GODOT" ]]; then
  GODOT="$(command -v godot4 || command -v godot || true)"
fi
if [[ -z "$GODOT" ]]; then
  echo "Godot 4 was not found. Set GODOT_BIN=/absolute/path/to/godot." >&2
  exit 127
fi

if [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$ROOT/$OUTPUT"
fi
BASE="${OUTPUT%.*}"
AVI="${BASE}.avi"
MP4="${BASE}.mp4"
mkdir -p "$(dirname "$AVI")"
FRAMES="$(awk -v fps="$FPS" -v seconds="$DURATION" 'BEGIN { printf "%d", fps * seconds + 0.5 }')"

USER_ARGS=(--clean-capture)
if [[ -n "$ASSET_PATH" ]]; then
  USER_ARGS+=("--asset=$ASSET_PATH")
fi

echo "Recording $MODE: ${DURATION}s, ${FPS} fps, $RESOLUTION"
"$GODOT" \
  --path "$ROOT" \
  --write-movie "$AVI" \
  --fixed-fps "$FPS" \
  --resolution "$RESOLUTION" \
  --quit-after "$FRAMES" \
  --disable-vsync \
  "$SCENE" \
  -- "${USER_ARGS[@]}"

if [[ ! -s "$AVI" ]]; then
  echo "Godot exited without producing $AVI" >&2
  exit 1
fi

if command -v ffmpeg >/dev/null; then
  ffmpeg -y -i "$AVI" \
    -map 0:v:0 -map '0:a?' \
    -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -movflags +faststart \
    "$MP4"
  echo "Delivery video: $MP4"
  echo "Lossless master: $AVI"
else
  echo "FFmpeg was not found; lossless movie saved to $AVI"
fi
