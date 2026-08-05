#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GODOT="${GODOT_BIN:-}"
if [[ -z "$GODOT" ]]; then
  GODOT="$(command -v godot4 || command -v godot || true)"
fi
if [[ -z "$GODOT" ]]; then
  echo "Godot 4 was not found. Set GODOT_BIN=/absolute/path/to/godot." >&2
  exit 127
fi
if [[ ! -x "$GODOT" ]]; then
  echo "Godot executable is not runnable: $GODOT" >&2
  exit 126
fi

VERSION_LINE="$("$GODOT" --version 2>&1 | head -n 1)"
REQUIRED_SERIES="${GODOT_REQUIRED_SERIES:-4.7}"
VERSION_PATTERN="^${REQUIRED_SERIES//./\\.}([.-]|$)"
if [[ ! "$VERSION_LINE" =~ $VERSION_PATTERN ]]; then
  echo "Expected Godot $REQUIRED_SERIES.x, found: $VERSION_LINE" >&2
  echo "Set GODOT_REQUIRED_SERIES only when deliberately testing another supported series." >&2
  exit 2
fi

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/asset-showcase-godot-validation.XXXXXX")"
echo "Validation logs: $LOG_DIR"

run_checked() {
  local label="$1"
  shift
  local log="$LOG_DIR/${label}.log"
  local -a pipeline_status
  echo "Running $label with $VERSION_LINE"
  set +e
  "$@" 2>&1 | tee "$log"
  pipeline_status=("${PIPESTATUS[@]}")
  set -e
  if (( pipeline_status[0] != 0 || pipeline_status[1] != 0 )); then
    echo "Godot command failed during $label (engine=${pipeline_status[0]}, tee=${pipeline_status[1]}). See $log." >&2
    return 1
  fi
  if grep -Eiq \
    'SCRIPT ERROR|Parse Error|Failed to load script|Shader (compilation )?failed|Invalid shader' \
    "$log"; then
    echo "Godot reported a parser, script, or shader failure during $label. See $log." >&2
    return 1
  fi
}

run_checked import-pass-1 "$GODOT" --headless --editor --path "$ROOT" --import --quit
run_checked import-pass-2 "$GODOT" --headless --editor --path "$ROOT" --import --quit
run_checked smoke "$GODOT" --headless --path "$ROOT" --quit-after 600 \
  --script res://tools/headless_smoke_test.gd
if ! grep -Fq 'SHOWCASE_SMOKE_TEST_OK' "$LOG_DIR/smoke.log"; then
  echo "Smoke test exited without its success marker. See $LOG_DIR/smoke.log." >&2
  exit 1
fi

echo "SHOWCASE_GODOT_VALIDATION_OK"
