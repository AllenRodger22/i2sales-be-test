from __future__ import annotations

from functools import wraps
from typing import Callable, Dict, Any, Optional

from flask import request, jsonify, g

from extensions import db, bcrypt
from models.user import User
from .supabase_auth import verify_supabase_jwt, SupabaseAuthError
import uuid


def _extract_bearer_token() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def _claims_email(claims: Dict[str, Any]) -> str:
    email = (
        (claims.get("email") or "")
        or (claims.get("user_metadata") or {}).get("email")
        or (claims.get("app_metadata") or {}).get("email")
        or ""
    )
    return str(email).strip().lower()


def _ensure_local_user(email: str, name_hint: Optional[str], supabase_sub: str, default_role: str = "BROKER") -> User:
    """Upsert user ensuring the local id matches the Supabase sub when creating.

    - If a user with primary key == supabase_sub exists, return it.
    - Else, if a user with the same email exists, return it (keeps legacy data).
    - Else, create a new user with id = supabase_sub and role = default_role.
    """
    # Normalize UUID for primary key lookup
    sup_uuid = uuid.UUID(str(supabase_sub))

    # Prefer lookup by PK (expected for new users)
    user = db.session.get(User, sup_uuid)
    if user:
        return user

    # Fallback to legacy by-email lookup
    user = db.session.query(User).filter(User.email == email).one_or_none()
    if user:
        return user

    # Auto-provision with a dummy password as Supabase manages credentials
    dummy_pw_hash = bcrypt.generate_password_hash("supabase-external").decode("utf-8")
    user = User(
        id=sup_uuid,
        name=name_hint or email.split("@")[0],
        email=email,
        password_hash=dummy_pw_hash,
        role=default_role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def supabase_required() -> Callable:
    """Decorator to protect endpoints using a Supabase access token.

    - Expects Authorization: Bearer <supabase_access_token>
    - Verifies token using SUPABASE_JWT_SECRET
    - Auto-provisions a local User (role=BROKER) if missing
    - Stores normalized claims into g.jwt with the same shape used previously:
        {"sub": <local_user_id>, "role": <local_user_role>, "email": <email>, "supabase_sub": <supabase_sub>}
    """

    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_bearer_token()
            if not token:
                return jsonify({"error": "Unauthorized"}), 401

            try:
                sup_claims = verify_supabase_jwt(token)
            except SupabaseAuthError as e:
                return jsonify({"error": "Unauthorized", "detail": str(e)}), 401

            email = _claims_email(sup_claims)
            if not email:
                return jsonify({"error": "Token without valid email"}), 400

            name_hint = (
                (sup_claims.get("user_metadata") or {}).get("name")
                or (sup_claims.get("user_metadata") or {}).get("full_name")
                or sup_claims.get("name")
            )

            try:
                user = _ensure_local_user(email, name_hint, sup_claims.get("sub"))
            except Exception as e:
                db.session.rollback()
                return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

            # Normalize claims to mimic previous JWT claims used in the app
            g.jwt = {
                "sub": str(user.id),
                "role": user.role,
                "email": user.email,
                "supabase_sub": sup_claims.get("sub"),
            }
            g.current_user = user

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_claims() -> Dict[str, Any]:
    return getattr(g, "jwt", {})


def current_sub() -> Optional[str]:
    return current_claims().get("sub")


def current_role() -> Optional[str]:
    return current_claims().get("role")
