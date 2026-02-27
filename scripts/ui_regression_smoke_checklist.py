#!/usr/bin/env python3
"""Local UI regression smoke checklist (Flask test client based).

This script avoids browser/runtime dependencies while still validating:
- route renders (no 500)
- key public page UI markers (home, achievements, goals, auth screens)
- PWA preview pages
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _status_line(result: CheckResult) -> str:
    flag = "PASS" if result.ok else "FAIL"
    return f"[{flag}] {result.name}: {result.detail}"


def run_checks() -> int:
    from app import app

    checks: list[CheckResult] = []
    client = app.test_client()

    def page_check(path: str, must_contain: Iterable[str] = ()) -> None:
        resp = client.get(path)
        if resp.status_code >= 500:
            checks.append(CheckResult(path, False, f"HTTP {resp.status_code}"))
            return
        body = resp.get_data(as_text=True)
        missing = [token for token in must_contain if token not in body]
        if missing:
            checks.append(CheckResult(path, False, f"missing markers: {', '.join(missing[:4])}"))
            return
        checks.append(CheckResult(path, True, f"HTTP {resp.status_code}"))

    page_check(
        "/",
        must_contain=[
            "Securely Manage Your Achievements",
            "Secure Web Platform",
            "Easy Achievement Timeline",
        ],
    )
    page_check(
        "/achievements",
        must_contain=[
            "Achievements",
            "Verified Achievement Records",
        ],
    )
    page_check(
        "/goals",
        must_contain=[
            "Goals",
            "Share Tips / Tricks / Career Post",
        ],
    )
    page_check(
        "/login",
        must_contain=[
            "Secure Access",
            "Login",
        ],
    )
    page_check(
        "/register",
        must_contain=[
            "Create Your Account",
            "Email Verification Required",
        ],
    )
    page_check("/pwa-preview?layout=wide")
    page_check("/pwa-preview?layout=mobile")

    print("UI Regression Smoke Checklist")
    print("=" * 32)
    failures = 0
    for item in checks:
        print(_status_line(item))
        if not item.ok:
            failures += 1
    print("-" * 32)
    print(f"Total: {len(checks)}  Passed: {len(checks) - failures}  Failed: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
