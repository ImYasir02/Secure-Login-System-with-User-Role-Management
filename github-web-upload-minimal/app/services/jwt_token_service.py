from datetime import datetime, timedelta
import uuid

import jwt


class JWTTokenError(Exception):
    pass


def issue_token_pair(secret_key, user_id, role, session_version, access_minutes=15, refresh_days=7):
    now = datetime.utcnow()
    base_claims = {
        "sub": str(user_id),
        "role": str(role or "user"),
        "sv": int(session_version or 1),
    }
    access_payload = {
        **base_claims,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=access_minutes)).timestamp()),
    }
    refresh_payload = {
        **base_claims,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=refresh_days)).timestamp()),
    }
    return {
        "access_token": jwt.encode(access_payload, secret_key, algorithm="HS256"),
        "refresh_token": jwt.encode(refresh_payload, secret_key, algorithm="HS256"),
        "access_expires_in_seconds": int(access_minutes) * 60,
        "refresh_expires_in_seconds": int(refresh_days) * 24 * 60 * 60,
    }


def decode_token(secret_key, token, expected_type=None):
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise JWTTokenError("Token expired.") from exc
    except jwt.PyJWTError as exc:
        raise JWTTokenError("Invalid token.") from exc
    token_type = str(payload.get("type") or "")
    if expected_type and token_type != expected_type:
        raise JWTTokenError("Invalid token type.")
    return payload
