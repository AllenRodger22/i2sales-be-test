import os
import base64
import json
import time
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")

from i2sales_api.app import app  # type: ignore
from i2sales_api.extensions import db  # type: ignore
from i2sales_api.models.client import Client  # type: ignore
from i2sales_api.utils import supabase_jwt  # type: ignore


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def make_token(sub: str = str(uuid.uuid4()), email: str = "user@example.com") -> str:
    header = {"alg": "RS256", "typ": "JWT", "kid": "kid1"}
    now = int(time.time())
    payload = {
        "iss": f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1",
        "aud": "authenticated",
        "sub": sub,
        "email": email,
        "exp": now + 3600,
        "iat": now,
        "user_metadata": {"role": "BROKER"},
    }
    return f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}.sig"


def setup_module():
    with app.app_context():
        db.drop_all()
        db.create_all()


def test_me_and_protected_routes(monkeypatch):
    # Monkeypatch JWKS and decode
    def fake_fetch_jwks():
        return {"keys": [{"kid": "kid1", "kty": "RSA", "n": "..", "e": "AQAB"}]}

    def fake_decode(token, key, algorithms, issuer, audience, options):
        header_b64, payload_b64, _sig = token.split(".")
        return json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))

    supabase_jwt._jwks_cache.clear()
    monkeypatch.setattr(supabase_jwt, "_fetch_jwks", fake_fetch_jwks)
    monkeypatch.setattr(supabase_jwt.pyjwt, "decode", fake_decode)

    sub = str(uuid.uuid4())
    token = make_token(sub=sub)

    with app.test_client() as c:
        # /api/me
        r = c.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        data = r.get_json()
        assert data["user"]["id"] == sub
        assert data["routing"]["target"] == "/app"

        # Protected without token → 401
        r2 = c.get("/api/clients")
        assert r2.status_code == 401

        # Create client, ignoring owner_id from body
        body = {
            "name": "Cliente X",
            "phone": "85999999999",
            "owner_id": str(uuid.uuid4()),  # should be ignored
        }
        r3 = c.post("/api/clients", json=body, headers={"Authorization": f"Bearer {token}"})
        assert r3.status_code == 201, r3.text
        created = r3.get_json()
        assert created["name"] == "Cliente X"

        # List only my clients
        r4 = c.get("/api/clients", headers={"Authorization": f"Bearer {token}"})
        assert r4.status_code == 200
        lst = r4.get_json()
        assert lst["page"] == 1 and lst["pageSize"] >= 1
        assert any(item["name"] == "Cliente X" for item in lst["items"]) is True

        # Isolation: create a client for another owner directly
        other_client_id = uuid.uuid4()
        other_owner = uuid.uuid4()
        with app.app_context():
            db.session.add(Client(id=other_client_id, name="Other", phone="85000000000", source="manual", status="Primeiro Atendimento", owner_id=other_owner))
            db.session.commit()

        # Accessing interactions of other user's client → 403
        r5 = c.get(f"/api/interactions?client_id={other_client_id}", headers={"Authorization": f"Bearer {token}"})
        assert r5.status_code == 403

