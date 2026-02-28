from datetime import date, datetime, timedelta
import os
import uuid
import re
import csv
import zipfile
import io
import base64
import hashlib
import smtplib
import json
import subprocess
import tempfile
import mimetypes
import time
from email.message import EmailMessage
from urllib import request as urllib_request
from urllib import parse as urllib_parse
from xml.etree import ElementTree as ET
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, session, jsonify, g, Response, has_request_context, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import inspect, text, or_, func, case
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from backend.services.jwt_token_service import issue_token_pair, decode_token, JWTTokenError
from backend.controllers.auth_api_controller import auth_success_payload, auth_error_payload
from backend.routes.api_route_factory import create_auth_api_blueprint

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()


try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

try:
    import pyotp
except ImportError:
    pyotp = None

# Flask app
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

# Runtime environment
APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"

# Security config
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///secure_login.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
max_content_mb_raw = (os.environ.get("MAX_CONTENT_LENGTH_MB", "0") or "0").strip()
try:
    max_content_mb = int(max_content_mb_raw)
except ValueError:
    max_content_mb = 0
app.config["MAX_CONTENT_LENGTH"] = None if max_content_mb <= 0 else max_content_mb * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
app.config["RECAPTCHA_SECRET_KEY"] = os.environ.get("RECAPTCHA_SECRET_KEY", "")
app.config["RECAPTCHA_SITE_KEY"] = os.environ.get("RECAPTCHA_SITE_KEY", "")
app.config["LOGIN_MAX_ATTEMPTS"] = 5
app.config["LOGIN_BLOCK_MINUTES"] = 15
app.config["CONTACT_MAX_ATTEMPTS"] = 12
app.config["CONTACT_BLOCK_MINUTES"] = 10
app.config["USER_CREATE_MAX_ATTEMPTS"] = 15
app.config["USER_CREATE_BLOCK_MINUTES"] = 10
app.config["ACHIEVEMENT_MAX_ATTEMPTS"] = 20
app.config["ACHIEVEMENT_BLOCK_MINUTES"] = 10
app.config["VAULT_MAX_ATTEMPTS"] = 40
app.config["VAULT_BLOCK_MINUTES"] = 10
app.config["VAULT_ACCESS_MAX_ATTEMPTS"] = int(os.environ.get("VAULT_ACCESS_MAX_ATTEMPTS", "5"))
app.config["VAULT_ACCESS_LOCK_MINUTES"] = int(os.environ.get("VAULT_ACCESS_LOCK_MINUTES", "10"))
app.config["COMMENT_COOLDOWN_SECONDS"] = 20
app.config["JWT_ACCESS_EXPIRES_MINUTES"] = int(os.environ.get("JWT_ACCESS_EXPIRES_MINUTES", "15"))
app.config["JWT_REFRESH_EXPIRES_DAYS"] = int(os.environ.get("JWT_REFRESH_EXPIRES_DAYS", "7"))

# Safer session defaults
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "1" if IS_PRODUCTION else "0") == "1"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = app.config["SESSION_COOKIE_SECURE"]
app.config["REMEMBER_COOKIE_SAMESITE"] = "Strict"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=45)
app.config["PROPAGATE_EXCEPTIONS"] = False
app.config["REQUIRE_EMAIL_VERIFICATION"] = os.environ.get("REQUIRE_EMAIL_VERIFICATION", "0") == "1"
app.config["ADMIN_SIGNUP_KEY"] = (os.environ.get("ADMIN_SIGNUP_KEY", "") or "").strip()
app.config["CONTACT_PUBLIC_EMAIL"] = (os.environ.get("CONTACT_PUBLIC_EMAIL", "yasirsec21@gmail.com") or "yasirsec21@gmail.com").strip()
smtp_port_raw = (os.environ.get("SMTP_PORT", "587") or "587").strip()
app.config["SMTP_FROM_EMAIL"] = (os.environ.get("SMTP_FROM_EMAIL", os.environ.get("SMTP_USER", "")) or "").strip()
app.config["CONTACT_NOTIFY_EMAIL"] = (
    os.environ.get("CONTACT_NOTIFY_EMAIL", app.config["CONTACT_PUBLIC_EMAIL"])
    or app.config["CONTACT_PUBLIC_EMAIL"]
).strip()
app.config["SMTP_USE_SSL"] = (os.environ.get("SMTP_USE_SSL", "1" if smtp_port_raw == "465" else "0") == "1")
app.config["SMTP_USE_TLS"] = (os.environ.get("SMTP_USE_TLS", "0" if smtp_port_raw == "465" else "1") == "1")
app.config["ENFORCE_HTTPS"] = os.environ.get("ENFORCE_HTTPS", "1" if IS_PRODUCTION else "0") == "1"
app.config["APP_VERSION"] = os.environ.get("APP_VERSION", "1.0.0")
app.config["SOCIAL_X_URL"] = (os.environ.get("SOCIAL_X_URL", "https://x.com") or "https://x.com").strip()
app.config["SOCIAL_LINKEDIN_URL"] = (os.environ.get("SOCIAL_LINKEDIN_URL", "https://www.linkedin.com") or "https://www.linkedin.com").strip()
app.config["SOCIAL_GITHUB_URL"] = (os.environ.get("SOCIAL_GITHUB_URL", "https://github.com/ImYasir02") or "https://github.com/ImYasir02").strip()
app.config["ENABLE_VIRUS_SCAN"] = os.environ.get("ENABLE_VIRUS_SCAN", "0") == "1"
app.config["PREFERRED_URL_SCHEME"] = "https" if app.config["ENFORCE_HTTPS"] else "http"
app.config["PROXY_FIX_ENABLED"] = os.environ.get("PROXY_FIX_ENABLED", "1" if IS_PRODUCTION else "0") == "1"
app.config["TRUST_X_FOR"] = int(os.environ.get("TRUST_X_FOR", "1"))
app.config["TRUST_X_PROTO"] = int(os.environ.get("TRUST_X_PROTO", "1"))
app.config["TRUST_X_HOST"] = int(os.environ.get("TRUST_X_HOST", "1"))
app.config["TRUST_X_PORT"] = int(os.environ.get("TRUST_X_PORT", "1"))
app.config["TRUST_X_PREFIX"] = int(os.environ.get("TRUST_X_PREFIX", "0"))
app.config["SECURITY_CSP"] = os.environ.get(
    "SECURITY_CSP",
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "script-src 'self' https://cdn.tailwindcss.com https://www.google.com https://www.gstatic.com 'unsafe-inline'; "
    "style-src 'self' https: 'unsafe-inline'; "
    "font-src 'self' https: data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'; "
    "upgrade-insecure-requests"
)

if app.config["PROXY_FIX_ENABLED"]:
    app.wsgi_app = ProxyFix(  # type: ignore[assignment]
        app.wsgi_app,
        x_for=app.config["TRUST_X_FOR"],
        x_proto=app.config["TRUST_X_PROTO"],
        x_host=app.config["TRUST_X_HOST"],
        x_port=app.config["TRUST_X_PORT"],
        x_prefix=app.config["TRUST_X_PREFIX"],
    )


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

ALLOWED_POST_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
ALLOWED_ACHIEVEMENT_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "pdf",
}
ALLOWED_CATEGORIES = {"hall_of_fame", "bug_bounty", "recognition", "certificate"}
ALLOWED_ACHIEVEMENT_CATEGORIES = {"certificate", "award", "exam", "project", "other"}
ALLOWED_VISIBILITY_STATUS = {"private", "public"}
ALLOWED_VERIFICATION_STATUS = {"pending", "verified"}
ALLOWED_ROLES = {"owner", "admin", "user"}
CONTACT_SUBJECT_OPTIONS = [
    "Account Support",
    "Document Storage Help",
    "Achievement Upload Issue",
    "Goal Tracking Support",
    "Feedback / Suggestions",
    "Report a Bug",
    "Partnership / Collaboration",
    "General Inquiry",
    "Other",
]
ALLOWED_CONTACT_SUBJECTS = set(CONTACT_SUBJECT_OPTIONS)
ALLOWED_CONTACT_ATTACHMENT_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_TIP_ATTACHMENT_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
SPECIAL_ABOUT_EMAIL = "yasir123@gmail.com"
PUBLIC_ABOUT_PROFILE = {
    "name": "Md Yasir",
    "email": "yasirsec21@gmail.com",
    "title": "About Me",
    "intro": (
        "My name is Md Yasir, and I am a cybersecurity enthusiast with over two years of practical "
        "experience in bug bounty hunting and vulnerability research. I have responsibly reported "
        "security issues to organizations, earning Hall of Fame recognition and bounty rewards, "
        "which reflects my commitment to ethical security practices."
    ),
    "experience": (
        "I have completed multiple cybersecurity certifications and structured training programs "
        "covering networking fundamentals, Linux systems, and Python programming. Through internships "
        "and hands-on projects, including the development of secure login systems with role-based "
        "access control, I have gained practical experience in secure application design and defensive "
        "security implementation."
    ),
    "goal": (
        "I am passionate about identifying real-world vulnerabilities, strengthening application "
        "security, and continuously improving my technical expertise. My goal is to contribute to "
        "building secure, reliable, and resilient digital systems while maintaining strong ethical "
        "standards in cybersecurity."
    ),
}
RATE_LIMIT_BUCKETS = {}
COMMENT_COOLDOWN_TRACKER = {}


# ---------- DB Models ----------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    is_active_user = db.Column(db.Boolean, nullable=False, default=True)
    is_email_verified = db.Column(db.Boolean, nullable=False, default=False)
    twofa_secret = db.Column(db.String(64), nullable=True)
    twofa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    login_lock_until = db.Column(db.DateTime, nullable=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    session_version = db.Column(db.Integer, nullable=False, default=1)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(64), nullable=True)
    about_page_title = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_active(self):
        return bool(self.is_active_user)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    attachment_original = db.Column(db.String(255), nullable=True)
    attachment_stored = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    ip_address = db.Column(db.String(64), nullable=False)
    success = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    issuer = db.Column(db.String(120), nullable=False)
    achievement_date = db.Column(db.Date, nullable=False)
    achievement_date_text = db.Column(db.String(40), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(20), nullable=False, default="other")
    visibility_status = db.Column(db.String(20), nullable=False, default="private")
    verification_status = db.Column(db.String(20), nullable=False, default="pending")
    document_label = db.Column(db.String(160), nullable=True)
    document_original = db.Column(db.String(255), nullable=False)
    document_stored = db.Column(db.String(255), unique=True, nullable=False)
    metadata_mode = db.Column(db.String(20), nullable=False, default="manual")
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(20), nullable=False, default="medium")
    status = db.Column(db.String(20), nullable=False, default="in_progress")
    progress_percent = db.Column(db.Integer, nullable=False, default=0)
    milestones = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VaultFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    label = db.Column(db.String(160), nullable=False)
    folder_tag = db.Column(db.String(80), nullable=True, index=True)
    note = db.Column(db.Text, nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    extension = db.Column(db.String(20), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    visibility_status = db.Column(db.String(20), nullable=False, default="private")
    share_enabled = db.Column(db.Boolean, nullable=False, default=False)
    share_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    share_expires_at = db.Column(db.DateTime, nullable=True)
    pin_hash = db.Column(db.String(200), nullable=True)
    pin_failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    pin_locked_until = db.Column(db.DateTime, nullable=True)
    download_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    event_type = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class VaultFileHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vault_file_id = db.Column(db.Integer, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    event_type = db.Column(db.String(40), nullable=False)
    details = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)



class RefreshToken(db.Model):
    __tablename__ = "refresh_token"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    jti = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    replaced_by_jti = db.Column(db.String(64), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)





class GoalTipPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.Text, nullable=False)
    visibility_status = db.Column(db.String(20), nullable=False, default="private")
    attachment_original = db.Column(db.String(255), nullable=True)
    attachment_stored = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class GoalTipLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip_id = db.Column(db.Integer, db.ForeignKey("goal_tip_post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class GoalTipComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip_id = db.Column(db.Integer, db.ForeignKey("goal_tip_post.id"), nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class GoalTipSave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip_id = db.Column(db.Integer, db.ForeignKey("goal_tip_post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    saved_name = db.Column(db.String(160), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Helpers ----------
def client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()[:64]
    return (request.remote_addr or "unknown")[:64]


def normalize_role(role):
    value = (role or "user").strip().lower()
    return value if value in ALLOWED_ROLES else "user"


def flash_notice(code, message, level="info"):
    label = sanitize_text(code, 80) or "notice"
    detail = sanitize_text(message, 500, multiline=True) or ""
    flash(f"{label} {detail}".strip() if detail else label, level)


def default_about_title_for_user(user):
    if not user:
        return "My Portfolio"
    name = sanitize_text(getattr(user, "username", None), 80) or "My"
    base = (name or "My").strip() or "My"
    possessive = f"{base}'" if base.endswith(("s", "S")) else f"{base}'s"
    return sanitize_text(f"{possessive} Portfolio", 120) or "My Portfolio"


def can_upload_posts():
    return current_user.is_authenticated and normalize_role(current_user.role) in {"owner", "admin"}


def can_view_goal_tip(tip_obj):
    if not tip_obj:
        return False
    if (tip_obj.visibility_status or "private") == "public":
        return True
    if not current_user.is_authenticated:
        return False
    if is_admin_or_owner():
        return True
    return bool(tip_obj.created_by and tip_obj.created_by == current_user.id)


def is_owner():
    return current_user.is_authenticated and normalize_role(current_user.role) == "owner"


def is_admin_or_owner():
    return current_user.is_authenticated and normalize_role(current_user.role) in {"owner", "admin"}


def get_panel_endpoint(user_obj):
    role = normalize_role(getattr(user_obj, "role", "user"))
    if role in {"owner", "admin"}:
        return "admin_dashboard"
    return "user_dashboard"


def role_required(*roles):
    allowed = {normalize_role(r) for r in roles}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()

            if normalize_role(current_user.role) not in allowed:
                flash_notice(
                    "rbac_access_denied",
                    "You do not have permission to access this page.",
                    "error",
                )
                return redirect(url_for(get_panel_endpoint(current_user)))

            return func(*args, **kwargs)

        return wrapper

    return decorator


def ctx(title):
    panel_endpoint = "user_panel"
    if current_user.is_authenticated:
        panel_endpoint = get_panel_endpoint(current_user)
    return {
        "title": title,
        "created_on": date.today().isoformat(),
        "is_logged_in": current_user.is_authenticated,
        "is_admin_owner": is_admin_or_owner(),
        "is_owner": is_owner(),
        "can_upload": can_upload_posts(),
        "panel_endpoint": panel_endpoint,
        "recaptcha_site_key": app.config.get("RECAPTCHA_SITE_KEY", ""),
        "app_version": app.config.get("APP_VERSION", "1.0.0"),
        "social_x_url": app.config.get("SOCIAL_X_URL", "https://x.com"),
        "social_linkedin_url": app.config.get("SOCIAL_LINKEDIN_URL", "https://www.linkedin.com"),
        "social_github_url": app.config.get("SOCIAL_GITHUB_URL", "https://github.com/ImYasir02"),
    }


def human_time_ago(dt_value):
    if not dt_value:
        return "just now"
    now = datetime.utcnow()
    diff = now - dt_value
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    years = months // 12
    return f"{years}y ago"


@app.template_filter("timeago")
def timeago_filter(value):
    return human_time_ago(value)


def security_key_bytes():
    raw_key = os.environ.get("APP_FILE_ENCRYPTION_KEY", "")
    if not raw_key:
        raw_key = app.config["SECRET_KEY"]
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return digest


def encrypt_content_bytes(content):
    if not AESGCM:
        return content
    nonce = os.urandom(12)
    aesgcm = AESGCM(security_key_bytes())
    encrypted = aesgcm.encrypt(nonce, content, None)
    return nonce + encrypted


def decrypt_content_bytes(content):
    if not AESGCM:
        return content
    if len(content) < 13:
        raise ValueError("Corrupted encrypted file")
    nonce, payload = content[:12], content[12:]
    aesgcm = AESGCM(security_key_bytes())
    return aesgcm.decrypt(nonce, payload, None)


def log_activity(event_type, details="", user_id=None):
    entry = ActivityLog(
        user_id=user_id if user_id is not None else (current_user.id if current_user.is_authenticated else None),
        event_type=sanitize_text(event_type, 80),
        details=sanitize_text(details, 1000, multiline=True),
        ip_address=client_ip(),
    )
    db.session.add(entry)
    db.session.commit()


def log_vault_file_history(vault_file_id, event_type, details="", owner_id=None, created_by=None, auto_commit=True):
    if not vault_file_id:
        return
    owner_value = owner_id if owner_id is not None else (current_user.id if current_user.is_authenticated else None)
    if owner_value is None:
        return
    actor_value = created_by if created_by is not None else (current_user.id if current_user.is_authenticated else None)
    entry = VaultFileHistory(
        vault_file_id=int(vault_file_id),
        owner_id=int(owner_value),
        created_by=int(actor_value) if actor_value is not None else None,
        event_type=sanitize_text(event_type, 40) or "update",
        details=sanitize_text(details, 500, multiline=True),
    )
    db.session.add(entry)
    if auto_commit:
        db.session.commit()


def recaptcha_verified():
    secret = (app.config.get("RECAPTCHA_SECRET_KEY") or "").strip()
    token = (request.form.get("g-recaptcha-response") or "").strip()
    if not secret:
        return True
    if not token:
        return False
    try:
        body = urllib_parse.urlencode(
            {"secret": secret, "response": token, "remoteip": client_ip()}
        ).encode("utf-8")
        req = urllib_request.Request(
            "https://www.google.com/recaptcha/api/siteverify",
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib_request.urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return bool(payload.get("success"))
    except Exception:
        return False


def otp_required(user):
    return bool(user and user.twofa_enabled and user.twofa_secret)


def verify_totp(user, code):
    if not otp_required(user) or not pyotp:
        return False
    totp = pyotp.TOTP(user.twofa_secret)
    return totp.verify((code or "").strip(), valid_window=1)


def send_security_alert(user, reason):
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = EmailMessage()
            msg["Subject"] = "Security Alert - SecureLogin"
            msg["From"] = smtp_user
            msg["To"] = user.email
            msg.set_content(f"Security alert detected: {reason}\nIP: {client_ip()}\nTime: {datetime.utcnow().isoformat()} UTC")
            with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        except Exception:
            pass
    log_activity("security_alert", f"{reason} | {user.email}", user_id=user.id)


def send_contact_notification(contact_message):
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    notify_to = (app.config.get("CONTACT_NOTIFY_EMAIL") or smtp_user).strip()
    from_email = (app.config.get("SMTP_FROM_EMAIL") or smtp_user).strip()
    use_ssl = bool(app.config.get("SMTP_USE_SSL", False))
    use_tls = bool(app.config.get("SMTP_USE_TLS", True)) and not use_ssl
    if not (smtp_host and smtp_user and smtp_pass and notify_to and from_email):
        return False, "SMTP configuration incomplete."
    try:
        msg = EmailMessage()
        msg["Subject"] = f"New Contact Submission: {contact_message.subject[:80]}"
        msg["From"] = from_email
        msg["To"] = notify_to
        msg["Reply-To"] = contact_message.email
        attachment_note = ""
        if contact_message.attachment_original:
            attachment_note = f"\nAttachment: {contact_message.attachment_original}"
        msg.set_content(
            f"Name: {contact_message.name}\nEmail: {contact_message.email}\n"
            f"Subject: {contact_message.subject}{attachment_note}\n\n{contact_message.message}"
        )
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(smtp_host, smtp_port, timeout=8) as server:
            if hasattr(server, "ehlo"):
                server.ehlo()
            if use_tls:
                server.starttls()
                if hasattr(server, "ehlo"):
                    server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, ""
    except Exception as exc:
        app.logger.exception("Contact email delivery failed for message_id=%s", getattr(contact_message, "id", None))
        return False, sanitize_text(str(exc), 240)


def build_goal_notifications_for_user(user_obj, limit=5):
    if not user_obj:
        return {"count": 0, "items": []}
    own_tip_ids = [
        row.id
        for row in GoalTipPost.query.with_entities(GoalTipPost.id).filter_by(created_by=user_obj.id).all()
    ]
    if not own_tip_ids:
        return {"count": 0, "items": []}

    since = user_obj.last_login_at or (datetime.utcnow() - timedelta(days=30))
    base_query = GoalTipComment.query.filter(
        GoalTipComment.tip_id.in_(own_tip_ids),
        GoalTipComment.created_at >= since,
        or_(GoalTipComment.created_by.is_(None), GoalTipComment.created_by != user_obj.id),
    )
    total_count = base_query.count()
    latest_comments = base_query.order_by(GoalTipComment.created_at.desc()).limit(limit).all()

    tip_map = {
        row.id: row.title
        for row in GoalTipPost.query.with_entities(GoalTipPost.id, GoalTipPost.title)
        .filter(GoalTipPost.id.in_(own_tip_ids))
        .all()
    }
    items = []
    for comment in latest_comments:
        tip_title = tip_map.get(comment.tip_id, "Your tip")
        items.append(
            {
                "tip_id": comment.tip_id,
                "tip_title": tip_title,
                "author_name": comment.author_name,
                "content_preview": (comment.content or "")[:80],
                "created_at": comment.created_at.isoformat() if comment.created_at else "",
                "time_ago": human_time_ago(comment.created_at),
            }
        )
    return {"count": total_count, "items": items}


def enforce_session_version():
    if not current_user.is_authenticated:
        return None
    current_version = session.get("session_version")
    if current_version is None:
        session["session_version"] = current_user.session_version
        return None
    if current_version != current_user.session_version:
        logout_user()
        flash("Session expired. Please login again.", "error")
        return redirect(url_for("login"))
    return None


def allowed_extension(filename, allowed_set=None):
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[1].lower()
    valid_set = allowed_set or ALLOWED_ACHIEVEMENT_EXTENSIONS
    if ext in valid_set:
        return ext
    return None


def valid_file_signature(file_storage, ext):
    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)

    if ext == "pdf":
        return header.startswith(b"%PDF-")
    if ext == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if ext == "gif":
        return header.startswith((b"GIF87a", b"GIF89a"))
    if ext == "webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False


def looks_like_plain_text(raw_sample):
    if not raw_sample:
        return True
    lowered = raw_sample.lstrip().lower()
    blocked_prefixes = (b"<!doctype html", b"<html", b"<script", b"<?php")
    if lowered.startswith(blocked_prefixes):
        return False
    return b"\x00" not in raw_sample


def valid_openxml_document(file_storage, ext):
    folder_by_ext = {"docx": "word/", "xlsx": "xl/", "pptx": "ppt/"}
    target_folder = folder_by_ext.get(ext)
    if not target_folder:
        return False

    header = file_storage.stream.read(4)
    file_storage.stream.seek(0)
    if header != b"PK\x03\x04":
        return False

    try:
        with zipfile.ZipFile(file_storage.stream) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                return False
            return any(name.startswith(target_folder) for name in names)
    except (zipfile.BadZipFile, OSError, ValueError):
        return False
    finally:
        file_storage.stream.seek(0)


def valid_achievement_document(file_storage, ext):
    if ext in {"png", "jpg", "jpeg", "pdf"}:
        return valid_file_signature(file_storage, ext)

    if ext == "docx":
        return valid_openxml_document(file_storage, ext)

    return False


def valid_mimetype_for_extension(mimetype, ext):
    allowed_map = {
        "pdf": {"application/pdf"},
        "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
        "png": {"image/png"},
        "jpg": {"image/jpeg"},
        "jpeg": {"image/jpeg"},
    }
    return (mimetype or "").lower() in allowed_map.get(ext, set())


def generate_stored_filename(filename):
    ext = filename.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def generate_vault_stored_filename(filename):
    safe = secure_filename(filename or "").strip()
    ext = ""
    if "." in safe:
        ext = safe.rsplit(".", 1)[1].lower()
        if not re.fullmatch(r"[a-z0-9]{1,16}", ext):
            ext = ""
    return f"{uuid.uuid4().hex}.{ext}" if ext else f"{uuid.uuid4().hex}.bin"


def generate_vault_share_token():
    return uuid.uuid4().hex + uuid.uuid4().hex


def parse_share_expiry_choice(raw_value):
    value = (raw_value or "never").strip().lower()
    if value in {"24h", "24", "1d"}:
        return "24h", datetime.utcnow() + timedelta(hours=24)
    if value in {"7d", "168", "week"}:
        return "7d", datetime.utcnow() + timedelta(days=7)
    return "never", None


def normalize_history_range(raw_value, default_value="all"):
    value = (raw_value or default_value).strip().lower()
    if value in {"today", "7d", "all"}:
        return value
    return default_value


def history_range_start_utc(range_key):
    now_utc = datetime.utcnow()
    value = normalize_history_range(range_key, "all")
    if value == "today":
        return now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    if value == "7d":
        return now_utc - timedelta(days=7)
    return None


def normalize_vault_access_code(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return None
    if re.fullmatch(r"\d{4,12}", value):
        return value
    if len(value) < 8 or len(value) > 64:
        return None
    # For password-style code, require at least one letter and one digit.
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        return None
    return value


def _vault_access_lock_window_minutes():
    try:
        value = int(app.config.get("VAULT_ACCESS_LOCK_MINUTES", 10))
    except (TypeError, ValueError):
        value = 10
    return max(1, value)


def _vault_access_max_attempts():
    try:
        value = int(app.config.get("VAULT_ACCESS_MAX_ATTEMPTS", 5))
    except (TypeError, ValueError):
        value = 5
    return max(1, value)


def is_vault_access_temporarily_locked(item):
    if not item or not item.pin_locked_until:
        return False
    return item.pin_locked_until > datetime.utcnow()


def vault_access_remaining_seconds(item):
    if not item or not item.pin_locked_until:
        return 0
    delta = item.pin_locked_until - datetime.utcnow()
    return max(0, int(delta.total_seconds()))


def reset_vault_access_fail_state(item):
    if not item:
        return
    item.pin_failed_attempts = 0
    item.pin_locked_until = None


def register_vault_access_failure(item):
    if not item:
        return {"locked": False, "remaining": _vault_access_max_attempts()}
    max_attempts = _vault_access_max_attempts()
    item.pin_failed_attempts = int(item.pin_failed_attempts or 0) + 1
    if int(item.pin_failed_attempts) >= max_attempts:
        item.pin_failed_attempts = 0
        item.pin_locked_until = datetime.utcnow() + timedelta(minutes=_vault_access_lock_window_minutes())
        return {"locked": True, "remaining": 0}
    remaining = max_attempts - int(item.pin_failed_attempts)
    return {"locked": False, "remaining": remaining}


def verify_vault_pin(item, pin_value):
    if not item or not item.pin_hash:
        return True
    normalized = normalize_vault_access_code(pin_value)
    if not normalized:
        return False
    try:
        return bool(bcrypt.check_password_hash(item.pin_hash, normalized))
    except ValueError:
        return False


def file_response_mimetype(filename):
    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or "application/octet-stream"


def is_removed_file_token(stored_name):
    return bool(stored_name and stored_name.startswith("removed_"))


def parse_achievement_date(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def pretty_title_from_filename(filename):
    base_name = os.path.splitext(filename or "")[0]
    text_value = re.sub(r"[_\-]+", " ", base_name)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    if not text_value:
        return ""
    return text_value.title()[:140]


def detect_vault_auto_label(file_storage, original_filename, extension, mime_type):
    base_label = pretty_title_from_filename(original_filename) or (secure_filename(original_filename or "")[:160] or "Vault File")
    ext = (extension or "").lower()
    mime_value = (mime_type or "").lower()

    if (mime_value.startswith("image/") or ext in {"png", "jpg", "jpeg", "webp", "gif", "bmp"}) and Image:
        try:
            file_storage.stream.seek(0)
            with Image.open(file_storage.stream) as image_obj:
                exif_data = image_obj.getexif() if hasattr(image_obj, "getexif") else None
                date_raw = (exif_data.get(36867) if exif_data else None) or (exif_data.get(306) if exif_data else None)
                if date_raw:
                    date_text = str(date_raw).strip()
                    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                        try:
                            parsed = datetime.strptime(date_text, fmt)
                            return sanitize_text(f"Photo {parsed.strftime('%Y-%m-%d %H:%M')}", 160) or base_label
                        except ValueError:
                            continue
        except Exception:
            pass
        finally:
            try:
                file_storage.stream.seek(0)
            except Exception:
                pass

    if ext == "pdf" and PdfReader:
        try:
            file_storage.stream.seek(0)
            reader = PdfReader(file_storage.stream)
            metadata = getattr(reader, "metadata", None)
            doc_title = ""
            if metadata:
                doc_title = str(metadata.get("/Title") or "").strip()
            if doc_title:
                cleaned = sanitize_text(doc_title, 160)
                if cleaned:
                    return cleaned
        except Exception:
            pass
        finally:
            try:
                file_storage.stream.seek(0)
            except Exception:
                pass

    return base_label


def auto_extract_achievement_from_filename(filename):
    base_name = os.path.splitext(filename or "")[0]
    if not base_name:
        return ("", None, None)

    normalized = base_name.lower().replace("_", " ").replace("-", " ")
    text_value = normalized.strip()
    parsed_date = None
    parsed_text = None

    for pattern in [
        r"(?<!\d)(20\d{2})[-_ /.](0[1-9]|1[0-2])[-_ /.]([0-2]\d|3[01])(?!\d)",
        r"(?<!\d)([0-2]\d|3[01])[-_ /.](0[1-9]|1[0-2])[-_ /.](20\d{2})(?!\d)",
    ]:
        match = re.search(pattern, base_name)
        if not match:
            continue

        if len(match.group(1)) == 4:
            year_value, month_value, day_value = int(match.group(1)), int(match.group(2)), int(match.group(3))
        else:
            day_value, month_value, year_value = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            parsed_date = date(year_value, month_value, day_value)
            parsed_text = parsed_date.isoformat()
            break
        except ValueError:
            parsed_date = None

    if not parsed_date:
        year_match = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", base_name)
        if year_match:
            year_value = int(year_match.group(1))
            parsed_date = date(year_value, 1, 1)
            parsed_text = year_match.group(1)

    pass_year_match = re.search(r"(?:pass|passed|qualif(?:y|ied)|result)\D*(19\d{2}|20\d{2})", normalized)
    if pass_year_match:
        year_value = int(pass_year_match.group(1))
        parsed_date = date(year_value, 1, 1)
        parsed_text = pass_year_match.group(1)

    class_token = ""
    if re.search(r"\b(10th|tenth|class\s*10|x)\b", normalized):
        class_token = "10th"
    elif re.search(r"\b(12th|twelfth|class\s*12|xii)\b", normalized):
        class_token = "12th"

    doc_type = ""
    if re.search(r"\b(marksheet|mark sheet)\b", normalized):
        doc_type = "Marksheet"
    elif re.search(r"\b(result|scorecard|score card)\b", normalized):
        doc_type = "Result"
    elif re.search(r"\b(certificate|cert)\b", normalized):
        doc_type = "Certificate"
    elif re.search(r"\b(transcript)\b", normalized):
        doc_type = "Transcript"
    elif re.search(r"\b(diploma)\b", normalized):
        doc_type = "Diploma"
    elif re.search(r"\b(resume|cv)\b", normalized):
        doc_type = "Resume"
    elif re.search(r"\b(aadhaar|aadhar|pan|passport|voter)\b", normalized):
        doc_type = "Identity Document"

    clean_title = re.sub(r"(19\d{2}|20\d{2})", "", text_value)
    clean_title = re.sub(r"\b(0[1-9]|1[0-2])[ /._-]([0-2]\d|3[01])\b", "", clean_title)
    clean_title = re.sub(r"\b([0-2]\d|3[01])[ /._-](0[1-9]|1[0-2])\b", "", clean_title)
    clean_title = re.sub(r"\b(pass|passed|qualify|qualified|result)\b", "", clean_title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -_")
    clean_title = clean_title.title()

    if class_token and doc_type:
        clean_title = f"{class_token} {doc_type}"
    elif class_token and not clean_title:
        clean_title = f"{class_token} Document"
    elif doc_type and not clean_title:
        clean_title = doc_type

    clean_title = clean_title[:140]

    return (clean_title, parsed_date, parsed_text)


def try_parse_date_strings(text_value):
    if not text_value:
        return (None, None)

    compact = re.sub(r"\s+", " ", text_value.strip())

    for pattern in [
        r"(?<!\d)(20\d{2})[/-](0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])(?!\d)",
        r"(?<!\d)(0?[1-9]|[12]\d|3[01])[/-](0?[1-9]|1[0-2])[/-](20\d{2})(?!\d)",
        r"(?<!\d)(0?[1-9]|[12]\d|3[01])\s+(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+(20\d{2})(?!\d)",
    ]:
        match = re.search(pattern, compact, flags=re.IGNORECASE)
        if not match:
            continue

        try:
            if len(match.group(1)) == 4:
                parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            elif match.group(2).isalpha():
                months = {
                    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
                    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
                    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
                    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
                }
                parsed = date(int(match.group(3)), months[match.group(2).lower()], int(match.group(1)))
            else:
                parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            return (parsed, parsed.isoformat())
        except (ValueError, KeyError):
            continue

    pass_year_match = re.search(r"(?:pass|passed|qualif(?:y|ied)|result|session|batch)\D*(19\d{2}|20\d{2})", compact, flags=re.IGNORECASE)
    if pass_year_match:
        year_value = int(pass_year_match.group(1))
        return (date(year_value, 1, 1), pass_year_match.group(1))

    year_match = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", compact)
    if year_match:
        year_value = int(year_match.group(1))
        return (date(year_value, 1, 1), year_match.group(1))

    return (None, None)


def clean_rtf_text(raw_text):
    if not raw_text:
        return ""
    text_value = re.sub(r"\\[a-zA-Z]+\d* ?", " ", raw_text)
    text_value = re.sub(r"[{}]", " ", text_value)
    text_value = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def extract_text_from_pdf(file_storage):
    if not PdfReader:
        return ""
    try:
        file_storage.stream.seek(0)
        reader = PdfReader(file_storage.stream)
        snippets = []
        for page in reader.pages[:5]:
            snippets.append(page.extract_text() or "")
        return " ".join(snippets)[:10000]
    except Exception:
        return ""
    finally:
        file_storage.stream.seek(0)


def extract_text_from_openxml(file_storage):
    try:
        file_storage.stream.seek(0)
        with zipfile.ZipFile(file_storage.stream) as archive:
            names = archive.namelist()
            candidates = [n for n in names if n.endswith(".xml") and (n.startswith("word/") or n.startswith("xl/") or n.startswith("ppt/"))][:8]
            chunks = []
            for name in candidates:
                payload = archive.read(name)
                root = ET.fromstring(payload)
                text_nodes = [node.text for node in root.iter() if node.text]
                chunks.append(" ".join(text_nodes))
            return " ".join(chunks)[:10000]
    except Exception:
        return ""
    finally:
        file_storage.stream.seek(0)


def extract_text_from_image_ocr(file_storage):
    if not Image or not pytesseract:
        return ""
    try:
        file_storage.stream.seek(0)
        blob = file_storage.stream.read()
        image = Image.open(io.BytesIO(blob))
        return (pytesseract.image_to_string(image) or "")[:10000]
    except Exception:
        return ""
    finally:
        file_storage.stream.seek(0)


def extract_text_for_metadata(file_storage, ext):
    if ext == "pdf":
        return extract_text_from_pdf(file_storage)
    if ext in {"png", "jpg", "jpeg", "gif", "webp"}:
        return extract_text_from_image_ocr(file_storage)
    if ext in {"docx", "xlsx", "pptx"}:
        return extract_text_from_openxml(file_storage)
    if ext in {"txt", "csv"}:
        try:
            file_storage.stream.seek(0)
            return file_storage.stream.read(10000).decode("utf-8", errors="ignore")
        except Exception:
            return ""
        finally:
            file_storage.stream.seek(0)
    if ext == "rtf":
        try:
            file_storage.stream.seek(0)
            raw_text = file_storage.stream.read(12000).decode("utf-8", errors="ignore")
            return clean_rtf_text(raw_text)[:10000]
        except Exception:
            return ""
        finally:
            file_storage.stream.seek(0)
    return ""


def auto_extract_achievement_from_text(text_value):
    normalized = (text_value or "").lower()
    if not normalized:
        return ("", None, None)

    class_token = ""
    if re.search(r"\b(10th|tenth|class\s*10|secondary school certificate|matric)\b", normalized):
        class_token = "10th"
    elif re.search(r"\b(12th|twelfth|class\s*12|higher secondary|intermediate)\b", normalized):
        class_token = "12th"

    doc_type = ""
    if re.search(r"\b(marksheet|mark sheet)\b", normalized):
        doc_type = "Marksheet"
    elif re.search(r"\b(result|score card|scorecard)\b", normalized):
        doc_type = "Result"
    elif re.search(r"\b(certificate|certified)\b", normalized):
        doc_type = "Certificate"
    elif re.search(r"\b(transcript)\b", normalized):
        doc_type = "Transcript"
    elif re.search(r"\b(diploma)\b", normalized):
        doc_type = "Diploma"
    elif re.search(r"\b(resume|curriculum vitae|cv)\b", normalized):
        doc_type = "Resume"

    title = ""
    if class_token and doc_type:
        title = f"{class_token} {doc_type}"
    elif class_token:
        title = f"{class_token} Document"
    elif doc_type:
        title = doc_type

    parsed_date, parsed_text = try_parse_date_strings(normalized)
    return (title[:140], parsed_date, parsed_text)


def detect_auto_achievement_metadata(file_storage, safe_original, ext):
    filename_title, filename_date, filename_date_text = auto_extract_achievement_from_filename(safe_original)
    content_text = extract_text_for_metadata(file_storage, ext)
    text_title, text_date, text_date_text = auto_extract_achievement_from_text(content_text)

    final_title = text_title or filename_title or pretty_title_from_filename(safe_original)
    final_date = text_date or filename_date
    final_date_text = text_date_text or filename_date_text
    return (final_title, final_date, final_date_text)


def detect_auto_metadata_from_saved_file(file_path, original_filename):
    ext = allowed_extension(original_filename, ALLOWED_ACHIEVEMENT_EXTENSIONS)
    if not ext or not os.path.isfile(file_path):
        return auto_extract_achievement_from_filename(original_filename)
    try:
        with open(file_path, "rb") as fh:
            payload = fh.read()
        proxy = type("UploadProxy", (), {})()
        proxy.stream = io.BytesIO(payload)
        return detect_auto_achievement_metadata(proxy, original_filename, ext)
    except OSError:
        return auto_extract_achievement_from_filename(original_filename)


def save_encrypted_upload(file_storage, path):
    if not AESGCM:
        raise RuntimeError("AES-256 encryption dependency missing")
    file_storage.stream.seek(0)
    raw_bytes = file_storage.stream.read()
    encrypted_bytes = encrypt_content_bytes(raw_bytes)
    with open(path, "wb") as outfile:
        outfile.write(encrypted_bytes)
    file_storage.stream.seek(0)


def virus_scan_ok(file_storage):
    if not app.config.get("ENABLE_VIRUS_SCAN", False):
        return True
    scanner = os.environ.get("CLAMSCAN_BIN", "clamscan").strip() or "clamscan"
    file_storage.stream.seek(0)
    payload = file_storage.stream.read()
    file_storage.stream.seek(0)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [scanner, "--no-summary", tmp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False
    finally:
        remove_file_if_exists(tmp_path)


def read_decrypted_file(path):
    if not AESGCM:
        raise RuntimeError("AES-256 encryption dependency missing")
    with open(path, "rb") as infile:
        payload = infile.read()
    return decrypt_content_bytes(payload)


def remove_file_if_exists(path):
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def current_stream_size(file_storage):
    try:
        stream = file_storage.stream
        current = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(current)
        return int(size or 0)
    except Exception:
        return 0


def login_rate_limited(email, ip_address):
    window_start = datetime.utcnow() - timedelta(minutes=app.config["LOGIN_BLOCK_MINUTES"])
    failed_count = LoginAttempt.query.filter(
        LoginAttempt.created_at >= window_start,
        LoginAttempt.success.is_(False),
        (LoginAttempt.email == email) | (LoginAttempt.ip_address == ip_address),
    ).count()
    return failed_count >= app.config["LOGIN_MAX_ATTEMPTS"]


def record_login_attempt(email, ip_address, success):
    attempt = LoginAttempt(email=email[:120], ip_address=ip_address[:64], success=success)
    db.session.add(attempt)
    db.session.commit()


def validate_email_input(email):
    value = (email or "").strip().lower()
    if not value or len(value) > 120 or "@" not in value:
        return None
    return value


def sanitize_text(value, max_len, multiline=False):
    text_value = (value or "").strip()
    if not multiline:
        text_value = " ".join(text_value.split())
    text_value = text_value.replace("\x00", "")
    text_value = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text_value)
    return text_value[:max_len]


def rate_limit_key(action_name):
    return f"{action_name}:{client_ip()}"


def is_action_rate_limited(action_name, max_attempts, window_minutes):
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)
    bucket_key = rate_limit_key(action_name)
    attempts = RATE_LIMIT_BUCKETS.get(bucket_key, [])
    attempts = [ts for ts in attempts if ts >= window_start]
    RATE_LIMIT_BUCKETS[bucket_key] = attempts
    return len(attempts) >= max_attempts


def record_action_attempt(action_name):
    now = datetime.utcnow()
    bucket_key = rate_limit_key(action_name)
    attempts = RATE_LIMIT_BUCKETS.get(bucket_key, [])
    attempts.append(now)
    RATE_LIMIT_BUCKETS[bucket_key] = attempts


































def find_user_for_admin_lookup(identifier):
    value = sanitize_text(identifier, 120)
    if not value:
        return None
    if value.isdigit():
        return User.query.get(int(value))
    email = validate_email_input(value)
    if email:
        return User.query.filter_by(email=email).first()
    return User.query.filter_by(username=value).first()



def comment_cooldown_remaining_seconds():
    now = datetime.utcnow()
    if current_user.is_authenticated:
        key = f"user:{current_user.id}"
    else:
        key = f"ip:{client_ip()}"
    last_at = COMMENT_COOLDOWN_TRACKER.get(key)
    if not last_at:
        return 0
    elapsed = (now - last_at).total_seconds()
    cooldown = app.config.get("COMMENT_COOLDOWN_SECONDS", 20)
    if elapsed >= cooldown:
        return 0
    return int(cooldown - elapsed)


def mark_comment_submitted():
    if current_user.is_authenticated:
        key = f"user:{current_user.id}"
    else:
        key = f"ip:{client_ip()}"
    COMMENT_COOLDOWN_TRACKER[key] = datetime.utcnow()


def get_reset_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="password-reset")


def get_email_verify_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="email-verify")


def generate_reset_token(email):
    return get_reset_serializer().dumps({"email": email})


def generate_email_verify_token(email):
    return get_email_verify_serializer().dumps({"email": email})


def verify_reset_token(token, max_age=900):
    try:
        data = get_reset_serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return validate_email_input(data.get("email"))


def verify_email_token(token, max_age=3600):
    try:
        data = get_email_verify_serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return validate_email_input(data.get("email"))


def issue_user_jwt_tokens(user_obj):
    return issue_token_pair(
        secret_key=app.config["SECRET_KEY"],
        user_id=user_obj.id,
        role=normalize_role(getattr(user_obj, "role", "user")),
        session_version=int(getattr(user_obj, "session_version", 1) or 1),
        access_minutes=app.config.get("JWT_ACCESS_EXPIRES_MINUTES", 15),
        refresh_days=app.config.get("JWT_REFRESH_EXPIRES_DAYS", 7),
    )


def bearer_token_from_request():
    auth_header = (request.headers.get("Authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    return token or None


def resolve_jwt_user(required_token_type="access"):
    token = bearer_token_from_request()
    if not token:
        raise JWTTokenError("Missing bearer token.")
    payload = decode_token(app.config["SECRET_KEY"], token, expected_type=required_token_type)
    user_id_raw = payload.get("sub")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise JWTTokenError("Invalid token subject.")
    user_obj = User.query.get(user_id)
    if not user_obj or not user_obj.is_active:
        raise JWTTokenError("User not found or inactive.")
    if int(payload.get("sv") or 0) != int(getattr(user_obj, "session_version", 1) or 1):
        raise JWTTokenError("Token has been revoked.")
    return user_obj, payload


def verifyJWT(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user_obj, payload = resolve_jwt_user("access")
        except JWTTokenError as exc:
            return jsonify(auth_error_payload(str(exc))), 401
        g.jwt_user = user_obj
        g.jwt_payload = payload
        return func(*args, **kwargs)

    return wrapper


def verifyRole(*roles):
    allowed = {normalize_role(r) for r in roles}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_obj = getattr(g, "jwt_user", None)
            if not user_obj:
                return jsonify(auth_error_payload("Unauthorized.")), 401
            if normalize_role(getattr(user_obj, "role", "user")) not in allowed:
                return jsonify(auth_error_payload("Forbidden.")), 403
            return func(*args, **kwargs)

        return wrapper

    return decorator


def api_actor_user():
    jwt_user = getattr(g, "jwt_user", None)
    if jwt_user:
        return jwt_user
    if current_user.is_authenticated:
        return current_user
    return None



def hash_refresh_token(token):
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def store_refresh_token_row(user_obj, refresh_token, payload=None):
    token_payload = payload or decode_token(app.config["SECRET_KEY"], refresh_token, expected_type="refresh")
    expires_ts = int(token_payload.get("exp") or 0)
    expires_at = datetime.utcfromtimestamp(expires_ts) if expires_ts else (datetime.utcnow() + timedelta(days=7))
    row = RefreshToken(
        user_id=user_obj.id,
        token_hash=hash_refresh_token(refresh_token),
        jti=sanitize_text(token_payload.get("jti"), 64) or "",
        expires_at=expires_at,
        ip_address=client_ip(),
        user_agent=sanitize_text(request.headers.get("User-Agent"), 255, multiline=True),
    )
    db.session.add(row)
    return row


def revoke_all_refresh_tokens_for_user(user_id):
    now = datetime.utcnow()
    rows = RefreshToken.query.filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).all()
    for row in rows:
        row.revoked_at = now
    return len(rows)


@csrf.exempt
def api_auth_login():
    payload = request.get_json(silent=True) or {}
    email = validate_email_input(payload.get("email"))
    password = str(payload.get("password") or "")
    otp_code = sanitize_text(payload.get("otp_code"), 12)
    if not email or not password:
        return jsonify(auth_error_payload("Email and password are required.")), 400
    user_obj = User.query.filter_by(email=email).first()
    if not user_obj or not user_obj.is_active:
        return jsonify(auth_error_payload("Invalid credentials.")), 401
    if user_obj.login_lock_until and user_obj.login_lock_until > datetime.utcnow():
        return jsonify(auth_error_payload("Account is temporarily locked.")), 423
    if not bcrypt.check_password_hash(user_obj.password_hash, password):
        return jsonify(auth_error_payload("Invalid credentials.")), 401
    if app.config.get("REQUIRE_EMAIL_VERIFICATION", False) and not user_obj.is_email_verified:
        return jsonify(auth_error_payload("Email verification required.")), 403
    if otp_required(user_obj):
        if not otp_code or not verify_totp(user_obj, otp_code):
            return jsonify(auth_error_payload("Valid OTP code is required.")), 401
    tokens = issue_user_jwt_tokens(user_obj)
    try:
        refresh_payload = decode_token(app.config["SECRET_KEY"], tokens["refresh_token"], expected_type="refresh")
        store_refresh_token_row(user_obj, tokens["refresh_token"], payload=refresh_payload)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(auth_error_payload("Unable to create refresh session.")), 500
    return jsonify(auth_success_payload(user_obj, tokens))


@csrf.exempt
def api_auth_refresh():
    payload = request.get_json(silent=True) or {}
    refresh_token = str(payload.get("refresh_token") or "")
    if not refresh_token:
        return jsonify(auth_error_payload("refresh_token is required.")), 400
    try:
        token_payload = decode_token(app.config["SECRET_KEY"], refresh_token, expected_type="refresh")
        user_id = int(token_payload.get("sub"))
    except (JWTTokenError, TypeError, ValueError) as exc:
        return jsonify(auth_error_payload(str(exc))), 401
    user_obj = User.query.get(user_id)
    if not user_obj or not user_obj.is_active:
        return jsonify(auth_error_payload("User not found or inactive.")), 401
    if int(token_payload.get("sv") or 0) != int(user_obj.session_version or 1):
        return jsonify(auth_error_payload("Token has been revoked.")), 401
    token_hash = hash_refresh_token(refresh_token)
    token_row = RefreshToken.query.filter_by(token_hash=token_hash, user_id=user_obj.id).first()
    if not token_row:
        return jsonify(auth_error_payload("Refresh token not recognized.")), 401
    if token_row.revoked_at is not None:
        return jsonify(auth_error_payload("Refresh token already used/revoked.")), 401
    if token_row.expires_at and token_row.expires_at < datetime.utcnow():
        return jsonify(auth_error_payload("Refresh token expired.")), 401
    tokens = issue_user_jwt_tokens(user_obj)
    try:
        new_refresh_payload = decode_token(app.config["SECRET_KEY"], tokens["refresh_token"], expected_type="refresh")
        token_row.revoked_at = datetime.utcnow()
        token_row.replaced_by_jti = sanitize_text(new_refresh_payload.get("jti"), 64)
        store_refresh_token_row(user_obj, tokens["refresh_token"], payload=new_refresh_payload)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(auth_error_payload("Unable to rotate refresh token.")), 500
    return jsonify(auth_success_payload(user_obj, tokens))


@verifyJWT
def api_auth_me():
    user_obj = g.jwt_user
    return jsonify(
        {
            "ok": True,
            "user": {
                "id": int(user_obj.id),
                "username": user_obj.username,
                "email": user_obj.email,
                "role": normalize_role(user_obj.role),
            },
        }
    )


@csrf.exempt
@verifyJWT
def api_auth_logout():
    user_obj = g.jwt_user
    revoke_all_refresh_tokens_for_user(user_obj.id)
    user_obj.session_version = int(user_obj.session_version or 1) + 1
    db.session.commit()
    return jsonify({"ok": True, "message": "Logged out. Tokens revoked."})


def ensure_schema_compatibility():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "user" in tables:
        user_cols = {col["name"] for col in inspector.get_columns("user")}
        with db.engine.begin() as conn:
            if "is_active_user" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN is_active_user BOOLEAN NOT NULL DEFAULT 1"))
            if "is_email_verified" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN is_email_verified BOOLEAN NOT NULL DEFAULT 0"))
            if "twofa_secret" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN twofa_secret VARCHAR(64)"))
            if "twofa_enabled" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN twofa_enabled BOOLEAN NOT NULL DEFAULT 0"))
            if "login_lock_until" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN login_lock_until DATETIME"))
            if "failed_login_count" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0"))
            if "session_version" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN session_version INTEGER NOT NULL DEFAULT 1"))
            if "last_login_at" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN last_login_at DATETIME"))
            if "last_login_ip" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN last_login_ip VARCHAR(64)"))
            if "about_page_title" not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN about_page_title VARCHAR(120)"))

    if "achievement" in tables:
        achievement_cols = {col["name"] for col in inspector.get_columns("achievement")}
        with db.engine.begin() as conn:
            if "achievement_date_text" not in achievement_cols:
                conn.execute(text("ALTER TABLE achievement ADD COLUMN achievement_date_text VARCHAR(40)"))
            if "document_label" not in achievement_cols:
                conn.execute(text("ALTER TABLE achievement ADD COLUMN document_label VARCHAR(160)"))
            if "metadata_mode" not in achievement_cols:
                conn.execute(text("ALTER TABLE achievement ADD COLUMN metadata_mode VARCHAR(20) NOT NULL DEFAULT 'manual'"))
            if "category" not in achievement_cols:
                conn.execute(text("ALTER TABLE achievement ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'other'"))
            if "visibility_status" not in achievement_cols:
                conn.execute(text("ALTER TABLE achievement ADD COLUMN visibility_status VARCHAR(20) NOT NULL DEFAULT 'private'"))
            if "verification_status" not in achievement_cols:
                conn.execute(text("ALTER TABLE achievement ADD COLUMN verification_status VARCHAR(20) NOT NULL DEFAULT 'pending'"))
            conn.execute(text("UPDATE achievement SET metadata_mode = 'manual' WHERE metadata_mode IS NULL OR metadata_mode = ''"))
            conn.execute(text("UPDATE achievement SET document_label = title WHERE (document_label IS NULL OR document_label = '')"))
            conn.execute(text("UPDATE achievement SET category = 'other' WHERE category IS NULL OR category = ''"))
            conn.execute(text("UPDATE achievement SET visibility_status = 'private' WHERE visibility_status IS NULL OR visibility_status = ''"))
            conn.execute(text("UPDATE achievement SET verification_status = 'pending' WHERE verification_status IS NULL OR verification_status = ''"))
            conn.execute(
                text(
                    "UPDATE achievement SET achievement_date_text = strftime('%Y-%m-%d', achievement_date) "
                    "WHERE achievement_date_text IS NULL OR achievement_date_text = ''"
                )
            )

    if "goal" not in tables:
        Goal.__table__.create(db.engine)

    if "vault_file" not in tables:
        VaultFile.__table__.create(db.engine)
    else:
        vault_cols = {col["name"] for col in inspector.get_columns("vault_file")}
        with db.engine.begin() as conn:
            if "visibility_status" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN visibility_status VARCHAR(20) NOT NULL DEFAULT 'private'"))
            if "share_enabled" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN share_enabled BOOLEAN NOT NULL DEFAULT 0"))
            if "share_token" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN share_token VARCHAR(64)"))
            if "share_expires_at" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN share_expires_at DATETIME"))
            if "pin_hash" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN pin_hash VARCHAR(200)"))
            if "pin_failed_attempts" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN pin_failed_attempts INTEGER NOT NULL DEFAULT 0"))
            if "pin_locked_until" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN pin_locked_until DATETIME"))
            if "download_count" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN download_count INTEGER NOT NULL DEFAULT 0"))
            if "label" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN label VARCHAR(160)"))
                conn.execute(text("UPDATE vault_file SET label = original_filename WHERE label IS NULL OR label = ''"))
            if "folder_tag" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN folder_tag VARCHAR(80)"))
            if "note" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN note TEXT"))
            if "mime_type" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN mime_type VARCHAR(120)"))
            if "extension" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN extension VARCHAR(20)"))
            if "size_bytes" not in vault_cols:
                conn.execute(text("ALTER TABLE vault_file ADD COLUMN size_bytes INTEGER NOT NULL DEFAULT 0"))
        missing_tokens = VaultFile.query.filter(or_(VaultFile.share_token.is_(None), VaultFile.share_token == "")).all()
        if missing_tokens:
            for row in missing_tokens:
                row.share_token = generate_vault_share_token()
            db.session.commit()

    if "activity_log" not in tables:
        ActivityLog.__table__.create(db.engine)

    if "vault_file_history" not in tables:
        VaultFileHistory.__table__.create(db.engine)

    if "refresh_token" not in tables:
        RefreshToken.__table__.create(db.engine)
    else:
        refresh_cols = {col["name"] for col in inspector.get_columns("refresh_token")}
        with db.engine.begin() as conn:
            if "replaced_by_jti" not in refresh_cols:
                conn.execute(text("ALTER TABLE refresh_token ADD COLUMN replaced_by_jti VARCHAR(64)"))
            if "ip_address" not in refresh_cols:
                conn.execute(text("ALTER TABLE refresh_token ADD COLUMN ip_address VARCHAR(64)"))
            if "user_agent" not in refresh_cols:
                conn.execute(text("ALTER TABLE refresh_token ADD COLUMN user_agent VARCHAR(255)"))


    if "goal_tip_post" not in tables:
        GoalTipPost.__table__.create(db.engine)
    else:
        tip_cols = {col["name"] for col in inspector.get_columns("goal_tip_post")}
        with db.engine.begin() as conn:
            if "visibility_status" not in tip_cols:
                conn.execute(text("ALTER TABLE goal_tip_post ADD COLUMN visibility_status VARCHAR(20) NOT NULL DEFAULT 'private'"))
            if "attachment_original" not in tip_cols:
                conn.execute(text("ALTER TABLE goal_tip_post ADD COLUMN attachment_original VARCHAR(255)"))
            if "attachment_stored" not in tip_cols:
                conn.execute(text("ALTER TABLE goal_tip_post ADD COLUMN attachment_stored VARCHAR(255)"))
            conn.execute(text("UPDATE goal_tip_post SET visibility_status = 'private' WHERE visibility_status IS NULL OR visibility_status = ''"))
    if "goal_tip_like" not in tables:
        GoalTipLike.__table__.create(db.engine)
    if "goal_tip_save" not in tables:
        GoalTipSave.__table__.create(db.engine)
    else:
        tip_save_cols = {col["name"] for col in inspector.get_columns("goal_tip_save")}
        with db.engine.begin() as conn:
            if "saved_name" not in tip_save_cols:
                conn.execute(text("ALTER TABLE goal_tip_save ADD COLUMN saved_name VARCHAR(160)"))
                conn.execute(text("UPDATE goal_tip_save SET saved_name = 'Saved Tip' WHERE saved_name IS NULL OR saved_name = ''"))
    if "goal_tip_comment" not in tables:
        GoalTipComment.__table__.create(db.engine)
    else:
        comment_cols = {col["name"] for col in inspector.get_columns("goal_tip_comment")}
        if "updated_at" not in comment_cols:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE goal_tip_comment ADD COLUMN updated_at DATETIME"))
                conn.execute(text("UPDATE goal_tip_comment SET updated_at = created_at WHERE updated_at IS NULL"))

    if "contact_message" in tables:
        contact_cols = {col["name"] for col in inspector.get_columns("contact_message")}
        with db.engine.begin() as conn:
            if "attachment_original" not in contact_cols:
                conn.execute(text("ALTER TABLE contact_message ADD COLUMN attachment_original VARCHAR(255)"))
            if "attachment_stored" not in contact_cols:
                conn.execute(text("ALTER TABLE contact_message ADD COLUMN attachment_stored VARCHAR(255)"))

    with db.engine.begin() as conn:
        conn.execute(text("UPDATE user SET role = lower(role) WHERE role IS NOT NULL"))
        conn.execute(text("UPDATE user SET role = 'user' WHERE role IS NULL OR role = ''"))


_runtime_setup_done = False


def ensure_runtime_setup():
    global _runtime_setup_done
    if _runtime_setup_done:
        return
    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        db.create_all()
        ensure_schema_compatibility()
    _runtime_setup_done = True


ensure_runtime_setup()


@app.before_request
def before_request_security():
    host = (request.host.split(":", 1)[0] if request.host else "").strip().lower()
    is_local_host = host in {"127.0.0.1", "localhost", "::1"}
    if (
        app.config.get("ENFORCE_HTTPS", False)
        and not request.is_secure
        and not app.debug
        and not is_local_host
        and request.headers.get("X-Forwarded-Proto", "").lower() != "https"
    ):
        return redirect(request.url.replace("http://", "https://", 1), code=301)
    redirect_resp = enforce_session_version()
    if redirect_resp:
        return redirect_resp


@app.after_request
def apply_security_headers(response):
    host = (request.host.split(":", 1)[0] if request.host else "").strip().lower()
    is_local_host = host in {"127.0.0.1", "localhost", "::1"}
    response.headers.pop("Server", None)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = app.config["SECURITY_CSP"]
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store" if request.endpoint in {
        "login", "login_2fa", "register", "forgot_password", "reset_password", "settings", "security_settings", "vault"
    } else "no-cache")
    if request.is_secure and not is_local_host:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response


# ---------- Routes ----------
@app.route("/")
def home():
    return render_template("home.html", **ctx("Home"))



@app.route("/pwa-preview")
def pwa_preview():
    layout = sanitize_text(request.args.get("layout"), 16).lower()
    layout = layout if layout in {"wide", "mobile"} else "wide"
    return render_template("pwa_screenshot_preview.html", layout=layout, **ctx("PWA Preview"))


@app.route("/about")
def about():
    posts = Post.query.filter(Post.category.in_(ALLOWED_CATEGORIES)).order_by(Post.created_at.desc()).limit(80).all()
    user_ids = {p.uploaded_by for p in posts}
    user_map = {u.id: u.username for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    grouped_posts = {key: [] for key in sorted(ALLOWED_CATEGORIES)}
    for post in posts:
        grouped_posts.setdefault(post.category, []).append(post)
    is_special_about_view = bool(
        current_user.is_authenticated and validate_email_input(current_user.email) == SPECIAL_ABOUT_EMAIL
    )

    custom_about_posts = []
    custom_about_title = "About Me"
    default_about_title_suggestion = "My Portfolio"
    if current_user.is_authenticated and not is_special_about_view:
        default_about_title_suggestion = default_about_title_for_user(current_user)
        custom_about_title = sanitize_text(
            getattr(current_user, "about_page_title", None),
            120,
        ) or default_about_title_suggestion
        custom_about_posts = [p for p in posts if p.uploaded_by == current_user.id]

    return render_template(
        "about.html",
        grouped_posts=grouped_posts,
        user_map=user_map,
        is_special_about_view=is_special_about_view,
        custom_about_posts=custom_about_posts,
        custom_about_title=custom_about_title,
        default_about_title_suggestion=default_about_title_suggestion,
        special_about_email=SPECIAL_ABOUT_EMAIL,
        public_about_profile=PUBLIC_ABOUT_PROFILE,
        **ctx("About Me"),
    )


@app.route("/about/title", methods=["POST"])
@login_required
def save_about_title():
    title = sanitize_text(request.form.get("about_page_title"), 120)
    if validate_email_input(current_user.email) == SPECIAL_ABOUT_EMAIL:
        flash("Default About sections are locked for this account.", "error")
        return redirect(url_for("about"))

    if not title:
        flash("About title is required.", "error")
        return redirect(url_for("about"))

    current_user.about_page_title = title
    db.session.commit()
    flash("About title updated.", "success")
    return redirect(url_for("about"))


@app.route("/about/upload", methods=["POST"])
@login_required
def about_upload():
    title = sanitize_text(request.form.get("title"), 120)
    description = sanitize_text(request.form.get("description"), 2000, multiline=True)
    category = (request.form.get("category") or "").strip().lower()
    file = request.files.get("file")
    is_special_about_view = validate_email_input(current_user.email) == SPECIAL_ABOUT_EMAIL
    custom_about_title = sanitize_text(request.form.get("about_page_title"), 120)

    if not title or not description or not file:
        flash("Title, description and file are required.", "error")
        return redirect(url_for("about"))

    if not is_special_about_view and category == "other":
        # Non-special accounts use a single custom About section; keep storage category compatible.
        category = "certificate"

    if not is_special_about_view and not category:
        category = "certificate"

    if category not in ALLOWED_CATEGORIES:
        flash("Invalid post category.", "error")
        return redirect(url_for("about"))

    safe_original = secure_filename(file.filename or "")
    ext = allowed_extension(safe_original, ALLOWED_POST_EXTENSIONS)
    if not safe_original or not ext:
        flash("Only PDF, JPG, PNG are allowed.", "error")
        return redirect(url_for("about"))
    if not valid_mimetype_for_extension(file.mimetype, ext):
        flash("File MIME type is not allowed for selected document type.", "error")
        return redirect(url_for("about"))
    if not valid_achievement_document(file, ext):
        flash("Invalid file type.", "error")
        return redirect(url_for("about"))
    if not virus_scan_ok(file):
        flash("File failed security scan.", "error")
        return redirect(url_for("about"))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    stored_filename = generate_stored_filename(safe_original)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
    try:
        save_encrypted_upload(file, save_path)
    except Exception:
        flash("Unable to securely encrypt and store file.", "error")
        return redirect(url_for("about"))

    post = Post(
        title=title,
        description=description,
        category=category,
        original_filename=safe_original,
        stored_filename=stored_filename,
        uploaded_by=current_user.id,
    )
    db.session.add(post)
    if not is_special_about_view and custom_about_title:
        current_user.about_page_title = custom_about_title
    db.session.commit()
    log_activity("file_upload", f"about_post:{post.id}", user_id=current_user.id)
    flash("Post uploaded successfully.", "success")
    return redirect(url_for("about"))


@app.route("/about/posts/<int:post_id>/edit", methods=["POST"])
@login_required
def edit_about_post(post_id):
    post = Post.query.get_or_404(post_id)
    can_manage = post.uploaded_by == current_user.id or is_admin_or_owner()
    if not can_manage:
        flash("You do not have permission to edit this post.", "error")
        return redirect(url_for("about"))

    title = sanitize_text(request.form.get("title"), 120)
    description = sanitize_text(request.form.get("description"), 2000, multiline=True)
    category = (request.form.get("category") or "").strip().lower()
    file = request.files.get("file")
    remove_file = request.form.get("remove_file") == "on"

    if not title or not description:
        flash("Title and description are required.", "error")
        return redirect(url_for("about"))
    if category not in ALLOWED_CATEGORIES:
        flash("Invalid post category.", "error")
        return redirect(url_for("about"))

    post.title = title
    post.description = description
    post.category = category

    if file and file.filename:
        safe_original = secure_filename(file.filename or "")
        ext = allowed_extension(safe_original, ALLOWED_POST_EXTENSIONS)
        if not safe_original or not ext:
            flash("Only PDF, JPG, PNG are allowed.", "error")
            return redirect(url_for("about"))
        if not valid_mimetype_for_extension(file.mimetype, ext):
            flash("File MIME type is not allowed for selected document type.", "error")
            return redirect(url_for("about"))
        if not valid_achievement_document(file, ext):
            flash("Invalid file type.", "error")
            return redirect(url_for("about"))
        if not virus_scan_ok(file):
            flash("File failed security scan.", "error")
            return redirect(url_for("about"))

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        stored_filename = generate_stored_filename(safe_original)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
        try:
            save_encrypted_upload(file, save_path)
        except Exception:
            flash("Unable to securely encrypt and store file.", "error")
            return redirect(url_for("about"))

        old_file = os.path.join(app.config["UPLOAD_FOLDER"], post.stored_filename)
        remove_file_if_exists(old_file)
        post.original_filename = safe_original
        post.stored_filename = stored_filename
        log_activity("file_upload", f"about_post_update:{post.id}", user_id=current_user.id)
    elif remove_file:
        old_file = os.path.join(app.config["UPLOAD_FOLDER"], post.stored_filename)
        remove_file_if_exists(old_file)
        post.original_filename = "removed"
        post.stored_filename = f"removed_{uuid.uuid4().hex}.none"
        log_activity("file_delete", f"about_post_doc_removed:{post.id}", user_id=current_user.id)

    db.session.commit()
    log_activity("profile_change", f"about_post_edit:{post.id}", user_id=current_user.id)
    flash("About post updated successfully.", "success")
    return redirect(url_for("about"))


@app.route("/achievements", methods=["GET", "POST"])
def achievements():
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please login to manage achievements.", "error")
            return redirect(url_for("login"))

        if is_action_rate_limited(
            "achievement_submit",
            app.config["ACHIEVEMENT_MAX_ATTEMPTS"],
            app.config["ACHIEVEMENT_BLOCK_MINUTES"],
        ):
            flash("Too many requests. Please try again later.", "error")
            return redirect(url_for("achievements"))

        metadata_mode = (request.form.get("metadata_mode") or "manual").strip().lower()
        if metadata_mode not in {"manual", "auto"}:
            metadata_mode = "manual"

        title = sanitize_text(request.form.get("title"), 140)
        issuer = sanitize_text(request.form.get("issuer"), 120)
        achievement_date = parse_achievement_date(request.form.get("achievement_date"))
        description = sanitize_text(request.form.get("description"), 2000, multiline=True)
        document_label = sanitize_text(request.form.get("document_label"), 160)
        category = (request.form.get("category") or "other").strip().lower()
        visibility_status = (request.form.get("visibility_status") or "private").strip().lower()
        verification_status = (request.form.get("verification_status") or "pending").strip().lower()
        file = request.files.get("document")

        if category not in ALLOWED_ACHIEVEMENT_CATEGORIES:
            category = "other"
        if visibility_status not in ALLOWED_VISIBILITY_STATUS:
            visibility_status = "private"
        if verification_status not in ALLOWED_VERIFICATION_STATUS:
            verification_status = "pending"

        if not file:
            flash("Document is required.", "error")
            return redirect(url_for("achievements"))

        raw_filename = file.filename or ""
        safe_original = secure_filename(raw_filename)
        ext = allowed_extension(safe_original, ALLOWED_ACHIEVEMENT_EXTENSIONS)

        if not safe_original or not ext:
            flash("Unsupported document type. Allowed: PDF, JPG, PNG only.", "error")
            return redirect(url_for("achievements"))

        if not valid_mimetype_for_extension(file.mimetype, ext):
            flash("File MIME type is not allowed for selected document type.", "error")
            return redirect(url_for("achievements"))

        if not valid_achievement_document(file, ext):
            flash("Invalid file type.", "error")
            return redirect(url_for("achievements"))
        if not virus_scan_ok(file):
            flash("File failed security scan.", "error")
            return redirect(url_for("achievements"))

        auto_title, auto_date, auto_date_text = detect_auto_achievement_metadata(file, safe_original, ext)
        if metadata_mode == "auto":
            title = title or auto_title or pretty_title_from_filename(safe_original)
            achievement_date = achievement_date or auto_date
            if not achievement_date:
                flash("Auto date detect nahi hua. Please pass date manually add karein.", "error")
                return redirect(url_for("achievements"))
            if not issuer:
                issuer = "Self Uploaded"
            if not document_label:
                document_label = auto_title or pretty_title_from_filename(safe_original)
        else:
            if not title or not achievement_date:
                flash("Manual mode me title aur pass date required hai.", "error")
                return redirect(url_for("achievements"))
            issuer = issuer or "Self Uploaded"
            document_label = document_label or title
            auto_date_text = achievement_date.isoformat()

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        stored_filename = generate_stored_filename(safe_original)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
        try:
            save_encrypted_upload(file, save_path)
        except Exception:
            flash("Unable to securely encrypt and store file.", "error")
            return redirect(url_for("achievements"))

        achievement = Achievement(
            title=title,
            issuer=issuer,
            achievement_date=achievement_date,
            achievement_date_text=auto_date_text or achievement_date.isoformat(),
            description=description,
            category=category,
            visibility_status=visibility_status,
            verification_status=verification_status,
            document_label=document_label,
            document_original=safe_original,
            document_stored=stored_filename,
            metadata_mode=metadata_mode,
            created_by=current_user.id,
        )
        db.session.add(achievement)
        db.session.commit()
        record_action_attempt("achievement_submit")
        log_activity("file_upload", f"achievement:{achievement.id}", user_id=current_user.id)
        flash("Achievement added successfully.", "success")
        return redirect(url_for("achievements"))

    search_query = sanitize_text(request.args.get("q"), 120)
    filter_category = (request.args.get("category") or "").strip().lower()
    filter_year = (request.args.get("year") or "").strip()
    sort_order = (request.args.get("sort") or "newest").strip().lower()
    if sort_order not in {"newest", "oldest"}:
        sort_order = "newest"

    your_achievements = []
    if current_user.is_authenticated:
        your_query = Achievement.query.filter_by(created_by=current_user.id)
        if search_query:
            search_like = f"%{search_query.lower()}%"
            your_query = your_query.filter(
                or_(
                    func.lower(Achievement.title).like(search_like),
                    func.lower(Achievement.issuer).like(search_like),
                    func.lower(Achievement.document_original).like(search_like),
                    func.lower(func.coalesce(Achievement.document_label, "")).like(search_like),
                    func.lower(func.coalesce(Achievement.description, "")).like(search_like),
                )
            )
        if filter_category in ALLOWED_ACHIEVEMENT_CATEGORIES:
            your_query = your_query.filter(Achievement.category == filter_category)
        if filter_year.isdigit() and len(filter_year) == 4:
            your_query = your_query.filter(func.strftime("%Y", Achievement.achievement_date) == filter_year)
        if sort_order == "oldest":
            your_query = your_query.order_by(Achievement.achievement_date.asc(), Achievement.created_at.asc())
        else:
            your_query = your_query.order_by(Achievement.achievement_date.desc(), Achievement.created_at.desc())
        your_achievements = your_query.all()

    public_query = Achievement.query.filter(Achievement.visibility_status == "public")
    if search_query:
        search_like = f"%{search_query.lower()}%"
        public_query = public_query.filter(
            or_(
                func.lower(Achievement.title).like(search_like),
                func.lower(Achievement.issuer).like(search_like),
                func.lower(Achievement.document_original).like(search_like),
                func.lower(func.coalesce(Achievement.document_label, "")).like(search_like),
                func.lower(func.coalesce(Achievement.description, "")).like(search_like),
            )
        )
    if filter_category in ALLOWED_ACHIEVEMENT_CATEGORIES:
        public_query = public_query.filter(Achievement.category == filter_category)
    if filter_year.isdigit() and len(filter_year) == 4:
        public_query = public_query.filter(func.strftime("%Y", Achievement.achievement_date) == filter_year)
    if sort_order == "oldest":
        public_query = public_query.order_by(Achievement.achievement_date.asc(), Achievement.created_at.asc())
    else:
        public_query = public_query.order_by(Achievement.achievement_date.desc(), Achievement.created_at.desc())
    public_achievements = public_query.limit(25).all()

    return render_template(
        "achievements.html",
        your_achievements=your_achievements,
        public_achievements=public_achievements,
        search_query=search_query,
        filter_category=filter_category,
        filter_year=filter_year,
        sort_order=sort_order,
        achievement_categories=sorted(ALLOWED_ACHIEVEMENT_CATEGORIES),
        **ctx("Achievements"),
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        raw_email = sanitize_text(request.form.get("email"), 120)
        if is_action_rate_limited(
            "contact_submit",
            app.config["CONTACT_MAX_ATTEMPTS"],
            app.config["CONTACT_BLOCK_MINUTES"],
        ):
            session["contact_form_data"] = {
                "name": sanitize_text(request.form.get("name"), 100),
                "email": raw_email,
                "subject": sanitize_text(request.form.get("subject"), 150),
                "custom_subject": sanitize_text(request.form.get("custom_subject"), 120),
                "message": sanitize_text(request.form.get("message"), 3000, multiline=True),
            }
            flash("Too many contact submissions. Try again later.", "error")
            return redirect(url_for("contact"))

        name = sanitize_text(request.form.get("name"), 100)
        email = validate_email_input(raw_email)
        subject = sanitize_text(request.form.get("subject"), 150)
        custom_subject = sanitize_text(request.form.get("custom_subject"), 120)
        message = sanitize_text(request.form.get("message"), 3000, multiline=True)
        issue_image = request.files.get("issue_image")
        draft_data = {
            "name": name,
            "email": raw_email,
            "subject": subject,
            "custom_subject": custom_subject,
            "message": message,
        }

        if not name or not email or not subject or not message:
            session["contact_form_data"] = draft_data
            flash("All contact fields are required.", "error")
            return redirect(url_for("contact"))
        if subject not in ALLOWED_CONTACT_SUBJECTS:
            session["contact_form_data"] = draft_data
            flash("Please select a valid subject.", "error")
            return redirect(url_for("contact"))
        if subject == "Other" and not custom_subject:
            session["contact_form_data"] = draft_data
            flash("Please enter your custom subject for Other.", "error")
            return redirect(url_for("contact"))

        if not recaptcha_verified():
            session["contact_form_data"] = draft_data
            flash("Captcha verification failed.", "error")
            return redirect(url_for("contact"))

        final_subject = subject if subject != "Other" else f"Other: {custom_subject}"
        attachment_original = None
        attachment_stored = None
        if issue_image and issue_image.filename:
            attachment_original = secure_filename(issue_image.filename or "")
            ext = allowed_extension(attachment_original, ALLOWED_CONTACT_ATTACHMENT_EXTENSIONS)
            if not attachment_original or not ext:
                session["contact_form_data"] = draft_data
                flash("Only JPG and PNG images are allowed for issue screenshot.", "error")
                return redirect(url_for("contact"))
            if not valid_mimetype_for_extension(issue_image.mimetype, ext):
                session["contact_form_data"] = draft_data
                flash("Issue screenshot MIME type is invalid.", "error")
                return redirect(url_for("contact"))
            if not valid_achievement_document(issue_image, ext):
                session["contact_form_data"] = draft_data
                flash("Issue screenshot content is invalid.", "error")
                return redirect(url_for("contact"))
            if not virus_scan_ok(issue_image):
                session["contact_form_data"] = draft_data
                flash("Issue screenshot failed security scan.", "error")
                return redirect(url_for("contact"))
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            attachment_stored = generate_stored_filename(attachment_original)
            attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], attachment_stored)
            try:
                save_encrypted_upload(issue_image, attachment_path)
            except Exception:
                session["contact_form_data"] = draft_data
                flash("Unable to securely store screenshot.", "error")
                return redirect(url_for("contact"))

        contact_message = ContactMessage(
            name=name,
            email=email,
            subject=final_subject,
            message=message,
            attachment_original=attachment_original,
            attachment_stored=attachment_stored,
        )
        db.session.add(contact_message)
        db.session.commit()
        email_sent, email_error = send_contact_notification(contact_message)
        log_activity("contact_submission", f"subject={final_subject[:60]}")
        if email_sent:
            log_activity("contact_email_sent", f"message_id={contact_message.id}")
        else:
            log_activity("contact_email_failed", f"message_id={contact_message.id} {email_error[:160]}")
        record_action_attempt("contact_submit")
        session.pop("contact_form_data", None)
        flash("Message submitted successfully.", "success")
        if not email_sent:
            flash("Message save ho gaya, but email notification send nahi hua. SMTP settings check karein.", "error")
        return redirect(url_for("contact"))

    contact_form_data = session.pop("contact_form_data", {}) or {}
    if request.method == "GET":
        # Allow prefilled contact drafts from UI helpers (safe, sanitized, optional).
        q_name = sanitize_text(request.args.get("name"), 100)
        q_email_raw = sanitize_text(request.args.get("email"), 120)
        q_email = validate_email_input(q_email_raw) or q_email_raw
        q_subject = sanitize_text(request.args.get("subject"), 150)
        q_custom_subject = sanitize_text(request.args.get("custom_subject"), 120)
        q_message = sanitize_text(request.args.get("message"), 3000, multiline=True)
        if q_subject and q_subject in ALLOWED_CONTACT_SUBJECTS:
            contact_form_data["subject"] = q_subject
        if q_custom_subject:
            contact_form_data["custom_subject"] = q_custom_subject
        if q_message:
            contact_form_data["message"] = q_message
        if q_name:
            contact_form_data["name"] = q_name
        if q_email:
            contact_form_data["email"] = q_email

    return render_template(
        "contact.html",
        subject_options=CONTACT_SUBJECT_OPTIONS,
        contact_form=contact_form_data,
        contact_public_email=app.config.get("CONTACT_PUBLIC_EMAIL", "yasirsec21@gmail.com"),
        **ctx("Contact Us"),
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = sanitize_text(request.form.get("username"), 80)
        email = validate_email_input(request.form.get("email"))
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        selected_role = normalize_role(request.form.get("role"))
        accept_terms = request.form.get("accept_terms") == "on"

        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if len(username) > 80:
            flash("Username is too long.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Password and confirm password must match.", "error")
            return redirect(url_for("register"))

        if not accept_terms:
            flash("Please accept Terms and Privacy Policy.", "error")
            return redirect(url_for("register"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

        pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(
            username=username,
            email=email,
            password_hash=pw_hash,
            role=selected_role if selected_role in {"user", "admin"} else "user",
            is_active_user=True,
            is_email_verified=False,
        )
        db.session.add(user)
        db.session.commit()

        verify_token = generate_email_verify_token(user.email)
        session["dev_verify_link"] = url_for("verify_email", token=verify_token)
        log_activity("registration_success", f"self signup role={user.role}", user_id=user.id)
        flash_notice(
            "registration_success",
            "Please verify your email before login.",
            "success",
        )
        return redirect(url_for("register"))

    verify_url = session.pop("dev_verify_link", None)
    return render_template(
        "register.html",
        verify_url=verify_url,
        **ctx("Signup"),
    )


@app.route("/verify-email/<token>")
def verify_email(token):
    email = verify_email_token(token)
    if not email:
        return render_template(
            "verify_email_result.html",
            verify_status="error",
            verify_title="Verification Link Invalid",
            verify_message="This email verification link is invalid or has expired.",
            verify_hint="Request a new signup verification link and try again.",
            primary_url=url_for("register"),
            primary_label="Go to Signup",
            secondary_url=url_for("login"),
            secondary_label="Back to Login",
            **ctx("Verify Email"),
        )

    user = User.query.filter_by(email=email).first()
    if not user:
        return render_template(
            "verify_email_result.html",
            verify_status="error",
            verify_title="Verification Failed",
            verify_message="We could not find an account for this verification request.",
            verify_hint="Try signing up again or contact support if the issue continues.",
            primary_url=url_for("register"),
            primary_label="Create Account",
            secondary_url=url_for("login"),
            secondary_label="Back to Login",
            **ctx("Verify Email"),
        )

    if user.is_email_verified:
        return render_template(
            "verify_email_result.html",
            verify_status="success",
            verify_title="Email Already Verified",
            verify_message="Your email is already verified. You can continue to login.",
            verify_hint="If you still cannot login, reset your password or check your email address.",
            primary_url=url_for("login"),
            primary_label="Go to Login",
            secondary_url=url_for("forgot_password"),
            secondary_label="Reset Password",
            **ctx("Verify Email"),
        )

    user.is_email_verified = True
    db.session.commit()
    log_activity("email_verified", user_id=user.id)
    return render_template(
        "verify_email_result.html",
        verify_status="success",
        verify_title="Email Verified Successfully",
        verify_message="Your account email has been verified. You can now login securely.",
        verify_hint="Use your registered email and password to continue.",
        primary_url=url_for("login"),
        primary_label="Login Now",
        secondary_url=url_for("register"),
        secondary_label="Back to Signup",
        **ctx("Verify Email"),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = validate_email_input(request.form.get("email"))
        password = request.form.get("password") or ""
        ip_address = client_ip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("login"))

        if not recaptcha_verified():
            flash("Captcha verification failed.", "error")
            return redirect(url_for("login"))

        if len(password) < 8:
            flash_notice("login_invalid", "Invalid credentials.", "error")
            return redirect(url_for("login"))

        if login_rate_limited(email, ip_address):
            flash("Too many login attempts. Try again later.", "error")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()
        if user and user.login_lock_until and user.login_lock_until > datetime.utcnow():
            log_activity("login_locked", f"user={user.email}", user_id=user.id)
            flash("Account temporarily locked due to suspicious login attempts.", "error")
            return redirect(url_for("login"))

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            record_login_attempt(email, ip_address, False)
            if user:
                user.failed_login_count = (user.failed_login_count or 0) + 1
                if user.failed_login_count >= app.config["LOGIN_MAX_ATTEMPTS"]:
                    user.login_lock_until = datetime.utcnow() + timedelta(minutes=app.config["LOGIN_BLOCK_MINUTES"])
                    send_security_alert(user, "Account lock triggered by failed login attempts")
                db.session.commit()
                log_activity("login_failed", "wrong password", user_id=user.id)
            else:
                log_activity("login_failed", f"unknown email={email}")
            flash_notice("login_invalid", "Invalid credentials.", "error")
            return redirect(url_for("login"))

        if not user.is_active_user:
            record_login_attempt(email, ip_address, False)
            flash("Account is deactivated. Contact administrator.", "error")
            return redirect(url_for("login"))

        if app.config["REQUIRE_EMAIL_VERIFICATION"] and not user.is_email_verified:
            flash("Please verify your email before login.", "error")
            return redirect(url_for("login"))

        record_login_attempt(email, ip_address, True)
        user.failed_login_count = 0
        user.login_lock_until = None
        user.last_login_ip = ip_address
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        if otp_required(user):
            session["pending_2fa_user"] = user.id
            flash_notice("login_success", "Enter your 2FA code to complete login.", "success")
            return redirect(url_for("login_2fa"))

        login_user(user)
        session["session_version"] = user.session_version
        log_activity("login_success", user_id=user.id)
        flash_notice("login_success", "Login successful.", "success")
        return redirect(url_for(get_panel_endpoint(user)))

    return render_template("login.html", **ctx("Login"))


@app.route("/login-2fa", methods=["GET", "POST"])
def login_2fa():
    pending_user_id = session.get("pending_2fa_user")
    if not pending_user_id:
        return redirect(url_for("login"))

    user = User.query.get(pending_user_id)
    if not user:
        session.pop("pending_2fa_user", None)
        return redirect(url_for("login"))

    if request.method == "POST":
        otp_code = sanitize_text(request.form.get("otp_code"), 12)
        if not verify_totp(user, otp_code):
            log_activity("login_2fa_failed", user_id=user.id)
            flash("Invalid 2FA code.", "error")
            return redirect(url_for("login_2fa"))

        login_user(user)
        session["session_version"] = user.session_version
        session.pop("pending_2fa_user", None)
        log_activity("login_success_2fa", user_id=user.id)
        flash_notice("login_success", "Login successful.", "success")
        return redirect(url_for(get_panel_endpoint(user)))

    return render_template("login_2fa.html", **ctx("Two-Factor Login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_url = None
    if request.method == "POST":
        email = validate_email_input(request.form.get("email"))
        if not email:
            flash("Please enter a valid email.", "error")
            return redirect(url_for("forgot_password"))

        if not recaptcha_verified():
            flash("Captcha verification failed.", "error")
            return redirect(url_for("forgot_password"))

        token = generate_reset_token(email)
        session["dev_reset_link"] = url_for("reset_password", token=token)
        flash("If the account exists, password reset link is generated below.", "success")
        return redirect(url_for("forgot_password"))

    if session.get("dev_reset_link"):
        reset_url = session.pop("dev_reset_link")
    return render_template("forgot_password.html", reset_url=reset_url, **ctx("Forgot Password"))


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("reset_password", token=token))

        if password != confirm_password:
            flash("Password and confirm password do not match.", "error")
            return redirect(url_for("reset_password", token=token))

        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        db.session.commit()
        log_activity("profile_change", "password reset", user_id=user.id)
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token, **ctx("Reset Password"))


@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for(get_panel_endpoint(current_user)))


@app.route("/user-dashboard")
@login_required
def user_dashboard():
    total_achievements = Achievement.query.filter_by(created_by=current_user.id).count()
    total_goals = Goal.query.filter_by(owner_id=current_user.id).count()
    recent_uploads = (
        Achievement.query.filter_by(created_by=current_user.id)
        .order_by(Achievement.created_at.desc())
        .limit(5)
        .all()
    )
    last_login = current_user.last_login_at
    security_status = "2FA Enabled" if current_user.twofa_enabled else "2FA Disabled"
    return render_template(
        "dashboard.html",
        total_achievements=total_achievements,
        total_goals=total_goals,
        recent_uploads=recent_uploads,
        last_login=last_login,
        security_status=security_status,
        dashboard_label="user_dashboard",
        **ctx("User Dashboard"),
    )


@app.route("/my-ai-history")
@login_required
def my_ai_history():
    return render_template("error.html", code=404, message="Page not found."), 404


def _run_ai_query_for_user(user_obj):
    return jsonify({"ok": False, "error": "This feature is disabled."}), 404











@app.route("/user-panel")
@login_required
def user_panel():
    return redirect(url_for("user_dashboard"))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", **ctx("Profile"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = (request.form.get("action") or "save").strip().lower()

        if action == "delete_account":
            confirm_text = (request.form.get("confirm_delete") or "").strip()
            current_password = request.form.get("current_password") or ""

            if confirm_text != "DELETE":
                flash("Type DELETE to confirm account deletion.", "error")
                return redirect(url_for("settings"))

            if not bcrypt.check_password_hash(current_user.password_hash, current_password):
                flash("Invalid password. Account not deleted.", "error")
                return redirect(url_for("settings"))

            if normalize_role(current_user.role) == "owner" and User.query.filter_by(role="owner").count() <= 1:
                flash("Primary owner account cannot be deleted.", "error")
                return redirect(url_for("settings"))

            user_id = current_user.id
            logout_user()
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
            flash("Account deleted successfully.", "success")
            return redirect(url_for("home"))

        session["pref_email_updates"] = request.form.get("email_updates") == "on"
        session["pref_compact_layout"] = request.form.get("compact_layout") == "on"
        session["pref_security_alerts"] = request.form.get("security_alerts") == "on"
        session["pref_public_profile"] = request.form.get("public_profile") == "on"
        session["pref_weekly_report"] = request.form.get("weekly_report") == "on"
        log_activity("profile_change", "settings updated", user_id=current_user.id)
        flash("Settings saved successfully.", "success")
        return redirect(url_for("settings"))

    return render_template(
        "settings.html",
        email_updates=session.get("pref_email_updates", False),
        compact_layout=session.get("pref_compact_layout", False),
        security_alerts=session.get("pref_security_alerts", True),
        public_profile=session.get("pref_public_profile", False),
        weekly_report=session.get("pref_weekly_report", False),
        **ctx("Settings"),
    )


@app.route("/security-settings", methods=["GET", "POST"])
@login_required
def security_settings():
    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()

        if action == "change_password":
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if not bcrypt.check_password_hash(current_user.password_hash, current_password):
                flash("Current password is invalid.", "error")
                return redirect(url_for("security_settings"))
            if len(new_password) < 8:
                flash("New password must be at least 8 characters.", "error")
                return redirect(url_for("security_settings"))
            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for("security_settings"))

            current_user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
            db.session.commit()
            log_activity("profile_change", "password changed", user_id=current_user.id)
            flash("Password updated successfully.", "success")
            return redirect(url_for("security_settings"))

        if action == "enable_2fa":
            if not pyotp:
                flash("pyotp not available on server.", "error")
                return redirect(url_for("security_settings"))
            current_user.twofa_secret = pyotp.random_base32()
            current_user.twofa_enabled = True
            db.session.commit()
            log_activity("profile_change", "2fa enabled", user_id=current_user.id)
            flash("2FA enabled. Add this secret in Google Authenticator.", "success")
            return redirect(url_for("security_settings"))

        if action == "disable_2fa":
            current_password = request.form.get("current_password") or ""
            if not bcrypt.check_password_hash(current_user.password_hash, current_password):
                flash("Invalid password.", "error")
                return redirect(url_for("security_settings"))
            current_user.twofa_enabled = False
            current_user.twofa_secret = None
            db.session.commit()
            log_activity("profile_change", "2fa disabled", user_id=current_user.id)
            flash("2FA disabled.", "success")
            return redirect(url_for("security_settings"))

        if action == "logout_all":
            current_user.session_version = (current_user.session_version or 1) + 1
            db.session.commit()
            log_activity("profile_change", "logout all sessions", user_id=current_user.id)
            logout_user()
            flash("Logged out from all devices. Please login again.", "success")
            return redirect(url_for("login"))

    recent_logins = (
        ActivityLog.query.filter_by(user_id=current_user.id)
        .filter(ActivityLog.event_type.like("login%"))
        .order_by(ActivityLog.created_at.desc())
        .limit(15)
        .all()
    )
    active_sessions = 1
    otp_uri = None
    if current_user.twofa_secret and pyotp:
        otp_uri = pyotp.TOTP(current_user.twofa_secret).provisioning_uri(
            name=current_user.email,
            issuer_name="SecureLogin",
        )
    return render_template(
        "security_settings.html",
        recent_logins=recent_logins,
        active_sessions=active_sessions,
        otp_uri=otp_uri,
        **ctx("Security Settings"),
    )


@app.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        action = (request.form.get("action") or "goal").strip().lower()
        if action == "goal":
            title = sanitize_text(request.form.get("title"), 140)
            description = sanitize_text(request.form.get("description"), 2000, multiline=True)
            target_date_raw = sanitize_text(request.form.get("target_date"), 20)
            priority = (request.form.get("priority") or "medium").strip().lower()
            status = (request.form.get("status") or "in_progress").strip().lower()
            milestones = sanitize_text(request.form.get("milestones"), 2000, multiline=True)
            progress_raw = sanitize_text(request.form.get("progress_percent"), 8) or "0"
            goal_draft = {
                "title": title,
                "description": description,
                "target_date": target_date_raw,
                "priority": priority,
                "status": status,
                "milestones": milestones,
                "progress_percent": progress_raw,
            }
            if not current_user.is_authenticated:
                session["goals_personal_form_data"] = goal_draft
                flash("Login required to add personal goals.", "error")
                return redirect(url_for("login"))

            target_date = parse_achievement_date(target_date_raw)

            if not title:
                session["goals_personal_form_data"] = goal_draft
                flash("Goal title is required.", "error")
                return redirect(url_for("goals"))

            if priority not in {"low", "medium", "high"}:
                priority = "medium"
            if status not in {"in_progress", "completed", "paused"}:
                status = "in_progress"
            if not progress_raw.isdigit():
                progress_raw = "0"
            progress = max(0, min(100, int(progress_raw)))
            if status == "completed":
                progress = 100

            goal = Goal(
                title=title,
                description=description,
                target_date=target_date,
                priority=priority,
                status=status,
                progress_percent=progress,
                milestones=milestones,
                owner_id=current_user.id,
            )
            db.session.add(goal)
            db.session.commit()
            session.pop("goals_personal_form_data", None)
            log_activity("profile_change", f"goal_created:{goal.id}", user_id=current_user.id)
            flash("Goal added.", "success")
            return redirect(url_for("goals"))

        if action == "tip":
            author_name = sanitize_text(request.form.get("author_name"), 100)
            title = sanitize_text(request.form.get("title"), 160)
            content = sanitize_text(request.form.get("content"), 3000, multiline=True)
            visibility_status = (request.form.get("visibility_status") or "private").strip().lower()
            tip_attachment = request.files.get("tip_attachment")
            tip_attachment_name = secure_filename((tip_attachment.filename or "").strip()) if tip_attachment else ""
            tip_draft = {
                "author_name": author_name,
                "title": title,
                "content": content,
                "visibility_status": visibility_status,
                "attachment_name": tip_attachment_name,
            }
            if current_user.is_authenticated and not author_name:
                author_name = current_user.username
            if not author_name or not title or not content:
                session["goals_tip_form_data"] = tip_draft
                flash("Author name, title, and content are required for tips.", "error")
                return redirect(url_for("goals"))
            if visibility_status not in ALLOWED_VISIBILITY_STATUS:
                visibility_status = "private"
            attachment_original = None
            attachment_stored = None
            if tip_attachment and tip_attachment.filename:
                attachment_original = secure_filename(tip_attachment.filename or "")
                ext = allowed_extension(attachment_original, ALLOWED_TIP_ATTACHMENT_EXTENSIONS)
                if not attachment_original or not ext:
                    session["goals_tip_form_data"] = tip_draft
                    flash("Tips attachment supports PDF, JPG, PNG only.", "error")
                    return redirect(url_for("goals"))
                if not valid_mimetype_for_extension(tip_attachment.mimetype, ext):
                    session["goals_tip_form_data"] = tip_draft
                    flash("Tips attachment MIME type is invalid.", "error")
                    return redirect(url_for("goals"))
                if not valid_achievement_document(tip_attachment, ext):
                    session["goals_tip_form_data"] = tip_draft
                    flash("Tips attachment content is invalid.", "error")
                    return redirect(url_for("goals"))
                if not virus_scan_ok(tip_attachment):
                    session["goals_tip_form_data"] = tip_draft
                    flash("Tips attachment failed security scan.", "error")
                    return redirect(url_for("goals"))
                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                attachment_stored = generate_stored_filename(attachment_original)
                attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], attachment_stored)
                try:
                    save_encrypted_upload(tip_attachment, attachment_path)
                except Exception:
                    session["goals_tip_form_data"] = tip_draft
                    flash("Unable to securely store tips attachment.", "error")
                    return redirect(url_for("goals"))
            tip = GoalTipPost(
                author_name=author_name,
                title=title,
                content=content,
                visibility_status=visibility_status,
                attachment_original=attachment_original,
                attachment_stored=attachment_stored,
                created_by=current_user.id if current_user.is_authenticated else None,
            )
            db.session.add(tip)
            db.session.commit()
            session.pop("goals_tip_form_data", None)
            log_activity("profile_change", f"goal_tip_created:{tip.id}", user_id=current_user.id if current_user.is_authenticated else None)
            flash("Tip shared successfully.", "success")
            return redirect(url_for("goals"))

        if action == "like":
            tip_id_raw = request.form.get("tip_id") or ""
            if not tip_id_raw.isdigit():
                flash("Invalid tip.", "error")
                return redirect(url_for("goals"))
            if not current_user.is_authenticated:
                flash("Login required to like a post.", "error")
                return redirect(url_for("login"))
            tip_id = int(tip_id_raw)
            tip = GoalTipPost.query.get(tip_id)
            if not tip:
                flash("Tip not found.", "error")
                return redirect(url_for("goals"))
            if not can_view_goal_tip(tip):
                flash("You do not have permission to interact with this private tip.", "error")
                return redirect(url_for("goals"))
            existing = GoalTipLike.query.filter_by(tip_id=tip_id, user_id=current_user.id).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
                log_activity("profile_change", f"goal_tip_unlike:{tip_id}", user_id=current_user.id)
                flash("Like removed.", "success")
            else:
                like = GoalTipLike(tip_id=tip_id, user_id=current_user.id)
                db.session.add(like)
                db.session.commit()
                log_activity("profile_change", f"goal_tip_like:{tip_id}", user_id=current_user.id)
                flash("Liked.", "success")
            return redirect(url_for("goals"))

        if action == "save_tip":
            if not current_user.is_authenticated:
                flash("Login required to save a tip.", "error")
                return redirect(url_for("login"))
            tip_id_raw = request.form.get("tip_id") or ""
            saved_name = sanitize_text(request.form.get("saved_name"), 160)
            if not tip_id_raw.isdigit():
                flash("Invalid tip.", "error")
                return redirect(url_for("goals"))
            tip_id = int(tip_id_raw)
            tip = GoalTipPost.query.get(tip_id)
            if not tip:
                flash("Tip not found.", "error")
                return redirect(url_for("goals"))
            if not can_view_goal_tip(tip):
                flash("You do not have permission to access this private tip.", "error")
                return redirect(url_for("goals"))
            final_saved_name = saved_name or tip.title
            existing = GoalTipSave.query.filter_by(tip_id=tip_id, user_id=current_user.id).first()
            if existing:
                existing.saved_name = final_saved_name
                db.session.commit()
                log_activity("profile_change", f"goal_tip_save_update:{tip_id}", user_id=current_user.id)
                flash("Saved tip name updated.", "success")
            else:
                save_item = GoalTipSave(
                    tip_id=tip_id,
                    user_id=current_user.id,
                    saved_name=final_saved_name,
                )
                db.session.add(save_item)
                db.session.commit()
                log_activity("profile_change", f"goal_tip_saved:{tip_id}", user_id=current_user.id)
                flash("Tip saved successfully.", "success")
            return redirect(url_for("goals"))

        if action == "unsave_tip":
            if not current_user.is_authenticated:
                flash("Login required to unsave a tip.", "error")
                return redirect(url_for("login"))
            tip_id_raw = request.form.get("tip_id") or ""
            if not tip_id_raw.isdigit():
                flash("Invalid tip.", "error")
                return redirect(url_for("goals"))
            tip_id = int(tip_id_raw)
            existing = GoalTipSave.query.filter_by(tip_id=tip_id, user_id=current_user.id).first()
            if not existing:
                flash("Saved tip not found.", "error")
                return redirect(url_for("goals"))
            db.session.delete(existing)
            db.session.commit()
            log_activity("profile_change", f"goal_tip_unsaved:{tip_id}", user_id=current_user.id)
            flash("Tip removed from saved list.", "success")
            return redirect(url_for("goals"))

        if action == "edit_tip":
            if not current_user.is_authenticated:
                flash("Login required.", "error")
                return redirect(url_for("login"))
            if not is_admin_or_owner():
                flash("Only owner/admin can edit goal tips.", "error")
                return redirect(url_for("goals"))
            tip_id_raw = request.form.get("tip_id") or ""
            author_name = sanitize_text(request.form.get("author_name"), 100)
            title = sanitize_text(request.form.get("title"), 160)
            content = sanitize_text(request.form.get("content"), 3000, multiline=True)
            visibility_status = (request.form.get("visibility_status") or "private").strip().lower()
            remove_attachment = request.form.get("remove_attachment") == "on"
            tip_attachment = request.files.get("tip_attachment")
            if not tip_id_raw.isdigit():
                flash("Invalid tip.", "error")
                return redirect(url_for("goals"))
            if not author_name or not title or not content:
                flash("Author name, title, and content are required.", "error")
                return redirect(url_for("goals"))
            if visibility_status not in ALLOWED_VISIBILITY_STATUS:
                visibility_status = "private"
            tip = GoalTipPost.query.get(int(tip_id_raw))
            if not tip:
                flash("Tip not found.", "error")
                return redirect(url_for("goals"))
            tip.author_name = author_name
            tip.title = title
            tip.content = content
            tip.visibility_status = visibility_status

            if tip_attachment and tip_attachment.filename:
                attachment_original = secure_filename(tip_attachment.filename or "")
                ext = allowed_extension(attachment_original, ALLOWED_TIP_ATTACHMENT_EXTENSIONS)
                if not attachment_original or not ext:
                    flash("Tips attachment supports PDF, JPG, PNG only.", "error")
                    return redirect(url_for("goals"))
                if not valid_mimetype_for_extension(tip_attachment.mimetype, ext):
                    flash("Tips attachment MIME type is invalid.", "error")
                    return redirect(url_for("goals"))
                if not valid_achievement_document(tip_attachment, ext):
                    flash("Tips attachment content is invalid.", "error")
                    return redirect(url_for("goals"))
                if not virus_scan_ok(tip_attachment):
                    flash("Tips attachment failed security scan.", "error")
                    return redirect(url_for("goals"))

                old_attachment = None
                if tip.attachment_stored:
                    old_attachment = os.path.join(app.config["UPLOAD_FOLDER"], tip.attachment_stored)
                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                attachment_stored = generate_stored_filename(attachment_original)
                attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], attachment_stored)
                try:
                    save_encrypted_upload(tip_attachment, attachment_path)
                except Exception:
                    flash("Unable to securely store tips attachment.", "error")
                    return redirect(url_for("goals"))
                tip.attachment_original = attachment_original
                tip.attachment_stored = attachment_stored
                if old_attachment:
                    remove_file_if_exists(old_attachment)
            elif remove_attachment and tip.attachment_stored:
                old_attachment = os.path.join(app.config["UPLOAD_FOLDER"], tip.attachment_stored)
                remove_file_if_exists(old_attachment)
                tip.attachment_original = None
                tip.attachment_stored = None

            db.session.commit()
            log_activity("profile_change", f"goal_tip_edit:{tip.id}", user_id=current_user.id)
            flash("Tip updated successfully.", "success")
            return redirect(url_for("goals"))

        if action == "delete_tip":
            if not current_user.is_authenticated:
                flash("Login required.", "error")
                return redirect(url_for("login"))
            if not is_admin_or_owner():
                flash("Only owner/admin can delete goal tips.", "error")
                return redirect(url_for("goals"))
            tip_id_raw = request.form.get("tip_id") or ""
            if not tip_id_raw.isdigit():
                flash("Invalid tip.", "error")
                return redirect(url_for("goals"))
            tip = GoalTipPost.query.get(int(tip_id_raw))
            if not tip:
                flash("Tip not found.", "error")
                return redirect(url_for("goals"))

            attachment_path = None
            if tip.attachment_stored:
                attachment_path = os.path.join(app.config["UPLOAD_FOLDER"], tip.attachment_stored)

            GoalTipSave.query.filter_by(tip_id=tip.id).delete(synchronize_session=False)
            GoalTipLike.query.filter_by(tip_id=tip.id).delete(synchronize_session=False)
            GoalTipComment.query.filter_by(tip_id=tip.id).delete(synchronize_session=False)
            db.session.delete(tip)
            db.session.commit()
            if attachment_path:
                remove_file_if_exists(attachment_path)

            log_activity("profile_change", f"goal_tip_delete:{tip_id_raw}", user_id=current_user.id)
            flash("Tip deleted successfully.", "success")
            return redirect(url_for("goals"))

        if action == "comment":
            tip_id_raw = request.form.get("tip_id") or ""
            author_name = sanitize_text(request.form.get("author_name"), 100)
            content = sanitize_text(request.form.get("content"), 2000, multiline=True)
            if not tip_id_raw.isdigit():
                flash("Invalid tip.", "error")
                return redirect(url_for("goals"))
            tip_id = int(tip_id_raw)
            tip = GoalTipPost.query.get(tip_id)
            if not tip:
                flash("Tip not found.", "error")
                return redirect(url_for("goals"))
            if not can_view_goal_tip(tip):
                flash("You do not have permission to comment on this private tip.", "error")
                return redirect(url_for("goals"))
            remaining = comment_cooldown_remaining_seconds()
            if remaining > 0:
                flash(f"Please wait {remaining}s before posting another comment.", "error")
                return redirect(url_for("goals"))
            if current_user.is_authenticated and not author_name:
                author_name = current_user.username
            if not author_name or not content:
                flash("Comment author and content required.", "error")
                return redirect(url_for("goals"))
            comment = GoalTipComment(
                tip_id=tip_id,
                author_name=author_name,
                content=content,
                created_by=current_user.id if current_user.is_authenticated else None,
            )
            db.session.add(comment)
            db.session.commit()
            mark_comment_submitted()
            log_activity("profile_change", f"goal_tip_comment:{tip_id}", user_id=current_user.id if current_user.is_authenticated else None)
            flash("Comment posted.", "success")
            return redirect(url_for("goals"))

        if action == "edit_comment":
            if not current_user.is_authenticated:
                flash("Login required.", "error")
                return redirect(url_for("login"))
            comment_id_raw = request.form.get("comment_id") or ""
            content = sanitize_text(request.form.get("content"), 2000, multiline=True)
            if not comment_id_raw.isdigit() or not content:
                flash("Invalid comment update.", "error")
                return redirect(url_for("goals"))
            comment = GoalTipComment.query.get(int(comment_id_raw))
            if not comment:
                flash("Comment not found.", "error")
                return redirect(url_for("goals"))
            can_manage = (comment.created_by == current_user.id and comment.created_by is not None) or is_admin_or_owner()
            if not can_manage:
                flash("You can edit only your own comments.", "error")
                return redirect(url_for("goals"))
            comment.content = content
            comment.updated_at = datetime.utcnow()
            db.session.commit()
            log_activity("profile_change", f"goal_tip_comment_edit:{comment.tip_id}", user_id=current_user.id)
            flash("Comment updated.", "success")
            return redirect(url_for("goals"))

        if action == "delete_comment":
            if not current_user.is_authenticated:
                flash("Login required.", "error")
                return redirect(url_for("login"))
            comment_id_raw = request.form.get("comment_id") or ""
            if not comment_id_raw.isdigit():
                flash("Invalid comment delete request.", "error")
                return redirect(url_for("goals"))
            comment = GoalTipComment.query.get(int(comment_id_raw))
            if not comment:
                flash("Comment not found.", "error")
                return redirect(url_for("goals"))
            can_manage = (comment.created_by == current_user.id and comment.created_by is not None) or is_admin_or_owner()
            if not can_manage:
                flash("You can delete only your own comments.", "error")
                return redirect(url_for("goals"))
            tip_id = comment.tip_id
            db.session.delete(comment)
            db.session.commit()
            log_activity("profile_change", f"goal_tip_comment_delete:{tip_id}", user_id=current_user.id)
            flash("Comment deleted.", "success")
            return redirect(url_for("goals"))

    your_goals = []
    if current_user.is_authenticated:
        your_goals = Goal.query.filter_by(owner_id=current_user.id).order_by(Goal.created_at.desc()).all()

    search_query = sanitize_text(request.args.get("q"), 120)
    author_filter = sanitize_text(request.args.get("author"), 100)
    saved_search_query = sanitize_text(request.args.get("saved_q"), 120)
    saved_author_filter = sanitize_text(request.args.get("saved_author"), 100)
    saved_sort_order = (request.args.get("saved_sort") or "newest").strip().lower()
    if saved_sort_order not in {"newest", "oldest", "name"}:
        saved_sort_order = "newest"
    sort_order = (request.args.get("sort") or "latest").strip().lower()
    if sort_order not in {"latest", "oldest", "popular"}:
        sort_order = "latest"
    page_raw = request.args.get("page") or "1"
    page = int(page_raw) if page_raw.isdigit() and int(page_raw) > 0 else 1
    per_page = 8
    comments_tip_raw = request.args.get("comments_tip") or ""
    comments_tip = int(comments_tip_raw) if comments_tip_raw.isdigit() else None
    comments_limit_raw = request.args.get("comments_limit") or "5"
    comments_limit = int(comments_limit_raw) if comments_limit_raw.isdigit() else 5
    comments_limit = max(5, min(50, comments_limit))

    tip_query = GoalTipPost.query
    if current_user.is_authenticated:
        if not is_admin_or_owner():
            tip_query = tip_query.filter(
                or_(
                    GoalTipPost.visibility_status == "public",
                    GoalTipPost.created_by == current_user.id,
                )
            )
    else:
        tip_query = tip_query.filter(GoalTipPost.visibility_status == "public")
    if search_query:
        search_like = f"%{search_query.lower()}%"
        tip_query = tip_query.filter(
            or_(
                func.lower(GoalTipPost.title).like(search_like),
                func.lower(GoalTipPost.content).like(search_like),
            )
        )
    if author_filter:
        tip_query = tip_query.filter(func.lower(GoalTipPost.author_name).like(f"%{author_filter.lower()}%"))

    all_tip_posts = tip_query.all()
    all_tip_ids = [tip.id for tip in all_tip_posts]
    likes_all_map = {}
    comments_map = {}
    liked_tip_ids = set()
    saved_tip_ids = set()
    saved_tip_names = {}
    saved_tip_cards = []

    if all_tip_ids:
        like_rows = (
            db.session.query(GoalTipLike.tip_id, func.count(GoalTipLike.id))
            .filter(GoalTipLike.tip_id.in_(all_tip_ids))
            .group_by(GoalTipLike.tip_id)
            .all()
        )
        likes_all_map = {tip_id: count for tip_id, count in like_rows}

    if sort_order == "oldest":
        sorted_tips = sorted(all_tip_posts, key=lambda x: x.created_at)
    elif sort_order == "popular":
        sorted_tips = sorted(all_tip_posts, key=lambda x: (likes_all_map.get(x.id, 0), x.created_at), reverse=True)
    else:
        sorted_tips = sorted(all_tip_posts, key=lambda x: x.created_at, reverse=True)

    total_tips = len(sorted_tips)
    total_pages = max(1, (total_tips + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    tip_posts = sorted_tips[start:start + per_page]
    tip_ids = [tip.id for tip in tip_posts]

    likes_map = {tip_id: likes_all_map.get(tip_id, 0) for tip_id in tip_ids}

    if tip_ids:
        comment_rows = (
            GoalTipComment.query.filter(GoalTipComment.tip_id.in_(tip_ids))
            .order_by(GoalTipComment.created_at.desc())
            .all()
        )
        for comment in comment_rows:
            comments_map.setdefault(comment.tip_id, []).append(comment)

        if current_user.is_authenticated:
            liked_rows = GoalTipLike.query.filter(
                GoalTipLike.tip_id.in_(tip_ids),
                GoalTipLike.user_id == current_user.id,
            ).all()
            liked_tip_ids = {row.tip_id for row in liked_rows}
            save_rows = GoalTipSave.query.filter(
                GoalTipSave.tip_id.in_(tip_ids),
                GoalTipSave.user_id == current_user.id,
            ).all()
            saved_tip_ids = {row.tip_id for row in save_rows}
            saved_tip_names = {row.tip_id: row.saved_name for row in save_rows}

    if current_user.is_authenticated:
        saved_query = GoalTipSave.query.join(GoalTipPost, GoalTipPost.id == GoalTipSave.tip_id).filter(
            GoalTipSave.user_id == current_user.id
        )
        if not is_admin_or_owner():
            saved_query = saved_query.filter(
                or_(
                    GoalTipPost.visibility_status == "public",
                    GoalTipPost.created_by == current_user.id,
                )
            )
        if saved_search_query:
            saved_like = f"%{saved_search_query.lower()}%"
            saved_query = saved_query.filter(
                or_(
                    func.lower(GoalTipSave.saved_name).like(saved_like),
                    func.lower(GoalTipPost.title).like(saved_like),
                    func.lower(GoalTipPost.content).like(saved_like),
                )
            )
        if saved_author_filter:
            saved_query = saved_query.filter(func.lower(GoalTipPost.author_name).like(f"%{saved_author_filter.lower()}%"))
        if saved_sort_order == "oldest":
            saved_query = saved_query.order_by(GoalTipSave.created_at.asc())
        elif saved_sort_order == "name":
            saved_query = saved_query.order_by(func.lower(GoalTipSave.saved_name).asc(), GoalTipSave.created_at.desc())
        else:
            saved_query = saved_query.order_by(GoalTipSave.created_at.desc())
        saved_rows = saved_query.limit(50).all()
        saved_ids = [row.tip_id for row in saved_rows]
        saved_tip_map = {}
        if saved_ids:
            saved_tip_map = {
                tip.id: tip
                for tip in GoalTipPost.query.filter(GoalTipPost.id.in_(saved_ids)).all()
            }
        for row in saved_rows:
            tip = saved_tip_map.get(row.tip_id)
            if not tip:
                continue
            saved_tip_cards.append(
                {
                    "tip_id": tip.id,
                    "saved_name": row.saved_name,
                    "tip_title": tip.title,
                    "author_name": tip.author_name,
                    "content_preview": (tip.content or "")[:120],
                    "visibility_status": tip.visibility_status,
                    "has_attachment": bool(tip.attachment_stored),
                    "attachment_original": tip.attachment_original or "",
                    "saved_at": row.created_at,
                }
            )

    goal_notifications = {"count": 0, "items": []}
    if current_user.is_authenticated:
        goal_notifications = build_goal_notifications_for_user(current_user, limit=5)
    notification_count = goal_notifications["count"]

    return render_template(
        "goals.html",
        your_goals=your_goals,
        tip_posts=tip_posts,
        goal_form=session.pop("goals_personal_form_data", {}) or {},
        tip_form=session.pop("goals_tip_form_data", {}) or {},
        saved_tip_cards=saved_tip_cards,
        saved_search_query=saved_search_query,
        saved_author_filter=saved_author_filter,
        saved_sort_order=saved_sort_order,
        likes_map=likes_map,
        comments_map=comments_map,
        liked_tip_ids=liked_tip_ids,
        saved_tip_ids=saved_tip_ids,
        saved_tip_names=saved_tip_names,
        search_query=search_query,
        author_filter=author_filter,
        sort_order=sort_order,
        page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        comments_tip=comments_tip,
        comments_limit=comments_limit,
        notification_count=notification_count,
        notification_items=goal_notifications["items"],
        **ctx("Goals"),
    )


@app.route("/goals/notifications")
@login_required
def goals_notifications():
    payload = build_goal_notifications_for_user(current_user, limit=6)
    return jsonify(payload)


@app.route("/goal-tip-files/<int:tip_id>")
def goal_tip_file(tip_id):
    tip = GoalTipPost.query.get_or_404(tip_id)
    if not can_view_goal_tip(tip):
        flash("You do not have permission to access this private attachment.", "error")
        return redirect(url_for("goals"))
    if not tip.attachment_stored:
        flash("No attachment found for this tip.", "error")
        return redirect(url_for("goals"))
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], tip.attachment_stored)
    if not os.path.isfile(file_path):
        flash("Attachment file not found.", "error")
        return redirect(url_for("goals"))
    try:
        decrypted_payload = read_decrypted_file(file_path)
    except Exception:
        flash("Unable to open attachment.", "error")
        return redirect(url_for("goals"))
    log_activity("file_download", f"goal_tip:{tip.id}", user_id=current_user.id if current_user.is_authenticated else None)
    return send_file(
        io.BytesIO(decrypted_payload),
        download_name=tip.attachment_original or "goal-tip-attachment",
        as_attachment=False,
        mimetype=file_response_mimetype(tip.attachment_original),
    )


@app.route("/contact-attachments/<int:message_id>")
@role_required("owner", "admin")
def contact_attachment(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    if not message.attachment_stored:
        flash("No attachment found for this contact message.", "error")
        return redirect(url_for("contact_messages"))
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], message.attachment_stored)
    if not os.path.isfile(file_path):
        flash("Attachment file not found.", "error")
        return redirect(url_for("contact_messages"))
    try:
        decrypted_payload = read_decrypted_file(file_path)
    except Exception:
        flash("Unable to open attachment.", "error")
        return redirect(url_for("contact_messages"))
    log_activity("file_download", f"contact_message:{message.id}", user_id=current_user.id if current_user.is_authenticated else None)
    return send_file(
        io.BytesIO(decrypted_payload),
        download_name=message.attachment_original or "contact-attachment",
        as_attachment=False,
        mimetype=file_response_mimetype(message.attachment_original),
    )


def _vault_item_for_owner(vault_file_id):
    item = VaultFile.query.get_or_404(vault_file_id)
    if item.owner_id != current_user.id:
        return None
    return item


def _vault_item_is_publicly_accessible(item):
    if not item:
        return False
    if item.share_expires_at and item.share_expires_at <= datetime.utcnow():
        return False
    return bool((item.visibility_status or "private") == "public" or item.share_enabled)


@app.route("/vault", methods=["GET", "POST"])
@login_required
def vault():
    if request.method == "POST":
        action = (request.form.get("action") or "upload").strip().lower()

        if action == "upload":
            if is_action_rate_limited(
                "vault_upload",
                app.config["VAULT_MAX_ATTEMPTS"],
                app.config["VAULT_BLOCK_MINUTES"],
            ):
                flash("Too many vault uploads. Try again shortly.", "error")
                return redirect(url_for("vault"))

            file = request.files.get("vault_file")
            if not file or not file.filename:
                flash("Select a file to upload.", "error")
                return redirect(url_for("vault"))

            safe_original = secure_filename(file.filename or "").strip()
            if not safe_original:
                flash("Invalid filename.", "error")
                return redirect(url_for("vault"))

            visibility_status = (request.form.get("visibility_status") or "private").strip().lower()
            if visibility_status not in ALLOWED_VISIBILITY_STATUS:
                visibility_status = "private"

            folder_tag = sanitize_text(request.form.get("folder_tag"), 80)
            note = sanitize_text(request.form.get("note"), 3000, multiline=True)
            lock_code = normalize_vault_access_code(request.form.get("file_pin"))
            lock_code_confirm = normalize_vault_access_code(request.form.get("file_pin_confirm"))
            mime_type = sanitize_text(file.mimetype or file_response_mimetype(safe_original), 120) or "application/octet-stream"
            extension = (safe_original.rsplit(".", 1)[1].lower() if "." in safe_original else "")
            auto_label = detect_vault_auto_label(file, safe_original, extension, mime_type)
            label = sanitize_text(request.form.get("label"), 160) or auto_label or safe_original[:160]
            size_bytes = current_stream_size(file)

            if (request.form.get("file_pin") or "").strip() or (request.form.get("file_pin_confirm") or "").strip():
                if not lock_code or not lock_code_confirm:
                    flash("Access code must be 4-12 digit PIN or 8-64 char password (letters + digits).", "error")
                    return redirect(url_for("vault"))
                if lock_code != lock_code_confirm:
                    flash("Access code and confirm code do not match.", "error")
                    return redirect(url_for("vault"))

            if not virus_scan_ok(file):
                flash("File failed malware/security scan.", "error")
                return redirect(url_for("vault"))

            stored_filename = generate_vault_stored_filename(safe_original)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
            try:
                save_encrypted_upload(file, save_path)
            except Exception:
                flash("Unable to securely store this file.", "error")
                return redirect(url_for("vault"))

            item = VaultFile(
                owner_id=current_user.id,
                label=label,
                folder_tag=folder_tag,
                note=note,
                original_filename=safe_original,
                stored_filename=stored_filename,
                mime_type=mime_type,
                extension=extension,
                size_bytes=size_bytes,
                visibility_status=visibility_status,
                share_enabled=False,
                share_token=generate_vault_share_token(),
                pin_hash=bcrypt.generate_password_hash(lock_code).decode("utf-8") if lock_code else None,
            )
            db.session.add(item)
            db.session.commit()
            log_vault_file_history(item.id, "upload", f"Uploaded: {item.label}", owner_id=item.owner_id)
            record_action_attempt("vault_upload")
            log_activity("vault_upload", f"vault_file:{item.id}", user_id=current_user.id)
            flash("File uploaded to your secure vault.", "success")
            return redirect(url_for("vault"))

        if action in {"bulk_download", "bulk_delete", "bulk_move"}:
            raw_ids = request.form.getlist("selected_vault_ids")
            selected_ids = []
            for value in raw_ids:
                if value and value.isdigit():
                    value_int = int(value)
                    if value_int not in selected_ids:
                        selected_ids.append(value_int)

            if not selected_ids:
                flash("Select at least one file.", "error")
                return redirect(url_for("vault"))

            vault_rows = (
                VaultFile.query.filter(VaultFile.owner_id == current_user.id, VaultFile.id.in_(selected_ids))
                .order_by(VaultFile.created_at.desc())
                .all()
            )
            if not vault_rows:
                flash("Selected files are not available.", "error")
                return redirect(url_for("vault"))

            if action == "bulk_move":
                target_folder = sanitize_text(request.form.get("bulk_folder_tag"), 80)
                if not target_folder:
                    flash("Enter a folder name to move selected files.", "error")
                    return redirect(url_for("vault"))
                for row in vault_rows:
                    row.folder_tag = target_folder
                    log_vault_file_history(
                        row.id,
                        "move",
                        f"Moved to folder: {target_folder}",
                        owner_id=row.owner_id,
                        auto_commit=False,
                    )
                db.session.commit()
                log_activity("vault_bulk_move", f"count:{len(vault_rows)}:folder:{target_folder}", user_id=current_user.id)
                flash(f"Moved {len(vault_rows)} file(s) to folder '{target_folder}'.", "success")
                return redirect(url_for("vault"))

            if action == "bulk_delete":
                removed_count = 0
                skipped_locked = 0
                for row in vault_rows:
                    if row.pin_hash:
                        skipped_locked += 1
                        continue
                    log_vault_file_history(
                        row.id,
                        "delete",
                        f"Deleted from vault: {row.label}",
                        owner_id=row.owner_id,
                        auto_commit=False,
                    )
                    remove_file_if_exists(os.path.join(app.config["UPLOAD_FOLDER"], row.stored_filename))
                    db.session.delete(row)
                    removed_count += 1
                db.session.commit()
                log_activity("vault_bulk_delete", f"count:{removed_count}", user_id=current_user.id)
                if skipped_locked:
                    flash(f"Deleted {removed_count} file(s). Skipped {skipped_locked} locked file(s).", "success")
                else:
                    flash(f"Deleted {removed_count} file(s) from vault.", "success")
                return redirect(url_for("vault"))

            archive = io.BytesIO()
            filename_counts = {}
            downloaded_rows = []
            with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                for row in vault_rows:
                    if row.pin_hash:
                        continue
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], row.stored_filename)
                    if not os.path.isfile(file_path):
                        continue
                    try:
                        decrypted_payload = read_decrypted_file(file_path)
                    except Exception:
                        continue

                    base_name = secure_filename(row.original_filename or row.label or f"vault-file-{row.id}")
                    if not base_name:
                        base_name = f"vault-file-{row.id}.bin"
                    current_count = filename_counts.get(base_name, 0) + 1
                    filename_counts[base_name] = current_count
                    if current_count > 1 and "." in base_name:
                        stem, ext = base_name.rsplit(".", 1)
                        output_name = f"{stem}-{current_count}.{ext}"
                    elif current_count > 1:
                        output_name = f"{base_name}-{current_count}"
                    else:
                        output_name = base_name

                    zf.writestr(output_name, decrypted_payload)
                    downloaded_rows.append(row)

            if not downloaded_rows:
                flash("No readable files found for bulk download.", "error")
                return redirect(url_for("vault"))

            for row in downloaded_rows:
                row.download_count = int(row.download_count or 0) + 1
            db.session.commit()

            log_activity("vault_bulk_download", f"count:{len(downloaded_rows)}", user_id=current_user.id)
            archive.seek(0)
            response = send_file(
                archive,
                as_attachment=True,
                download_name=f"vault-bundle-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip",
                mimetype="application/zip",
            )
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        target_id = request.form.get("vault_file_id")
        if not target_id or not target_id.isdigit():
            flash("Invalid vault item.", "error")
            return redirect(url_for("vault"))

        item = _vault_item_for_owner(int(target_id))
        if not item:
            flash("You cannot modify this file.", "error")
            return redirect(url_for("vault"))

        if action == "quick_action":
            quick_action = (request.form.get("quick_action") or "").strip().lower()
            if quick_action == "edit_details":
                new_label = sanitize_text(request.form.get("quick_label"), 160) or item.label
                new_folder = sanitize_text(request.form.get("quick_folder_tag"), 80)
                new_note = sanitize_text(request.form.get("quick_note"), 3000, multiline=True)
                item.label = new_label
                item.folder_tag = new_folder
                item.note = new_note
                db.session.commit()
                log_vault_file_history(item.id, "edit_details", "Updated name/folder/note", owner_id=item.owner_id)
                log_activity("vault_meta_update", f"vault_file:{item.id}", user_id=current_user.id)
                flash("File details updated.", "success")
                return redirect(url_for("vault"))

            if quick_action == "rename":
                new_label = sanitize_text(request.form.get("quick_label"), 160)
                if not new_label:
                    flash("Enter a valid new file name.", "error")
                    return redirect(url_for("vault"))
                item.label = new_label
                db.session.commit()
                log_vault_file_history(item.id, "rename", f"Renamed to: {new_label}", owner_id=item.owner_id)
                log_activity("vault_rename", f"vault_file:{item.id}", user_id=current_user.id)
                flash("File renamed.", "success")
                return redirect(url_for("vault"))

            if quick_action == "move":
                new_folder = sanitize_text(request.form.get("quick_folder_tag"), 80)
                if not new_folder:
                    flash("Enter a target folder name.", "error")
                    return redirect(url_for("vault"))
                item.folder_tag = new_folder
                db.session.commit()
                log_vault_file_history(item.id, "move", f"Moved to folder: {new_folder}", owner_id=item.owner_id)
                log_activity("vault_move", f"vault_file:{item.id}:folder:{new_folder}", user_id=current_user.id)
                flash("File moved to new folder.", "success")
                return redirect(url_for("vault"))

            if quick_action == "set_password":
                pin_value = normalize_vault_access_code(request.form.get("file_pin"))
                pin_confirm = normalize_vault_access_code(request.form.get("file_pin_confirm"))
                if not pin_value or not pin_confirm:
                    flash("Password must be 4-12 digit PIN or 8-64 char password (letters + digits).", "error")
                    return redirect(url_for("vault"))
                if pin_value != pin_confirm:
                    flash("Password and confirm password do not match.", "error")
                    return redirect(url_for("vault"))
                item.pin_hash = bcrypt.generate_password_hash(pin_value).decode("utf-8")
                db.session.commit()
                log_vault_file_history(item.id, "set_password", "Password set/changed", owner_id=item.owner_id)
                log_activity("vault_pin_set", f"vault_file:{item.id}", user_id=current_user.id)
                flash("File password enabled.", "success")
                return redirect(url_for("vault"))

            if quick_action == "remove_password":
                current_pin = request.form.get("current_pin")
                if item.pin_hash and not verify_vault_pin(item, current_pin):
                    flash("Invalid current password.", "error")
                    return redirect(url_for("vault"))
                item.pin_hash = None
                db.session.commit()
                log_vault_file_history(item.id, "remove_password", "Password removed", owner_id=item.owner_id)
                log_activity("vault_pin_clear", f"vault_file:{item.id}", user_id=current_user.id)
                flash("File password removed.", "success")
                return redirect(url_for("vault"))

            if quick_action == "delete":
                if item.pin_hash:
                    delete_code = request.form.get("current_pin")
                    if not verify_vault_pin(item, delete_code):
                        flash("This file is password protected. Enter valid password to delete.", "error")
                        return redirect(url_for("vault"))
                remove_file_if_exists(os.path.join(app.config["UPLOAD_FOLDER"], item.stored_filename))
                db.session.delete(item)
                db.session.commit()
                log_vault_file_history(item.id, "delete", f"Deleted from vault: {item.label}", owner_id=item.owner_id)
                log_activity("vault_delete", f"vault_file:{target_id}", user_id=current_user.id)
                flash("File removed from vault.", "success")
                return redirect(url_for("vault"))

            flash("Unsupported quick action.", "error")
            return redirect(url_for("vault"))

        if action == "delete":
            if item.pin_hash:
                delete_code = request.form.get("current_pin")
                if not verify_vault_pin(item, delete_code):
                    flash("This file is locked. Enter valid PIN/password to delete it.", "error")
                    return redirect(url_for("vault"))
            remove_file_if_exists(os.path.join(app.config["UPLOAD_FOLDER"], item.stored_filename))
            db.session.delete(item)
            db.session.commit()
            log_vault_file_history(item.id, "delete", f"Deleted from vault: {item.label}", owner_id=item.owner_id)
            log_activity("vault_delete", f"vault_file:{target_id}", user_id=current_user.id)
            flash("File removed from vault.", "success")
            return redirect(url_for("vault"))

        if action == "visibility":
            visibility_status = (request.form.get("visibility_status") or "private").strip().lower()
            if visibility_status not in ALLOWED_VISIBILITY_STATUS:
                visibility_status = "private"
            item.visibility_status = visibility_status
            if not item.share_token:
                item.share_token = generate_vault_share_token()
            db.session.commit()
            log_vault_file_history(item.id, "visibility", f"Visibility set to: {visibility_status}", owner_id=item.owner_id)
            log_activity("vault_visibility", f"vault_file:{item.id}:{visibility_status}", user_id=current_user.id)
            flash("Visibility updated.", "success")
            return redirect(url_for("vault"))

        if action == "toggle_share":
            item.share_enabled = not bool(item.share_enabled)
            if item.share_enabled and not item.share_token:
                item.share_token = generate_vault_share_token()
            if item.share_enabled:
                _, expiry_dt = parse_share_expiry_choice(request.form.get("share_expiry"))
                item.share_expires_at = expiry_dt
            else:
                item.share_expires_at = None
            db.session.commit()
            status = "enabled" if item.share_enabled else "disabled"
            log_vault_file_history(item.id, "share_toggle", f"Share link {status}", owner_id=item.owner_id)
            log_activity("vault_share_toggle", f"vault_file:{item.id}:{status}", user_id=current_user.id)
            flash(f"Share link {status}.", "success")
            return redirect(url_for("vault"))

        if action == "regenerate_share":
            item.share_token = generate_vault_share_token()
            item.share_enabled = True
            _, expiry_dt = parse_share_expiry_choice(request.form.get("share_expiry"))
            item.share_expires_at = expiry_dt
            db.session.commit()
            log_vault_file_history(item.id, "share_regenerate", "Share link regenerated", owner_id=item.owner_id)
            log_activity("vault_share_regenerate", f"vault_file:{item.id}", user_id=current_user.id)
            flash("New share link generated.", "success")
            return redirect(url_for("vault"))

        if action == "set_pin":
            pin_value = normalize_vault_access_code(request.form.get("file_pin"))
            pin_confirm = normalize_vault_access_code(request.form.get("file_pin_confirm"))
            if not pin_value or not pin_confirm:
                flash("Access code must be 4-12 digit PIN or 8-64 char password (letters + digits).", "error")
                return redirect(url_for("vault"))
            if pin_value != pin_confirm:
                flash("Access code and confirm code do not match.", "error")
                return redirect(url_for("vault"))
            item.pin_hash = bcrypt.generate_password_hash(pin_value).decode("utf-8")
            db.session.commit()
            log_vault_file_history(item.id, "set_password", "Password set/changed", owner_id=item.owner_id)
            log_activity("vault_pin_set", f"vault_file:{item.id}", user_id=current_user.id)
            flash("File access lock enabled.", "success")
            return redirect(url_for("vault"))

        if action == "clear_pin":
            current_pin = request.form.get("current_pin")
            if item.pin_hash and not verify_vault_pin(item, current_pin):
                flash("Invalid access code. Unable to remove lock.", "error")
                return redirect(url_for("vault"))
            item.pin_hash = None
            db.session.commit()
            log_vault_file_history(item.id, "remove_password", "Password removed", owner_id=item.owner_id)
            log_activity("vault_pin_clear", f"vault_file:{item.id}", user_id=current_user.id)
            flash("File access lock removed.", "success")
            return redirect(url_for("vault"))

        if action == "update_meta":
            item.label = sanitize_text(request.form.get("label"), 160) or item.label
            item.folder_tag = sanitize_text(request.form.get("folder_tag"), 80)
            item.note = sanitize_text(request.form.get("note"), 3000, multiline=True)
            db.session.commit()
            log_vault_file_history(item.id, "edit_details", "Updated details", owner_id=item.owner_id)
            flash("Vault file details updated.", "success")
            return redirect(url_for("vault"))

        flash("Unsupported vault action.", "error")
        return redirect(url_for("vault"))

    search_query = sanitize_text(request.args.get("q"), 120)
    visibility_filter = (request.args.get("visibility") or "all").strip().lower()
    if visibility_filter not in {"all", "private", "public"}:
        visibility_filter = "all"
    share_filter = (request.args.get("share") or "all").strip().lower()
    if share_filter not in {"all", "on", "off"}:
        share_filter = "all"
    folder_filter = sanitize_text(request.args.get("folder"), 80)
    sort_order = (request.args.get("sort") or "newest").strip().lower()
    if sort_order not in {"newest", "oldest", "name_asc", "name_desc", "size_desc", "size_asc", "downloads_desc"}:
        sort_order = "newest"
    view_mode = (request.args.get("view") or "list").strip().lower()
    if view_mode not in {"list", "grid"}:
        view_mode = "list"

    base_query = VaultFile.query.filter(VaultFile.owner_id == current_user.id)

    if search_query:
        pattern = f"%{search_query.lower()}%"
        base_query = base_query.filter(
            or_(
                func.lower(VaultFile.label).like(pattern),
                func.lower(VaultFile.original_filename).like(pattern),
                func.lower(func.coalesce(VaultFile.note, "")).like(pattern),
                func.lower(func.coalesce(VaultFile.folder_tag, "")).like(pattern),
            )
        )

    if visibility_filter in {"private", "public"}:
        base_query = base_query.filter(VaultFile.visibility_status == visibility_filter)

    if share_filter == "on":
        base_query = base_query.filter(VaultFile.share_enabled.is_(True))
    elif share_filter == "off":
        base_query = base_query.filter(VaultFile.share_enabled.is_(False))

    if folder_filter:
        base_query = base_query.filter(func.lower(func.coalesce(VaultFile.folder_tag, "")) == folder_filter.lower())

    if sort_order == "oldest":
        base_query = base_query.order_by(VaultFile.created_at.asc())
    elif sort_order == "name_asc":
        base_query = base_query.order_by(func.lower(VaultFile.label).asc(), VaultFile.created_at.desc())
    elif sort_order == "name_desc":
        base_query = base_query.order_by(func.lower(VaultFile.label).desc(), VaultFile.created_at.desc())
    elif sort_order == "size_desc":
        base_query = base_query.order_by(VaultFile.size_bytes.desc(), VaultFile.created_at.desc())
    elif sort_order == "size_asc":
        base_query = base_query.order_by(VaultFile.size_bytes.asc(), VaultFile.created_at.desc())
    elif sort_order == "downloads_desc":
        base_query = base_query.order_by(VaultFile.download_count.desc(), VaultFile.created_at.desc())
    else:
        base_query = base_query.order_by(VaultFile.created_at.desc())

    items = base_query.all()
    item_ids = [row.id for row in items]
    history_map = {}
    history_actor_map = {}
    if item_ids:
        history_rows = (
            VaultFileHistory.query.filter(
                VaultFileHistory.owner_id == current_user.id,
                VaultFileHistory.vault_file_id.in_(item_ids),
            )
            .order_by(VaultFileHistory.created_at.desc())
            .all()
        )
        actor_ids = {h.created_by for h in history_rows if h.created_by}
        if actor_ids:
            history_actor_map = {
                row.id: row.username
                for row in User.query.with_entities(User.id, User.username).filter(User.id.in_(actor_ids)).all()
            }
        for h in history_rows:
            bucket = history_map.setdefault(h.vault_file_id, [])
            if len(bucket) >= 40:
                continue
            bucket.append(
                {
                    "event_type": h.event_type,
                    "details": h.details or "",
                    "created_at": h.created_at,
                    "created_at_iso": h.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if h.created_at else "",
                    "actor_name": history_actor_map.get(h.created_by, "You"),
                }
            )

    folder_rows = VaultFile.query.with_entities(VaultFile.folder_tag).filter(VaultFile.owner_id == current_user.id).all()
    folder_tags = sorted(
        {(row[0] or "").strip() for row in folder_rows if (row[0] or "").strip()},
        key=lambda value: value.lower(),
    )
    files_payload = []
    for item in items:
        share_url = url_for("vault_share_page", token=item.share_token, _external=True) if item.share_token else ""
        share_expiry_choice = "never"
        if item.share_expires_at:
            remaining = item.share_expires_at - datetime.utcnow()
            share_expiry_choice = "7d" if remaining.total_seconds() > (36 * 3600) else "24h"
        files_payload.append(
            {
                "id": item.id,
                "label": item.label,
                "folder_tag": (item.folder_tag or "").strip(),
                "note": item.note or "",
                "original_filename": item.original_filename,
                "mime_type": item.mime_type or file_response_mimetype(item.original_filename),
                "extension": item.extension or "",
                "size_bytes": int(item.size_bytes or 0),
                "visibility_status": item.visibility_status or "private",
                "share_enabled": bool(item.share_enabled),
                "share_expired": bool(item.share_expires_at and item.share_expires_at <= datetime.utcnow()),
                "share_expires_at": item.share_expires_at,
                "share_expiry_choice": share_expiry_choice,
                "download_count": int(item.download_count or 0),
                "created_at": item.created_at,
                "pin_protected": bool(item.pin_hash),
                "share_url": share_url,
                "share_url_encoded": urllib_parse.quote_plus(share_url) if share_url else "",
                "share_text_encoded": urllib_parse.quote_plus(f"{item.label} - Secure Vault") if share_url else "",
                "history_rows": history_map.get(item.id, []),
            }
        )

    folder_group_map = {}
    for row in files_payload:
        group_name = (row.get("folder_tag") or "").strip() or "Uncategorized"
        folder_group_map.setdefault(group_name, []).append(row)
    folder_groups = [
        {"name": name, "items": values}
        for name, values in sorted(folder_group_map.items(), key=lambda pair: pair[0].lower())
    ]

    return render_template(
        "vault.html",
        vault_items=files_payload,
        folder_groups=folder_groups,
        total_items=len(files_payload),
        private_items=sum(1 for x in files_payload if x["visibility_status"] == "private"),
        public_items=sum(1 for x in files_payload if x["visibility_status"] == "public"),
        shared_items=sum(1 for x in files_payload if x["share_enabled"]),
        search_query=search_query,
        visibility_filter=visibility_filter,
        share_filter=share_filter,
        folder_filter=folder_filter,
        sort_order=sort_order,
        view_mode=view_mode,
        folder_tags=folder_tags,
        **ctx("Secure Vault"),
    )


@app.route("/vault/files/<int:vault_file_id>/download", methods=["GET", "POST"])
@login_required
def vault_file_download(vault_file_id):
    item = _vault_item_for_owner(vault_file_id)
    if not item:
        flash("You do not have permission to access this vault file.", "error")
        return redirect(url_for("vault"))

    if item.pin_hash:
        if is_vault_access_temporarily_locked(item):
            remaining_sec = vault_access_remaining_seconds(item)
            remaining_min = max(1, (remaining_sec + 59) // 60)
            flash(f"This file is temporarily locked due to failed attempts. Try again in about {remaining_min} minute(s).", "error")
            return redirect(url_for("vault"))
        pin_value = request.form.get("file_pin") if request.method == "POST" else request.args.get("pin")
        if not verify_vault_pin(item, pin_value):
            state = register_vault_access_failure(item)
            db.session.commit()
            if state["locked"]:
                wait_min = _vault_access_lock_window_minutes()
                log_activity("vault_access_lockout_owner", f"vault_file:{item.id}:download", user_id=current_user.id)
                flash(f"Too many wrong attempts. File locked for {wait_min} minute(s).", "error")
            else:
                flash(f"Invalid access code. {state['remaining']} attempt(s) remaining.", "error")
            return redirect(url_for("vault"))
        reset_vault_access_fail_state(item)

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], item.stored_filename)
    if not os.path.isfile(file_path):
        flash("Vault file not found.", "error")
        return redirect(url_for("vault"))

    try:
        decrypted_payload = read_decrypted_file(file_path)
    except Exception:
        flash("Unable to open vault file.", "error")
        return redirect(url_for("vault"))

    item.download_count = int(item.download_count or 0) + 1
    db.session.commit()
    log_activity("vault_download", f"vault_file:{item.id}", user_id=current_user.id)
    response = send_file(
        io.BytesIO(decrypted_payload),
        download_name=item.original_filename or item.label,
        as_attachment=True,
        mimetype=item.mime_type or file_response_mimetype(item.original_filename),
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/vault/files/<int:vault_file_id>/history.csv")
@login_required
def vault_file_history_csv(vault_file_id):
    item = _vault_item_for_owner(vault_file_id)
    if not item:
        flash("You do not have permission to access this vault file history.", "error")
        return redirect(url_for("vault"))

    range_key = normalize_history_range(request.args.get("range"), "all")
    base_query = VaultFileHistory.query.filter(
        VaultFileHistory.owner_id == current_user.id,
        VaultFileHistory.vault_file_id == item.id,
    )
    start_at = history_range_start_utc(range_key)
    if start_at is not None:
        base_query = base_query.filter(VaultFileHistory.created_at >= start_at)
    rows = base_query.order_by(VaultFileHistory.created_at.desc()).all()

    actor_ids = {row.created_by for row in rows if row.created_by}
    actor_map = {}
    if actor_ids:
        actor_map = {
            row.id: row.username
            for row in User.query.with_entities(User.id, User.username).filter(User.id.in_(actor_ids)).all()
        }

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["timestamp_utc", "event_type", "details", "actor"])
    for row in rows:
        writer.writerow(
            [
                row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
                row.event_type or "",
                (row.details or "").strip(),
                actor_map.get(row.created_by, "You"),
            ]
        )

    safe_name = secure_filename(item.label or f"vault-file-{item.id}") or f"vault-file-{item.id}"
    filename = f"{safe_name}-history-{range_key}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    response = Response(
        csv_buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/vault/share/<token>")
def vault_share_page(token):
    item = VaultFile.query.filter_by(share_token=(token or "").strip()).first_or_404()
    if not _vault_item_is_publicly_accessible(item):
        return render_template("error.html", code=403, message="This shared file is private or disabled."), 403

    share_url = url_for("vault_share_page", token=item.share_token, _external=True)
    return render_template(
        "vault_share.html",
        vault_item=item,
        access_error=None,
        access_locked=is_vault_access_temporarily_locked(item),
        access_lock_remaining=vault_access_remaining_seconds(item),
        share_expired=bool(item.share_expires_at and item.share_expires_at <= datetime.utcnow()),
        share_url=share_url,
        share_url_encoded=urllib_parse.quote_plus(share_url),
        share_text_encoded=urllib_parse.quote_plus(f"{item.label} - Secure Vault"),
        **ctx("Shared Vault File"),
    )


@app.route("/vault/share/<token>/download", methods=["GET", "POST"])
def vault_share_download(token):
    item = VaultFile.query.filter_by(share_token=(token or "").strip()).first_or_404()
    if not _vault_item_is_publicly_accessible(item):
        return render_template("error.html", code=403, message="This shared file is private or disabled."), 403

    if item.pin_hash:
        if is_vault_access_temporarily_locked(item):
            share_url = url_for("vault_share_page", token=item.share_token, _external=True)
            return render_template(
                "vault_share.html",
                vault_item=item,
                access_error="Too many wrong attempts. This file is temporarily locked.",
                access_locked=True,
                access_lock_remaining=vault_access_remaining_seconds(item),
                share_expired=bool(item.share_expires_at and item.share_expires_at <= datetime.utcnow()),
                share_url=share_url,
                share_url_encoded=urllib_parse.quote_plus(share_url),
                share_text_encoded=urllib_parse.quote_plus(f"{item.label} - Secure Vault"),
                **ctx("Shared Vault File"),
            ), 429
        pin_value = request.form.get("file_pin") if request.method == "POST" else request.args.get("pin")
        if not verify_vault_pin(item, pin_value):
            state = register_vault_access_failure(item)
            db.session.commit()
            share_url = url_for("vault_share_page", token=item.share_token, _external=True)
            error_message = (
                f"Too many wrong attempts. File locked for {_vault_access_lock_window_minutes()} minute(s)."
                if state["locked"]
                else f"Invalid access code. {state['remaining']} attempt(s) remaining."
            )
            if state["locked"]:
                log_activity("vault_access_lockout_shared", f"vault_file:{item.id}:shared_download", user_id=current_user.id if current_user.is_authenticated else None)
            return render_template(
                "vault_share.html",
                vault_item=item,
                access_error=error_message,
                access_locked=is_vault_access_temporarily_locked(item),
                access_lock_remaining=vault_access_remaining_seconds(item),
                share_expired=bool(item.share_expires_at and item.share_expires_at <= datetime.utcnow()),
                share_url=share_url,
                share_url_encoded=urllib_parse.quote_plus(share_url),
                share_text_encoded=urllib_parse.quote_plus(f"{item.label} - Secure Vault"),
                **ctx("Shared Vault File"),
            ), 403
        reset_vault_access_fail_state(item)

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], item.stored_filename)
    if not os.path.isfile(file_path):
        return render_template("error.html", code=404, message="Shared file not found."), 404

    try:
        decrypted_payload = read_decrypted_file(file_path)
    except Exception:
        return render_template("error.html", code=500, message="Unable to decrypt shared file."), 500

    item.download_count = int(item.download_count or 0) + 1
    db.session.commit()
    log_activity("vault_shared_download", f"vault_file:{item.id}", user_id=current_user.id if current_user.is_authenticated else None)
    response = send_file(
        io.BytesIO(decrypted_payload),
        download_name=item.original_filename or item.label,
        as_attachment=True,
        mimetype=item.mime_type or file_response_mimetype(item.original_filename),
    )
    response.headers["Cache-Control"] = "public, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html", **ctx("Privacy Policy"))


@app.route("/privacy-vault")
def privacy_vault():
    return render_template("privacy_vault.html", **ctx("Privacy Vault"))


@app.route("/terms")
def terms():
    return render_template("terms.html", **ctx("Terms & Conditions"))


@app.route("/data-retention")
def data_retention():
    return render_template("data_retention.html", **ctx("Data Retention"))


def render_admin_dashboard():
    total_users = User.query.count()
    total_messages = ContactMessage.query.count()
    active_users = User.query.filter_by(is_active_user=True).count()
    audit_range = (request.args.get("audit_range") or "all").strip().lower()
    if audit_range not in {"today", "7d", "all"}:
        audit_range = "all"
    lockout_range = (request.args.get("lockout_range") or "7d").strip().lower()
    if lockout_range not in {"today", "7d", "all"}:
        lockout_range = "7d"
    deletion_query = ActivityLog.query.filter(
        or_(
            ActivityLog.event_type == "file_delete",
            ActivityLog.details.like("%delete%"),
        )
    )
    now_utc = datetime.utcnow()
    today_start_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    def apply_time_range(query_obj, range_key):
        if range_key == "today":
            return query_obj.filter(ActivityLog.created_at >= today_start_utc)
        if range_key == "7d":
            return query_obj.filter(ActivityLog.created_at >= (now_utc - timedelta(days=7)))
        return query_obj

    if audit_range == "today":
        deletion_query = deletion_query.filter(ActivityLog.created_at >= today_start_utc)
    elif audit_range == "7d":
        deletion_query = deletion_query.filter(ActivityLog.created_at >= (now_utc - timedelta(days=7)))
    deletion_logs = deletion_query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    actor_ids = {entry.user_id for entry in deletion_logs if entry.user_id}
    actor_map = {}
    if actor_ids:
        actor_map = {
            row.id: row.username
            for row in User.query.with_entities(User.id, User.username).filter(User.id.in_(actor_ids)).all()
        }
    deletion_audit = []
    for entry in deletion_logs:
        details_text = (entry.details or "").strip()
        if not details_text and entry.event_type == "file_delete":
            details_text = "File delete action"
        deletion_audit.append(
            {
                "actor_name": actor_map.get(entry.user_id, "System"),
                "event_type": entry.event_type,
                "details": details_text,
                "ip_address": entry.ip_address or "n/a",
                "created_at": entry.created_at,
            }
        )
    lockout_base_query = ActivityLog.query.filter(
        ActivityLog.event_type.in_(["vault_access_lockout_owner", "vault_access_lockout_shared"])
    )
    lockout_today_count = apply_time_range(lockout_base_query, "today").count()
    lockout_7d_count = apply_time_range(lockout_base_query, "7d").count()
    filtered_lockout_query = apply_time_range(lockout_base_query, lockout_range)

    if (request.args.get("export") or "").strip().lower() == "lockout_csv":
        export_rows = filtered_lockout_query.order_by(ActivityLog.created_at.desc()).all()
        export_actor_ids = {entry.user_id for entry in export_rows if entry.user_id}
        export_actor_map = {}
        if export_actor_ids:
            export_actor_map = {
                row.id: row.username
                for row in User.query.with_entities(User.id, User.username).filter(User.id.in_(export_actor_ids)).all()
            }
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["timestamp_utc", "actor", "event_type", "details", "ip_address"])
        for entry in export_rows:
            writer.writerow(
                [
                    entry.created_at.strftime("%Y-%m-%d %H:%M:%S") if entry.created_at else "",
                    export_actor_map.get(entry.user_id, "Guest/Unknown"),
                    entry.event_type or "",
                    (entry.details or "").strip(),
                    entry.ip_address or "",
                ]
            )
        filename = f"vault-lockouts-{lockout_range}-{now_utc.strftime('%Y%m%d-%H%M%S')}.csv"
        return Response(
            csv_buffer.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    recent_lockouts = filtered_lockout_query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    lockout_actor_ids = {entry.user_id for entry in recent_lockouts if entry.user_id}
    lockout_actor_map = {}
    if lockout_actor_ids:
        lockout_actor_map = {
            row.id: row.username
            for row in User.query.with_entities(User.id, User.username).filter(User.id.in_(lockout_actor_ids)).all()
        }
    lockout_feed = []
    for entry in recent_lockouts:
        lockout_feed.append(
            {
                "actor_name": lockout_actor_map.get(entry.user_id, "Guest/Unknown"),
                "event_type": entry.event_type,
                "details": (entry.details or "").strip() or "Vault access lockout",
                "ip_address": entry.ip_address or "n/a",
                "created_at": entry.created_at,
            }
        )
    return render_template(
        "owner_panel.html",
        total_users=total_users,
        total_messages=total_messages,
        active_users=active_users,
        deletion_audit=deletion_audit,
        lockout_today_count=lockout_today_count,
        lockout_7d_count=lockout_7d_count,
        lockout_range=lockout_range,
        lockout_feed=lockout_feed,
        audit_range=audit_range,
        dashboard_label="admin_dashboard",
        **ctx("Admin Dashboard"),
    )


@app.route("/owner")
@role_required("owner", "admin")
def owner_panel():
    return render_admin_dashboard()


@app.route("/admin-dashboard")
@role_required("owner", "admin")
def admin_dashboard():
    return render_admin_dashboard()
















@app.route("/user-management", methods=["GET", "POST"])
@role_required("owner", "admin")
def user_management():
    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        target_id = request.form.get("user_id")

        if action == "create":
            if is_action_rate_limited(
                "user_create",
                app.config["USER_CREATE_MAX_ATTEMPTS"],
                app.config["USER_CREATE_BLOCK_MINUTES"],
            ):
                flash("Too many user creation attempts. Try again later.", "error")
                return redirect(url_for("user_management"))

            username = sanitize_text(request.form.get("username"), 80)
            email = validate_email_input(request.form.get("email"))
            password = request.form.get("password") or ""
            role = normalize_role(request.form.get("role"))

            if not username or not email or not password:
                flash("Username, email and password are required.", "error")
                return redirect(url_for("user_management"))

            if len(username) > 80 or len(password) < 8:
                flash("Invalid username or weak password.", "error")
                return redirect(url_for("user_management"))

            if User.query.filter_by(email=email).first():
                flash("Email already exists.", "error")
                return redirect(url_for("user_management"))

            if role == "owner" and not is_owner():
                flash("Only owner can assign owner role.", "error")
                return redirect(url_for("user_management"))

            new_user = User(
                username=username,
                email=email,
                password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
                role=role if role in ALLOWED_ROLES else "user",
                is_active_user=True,
            )
            db.session.add(new_user)
            db.session.commit()
            record_action_attempt("user_create")
            flash("User created successfully.", "success")
            return redirect(url_for("user_management"))

        if action == "bulk":
            bulk_action = (request.form.get("bulk_action") or "").strip().lower()
            raw_ids = request.form.getlist("selected_user_ids")
            selected_ids = []
            for value in raw_ids:
                if value and value.isdigit():
                    uid = int(value)
                    if uid not in selected_ids:
                        selected_ids.append(uid)

            if bulk_action not in {"activate", "deactivate", "delete", "set_role_user", "set_role_admin"}:
                flash("Select a valid bulk action.", "error")
                return redirect(url_for("user_management"))

            if not selected_ids:
                flash("Select at least one user.", "error")
                return redirect(url_for("user_management"))

            users_map = {u.id: u for u in User.query.filter(User.id.in_(selected_ids)).all()}
            to_process = [users_map[uid] for uid in selected_ids if uid in users_map]
            if not to_process:
                flash("Selected users not found.", "error")
                return redirect(url_for("user_management"))

            owner_ids_selected_for_role_change = {
                u.id
                for u in to_process
                if normalize_role(u.role) == "owner" and bulk_action in {"set_role_user", "set_role_admin"}
            }
            owner_ids_selected_for_delete = {
                u.id for u in to_process if normalize_role(u.role) == "owner" and bulk_action == "delete"
            }
            owner_ids_that_lose_owner = owner_ids_selected_for_delete | owner_ids_selected_for_role_change
            if owner_ids_that_lose_owner:
                remaining_owner_count = (
                    User.query.filter_by(role="owner").filter(~User.id.in_(owner_ids_that_lose_owner)).count()
                )
                if remaining_owner_count <= 0:
                    flash("At least one owner account must remain.", "error")
                    return redirect(url_for("user_management"))

            applied = 0
            skipped = 0
            skip_reasons = []

            for target_user in to_process:
                target_role = normalize_role(target_user.role)

                if target_user.id == current_user.id:
                    skipped += 1
                    skip_reasons.append(f"{target_user.username}: cannot modify your own account in bulk.")
                    continue

                if target_role == "owner" and not is_owner():
                    skipped += 1
                    skip_reasons.append(f"{target_user.username}: admin cannot manage owner account.")
                    continue

                if bulk_action == "activate":
                    if not target_user.is_active_user:
                        target_user.is_active_user = True
                        applied += 1
                    else:
                        skipped += 1
                elif bulk_action == "deactivate":
                    if target_user.is_active_user:
                        target_user.is_active_user = False
                        applied += 1
                    else:
                        skipped += 1
                elif bulk_action == "delete":
                    db.session.delete(target_user)
                    applied += 1
                elif bulk_action == "set_role_user":
                    if target_role != "user":
                        target_user.role = "user"
                        applied += 1
                    else:
                        skipped += 1
                elif bulk_action == "set_role_admin":
                    if target_role != "admin":
                        target_user.role = "admin"
                        applied += 1
                    else:
                        skipped += 1

            if applied:
                db.session.commit()
                action_label_map = {
                    "activate": "activate",
                    "deactivate": "deactivate",
                    "delete": "delete",
                    "set_role_user": "change role to user",
                    "set_role_admin": "change role to admin",
                }
                action_label = action_label_map.get(bulk_action, bulk_action)
                flash(f"Bulk {action_label} completed for {applied} user(s).", "success")
            else:
                db.session.rollback()
                action_label_map = {
                    "activate": "activate",
                    "deactivate": "deactivate",
                    "delete": "delete",
                    "set_role_user": "change role to user",
                    "set_role_admin": "change role to admin",
                }
                action_label = action_label_map.get(bulk_action, bulk_action)

            if skipped:
                detail = f" Skipped {skipped} user(s)."
                if skip_reasons:
                    detail += " " + " ".join(skip_reasons[:3])
                    if len(skip_reasons) > 3:
                        detail += " ..."
                flash(detail.strip(), "error")

            session["user_mgmt_bulk_result"] = {
                "action": action_label,
                "applied": int(applied),
                "skipped": int(skipped),
            }

            return redirect(url_for("user_management"))

        if not target_id or not target_id.isdigit():
            flash("Invalid user selection.", "error")
            return redirect(url_for("user_management"))

        target_user = User.query.get(int(target_id))
        if not target_user:
            flash("User not found.", "error")
            return redirect(url_for("user_management"))

        if normalize_role(target_user.role) == "owner" and not is_owner():
            flash("Admin cannot manage owner account.", "error")
            return redirect(url_for("user_management"))

        if action == "update":
            username = sanitize_text(request.form.get("username"), 80)
            role = normalize_role(request.form.get("role"))

            if not username:
                flash("Username is required.", "error")
                return redirect(url_for("user_management"))

            if role == "owner" and not is_owner():
                flash("Only owner can assign owner role.", "error")
                return redirect(url_for("user_management"))

            if (
                target_user.id == current_user.id
                and normalize_role(target_user.role) == "owner"
                and role != "owner"
                and User.query.filter_by(role="owner").count() <= 1
            ):
                flash("At least one owner account must remain owner.", "error")
                return redirect(url_for("user_management"))

            target_user.username = username
            target_user.role = role
            db.session.commit()
            flash("User updated successfully.", "success")
            return redirect(url_for("user_management"))

        if action == "toggle_active":
            if target_user.id == current_user.id:
                flash("You cannot deactivate your own account.", "error")
                return redirect(url_for("user_management"))

            target_user.is_active_user = not target_user.is_active_user
            db.session.commit()
            flash("User status updated.", "success")
            return redirect(url_for("user_management"))

        if action == "delete":
            if target_user.id == current_user.id:
                flash("You cannot delete your own account.", "error")
                return redirect(url_for("user_management"))

            if normalize_role(target_user.role) == "owner" and not is_owner():
                flash("Admin cannot delete owner account.", "error")
                return redirect(url_for("user_management"))

            db.session.delete(target_user)
            db.session.commit()
            flash("User deleted.", "success")
            return redirect(url_for("user_management"))

        flash("Unsupported action.", "error")
        return redirect(url_for("user_management"))

    users = User.query.order_by(User.created_at.desc()).all()
    bulk_result = session.pop("user_mgmt_bulk_result", None)
    return render_template("user_management.html", users=users, bulk_result=bulk_result, **ctx("User Management"))


@app.route("/contact-messages")
@role_required("owner", "admin")
def contact_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("contact_messages.html", messages=messages, **ctx("Contact Messages"))


@app.route("/messages-view")
@role_required("owner", "admin")
def messages_view_alias():
    return redirect(url_for("contact_messages"))


@app.route("/achievements/<int:achievement_id>/edit", methods=["POST"])
@login_required
def edit_achievement(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)
    can_manage = achievement.created_by == current_user.id or is_admin_or_owner()
    if not can_manage:
        flash("You do not have permission to edit this achievement.", "error")
        return redirect(url_for("achievements"))

    metadata_mode = (request.form.get("metadata_mode") or "manual").strip().lower()
    if metadata_mode not in {"manual", "auto"}:
        metadata_mode = "manual"

    title = sanitize_text(request.form.get("title"), 140)
    issuer = sanitize_text(request.form.get("issuer"), 120)
    achievement_date = parse_achievement_date(request.form.get("achievement_date"))
    description = sanitize_text(request.form.get("description"), 2000, multiline=True)
    document_label = sanitize_text(request.form.get("document_label"), 160)
    category = (request.form.get("category") or "other").strip().lower()
    visibility_status = (request.form.get("visibility_status") or "private").strip().lower()
    verification_status = (request.form.get("verification_status") or "pending").strip().lower()
    file = request.files.get("document")
    remove_document = request.form.get("remove_document") == "on"

    if metadata_mode == "manual" and (not title or not achievement_date):
        flash("Manual mode me title aur pass date required hai.", "error")
        return redirect(url_for("achievements"))

    if metadata_mode == "manual" and not issuer:
        issuer = "Self Uploaded"

    achievement.title = title
    achievement.issuer = issuer
    achievement.achievement_date = achievement_date
    achievement.description = description
    achievement.document_label = document_label
    achievement.metadata_mode = metadata_mode
    achievement.category = category if category in ALLOWED_ACHIEVEMENT_CATEGORIES else "other"
    achievement.visibility_status = visibility_status if visibility_status in ALLOWED_VISIBILITY_STATUS else "private"
    achievement.verification_status = verification_status if verification_status in ALLOWED_VERIFICATION_STATUS else "pending"

    if file and file.filename:
        safe_original = secure_filename(file.filename)
        ext = allowed_extension(safe_original, ALLOWED_ACHIEVEMENT_EXTENSIONS)
        if not safe_original or not ext:
            flash("Unsupported document type. Allowed: PDF, JPG, PNG only.", "error")
            return redirect(url_for("achievements"))

        if not valid_mimetype_for_extension(file.mimetype, ext):
            flash("File MIME type is not allowed for selected document type.", "error")
            return redirect(url_for("achievements"))

        if not valid_achievement_document(file, ext):
            flash("Invalid file type.", "error")
            return redirect(url_for("achievements"))
        if not virus_scan_ok(file):
            flash("File failed security scan.", "error")
            return redirect(url_for("achievements"))

        auto_title, auto_date, auto_date_text = detect_auto_achievement_metadata(file, safe_original, ext)
        if metadata_mode == "auto":
            achievement.title = title or auto_title or pretty_title_from_filename(safe_original)
            achievement.achievement_date = achievement_date or auto_date
            if not achievement.achievement_date:
                flash("Auto date detect nahi hua. Please pass date manually add karein.", "error")
                return redirect(url_for("achievements"))
            achievement.achievement_date_text = auto_date_text or achievement.achievement_date.isoformat()
            achievement.issuer = issuer or "Self Uploaded"
            achievement.document_label = document_label or auto_title or pretty_title_from_filename(safe_original)
        else:
            achievement.achievement_date_text = achievement.achievement_date.isoformat() if achievement.achievement_date else None
            achievement.document_label = document_label or achievement.title

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        stored_filename = generate_stored_filename(safe_original)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
        try:
            save_encrypted_upload(file, save_path)
        except Exception:
            flash("Unable to securely encrypt and store file.", "error")
            return redirect(url_for("achievements"))

        old_file = os.path.join(app.config["UPLOAD_FOLDER"], achievement.document_stored)
        remove_file_if_exists(old_file)

        achievement.document_original = safe_original
        achievement.document_stored = stored_filename
        log_activity("file_upload", f"achievement:{achievement.id}", user_id=current_user.id)
    elif remove_document:
        if metadata_mode == "auto":
            flash("Document remove ke liye Manual mode use karein.", "error")
            return redirect(url_for("achievements"))
        old_file = os.path.join(app.config["UPLOAD_FOLDER"], achievement.document_stored)
        remove_file_if_exists(old_file)
        achievement.document_original = "removed"
        achievement.document_stored = f"removed_{uuid.uuid4().hex}.none"
        achievement.document_label = document_label or "Document removed"
        achievement.achievement_date_text = achievement_date.isoformat()
        log_activity("file_delete", f"achievement_doc_removed:{achievement.id}", user_id=current_user.id)
    else:
        if metadata_mode == "auto":
            existing_path = os.path.join(app.config["UPLOAD_FOLDER"], achievement.document_stored)
            if is_removed_file_token(achievement.document_stored):
                flash("Auto mode ke liye document required hai. Please new document upload karein.", "error")
                return redirect(url_for("achievements"))
            auto_title, auto_date, auto_date_text = detect_auto_metadata_from_saved_file(
                existing_path,
                achievement.document_original,
            )
            achievement.title = title or auto_title or achievement.title
            achievement.achievement_date = achievement_date or auto_date or achievement.achievement_date
            if not achievement.achievement_date:
                flash("Auto date detect nahi hua. Please pass date manually add karein.", "error")
                return redirect(url_for("achievements"))
            achievement.achievement_date_text = auto_date_text or achievement.achievement_date.isoformat()
            achievement.issuer = issuer or "Self Uploaded"
            achievement.document_label = document_label or auto_title or achievement.document_label
        else:
            achievement.title = title
            achievement.achievement_date = achievement_date
            achievement.achievement_date_text = achievement_date.isoformat()
            achievement.issuer = issuer or "Self Uploaded"
            achievement.document_label = document_label or title

    db.session.commit()
    log_activity("profile_change", f"achievement_update:{achievement.id}", user_id=current_user.id)
    flash("Achievement updated successfully.", "success")
    return redirect(url_for("achievements"))


@app.route("/achievements/<int:achievement_id>/delete", methods=["POST"])
@login_required
def delete_achievement(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)
    can_manage = achievement.created_by == current_user.id or is_admin_or_owner()
    if not can_manage:
        flash("You do not have permission to delete this achievement.", "error")
        return redirect(url_for("achievements"))

    document_path = os.path.join(app.config["UPLOAD_FOLDER"], achievement.document_stored)
    db.session.delete(achievement)
    db.session.commit()
    remove_file_if_exists(document_path)
    log_activity("file_delete", f"achievement:{achievement_id}", user_id=current_user.id)

    flash("Achievement deleted successfully.", "success")
    return redirect(url_for("achievements"))


@app.route("/achievement-files/<int:achievement_id>")
@login_required
def achievement_file(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)
    can_manage = achievement.created_by == current_user.id or is_admin_or_owner()
    if not can_manage:
        flash("You do not have permission to access this document.", "error")
        return redirect(url_for("achievements"))
    if is_removed_file_token(achievement.document_stored):
        flash("Document removed from this achievement.", "error")
        return redirect(url_for("achievements"))
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], achievement.document_stored)
    if not os.path.isfile(file_path):
        flash("Document not found.", "error")
        return redirect(url_for("achievements"))
    try:
        decrypted_payload = read_decrypted_file(file_path)
    except Exception:
        flash("Unable to open encrypted document.", "error")
        return redirect(url_for("achievements"))
    log_activity("file_download", f"achievement:{achievement.id}", user_id=current_user.id)
    return send_file(
        io.BytesIO(decrypted_payload),
        download_name=achievement.document_original,
        as_attachment=False,
        mimetype="application/octet-stream",
    )


@app.route("/posts/upload", methods=["POST"])
@login_required
def upload_post():
    title = sanitize_text(request.form.get("title"), 120)
    description = sanitize_text(request.form.get("description"), 2000, multiline=True)
    category = (request.form.get("category") or "").strip().lower()
    file = request.files.get("file")

    if not title or not description or not file:
        flash("Title, description and file are required.", "error")
        return redirect(url_for("home"))

    if category not in ALLOWED_CATEGORIES:
        flash("Invalid post category.", "error")
        return redirect(url_for("home"))

    raw_filename = file.filename or ""
    safe_original = secure_filename(raw_filename)
    ext = allowed_extension(safe_original, ALLOWED_POST_EXTENSIONS)

    if not safe_original or not ext:
        flash("Only PDF, JPG, PNG are allowed.", "error")
        return redirect(url_for("home"))

    if not valid_mimetype_for_extension(file.mimetype, ext):
        flash("File MIME type is not allowed for selected document type.", "error")
        return redirect(url_for("home"))

    if not valid_achievement_document(file, ext):
        flash("File content does not match allowed type.", "error")
        return redirect(url_for("home"))
    if not virus_scan_ok(file):
        flash("File failed security scan.", "error")
        return redirect(url_for("home"))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    stored_filename = generate_stored_filename(safe_original)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
    try:
        save_encrypted_upload(file, save_path)
    except Exception:
        flash("Unable to securely encrypt and store file.", "error")
        return redirect(url_for("home"))

    post = Post(
        title=title,
        description=description,
        category=category,
        original_filename=safe_original,
        stored_filename=stored_filename,
        uploaded_by=current_user.id,
    )
    db.session.add(post)
    db.session.commit()

    flash("Post uploaded successfully.", "success")
    return redirect(url_for("home"))


@app.route("/uploads/<int:post_id>")
def serve_upload(post_id):
    post = Post.query.get_or_404(post_id)
    if is_removed_file_token(post.stored_filename):
        flash("Document removed from this post.", "error")
        return redirect(url_for("about"))
    path = os.path.join(app.config["UPLOAD_FOLDER"], post.stored_filename)
    try:
        payload = read_decrypted_file(path)
    except Exception:
        flash("Unable to read file.", "error")
        return redirect(url_for("home"))
    log_activity("file_download", f"post:{post.id}", user_id=current_user.id)
    return send_file(io.BytesIO(payload), as_attachment=False, download_name=post.original_filename)


@app.route("/admin")
@role_required("owner", "admin")
def admin_alias():
    return redirect(url_for("owner_panel"))


@app.route("/logout")
@login_required
def logout():
    log_activity("logout", user_id=current_user.id)
    logout_user()
    session.pop("session_version", None)
    flash("Logged out.", "success")
    return redirect(url_for("home"))


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    flash("File too large for current server policy.", "error")
    return redirect(url_for("home")), 413


# Incremental blueprint split for new API route groups
app.register_blueprint(
    create_auth_api_blueprint(
        login_view=api_auth_login,
        refresh_view=api_auth_refresh,
        me_view=api_auth_me,
        logout_view=api_auth_logout,
    )
)




@app.errorhandler(400)
def bad_request(_error):
    return render_template("error.html", code=400, message="Bad request."), 400


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="Access denied."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(429)
def too_many_requests(_error):
    return render_template("error.html", code=429, message="Too many requests. Please try again later."), 429


@app.errorhandler(500)
def server_error(_error):
    db.session.rollback()
    return render_template("error.html", code=500, message="Something went wrong."), 500


if __name__ == "__main__":
    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        db.create_all()
        ensure_schema_compatibility()
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    debug_enabled = (os.environ.get("FLASK_DEBUG", "0") == "1") and not IS_PRODUCTION
    ssl_pref = str(os.environ.get("FLASK_SSL", "off")).strip().lower()
    ssl_context = None
    if not IS_PRODUCTION and ssl_pref in {"1", "true", "yes", "on", "adhoc"}:
        ssl_context = "adhoc"
    if IS_PRODUCTION:
        print("Production mode detected. Use gunicorn behind Nginx instead of Flask built-in server.")
    scheme = "https" if ssl_context else "http"
    print(f"Starting local server on {scheme}://{host}:{port} (FLASK_SSL={ssl_pref})")
    app.run(host=host, port=port, debug=debug_enabled, ssl_context=ssl_context)
