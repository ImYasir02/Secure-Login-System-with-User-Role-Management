#!/usr/bin/env bash
set -euo pipefail

# verify_security_report.sh
# Runs verify_security.sh and stores a markdown report for audit/share purposes.
#
# Usage:
#   ./verify_security_report.sh example.com
#   ./verify_security_report.sh https://example.com --cloudflare
#   ./verify_security_report.sh example.com --cloudflare --out reports/security_check.md

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
Usage: ./verify_security_report.sh <domain-or-url> [--cloudflare] [--verbose] [--out <path>]

Examples:
  ./verify_security_report.sh example.com
  ./verify_security_report.sh https://example.com --cloudflare
  ./verify_security_report.sh example.com --cloudflare --out reports/security_report.md
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
  OUT_FILE="$ROOT_DIR/security_report_${SAFE_NAME}_$(date +%F_%H%M%S).md"
fi

mkdir -p "$(dirname "$OUT_FILE")"

CMD_ARGS=("$URL_INPUT" "--no-color")
[[ "$EXPECT_CLOUDFLARE" -eq 1 ]] && CMD_ARGS+=("--cloudflare")
[[ "$VERBOSE" -eq 1 ]] && CMD_ARGS+=("--verbose")

TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

START_TS_UTC="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"

set +e
"$VERIFY_SCRIPT" "${CMD_ARGS[@]}" >"$TMP_OUTPUT" 2>&1
VERIFY_EXIT=$?
set -e

PASS_COUNT="$(grep -c '^PASS - ' "$TMP_OUTPUT" || true)"
WARN_COUNT="$(grep -c '^WARN - ' "$TMP_OUTPUT" || true)"
FAIL_COUNT="$(grep -c '^FAIL - ' "$TMP_OUTPUT" || true)"

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

{
  echo "# Security Verification Report"
  echo
  echo "- **Target**: \`$DISPLAY_URL\`"
  echo "- **Generated At (UTC)**: $START_TS_UTC"
  echo "- **Cloudflare Expected**: $([[ "$EXPECT_CLOUDFLARE" -eq 1 ]] && echo "Yes" || echo "No")"
  echo "- **Verbose Mode**: $([[ "$VERBOSE" -eq 1 ]] && echo "Yes" || echo "No")"
  echo "- **Overall Status**: **$STATUS_LABEL**"
  echo "- **Script Exit Code**: \`$VERIFY_EXIT\`"
  echo
  echo "## Summary"
  echo
  echo "- PASS: **$PASS_COUNT**"
  echo "- WARN: **$WARN_COUNT**"
  echo "- FAIL: **$FAIL_COUNT**"
  echo
  echo "## Command Used"
  echo
  printf '```bash\n%s' "$VERIFY_SCRIPT"
  for arg in "${CMD_ARGS[@]}"; do
    printf ' %q' "$arg"
  done
  echo
  echo '```'
  echo
  echo "## Raw Output"
  echo
  echo '```text'
  cat "$TMP_OUTPUT"
  echo '```'
  echo
  echo "## Notes"
  echo
  echo "- Wappalyzer is not a reliable source for backend hardening verification."
  echo "- Use this report together with Cloudflare dashboard, Nginx config, and server-level checks (UFW/Fail2Ban/SSH)."
} > "$OUT_FILE"

echo "Security markdown report written to: $OUT_FILE"
echo "Status: $STATUS_LABEL (PASS=$PASS_COUNT WARN=$WARN_COUNT FAIL=$FAIL_COUNT)"

exit "$VERIFY_EXIT"

