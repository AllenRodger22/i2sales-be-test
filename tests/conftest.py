# tests/conftest.py
import os, time
import pytest
import httpx
from dotenv import load_dotenv

# Carrega .env.test se existir; senão, .env
load_dotenv(".env.test") or load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000/api/v1").rstrip("/")

# Credenciais (defaults batem com seu seed)
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL",   "admin@x.com")
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "manager@x.com")
BROKER_EMAIL  = os.getenv("BROKER_EMAIL",  "broker@x.com")
PASSWORD      = os.getenv("PASSWORD", "1234567890")  # mesma p/ todos

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(scope="session")
def client(base_url):
    # Espera o server subir (até 20s) batendo no /health
    deadline = time.time() + 20
    last_err = None
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=5.0) as c:
                r = c.get(f"{base_url}/health")
                if r.status_code in (200, 204):
                    break
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    else:
        raise RuntimeError(f"API não respondeu no /health: {last_err}")

    # Client para os testes
    with httpx.Client(timeout=30.0) as c:
        yield c

def _login(c: httpx.Client, email: str, password: str, base_url: str) -> str:
    r = c.post(f"{base_url}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    data = r.json()
    assert "token" in data, f"Response sem token: {data}"
    return data["token"]

# ---- Fixtures por papel ----
@pytest.fixture(scope="session")
def admin_token(client, base_url):
    return _login(client, ADMIN_EMAIL, PASSWORD, base_url)

@pytest.fixture(scope="session")
def manager_token(client, base_url):
    return _login(client, MANAGER_EMAIL, PASSWORD, base_url)

@pytest.fixture(scope="session")
def broker_token(client, base_url):
    return _login(client, BROKER_EMAIL, PASSWORD, base_url)

# Headers prontos
@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.fixture
def manager_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}"}

@pytest.fixture
def broker_headers(broker_token):
    return {"Authorization": f"Bearer {broker_token}"}

# ---- Compat: testes legados esperam 'auth_token' e 'auth_headers'
@pytest.fixture(scope="session")
def auth_token(admin_token):
    return admin_token  # usa token do ADMIN por padrão

@pytest.fixture
def auth_headers(admin_headers):
    return admin_headers  # usa headers do ADMIN por padrão

# Utils simples pra gerar dados
import random, string
def rand_phone():
    return "85" + "".join(random.choice("0123456789") for _ in range(9))

def rand_name(prefix="QA"):
    suffix = "".join(random.choice(string.ascii_uppercase) for _ in range(5))
    return f"{prefix} {suffix}"
