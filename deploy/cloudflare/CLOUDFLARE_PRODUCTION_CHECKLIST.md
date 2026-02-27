# Cloudflare Production Checklist

Enable / configure:
- [ ] DNS proxy (orange cloud) enabled for production domain
- [ ] SSL/TLS mode = Full (strict)
- [ ] Always Use HTTPS = ON
- [ ] Automatic HTTPS Rewrites = ON
- [ ] HSTS = ON (only after HTTPS is stable)
- [ ] WAF Managed Rules = ON
- [ ] Bot Fight Mode = ON
- [ ] Super Bot Fight Mode = ON (if plan supports)
- [ ] Rate Limiting rules for `/login`, `/register`, `/contact`, `/forgot-password`
- [ ] Under Attack Mode (optional, temporary during incidents)
- [ ] Browser Integrity Check = ON
- [ ] Security Level = Medium or High (traffic-dependent)
- [ ] Auto Minify (HTML/CSS/JS) = ON (validate site first)
- [ ] Brotli = ON
- [ ] Caching level appropriate (Standard)
- [ ] Cache Rules/Page Rules: bypass cache for auth and account pages

Notes:
- This app is Python/Flask (not WordPress), so XML-RPC disabling is N/A.
- Keep Cloudflare IP list updated in Nginx real IP config.
