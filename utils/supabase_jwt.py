from __future__ import annotations

import base64
import json
import time
import logging
from functools import wraps
from typing import Any, Dict, Optional, Tuple

import httpx
import jwt as pyjwt
from cachetools import TTLCache
from flask import current_app, g, request

from extensions import db
from models.user import User
from models.profile import Profile
from utils.responses import unauthorized, server_error
from flask import jsonify


_jwks_cache: TTLCache[str, Dict[str, Any]] = TTLCache(maxsize=4, ttl=15 * 60)
_rate_cache: TTLCache[str, int] = TTLCache(maxsize=10000, ttl=60)


class JwtValidationError(Exception):
    pass


def _allowed_roles() -> set[str]:
    roles_csv = (current_app.config.get("ALLOWED_ROLES") or "BROKER,MANAGER,ADMIN").upper()
    return {r.strip() for r in roles_csv.split(",") if r.strip()}


def _jwks_url() -> str:
    supabase_url = (current_app.config.get("SUPABASE_URL") or "").rstrip("/")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing in configuration")
    return f"{supabase_url}/auth/v1/keys"


def _fetch_jwks() -> Dict[str, Any]:
    url = _jwks_url()
    if url in _jwks_cache:
        return _jwks_cache[url]
    with httpx.Client(timeout=5.0) as c:
        r = c.get(url)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict) or "keys" not in data:
            raise JwtValidationError("Invalid JWKS document")
        _jwks_cache[url] = data
        return data


def _b64url_decode(data: str) -> bytes:
    pad = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _select_key(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return k
    return None


def _public_key_from_jwk(jwk: Dict[str, Any]):
    # PyJWT understands JWKs directly from from_jwk
    return pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))


def _expected_iss() -> str:
    # If provided explicitly, use SUPABASE_JWT_ISS; else derive from SUPABASE_URL
    iss = current_app.config.get("SUPABASE_JWT_ISS")
    if iss:
        return iss.rstrip("/")
    supabase_url = (current_app.config.get("SUPABASE_URL") or "").rstrip("/")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL missing in configuration")
    return f"{supabase_url}/auth/v1"


def verify_supabase_jwt(bearer_token: str) -> Dict[str, Any]:
    """Validate a Supabase access token and return claims.

    Supports RS256 (via JWKS) and HS256 (via SUPABASE_JWT_SECRET) for
    compatibility with different Supabase project configurations.

    Raises JwtValidationError on failure.
    """
    token = bearer_token.strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    if not token:
        raise JwtValidationError("Empty token")

    try:
        header = pyjwt.get_unverified_header(token)
    except Exception as e:  # pragma: no cover - malformed header
        raise JwtValidationError(f"Invalid token header: {e}")

    alg = (header.get("alg") or "").upper()
    options = {"require": ["sub", "exp", "iat"], "verify_signature": True}
    expected_issuer = _expected_iss()
    audience = current_app.config.get("SUPABASE_JWT_AUD")

    try:
        if alg.startswith("RS"):
            kid = header.get("kid")
            if not kid:
                raise JwtValidationError("Missing kid in token header")
            jwks = _fetch_jwks()
            jwk = _select_key(jwks, kid)
            if not jwk:
                raise JwtValidationError("Signing key not found")
            pub_key = _public_key_from_jwk(jwk)
            claims = pyjwt.decode(
                token,
                pub_key,
                algorithms=["RS256"],
                issuer=expected_issuer,
                audience=audience if audience else None,
                options=options,
            )
        elif alg == "HS256":
            secret = current_app.config.get("SUPABASE_JWT_SECRET") or ""
            if not secret:
                raise JwtValidationError("HS256 token but SUPABASE_JWT_SECRET not configured")
            claims = pyjwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                issuer=expected_issuer,
                audience=audience if audience else None,
                options=options,
            )
        else:
            raise JwtValidationError(f"Unsupported JWT alg: {alg}")
    except Exception as e:
        current_app.logger.warning("JWT validation failed: %s", e)
        raise JwtValidationError("Invalid or expired token")

    # Basic claim sanity checks
    now = int(time.time())
    if int(claims.get("exp", now - 1)) <= now:
        raise JwtValidationError("Token expired")
    if int(claims.get("nbf", now)) > now + 60:
        raise JwtValidationError("Token not yet valid")

    # Derive normalized fields commonly needed by the app
    email = (
        claims.get("email")
        or (claims.get("user_metadata") or {}).get("email")
        or (claims.get("app_metadata") or {}).get("email")
    )
    role = (
        (claims.get("user_metadata") or {}).get("role")
        or (claims.get("user_metadata") or {}).get("requested_role")
        or (claims.get("app_metadata") or {}).get("requested_role")
        or (claims.get("app_metadata") or {}).get("role")
    )

    role = (str(role).upper() if role else "BROKER")
    if role not in _allowed_roles():
        role = "BROKER"

    claims["email"] = email
    claims["role"] = role
    return claims


def get_or_create_user_and_profile(auth_user_id, email: Optional[str]) -> Tuple[User, Optional[Profile]]:
    """Ensure 1:1 mapping auth.users.id -> users.id -> profiles.user_id.

    - User.id equals auth_user_id (UUID from token)
    - Create Profile if missing (empty)
    - Single commit; idempotent
    """
    # Ensure UUID is a proper type for SQLAlchemy
    from uuid import UUID

    sup_uuid = UUID(str(auth_user_id))

    user = db.session.get(User, sup_uuid)
    if not user:
        # Minimal user: name hint from email
        name_hint = (email or "").split("@")[0] if email else None
        user = User(id=sup_uuid, email=email or None, name=name_hint or "user", role="BROKER", password_hash="supabase-external")
        db.session.add(user)

    profile = db.session.query(Profile).filter_by(user_id=sup_uuid).one_or_none()
    if not profile:
        profile = Profile(user_id=sup_uuid, is_active=True)
        db.session.add(profile)

    db.session.commit()
    return user, profile


def _rate_limit_exceeded(ip: str) -> bool:
    try:
        count = _rate_cache.get(ip, 0)
        count += 1
        _rate_cache[ip] = count
        return count > 60
    except Exception:
        return False


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Basic IP-based rate limiting (best-effort)
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
        if _rate_limit_exceeded(ip):
            return jsonify({"error": "Too Many Requests"}), 429

        auth_header = request.headers.get("Authorization", "").strip()
        if not auth_header:
            return unauthorized("Missing Authorization header")

        try:
            claims = verify_supabase_jwt(auth_header)
        except JwtValidationError as e:
            return unauthorized(str(e))
        except Exception as e:  # pragma: no cover - unexpected
            current_app.logger.exception("JWT verification error")
            return server_error("JWT verification error")

        # Inject into g
        g.user_claims = claims
        g.user_id = claims.get("sub")
        g.email = claims.get("email")
        g.role = claims.get("role")
        return fn(*args, **kwargs)

    return wrapper
