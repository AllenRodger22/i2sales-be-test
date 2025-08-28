"""Auth routes for Supabase-only flow.

Frontend authenticates with Supabase and calls the API with
Authorization: Bearer <supabase_access_token>.
"""

from flask import Blueprint, jsonify, g
from extensions import db
from models.user import User
from .supabase_middleware import supabase_required

# Registered by app.py at /api/v1/auth
bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["POST"])
def login():
    # Deprecated in Supabase-only flow
    return jsonify({"error": "Deprecated. Use Supabase auth in frontend."}), 410


@bp.route("/register", methods=["POST"])
def register():
    # Deprecated in Supabase-only flow
    return jsonify({"error": "Deprecated. Use Supabase signup in frontend."}), 410


@bp.route("/me", methods=["GET"])
@supabase_required()
def me():
    # Middleware already validated token, ensured local user, and set g.current_user
    user = getattr(g, "current_user", None)
    if not user:
        # Fallback by jwt sub (should not happen)
        j = getattr(g, "jwt", {})
        u = db.session.query(User).filter_by(id=j.get("sub")).one_or_none()
        if not u:
            return jsonify({"error": "User not found"}), 404
        user = u

    return jsonify({
        "id": str(user.id),
        "name": user.name or (user.email.split("@")[0] if user.email else None),
        "email": user.email,
        "role": user.role,
    }), 200


@bp.route("/supabase/login", methods=["POST"])
def supabase_login():
    # Deprecated: no API JWT exchange anymore
    return jsonify({"error": "Deprecated. Call API with Supabase access token."}), 410
