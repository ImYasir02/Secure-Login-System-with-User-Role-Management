#!/usr/bin/env bash
set -euo pipefail

# verify_security_json.sh
# Runs verify_security.sh and emits machine-readable JSON for CI/CD pipelines.
#
# Usage:
#   ./verify_security_json.sh example.com
#   ./verify_security_json.sh https://example.com --cloudflare
#   ./verify_security_json.sh example.com --cloudflare --out reports/security.json

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFY_SCRIPT="$ROOT_DIR/verify_security.sh"

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
  echo "Error: $VERIFY_SCRIPT not found or not executable" >&2
  exit 1
fi

URL_INPUT=""
EXPECT_CLOUDFLARE=0
VERBOSE=0
OUT_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cloudflare)
      EXPECT_CLOUDFLARE=1
      shift
      ;;
    --verbose|-v)
      VERBOSE=1
      shift
      ;;
    --out)
      [[ $# -lt 2 ]] && { echo "Error: --out requires a file path" >&2; exit 2; }
      OUT_FILE="$2"
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./verify_security_json.sh <domain-or-url> [--cloudflare] [--verbose] [--out <path>]

Examples:
  ./verify_security_json.sh example.com
  ./verify_security_json.sh https://example.com --cloudflare
  ./verify_security_json.sh example.com --cloudflare --out reports/security_report.json
EOF
      exit 0
      ;;
    *)
      if [[ -z "$URL_INPUT" ]]; then
        URL_INPUT="$1"
      else
        echo "Unexpected argument: $1" >&2
        exit 2
      fi
      shift
      ;;
  esac
done

if [[ -z "$URL_INPUT" ]]; then
  echo "Error: missing domain or URL. Run with --help." >&2
  exit 2
fi

if [[ -z "$OUT_FILE" ]]; then
  SAFE_NAME="$(printf '%s' "$URL_INPUT" | sed -E 's#^https?://##' | tr '/:?' '_' | tr -cd '[:alnum:]_.-')"
  OUT_FILE="$ROOT_DIR/security_report_${SAFE_NAME}_$(date +%F_%H%M%S).json"
fi

mkdir -p "$(dirname "$OUT_FILE")"

CMD_ARGS=("$URL_INPUT" "--no-color")
[[ "$EXPECT_CLOUDFLARE" -eq 1 ]] && CMD_ARGS+=("--cloudflare")
[[ "$VERBOSE" -eq 1 ]] && CMD_ARGS+=("--verbose")

TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

START_TS_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

set +e
"$VERIFY_SCRIPT" "${CMD_ARGS[@]}" >"$TMP_OUTPUT" 2>&1
VERIFY_EXIT=$?
set -e

PASS_COUNT="$(grep -c '^PASS - ' "$TMP_OUTPUT" || true)"
WARN_COUNT="$(grep -c '^WARN - ' "$TMP_OUTPUT" || true)"
FAIL_COUNT="$(grep -c '^FAIL - ' "$TMP_OUTPUT" || true)"
INFO_COUNT="$(grep -c '^INFO - ' "$TMP_OUTPUT" || true)"

if [[ "$URL_INPUT" =~ ^https?:// ]]; then
  DISPLAY_URL="$URL_INPUT"
else
  DISPLAY_URL="https://$URL_INPUT"
fi

STATUS_LABEL="PASS"
if [[ "$VERIFY_EXIT" -ne 0 ]]; then
  if [[ "$FAIL_COUNT" -gt 0 ]]; then
    STATUS_LABEL="FAIL"
  else
    STATUS_LABEL="ERROR"
  fi
elif [[ "$WARN_COUNT" -gt 0 ]]; then
  STATUS_LABEL="PASS_WITH_WARNINGS"
fi

json_escape() {
  sed \
    -e 's/\\/\\\\/g' \
    -e 's/"/\\"/g' \
    -e 's/\t/\\t/g' \
    -e 's/\r/\\r/g' \
    -e ':a;N;$!ba;s/\n/\\n/g'
}

emit_array() {
  local prefix="$1"
  local first=1
  printf '['
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    line="${line#${prefix} - }"
    escaped="$(printf '%s' "$line" | json_escape)"
    if [[ "$first" -eq 1 ]]; then
      first=0
    else
      printf ','
    fi
    printf '"%s"' "$escaped"
  done < <(grep "^${prefix} - " "$TMP_OUTPUT" || true)
  printf ']'
}

RAW_OUTPUT_ESCAPED="$(cat "$TMP_OUTPUT" | json_escape)"

{
  printf '{\n'
  printf '  "target": "%s",\n' "$(printf '%s' "$DISPLAY_URL" | json_escape)"
  printf '  "generated_at_utc": "%s",\n' "$START_TS_UTC"
  printf '  "cloudflare_expected": %s,\n' "$([[ "$EXPECT_CLOUDFLARE" -eq 1 ]] && echo true || echo false)"
  printf '  "verbose": %s,\n' "$([[ "$VERBOSE" -eq 1 ]] && echo true || echo false)"
  printf '  "status": "%s",\n' "$STATUS_LABEL"
  printf '  "exit_code": %s,\n' "$VERIFY_EXIT"
  printf '  "counts": {\n'
  printf '    "pass": %s,\n' "$PASS_COUNT"
  printf '    "warn": %s,\n' "$WARN_COUNT"
  printf '    "fail": %s,\n' "$FAIL_COUNT"
  printf '    "info": %s\n' "$INFO_COUNT"
  printf '  },\n'
  printf '  "results": {\n'
  printf '    "pass": '
  emit_array "PASS"
  printf ',\n'
  printf '    "warn": '
  emit_array "WARN"
  printf ',\n'
  printf '    "fail": '
  emit_array "FAIL"
  printf ',\n'
  printf '    "info": '
  emit_array "INFO"
  printf '\n'
  printf '  },\n'
  printf '  "raw_output": "%s"\n' "$RAW_OUTPUT_ESCAPED"
  printf '}\n'
} > "$OUT_FILE"

echo "Security JSON report written to: $OUT_FILE"
echo "Status: $STATUS_LABEL (PASS=$PASS_COUNT WARN=$WARN_COUNT FAIL=$FAIL_COUNT INFO=$INFO_COUNT)"

exit "$VERIFY_EXIT"

