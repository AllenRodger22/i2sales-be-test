from __future__ import annotations

from flask import Blueprint, request, jsonify
from uuid import UUID

from utils.supabase_jwt import auth_required, verify_supabase_jwt, get_or_create_user_and_profile

bp = Blueprint("me_routes", __name__)


def _routing_target(role: str, profile_active: bool) -> tuple[str, str]:
    if not profile_active:
        return "/onboarding", "profile_inactive"
    if role == "ADMIN":
        return "/admin", "role=ADMIN"
    if role == "MANAGER":
        return "/manager", "role=MANAGER"
    return "/app", "role=BROKER"


@bp.get("/me")
def me():
    # Public route that requires token in Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Unauthorized", "detail": "Missing Authorization header"}), 401
    try:
        claims = verify_supabase_jwt(auth_header)
    except Exception as e:
        return jsonify({"error": "Unauthorized", "detail": str(e)}), 401

    sub = claims.get("sub")
    email = claims.get("email")
    role = claims.get("role") or "BROKER"

    user, profile = get_or_create_user_and_profile(sub, email)

    target, reason = _routing_target(user.role or role, bool(profile.is_active if profile else True))

    return jsonify({
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        },
        "profile": {
            "phoneNumber": profile.phone_number if profile else None,
            "address": profile.address if profile else None,
            "avatarUrl": profile.avatar_url if profile else None,
            "isActive": bool(profile.is_active) if profile else True,
        },
        "routing": {
            "target": target,
            "reason": reason,
        }
    }), 200

