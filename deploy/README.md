# Production Deployment / Hardening Templates (Python Flask)

This project is a Python Flask application (not PHP). This folder provides production-grade templates and checklists for:
- Nginx (security headers, rate limiting, TLS, caching)
- Gunicorn + systemd
- Cloudflare WAF/CDN checklist
- MariaDB hardening
- Fail2Ban / UFW / SSH hardening
- Optional Varnish cache for high traffic
- PHP hardening snippet (only if co-hosting PHP apps)

## Recommended Stack
- Web Server: Nginx
- CDN + WAF: Cloudflare
- Reverse Proxy Cache: Varnish (optional, high traffic only)
- Database: MariaDB
- Backend: Python (Flask + Gunicorn)
- Frontend: Tailwind CSS (current app uses CDN; for production, prefer compiled assets)

## Important
These are templates. You must review and adapt:
- domain names
- file paths
- TLS certificate paths
- MariaDB credentials
- SSH port
- Cloudflare IP list

## Flask Security Already Present in App
The app includes:
- SQLAlchemy ORM (primary data access)
- CSRF protection (Flask-WTF)
- upload size/extension/MIME checks
- session/cookie hardening defaults
- app-level security headers
- HTTPS enforcement (env-controlled)

## Apply Order (Recommended)
1. Set `.env.production` from `.env.production.example`
2. Configure MariaDB (`deploy/mariadb/*`)
3. Create systemd service (`deploy/systemd/*`)
4. Configure Nginx (`deploy/nginx/*`)
5. Enable UFW + SSH hardening (`deploy/ufw`, `deploy/ssh`)
6. Enable Fail2Ban (`deploy/fail2ban/*`)
7. Enable Cloudflare protections (`deploy/cloudflare/*`)
8. Test backups (`deploy/ops/backup_mariadb.sh`)
