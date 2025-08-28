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
    j = getattr(g, "jwt", {})
    try:
        user = db.session.query(User).filter_by(id=j.get("sub")).one()
    except Exception:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }), 200


@bp.route("/supabase/login", methods=["POST"])
def supabase_login():
    # Deprecated: no API JWT exchange anymore
    return jsonify({"error": "Deprecated. Call API with Supabase access token."}), 410

