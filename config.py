# config.py
import os
import socket
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from datetime import timedelta

def _parse_duration(s: str) -> timedelta:
    if not s:
        return timedelta(days=7)
    s = s.strip().lower()
    if s.endswith("d"):
        return timedelta(days=int(s[:-1] or 7))
    if s.endswith("h"):
        return timedelta(hours=int(s[:-1] or 24))
    if s.endswith("m"):
        return timedelta(minutes=int(s[:-1] or 60))
    return timedelta(days=int(s))

class Config:
    # Supabase project URL (e.g., https://<ref>.supabase.co)
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    # Optional audience to validate against (if configured in Supabase)
    SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD")
    # Optional issuer override (defaults to f"{SUPABASE_URL}/auth/v1")
    SUPABASE_JWT_ISS = os.getenv("SUPABASE_JWT_ISS")
    # Backwards-compat: previously used HS256 secret; kept only for legacy paths
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
    # Public anon key (allowed for calling public GoTrue endpoints)
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    # Roles allowed in the system
    ALLOWED_ROLES = os.getenv("ALLOWED_ROLES", "BROKER,MANAGER,ADMIN")

    # Password pepper (concatenated to user password before hashing)
    PASSWORD_PEPPER = os.getenv("PASSWORD_PEPPER", "pikachu")

    # DB
    # Prefer DATABASE_URL (Render/Supabase padrão), caindo para SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL/SQLALCHEMY_DATABASE_URI não definida no ambiente/.env")

    # Corrige URLs antigas 'postgres://'
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql+psycopg2://", 1)

    # Força IPv4 quando o resolver devolver IPv6 não alcançável (comum em hosts serverless)
    # Implementado adicionando 'hostaddr=<ipv4>' na query string do DSN.
    try:
        parsed = urlparse(SQLALCHEMY_DATABASE_URI)
        host = parsed.hostname or ""
        if host.endswith("supabase.co") or host.endswith("supabase.com"):
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            # Garante SSL por padrão
            if "sslmode" not in q:
                q["sslmode"] = "require"

            if "hostaddr" not in q:
                # resolve apenas IPv4
                infos = socket.getaddrinfo(host, parsed.port or 5432, socket.AF_INET, socket.SOCK_STREAM)
                if infos:
                    ipv4 = infos[0][4][0]
                    q["hostaddr"] = ipv4

            new_query = urlencode(q)
            SQLALCHEMY_DATABASE_URI = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))
    except Exception:
        # Qualquer falha mantém a URI original
        pass

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    }

    # CORS
    # Permitir apenas origens conhecidas por padrão; pode sobrescrever via CORS_ORIGINS
    _cors_from_env = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    CORS_ORIGINS = _cors_from_env or [
        "http://localhost:7132",
        "http://localhost:5173",
        "https://SEU-PROJETO.vercel.app",
    ]

    # Cookie settings for JWT in cookies
    COOKIE_ACCESS_NAME = os.getenv("COOKIE_ACCESS_NAME", "sb-access-token")
    COOKIE_REFRESH_NAME = os.getenv("COOKIE_REFRESH_NAME", "sb-refresh-token")
    COOKIE_EXPIRES_NAME = os.getenv("COOKIE_EXPIRES_NAME", "sb-expires-at")
    COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None
    COOKIE_PATH = os.getenv("COOKIE_PATH", "/")
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
    COOKIE_HTTPONLY = True  # always httpOnly for security
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")  # Lax | None | Strict
