#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ZIP="${1:-$ROOT_DIR/github-upload-ready.zip}"

cd "$ROOT_DIR"
rm -f "$OUTPUT_ZIP"

zip -r "$OUTPUT_ZIP" . \
  -x "venv/*" \
  -x ".venv/*" \
  -x "env/*" \
  -x "ENV/*" \
  -x "__pycache__/*" \
  -x "**/__pycache__/*" \
  -x "*.pyc" \
  -x ".env" \
  -x "site.db" \
  -x "instance/*.db" \
  -x "instance/uploads/*" \
  -x "*.sqlite3" \
  -x ".git/*"

echo "Created upload zip: $OUTPUT_ZIP"
