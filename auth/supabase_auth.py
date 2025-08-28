# auth/supabase_auth.py
import os
from typing import Dict, Any

from flask import current_app

# PyJWT is required to validate Supabase tokens
import jwt as pyjwt


class SupabaseAuthError(Exception):
    pass


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """Validate a Supabase access token (HS256) and return its claims.

    Requires SUPABASE_JWT_SECRET to be configured.
    """
    secret = (current_app.config.get("SUPABASE_JWT_SECRET")
              if current_app else os.getenv("SUPABASE_JWT_SECRET"))
    if not secret:
        raise SupabaseAuthError("SUPABASE_JWT_SECRET is not configured")

    try:
        # Enforce Supabase audience to be "authenticated" as per frontend setup
        claims = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["sub", "exp"]},
        )
        return claims
    except Exception as e:
        raise SupabaseAuthError(str(e))
