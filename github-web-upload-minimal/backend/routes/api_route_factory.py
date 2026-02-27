from flask import Blueprint


def create_auth_api_blueprint(login_view, refresh_view, me_view, logout_view):
    bp = Blueprint("auth_api_bp", __name__, url_prefix="/api/auth")
    bp.add_url_rule("/login", view_func=login_view, methods=["POST"])
    bp.add_url_rule("/refresh", view_func=refresh_view, methods=["POST"])
    bp.add_url_rule("/me", view_func=me_view, methods=["GET"])
    bp.add_url_rule("/logout", view_func=logout_view, methods=["POST"])
    return bp
