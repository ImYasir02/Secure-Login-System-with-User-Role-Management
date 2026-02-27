# SecureLogin

## UI QA & PWA Tools

- Manual QA checklist: `docs/UI_QA_CHECKLIST.md`
- UI regression smoke checklist: `scripts/ui_regression_smoke_checklist.py`
- PWA screenshot capture script: `scripts/capture_pwa_screenshots.py`

### Quick Commands

Run UI smoke checklist:

```bash
./venv/bin/python scripts/ui_regression_smoke_checklist.py
```

Capture PWA screenshots (default PNG):

```bash
./venv/bin/python scripts/capture_pwa_screenshots.py --auto-start --env-file .env
```

Capture only mobile screenshot (WEBP):

```bash
./venv/bin/python scripts/capture_pwa_screenshots.py --auto-start --env-file .env --only mobile --format webp
```
