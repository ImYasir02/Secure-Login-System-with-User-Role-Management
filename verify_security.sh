#!/usr/bin/env bash
set -euo pipefail

# verify_security.sh
# Checks common production security headers and HTTPS behavior for a public URL.
#
# Usage:
#   ./verify_security.sh https://example.com
#   ./verify_security.sh example.com --cloudflare
#   ./verify_security.sh https://example.com --cloudflare --verbose

COLOR=1
VERBOSE=0
EXPECT_CLOUDFLARE=0
URL_INPUT=""

for arg in "$@"; do
  case "$arg" in
    --no-color) COLOR=0 ;;
    --verbose|-v) VERBOSE=1 ;;
    --cloudflare) EXPECT_CLOUDFLARE=1 ;;
    --help|-h)
      cat <<'EOF'
Usage: ./verify_security.sh <domain-or-url> [--cloudflare] [--verbose] [--no-color]

Checks:
  - HTTPS redirect (http -> https)
  - CSP
  - HSTS
  - X-Frame-Options
  - Referrer-Policy
  - X-Content-Type-Options
  - Server header hidden/minimized
  - Cloudflare headers present (if --cloudflare)

Examples:
  ./verify_security.sh example.com
  ./verify_security.sh https://example.com --cloudflare --verbose
EOF
      exit 0
      ;;
    *)
      if [[ -z "$URL_INPUT" ]]; then
        URL_INPUT="$arg"
      else
        echo "Unexpected argument: $arg" >&2
        exit 2
      fi
      ;;
  esac
done

if [[ -z "$URL_INPUT" ]]; then
  echo "Error: missing domain or URL. Run with --help." >&2
  exit 2
fi

if [[ "$URL_INPUT" =~ ^https?:// ]]; then
  HTTPS_URL="$URL_INPUT"
else
  HTTPS_URL="https://$URL_INPUT"
fi

HOST_ONLY="$(printf '%s' "$HTTPS_URL" | sed -E 's#^https?://([^/]+).*$#\1#')"
HTTP_URL="http://$HOST_ONLY/"

if [[ "$COLOR" -eq 1 ]] && [[ -t 1 ]]; then
  RED=$'\033[31m'
  GREEN=$'\033[32m'
  YELLOW=$'\033[33m'
  BLUE=$'\033[34m'
  BOLD=$'\033[1m'
  RESET=$'\033[0m'
else
  RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; RESET=""
fi

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() { PASS_COUNT=$((PASS_COUNT+1)); echo "${GREEN}PASS${RESET} - $*"; }
warn() { WARN_COUNT=$((WARN_COUNT+1)); echo "${YELLOW}WARN${RESET} - $*"; }
fail() { FAIL_COUNT=$((FAIL_COUNT+1)); echo "${RED}FAIL${RESET} - $*"; }
info() { echo "${BLUE}INFO${RESET} - $*"; }

header_value() {
  # case-insensitive header extraction from raw header block
  local key="$1"
  local data="$2"
  printf '%s\n' "$data" | awk -v IGNORECASE=1 -v k="$key" '
    BEGIN { FS=": *" }
    tolower($1) == tolower(k) { sub(/\r$/, "", $2); print $2; exit }
  '
}

contains_ci() {
  local haystack="$1"
  local needle="$2"
  printf '%s' "$haystack" | grep -qi -- "$needle"
}

echo "${BOLD}Security Verification${RESET}"
echo "Target (HTTPS): $HTTPS_URL"
echo "Target (HTTP):  $HTTP_URL"
echo

HTTPS_HEADERS=""
if ! HTTPS_HEADERS="$(curl -sS -I -L --max-redirs 5 --connect-timeout 10 --max-time 20 "$HTTPS_URL")"; then
  echo "${RED}FAIL${RESET} - Unable to fetch HTTPS headers from $HTTPS_URL"
  exit 1
fi

HTTP_CHAIN=""
HTTP_STATUS_LINE=""
HTTP_LOCATION=""
if HTTP_CHAIN="$(curl -sS -I --max-redirs 0 --connect-timeout 10 --max-time 20 "$HTTP_URL" 2>/dev/null || true)"; then
  HTTP_STATUS_LINE="$(printf '%s\n' "$HTTP_CHAIN" | head -n1 | tr -d '\r')"
  HTTP_LOCATION="$(header_value "Location" "$HTTP_CHAIN")"
fi

if [[ "$VERBOSE" -eq 1 ]]; then
  echo "${BOLD}Raw HTTPS headers${RESET}"
  echo "$HTTPS_HEADERS"
  echo
  echo "${BOLD}Raw HTTP headers (no redirect follow)${RESET}"
  echo "$HTTP_CHAIN"
  echo
fi

# 1) HTTPS redirect
if [[ -n "$HTTP_STATUS_LINE" ]] && printf '%s' "$HTTP_STATUS_LINE" | grep -Eq ' 30[1278] '; then
  if [[ "$HTTP_LOCATION" =~ ^https:// ]]; then
    pass "HTTP redirects to HTTPS ($HTTP_STATUS_LINE -> $HTTP_LOCATION)"
  else
    fail "HTTP redirect found but not to HTTPS ($HTTP_STATUS_LINE -> ${HTTP_LOCATION:-<missing Location>})"
  fi
else
  fail "HTTP does not appear to redirect to HTTPS (status: ${HTTP_STATUS_LINE:-unknown})"
fi

# Extract headers from final HTTPS response
CSP="$(header_value "Content-Security-Policy" "$HTTPS_HEADERS")"
HSTS="$(header_value "Strict-Transport-Security" "$HTTPS_HEADERS")"
XFO="$(header_value "X-Frame-Options" "$HTTPS_HEADERS")"
REFPOL="$(header_value "Referrer-Policy" "$HTTPS_HEADERS")"
XCTO="$(header_value "X-Content-Type-Options" "$HTTPS_HEADERS")"
XXSS="$(header_value "X-XSS-Protection" "$HTTPS_HEADERS")"
SERVER_HDR="$(header_value "Server" "$HTTPS_HEADERS")"
CF_RAY="$(header_value "CF-Ray" "$HTTPS_HEADERS")"
CF_CACHE="$(header_value "CF-Cache-Status" "$HTTPS_HEADERS")"
CF_VISITOR="$(header_value "CF-Visitor" "$HTTPS_HEADERS")"

# 2) CSP
if [[ -n "$CSP" ]]; then
  if contains_ci "$CSP" "default-src" && contains_ci "$CSP" "frame-ancestors"; then
    pass "CSP present and includes core directives"
  else
    warn "CSP present but missing some expected directives (default-src/frame-ancestors)"
  fi
else
  fail "Content-Security-Policy header missing"
fi

# 3) HSTS
if [[ -n "$HSTS" ]]; then
  if contains_ci "$HSTS" "max-age="; then
    pass "HSTS present (${HSTS})"
  else
    warn "HSTS present but max-age missing/invalid"
  fi
else
  fail "Strict-Transport-Security header missing"
fi

# 4) X-Frame-Options
if [[ -n "$XFO" ]]; then
  if [[ "${XFO^^}" == "SAMEORIGIN" || "${XFO^^}" == "DENY" ]]; then
    pass "X-Frame-Options set to $XFO"
  else
    warn "X-Frame-Options present but unusual value: $XFO"
  fi
else
  fail "X-Frame-Options header missing"
fi

# 5) Referrer-Policy
if [[ -n "$REFPOL" ]]; then
  if contains_ci "$REFPOL" "strict-origin-when-cross-origin"; then
    pass "Referrer-Policy set to strict-origin-when-cross-origin"
  else
    warn "Referrer-Policy present but different value: $REFPOL"
  fi
else
  fail "Referrer-Policy header missing"
fi

# 6) X-Content-Type-Options
if [[ -n "$XCTO" ]]; then
  if contains_ci "$XCTO" "nosniff"; then
    pass "X-Content-Type-Options set to nosniff"
  else
    warn "X-Content-Type-Options present but not nosniff: $XCTO"
  fi
else
  fail "X-Content-Type-Options header missing"
fi

# Optional legacy header
if [[ -n "$XXSS" ]]; then
  pass "X-XSS-Protection present ($XXSS)"
else
  warn "X-XSS-Protection missing (legacy header; optional on modern browsers)"
fi

# 7) Server info leakage
if [[ -z "$SERVER_HDR" ]]; then
  pass "Server header hidden (not exposed)"
else
  case "${SERVER_HDR,,}" in
    cloudflare)
      pass "Server header shows Cloudflare only (origin info hidden)"
      ;;
    *nginx*|*apache*|*gunicorn*|*werkzeug*|*php*|*openresty*)
      fail "Server header exposes backend/server software: $SERVER_HDR"
      ;;
    *)
      warn "Server header present (review if acceptable): $SERVER_HDR"
      ;;
  esac
fi

# 8) Cloudflare presence (optional / auto-detect)
if [[ "$EXPECT_CLOUDFLARE" -eq 1 ]]; then
  if [[ -n "$CF_RAY" || -n "$CF_CACHE" || "${SERVER_HDR,,}" == "cloudflare" ]]; then
    pass "Cloudflare appears active (CF-Ray/CF-Cache-Status/server: cloudflare detected)"
  else
    fail "Cloudflare headers not detected, but --cloudflare was requested"
  fi
else
  if [[ -n "$CF_RAY" || -n "$CF_CACHE" || "${SERVER_HDR,,}" == "cloudflare" || -n "$CF_VISITOR" ]]; then
    info "Cloudflare detected (CF headers present)"
  else
    info "Cloudflare not detected (this may be expected)"
  fi
fi

echo
echo "${BOLD}Summary${RESET}"
echo "PASS: $PASS_COUNT"
echo "WARN: $WARN_COUNT"
echo "FAIL: $FAIL_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  exit 1
fi
exit 0

