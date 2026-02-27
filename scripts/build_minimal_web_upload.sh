#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT_DIR/github-web-upload-minimal}"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

cp "$ROOT_DIR/app.py" "$OUT_DIR/"
cp "$ROOT_DIR/wsgi.py" "$OUT_DIR/"
cp "$ROOT_DIR/requirements.txt" "$OUT_DIR/"
cp "$ROOT_DIR/.gitignore" "$OUT_DIR/"
cp "$ROOT_DIR/.env.production.example" "$OUT_DIR/"

cp -r "$ROOT_DIR/app" "$OUT_DIR/"
cp -r "$ROOT_DIR/backend" "$OUT_DIR/"

mkdir -p "$OUT_DIR/instance/uploads"

find "$OUT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$OUT_DIR" -type f -name "*.pyc" -delete

cat > "$OUT_DIR/UPLOAD_STEPS.txt" <<'EOF'
GitHub web upload quick steps:
1) Open your GitHub repository in browser.
2) Upload only the contents of this folder (not your full project root).
3) Then on server/machine run:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
EOF

FILE_COUNT="$(find "$OUT_DIR" -type f | wc -l | tr -d ' ')"
echo "Created: $OUT_DIR"
echo "Total files: $FILE_COUNT"
