#!/usr/bin/env bash
set -euo pipefail

# Review before running on remote servers to avoid lockout.
SSH_PORT="${SSH_PORT:-2222}"

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ${SSH_PORT}/tcp comment 'SSH hardened port'
ufw allow 80/tcp comment 'HTTP (redirect to HTTPS)'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose
