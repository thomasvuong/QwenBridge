#!/usr/bin/env bash
# Regenerate architecture.png from architecture.mmd
# Usage: bash docs/render_diagram.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [[ ! -f "$CHROME" ]]; then
  echo "Chrome not found at: $CHROME"
  echo "Set PUPPETEER_EXECUTABLE_PATH manually or install Chrome."
  exit 1
fi

PUPPETEER_EXECUTABLE_PATH="$CHROME" \
  mmdc -i "$SCRIPT_DIR/architecture.mmd" \
       -o "$SCRIPT_DIR/architecture.png" \
       -b white -w 1600 -H 900

echo "✓ Rendered: docs/architecture.png"
