import os
import base64
import json
import time


# Configure env BEFORE importing app/config
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("ALLOWED_ROLES", "BROKER,MANAGER,ADMIN")

from i2sales_api.app import app  # type: ignore
from i2sales_api.extensions import db  # type: ignore
from i2sales_api.utils import supabase_jwt  # type: ignore


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def make_token(claims: dict, kid: str = "kid1") -> str:
    header = {"alg": "RS256", "typ": "JWT", "kid": kid}
    return f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(claims).encode())}.sig"


def setup_module():
    with app.app_context():
        db.create_all()


def test_verify_supabase_jwt_with_jwks_cache(monkeypatch):
    # Prepare dummy JWKS and a decode stub (bypass crypto)
    calls = {"jwks": 0, "decode": 0}

    def fake_fetch_jwks():
        calls["jwks"] += 1
        return {"keys": [{"kid": "kid1", "kty": "RSA", "n": "..", "e": "AQAB"}]}

    def fake_decode(token, key, algorithms, issuer, audience, options):
        calls["decode"] += 1
        header_b64, payload_b64, _sig = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        # Enforce iss/aud as verify_supabase_jwt would
        assert issuer == f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1"
        if audience:
            assert payload.get("aud") == audience
        return payload

    monkeypatch.setattr(supabase_jwt, "_fetch_jwks", fake_fetch_jwks)
    monkeypatch.setattr(supabase_jwt.pyjwt, "decode", fake_decode)
    supabase_jwt._jwks_cache.clear()

    now = int(time.time())
    claims = {
        "iss": f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1",
        "aud": "authenticated",
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "user@example.com",
        "exp": now + 3600,
        "iat": now,
        "user_metadata": {"role": "BROKER"},
    }
    token = make_token(claims)

    out1 = supabase_jwt.verify_supabase_jwt(f"Bearer {token}")
    out2 = supabase_jwt.verify_supabase_jwt(token)

    assert out1["sub"] == claims["sub"]
    assert out1["email"] == claims["email"]
    assert out1["role"] == "BROKER"
    assert out2["sub"] == claims["sub"]
    # JWKS fetched only once due to cache
    assert calls["jwks"] == 1

