"""Auth routes for Supabase-only flow.

Frontend authenticates with Supabase and calls the API with
Authorization: Bearer <supabase_access_token>.
"""

from flask import Blueprint, jsonify, g, request, current_app
import os
from extensions import db
from models.user import User
from .supabase_middleware import supabase_required
import time
import uuid as _uuid
import jwt as pyjwt

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


@bp.route("/dev/login", methods=["POST"])
def dev_login():
    """Mint a short-lived JWT for local testing.

    Body JSON: {"email": str, "role": "BROKER"|"MANAGER"|"ADMIN", "sub": optional UUID string}

    Security: gated by DEV_LOGIN_ENABLED=1 env var. Not for production use.
    """
    if not (current_app.config.get("DEV_LOGIN_ENABLED") or os.getenv("DEV_LOGIN_ENABLED") == "1"):
        return jsonify({"error": "Forbidden", "detail": "DEV login disabled"}), 403

    try:
        data = request.get_json(force=True, silent=False) or {}
    except Exception:
        data = {}

    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "BROKER").strip().upper()
    sub_str = (data.get("sub") or "").strip()

    if not email:
        return jsonify({"error": "email is required"}), 400
    if role not in {r.strip() for r in (current_app.config.get("ALLOWED_ROLES") or "BROKER,MANAGER,ADMIN").upper().split(",")}:
        return jsonify({"error": "invalid role"}), 400

    # Stable UUID v5 from email unless provided
    try:
        sup_uuid = _uuid.UUID(sub_str) if sub_str else _uuid.uuid5(_uuid.NAMESPACE_DNS, email)
    except Exception:
        return jsonify({"error": "invalid sub UUID"}), 400

    # Build claims matching expected issuer/audience
    iss = (current_app.config.get("SUPABASE_JWT_ISS") or (current_app.config.get("SUPABASE_URL") or "").rstrip("/") + "/auth/v1").rstrip("/")
    aud = current_app.config.get("SUPABASE_JWT_AUD")
    now = int(time.time())
    exp = now + 60 * 60  # 1 hour

    claims = {
        "iss": iss,
        "sub": str(sup_uuid),
        "email": email,
        "iat": now,
        "exp": exp,
        # Put role/email also into user_metadata to be picked up by verifier
        "user_metadata": {
            "email": email,
            "role": role,
        },
    }
    # Ensure compat with both verifiers: include audience 'authenticated'
    if aud and aud != "authenticated":
        claims["aud"] = [aud, "authenticated"]
    else:
        claims["aud"] = "authenticated"

    secret = current_app.config.get("SUPABASE_JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET") or "dev-secret"
    token = pyjwt.encode(claims, secret, algorithm="HS256")

    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "example_auth_header": f"Bearer {token}",
        "claims": claims,
    }), 200
