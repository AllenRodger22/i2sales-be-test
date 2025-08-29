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
    """Backend registration using Supabase Admin API + local bootstrap.

    Body JSON: {"email": str, "password": str, "name"?: str, "role"?: "BROKER"|"MANAGER"|"ADMIN"}

    - Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in config/.env
    - Creates user in Supabase Auth (GoTrue Admin)
    - Ensures local public.users and public.profiles rows (1:1 mapping)
    """
    import httpx

    try:
        data = request.get_json(force=True, silent=False) or {}
    except Exception:
        data = {}

    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    name = (data.get("name") or "").strip() or None
    role = (data.get("role") or "BROKER").strip().upper()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    allowed_roles = {r.strip() for r in (current_app.config.get("ALLOWED_ROLES") or "BROKER,MANAGER,ADMIN").upper().split(",")}
    if role not in allowed_roles:
        role = "BROKER"

    supabase_url = (current_app.config.get("SUPABASE_URL") or "").rstrip("/")
    service_key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not supabase_url or not service_key:
        return jsonify({"error": "Server not configured", "detail": "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"}), 503

    admin_users_url = f"{supabase_url}/auth/v1/admin/users"

    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,  # allow immediate sign-in without email verification
        "user_metadata": {"name": name, "role": role},
    }

    try:
        with httpx.Client(timeout=10.0) as c:
            r = c.post(
                admin_users_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {service_key}",
                    "apikey": service_key,
                    "Content-Type": "application/json",
                },
            )
    except Exception as e:
        current_app.logger.exception("Supabase admin create_user request failed")
        return jsonify({"error": "Upstream error", "detail": str(e)}), 502

    if r.status_code not in (200, 201):
        try:
            err = r.json()
        except Exception:
            err = {"status_code": r.status_code, "text": r.text[:200]}
        # Conflict or validation errors → 409
        code = 409 if r.status_code in (400, 409, 422) else 502
        return jsonify({"error": "Supabase create_user failed", "detail": err}), code

    body = r.json() or {}
    supabase_user = body.get("user") or body  # compatible with possible shapes
    sup_id = supabase_user.get("id")
    if not sup_id:
        return jsonify({"error": "Invalid Supabase response", "detail": body}), 502

    # Ensure local user + profile
    try:
        from utils.supabase_jwt import get_or_create_user_and_profile
        user, profile = get_or_create_user_and_profile(sup_id, email, role)
        # Update name if provided
        if name and user.name != name:
            user.name = name
            db.session.commit()
    except Exception as e:
        current_app.logger.exception("Local bootstrap failed")
        db.session.rollback()
        return jsonify({"error": "Local bootstrap failed", "detail": str(e)}), 500

    return jsonify({
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "supabase_user_id": sup_id,
    }), 201


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
