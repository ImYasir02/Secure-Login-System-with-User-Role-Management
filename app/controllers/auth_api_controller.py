def auth_success_payload(user_obj, tokens):
    return {
        "ok": True,
        "tokens": tokens,
        "user": {
            "id": int(user_obj.id),
            "username": str(user_obj.username or ""),
            "email": str(user_obj.email or ""),
            "role": str(user_obj.role or "user"),
            "planType": str(getattr(user_obj, "ai_plan_type", "free") or "free"),
        },
    }


def auth_error_payload(message):
    return {"ok": False, "error": str(message)}
