# Security Automation Setup (GitHub Actions)

This document explains how to configure and run the security verification workflows added to this repository.

## What You Already Have

### Scripts
- `verify_security.sh` (terminal security header checks)
- `verify_security_report.sh` (markdown report generator)
- `verify_security_json.sh` (JSON output for CI/CD)

### GitHub Actions Workflows
- `.github/workflows/security-headers-check.yml`
  - Single target (manual + scheduled)
- `.github/workflows/security-headers-check-matrix.yml`
  - Staging + Production matrix (manual + scheduled)

---

## 1. GitHub Actions Variables / Secrets to Create

Go to:
- `GitHub Repo -> Settings -> Secrets and variables -> Actions`

Create the following.

## A) For Single-Target Workflow (optional but recommended)

### Variable or Secret
- `SECURITY_CHECK_TARGET_URL`

Example values:
- `https://example.com`
- `example.com`

### Optional Variable
- `SECURITY_CHECK_CLOUDFLARE`

Allowed values:
- `true`
- `false`

Use `true` if your site is behind Cloudflare and you expect `CF-*` headers.

## B) For Matrix Workflow (Staging + Production)

### Required (Variables or Secrets)
- `SECURITY_CHECK_STAGING_URL`
- `SECURITY_CHECK_PRODUCTION_URL`

Example:
- `SECURITY_CHECK_STAGING_URL=https://staging.example.com`
- `SECURITY_CHECK_PRODUCTION_URL=https://example.com`

### Optional (Variables)
- `SECURITY_CHECK_STAGING_CLOUDFLARE`
- `SECURITY_CHECK_PRODUCTION_CLOUDFLARE`

Values:
- `true`
- `false`

---

## 2. Variable vs Secret (Which One to Use?)

Use **Variables** if:
- Domain names are public and not sensitive

Use **Secrets** if:
- You prefer not exposing target URLs in workflow env/debug logs

Either works because the workflows support both.

Priority used by workflows:

### Single-target workflow
1. manual input `target_url`
2. repo variable `SECURITY_CHECK_TARGET_URL`
3. repo secret `SECURITY_CHECK_TARGET_URL`

### Matrix workflow
- Staging: variable first, then secret
- Production: variable first, then secret

---

## 3. How to Run (Single Target Workflow)

Workflow file:
- `.github/workflows/security-headers-check.yml`

### Manual run
1. Open `Actions` tab in GitHub
2. Select `Security Headers Check`
3. Click `Run workflow`
4. (Optional) Fill:
   - `target_url`
   - `cloudflare_expected`
5. Run

### Scheduled run
- Runs daily automatically (if workflow enabled and repository has activity)

---

## 4. How to Run (Staging + Production Matrix Workflow)

Workflow file:
- `.github/workflows/security-headers-check-matrix.yml`

### Manual run
1. Open `Actions`
2. Select `Security Headers Check (Staging + Production)`
3. Click `Run workflow`
4. Choose:
   - `run_staging = true/false`
   - `run_production = true/false`
5. Run

### Scheduled run
- Runs daily automatically
- Uses configured staging/production URLs from variables/secrets

---

## 5. What the Workflows Generate

Artifacts are uploaded automatically.

### Single-target workflow artifacts
- `reports/security_report.json`
- `reports/security_report.md`

### Matrix workflow artifacts
Per environment:
- `reports/staging/security_report.json`
- `reports/staging/security_report.md`
- `reports/production/security_report.json`
- `reports/production/security_report.md`

Artifact names include workflow run number.

---

## 6. How Workflow Success/Failure Works

The workflow will **FAIL** if:
- `verify_security_json.sh` returns non-zero
- required target URL variable/secret is missing
- security checks detect failures (e.g., missing CSP/HSTS)

The workflow may still produce artifacts even when failing (this is intentional, for debugging).

---

## 7. Reading the Results

## JSON report (`security_report.json`)
Best for:
- CI/CD integrations
- dashboards
- machine parsing

Includes:
- status (`PASS`, `PASS_WITH_WARNINGS`, `FAIL`, `ERROR`)
- counts (`pass/warn/fail/info`)
- arrays of messages
- raw output

## Markdown report (`security_report.md`)
Best for:
- sharing with team
- audit evidence
- manual review

Includes:
- summary
- command used
- raw checker output

---

## 8. Recommended CI Policy

Start with:
- Fail on `FAIL`
- Allow `WARN` (workflow passes with warnings)

Then tighten later:
- Review warnings and fix them
- Adjust `verify_security.sh` logic if you want stricter org-specific policies

---

## 9. Common Setup Mistakes (and Fixes)

### Problem: Workflow says target URL not configured
Fix:
- Add `SECURITY_CHECK_TARGET_URL` (single workflow), or
- Add `SECURITY_CHECK_STAGING_URL` / `SECURITY_CHECK_PRODUCTION_URL` (matrix workflow)

### Problem: Cloudflare check fails
Fix:
- Confirm site is actually proxied through Cloudflare (orange cloud)
- Set `*_CLOUDFLARE=false` if not using Cloudflare yet

### Problem: HSTS missing
Fix:
- Ensure HTTPS request terminates at Nginx with `Strict-Transport-Security`
- Make sure checker is hitting real production domain over HTTPS

### Problem: Server header exposed
Fix:
- Ensure Nginx `server_tokens off;`
- Use `proxy_hide_header Server;`
- Confirm upstream/proxy does not inject backend server header

---

## 10. Best-Practice Rollout Order

1. Configure **single-target workflow** on staging
2. Fix header/security issues until green
3. Configure **matrix workflow** with staging + production
4. Enable scheduled runs
5. Review artifacts weekly / after infra changes

---

## 11. Optional Next Enhancements

You can add later:
- GitHub issue auto-creation when workflow fails
- Slack/Discord alert on failure
- JSON schema validation in CI
- Security baseline diffing between runs
- TLS/SSL Labs API checks (separate workflow)

