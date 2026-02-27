# Server Hardening Checklist (Ubuntu/Debian)

## OS / Packages
- [ ] `apt update && apt upgrade -y`
- [ ] Install unattended upgrades (`unattended-upgrades`) and enable
- [ ] Install `fail2ban`, `ufw`, `nginx`, `mariadb-server`, `python3-venv`
- [ ] Install `certbot` + nginx plugin (or alternative ACME client)
- [ ] Install `clamav` (optional) if ENABLE_VIRUS_SCAN=1

## Python App (Flask)
- [ ] Use `gunicorn` behind Nginx
- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` set to long random value
- [ ] `ENFORCE_HTTPS=1`
- [ ] `SESSION_COOKIE_SECURE=1`
- [ ] `PROXY_FIX_ENABLED=1`
- [ ] Debug disabled (`FLASK_DEBUG=0`)
- [ ] SQLAlchemy database URL uses MariaDB user (no root)

## MariaDB
- [ ] Change port from default (e.g. `3307`)
- [ ] Bind to localhost only
- [ ] Disable remote root login
- [ ] Strong root password
- [ ] Least-privilege app user
- [ ] Regular backups + restore tests

## Nginx / TLS
- [ ] `server_tokens off`
- [ ] Security headers enabled
- [ ] Rate limiting enabled
- [ ] HTTP -> HTTPS redirect enabled
- [ ] TLS v1.2/v1.3 only
- [ ] Static cache headers enabled
- [ ] `proxy_hide_header` for upstream info

## Cloudflare
- [ ] WAF managed rules ON
- [ ] Bot Fight Mode ON
- [ ] Force HTTPS ON
- [ ] Brotli ON
- [ ] Rate limits on auth endpoints

## SSH / Firewall
- [ ] UFW default deny incoming
- [ ] Allow only `80`, `443`, hardened SSH port
- [ ] SSH password login disabled
- [ ] Root login disabled
- [ ] SSH key auth only

## Monitoring / Logging
- [ ] Fail2Ban active (`sshd` + `nginx` jails)
- [ ] Nginx logs rotated
- [ ] MariaDB logs monitored
- [ ] Application logs monitored (journalctl/gunicorn)
