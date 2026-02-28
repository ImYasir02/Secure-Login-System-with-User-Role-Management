#!/usr/bin/env python3
"""Deeper local regression checklist (public/auth/admin/uploads).

Modes:
- default      : public checks + public form validation
- --auth       : adds authenticated user checks and user form actions
- --full       : adds owner/admin smoke + upload validation/success paths
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc````\x00\x00\x00\x05\x00\x01\xa5\xf6E@"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)
PDF_MIN = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
TEXT_BYTES = b"this is not a valid png or pdf"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _status_line(result: CheckResult) -> str:
    return f"[{'PASS' if result.ok else 'FAIL'}] {result.name}: {result.detail}"


def run_checks(include_auth: bool = False, include_full: bool = False) -> int:
    from app import (
        ActivityLog,
        Achievement,
        ContactMessage,
        Goal,
        GoalTipPost,
        LoginAttempt,
        Post,
        RATE_LIMIT_BUCKETS,
        User,
        app,
        bcrypt,
        db,
        remove_file_if_exists,
    )

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["RECAPTCHA_SECRET_KEY"] = ""
    app.config["ENABLE_VIRUS_SCAN"] = False

    checks: list[CheckResult] = []
    stamp = str(time.time_ns())

    user_email = f"codex.user.{stamp}@example.com"
    user_password = "SmokePass123!"
    user_name = f"codex_user_{stamp}"

    admin_email = f"codex.admin.{stamp}@example.com"
    admin_password = "SmokePass123!"
    admin_name = f"codex_admin_{stamp}"

    owner_email = f"codex.owner.{stamp}@example.com"
    owner_password = "SmokePass123!"
    owner_name = f"codex_owner_{stamp}"

    created_user_ids: set[int] = set()
    managed_created_user_email = f"managed.user.{stamp}@example.com"
    test_contact_name = f"Smoke Contact {stamp}"
    test_goal_title = f"Smoke Goal {stamp}"
    test_tip_title = f"Smoke Tip {stamp}"
    test_about_title = f"Smoke About Post {stamp}"
    test_ach_title = f"Smoke Achievement {stamp}"

    with app.app_context():
        db.create_all()

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append(CheckResult(name, ok, detail))

    def assert_contains(name: str, resp, tokens: Iterable[str], expected_status: int | None = None) -> None:
        body = resp.get_data(as_text=True)
        if expected_status is not None and resp.status_code != expected_status:
            add(name, False, f"HTTP {resp.status_code} (expected {expected_status})")
            return
        missing = [t for t in tokens if t not in body]
        if missing:
            add(name, False, f"missing markers: {', '.join(missing[:4])}")
            return
        add(name, True, f"HTTP {resp.status_code}")

    def post_multipart(client, path: str, data: dict, *, follow_redirects: bool = True):
        return client.post(path, data=data, content_type="multipart/form-data", follow_redirects=follow_redirects)

    def clear_rate_limits() -> None:
        RATE_LIMIT_BUCKETS.clear()

    def ensure_user(email: str, username: str, password: str, role: str) -> int:
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
                    role=role,
                    is_active_user=True,
                    is_email_verified=True,
                )
                db.session.add(user)
                db.session.commit()
            created_user_ids.add(user.id)
            return int(user.id)

    def login_and_assert(client, email: str, password: str, name: str) -> None:
        clear_rate_limits()
        resp = client.post("/login", data={"email": email, "password": password}, follow_redirects=True)
        assert_contains(name, resp, ["login_success"])

    def cleanup() -> None:
        with app.app_context():
            try:
                # Collect file paths before row deletion.
                post_rows = Post.query.filter_by(title=test_about_title).all()
            except Exception:
                post_rows = []
            try:
                ach_rows = Achievement.query.filter_by(title=test_ach_title).all()
                tip_rows = GoalTipPost.query.filter_by(title=test_tip_title).all()
                contact_rows = ContactMessage.query.filter(
                    (ContactMessage.email.in_([user_email, admin_email, owner_email]))
                    | (ContactMessage.name == test_contact_name)
                ).all()
                upload_folder = app.config.get("UPLOAD_FOLDER", "")
                for row in post_rows:
                    remove_file_if_exists(str(Path(upload_folder) / (row.stored_filename or "")))
                for row in ach_rows:
                    remove_file_if_exists(str(Path(upload_folder) / (row.document_stored or "")))
                for row in tip_rows:
                    remove_file_if_exists(str(Path(upload_folder) / (row.attachment_stored or "")))
                for row in contact_rows:
                    remove_file_if_exists(str(Path(upload_folder) / (row.attachment_stored or "")))

                ActivityLog.query.filter(ActivityLog.user_id.in_(list(created_user_ids))).delete(synchronize_session=False)
                Goal.query.filter_by(title=test_goal_title).delete(synchronize_session=False)
                Goal.query.filter(Goal.owner_id.in_(list(created_user_ids))).delete(synchronize_session=False)
                Achievement.query.filter_by(title=test_ach_title).delete(synchronize_session=False)
                Post.query.filter_by(title=test_about_title).delete(synchronize_session=False)
                GoalTipPost.query.filter_by(title=test_tip_title).delete(synchronize_session=False)
                ContactMessage.query.filter(
                    (ContactMessage.email.in_([user_email, admin_email, owner_email]))
                    | (ContactMessage.name == test_contact_name)
                ).delete(synchronize_session=False)
                LoginAttempt.query.filter(
                    LoginAttempt.email.in_(
                        [user_email, admin_email, owner_email, "nobody@example.com", managed_created_user_email]
                    )
                ).delete(synchronize_session=False)
                if created_user_ids:
                    User.query.filter(User.id.in_(list(created_user_ids))).delete(synchronize_session=False)
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                add("cleanup", False, repr(exc))

    try:
        public_client = app.test_client()

        # Public GET checks
        assert_contains(
            "GET /",
            public_client.get("/"),
            ["Securely Manage Your Achievements", "Easy Achievement Timeline", "Secure Web Platform"],
            200,
        )
        assert_contains("GET /achievements", public_client.get("/achievements"), ["Verified Achievement Records"], 200)
        assert_contains("GET /goals", public_client.get("/goals"), ["Goals", "Share Tips / Tricks / Career Post"], 200)
        assert_contains("GET /contact", public_client.get("/contact"), ["Contact", "subject", "message"], 200)
        assert_contains("GET /register", public_client.get("/register"), ["Create Your Account"], 200)
        assert_contains("GET /login", public_client.get("/login"), ["Secure Access", "Login"], 200)
        assert_contains("GET /pwa wide", public_client.get("/pwa-preview?layout=wide"), ["SecureLogin"], 200)
        assert_contains("GET /pwa mobile", public_client.get("/pwa-preview?layout=mobile"), ["SecureLogin"], 200)

        # Public form validation
        assert_contains(
            "POST /register missing fields",
            public_client.post("/register", data={"username": "", "email": "", "password": "", "confirm_password": ""}, follow_redirects=True),
            ["All fields are required."],
        )
        assert_contains(
            "POST /register mismatch",
            public_client.post(
                "/register",
                data={
                    "username": "tmpuser",
                    "email": "tmp@example.com",
                    "password": "Password123!",
                    "confirm_password": "Password999!",
                    "accept_terms": "on",
                },
                follow_redirects=True,
            ),
            ["Password and confirm password must match."],
        )
        assert_contains(
            "POST /register terms required",
            public_client.post(
                "/register",
                data={
                    "username": "tmpuser",
                    "email": "tmp@example.com",
                    "password": "Password123!",
                    "confirm_password": "Password123!",
                },
                follow_redirects=True,
            ),
            ["Please accept Terms and Privacy Policy."],
        )
        assert_contains(
            "POST /login missing fields",
            public_client.post("/login", data={"email": "", "password": ""}, follow_redirects=True),
            ["Email and password are required."],
        )
        clear_rate_limits()
        assert_contains(
            "POST /login invalid credentials",
            public_client.post(
                "/login",
                data={"email": "nobody@example.com", "password": "WrongPass123!"},
                follow_redirects=True,
            ),
            ["Invalid credentials."],
        )
        clear_rate_limits()
        assert_contains(
            "POST /contact missing fields",
            public_client.post("/contact", data={"name": "", "email": "", "subject": "", "message": ""}, follow_redirects=True),
            ["All contact fields are required."],
        )
        assert_contains(
            "POST /goals personal goal unauth",
            public_client.post("/goals", data={"action": "goal", "title": "Guest Goal", "description": "x"}, follow_redirects=True),
            ["Login required to add personal goals.", "Login"],
        )
        assert_contains(
            "POST /goals tip validation unauth",
            public_client.post("/goals", data={"action": "tip", "author_name": "", "title": "", "content": ""}, follow_redirects=True),
            ["Author name, title, and content are required for tips."],
        )

        if not (include_auth or include_full):
            # Default mode stops at public + public validation checks.
            pass
        else:
            ensure_user(user_email, user_name, user_password, "user")

            auth_client = app.test_client()
            login_and_assert(auth_client, user_email, user_password, "POST /login success (user)")

            # Authenticated GET checks
            assert_contains("GET /dashboard (auth)", auth_client.get("/dashboard", follow_redirects=True), ["User Dashboard", "Security Status"], 200)
            assert_contains("GET /profile (auth)", auth_client.get("/profile"), ["Profile"], 200)
            assert_contains("GET /settings (auth)", auth_client.get("/settings"), ["Settings", "Save Settings"], 200)
            assert_contains(
                "GET /security-settings (auth)",
                auth_client.get("/security-settings"),
                ["Security Settings"],
                200,
            )
            assert_contains("GET /about (auth)", auth_client.get("/about"), ["About Me"], 200)
            assert_contains("GET /achievements (auth)", auth_client.get("/achievements"), ["Verified Achievement Records"], 200)

            # Authenticated form validations and success paths
            assert_contains(
                "POST /goals goal validation auth",
                auth_client.post("/goals", data={"action": "goal", "title": "", "description": "desc"}, follow_redirects=True),
                ["Goal title is required."],
            )
            assert_contains(
                "POST /goals goal success auth",
                auth_client.post(
                    "/goals",
                    data={
                        "action": "goal",
                        "title": test_goal_title,
                        "description": "Deeper smoke goal check",
                        "target_date": "",
                        "priority": "medium",
                        "status": "in_progress",
                        "milestones": "m1\nm2",
                        "progress_percent": "15",
                    },
                    follow_redirects=True,
                ),
                ["Goal added."],
            )
            assert_contains(
                "POST /goals tip success auth",
                auth_client.post(
                    "/goals",
                    data={
                        "action": "tip",
                        "author_name": user_name,
                        "title": test_tip_title,
                        "content": "Smoke tip content",
                        "visibility_status": "private",
                    },
                    follow_redirects=True,
                ),
                ["Tip shared successfully."],
            )
            assert_contains(
                "POST /settings save auth",
                auth_client.post("/settings", data={"action": "save", "email_updates": "on"}, follow_redirects=True),
                ["Settings saved successfully."],
            )

            clear_rate_limits()
            assert_contains(
                "POST /contact success",
                public_client.post(
                    "/contact",
                    data={
                        "name": test_contact_name,
                        "email": user_email,
                        "subject": "General Inquiry",
                        "message": "Smoke contact message",
                    },
                    follow_redirects=True,
                ),
                ["Message submitted successfully."],
            )

            if include_full:
                ensure_user(admin_email, admin_name, admin_password, "admin")
                owner_id = ensure_user(owner_email, owner_name, owner_password, "owner")

                # Owner/admin route smoke
                owner_client = app.test_client()
                admin_client = app.test_client()
                login_and_assert(owner_client, owner_email, owner_password, "POST /login success (owner)")
                login_and_assert(admin_client, admin_email, admin_password, "POST /login success (admin)")

                assert_contains("GET /owner (owner)", owner_client.get("/owner"), ["Admin Dashboard", "User Management"], 200)
                assert_contains("GET /user-management (owner)", owner_client.get("/user-management"), ["User Management"], 200)
                assert_contains("GET /contact-messages (owner)", owner_client.get("/contact-messages"), ["Contact Messages View"], 200)

                assert_contains("GET /owner (admin)", admin_client.get("/owner"), ["Admin Dashboard"], 200)
                assert_contains("GET /admin alias (admin)", admin_client.get("/admin", follow_redirects=True), ["Admin Dashboard"], 200)

                # Admin should not manage owner account.
                assert_contains(
                    "POST /user-management admin block owner",
                    admin_client.post(
                        "/user-management",
                        data={"action": "toggle_active", "user_id": str(owner_id)},
                        follow_redirects=True,
                    ),
                    ["Admin cannot manage owner account."],
                )

                clear_rate_limits()
                assert_contains(
                    "POST /user-management create by owner",
                    owner_client.post(
                        "/user-management",
                        data={
                            "action": "create",
                            "username": f"managed_{stamp}",
                            "email": managed_created_user_email,
                            "password": "ManagedPass123!",
                            "role": "user",
                        },
                        follow_redirects=True,
                    ),
                    ["User created successfully."],
                )
                with app.app_context():
                    managed = User.query.filter_by(email=managed_created_user_email).first()
                    if managed:
                        created_user_ids.add(managed.id)

                # Upload validation + success paths using in-memory files.
                # About upload invalid file
                assert_contains(
                    "POST /about/upload invalid file",
                    post_multipart(
                        auth_client,
                        "/about/upload",
                        {
                            "title": test_about_title,
                            "description": "about post invalid",
                            "category": "certificate",
                            "file": (io.BytesIO(TEXT_BYTES), "bad.png", "image/png"),
                        },
                    ),
                    ["Invalid file type."],
                )
                # About upload valid PDF
                assert_contains(
                    "POST /about/upload valid pdf",
                    post_multipart(
                        auth_client,
                        "/about/upload",
                        {
                            "title": test_about_title,
                            "description": "about post pdf",
                            "category": "certificate",
                            "file": (io.BytesIO(PDF_MIN), "about.pdf", "application/pdf"),
                        },
                    ),
                    ["Post uploaded successfully."],
                )

                # Achievements invalid and valid upload
                clear_rate_limits()
                assert_contains(
                    "POST /achievements invalid file",
                    post_multipart(
                        auth_client,
                        "/achievements",
                        {
                            "metadata_mode": "manual",
                            "title": test_ach_title,
                            "issuer": "Smoke Issuer",
                            "achievement_date": "2025-01-01",
                            "description": "bad achievement doc",
                            "document_label": "Bad Doc",
                            "category": "certificate",
                            "visibility_status": "private",
                            "verification_status": "pending",
                            "document": (io.BytesIO(TEXT_BYTES), "bad.png", "image/png"),
                        },
                    ),
                    ["Invalid file type."],
                )
                clear_rate_limits()
                assert_contains(
                    "POST /achievements valid png",
                    post_multipart(
                        auth_client,
                        "/achievements",
                        {
                            "metadata_mode": "manual",
                            "title": test_ach_title,
                            "issuer": "Smoke Issuer",
                            "achievement_date": "2025-01-01",
                            "description": "valid achievement doc",
                            "document_label": "Achievement PNG",
                            "category": "certificate",
                            "visibility_status": "private",
                            "verification_status": "pending",
                            "document": (io.BytesIO(PNG_1X1), "ach.png", "image/png"),
                        },
                    ),
                    ["Achievement added successfully."],
                )

                # Goals tip attachment invalid + valid PDF
                assert_contains(
                    "POST /goals tip attachment invalid",
                    post_multipart(
                        auth_client,
                        "/goals",
                        {
                            "action": "tip",
                            "author_name": user_name,
                            "title": f"{test_tip_title} invalid attachment",
                            "content": "tip with invalid attachment",
                            "visibility_status": "private",
                            "tip_attachment": (io.BytesIO(TEXT_BYTES), "tip.png", "image/png"),
                        },
                    ),
                    ["Tips attachment content is invalid."],
                )
                assert_contains(
                    "POST /goals tip attachment valid pdf",
                    post_multipart(
                        auth_client,
                        "/goals",
                        {
                            "action": "tip",
                            "author_name": user_name,
                            "title": f"{test_tip_title} with attachment",
                            "content": "tip with valid attachment",
                            "visibility_status": "private",
                            "tip_attachment": (io.BytesIO(PDF_MIN), "tip.pdf", "application/pdf"),
                        },
                    ),
                    ["Tip shared successfully."],
                )

                # Contact image attachment invalid + valid PNG
                clear_rate_limits()
                assert_contains(
                    "POST /contact issue_image invalid",
                    post_multipart(
                        public_client,
                        "/contact",
                        {
                            "name": test_contact_name,
                            "email": user_email,
                            "subject": "General Inquiry",
                            "message": "invalid screenshot",
                            "issue_image": (io.BytesIO(TEXT_BYTES), "issue.png", "image/png"),
                        },
                    ),
                    ["Issue screenshot content is invalid."],
                )
                clear_rate_limits()
                assert_contains(
                    "POST /contact issue_image valid png",
                    post_multipart(
                        public_client,
                        "/contact",
                        {
                            "name": test_contact_name,
                            "email": user_email,
                            "subject": "Report a Bug",
                            "message": "valid screenshot",
                            "issue_image": (io.BytesIO(PNG_1X1), "issue.png", "image/png"),
                        },
                    ),
                    ["Message submitted successfully."],
                )

    finally:
        cleanup()

    mode_name = "full" if include_full else "auth" if include_auth else "public"
    print(f"Deep Regression Auth Checklist ({mode_name})")
    print("=" * 40)
    failures = 0
    for item in checks:
        print(_status_line(item))
        if not item.ok:
            failures += 1
    print("-" * 40)
    print(f"Total: {len(checks)}  Passed: {len(checks)-failures}  Failed: {failures}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deeper regression smoke checks (public/auth/full).")
    parser.add_argument("--auth", action="store_true", help="Include authenticated user smoke checks.")
    parser.add_argument("--full", action="store_true", help="Include auth checks + owner/admin + upload path checks.")
    args = parser.parse_args()

    include_full = bool(args.full)
    include_auth = bool(args.auth or include_full)
    return run_checks(include_auth=include_auth, include_full=include_full)


if __name__ == "__main__":
    raise SystemExit(main())
