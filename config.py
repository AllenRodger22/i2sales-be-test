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
    # Supabase (GoTrue) JWT secret para validar tokens do frontend
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

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
        "http://localhost:5173",
        "https://SEU-PROJETO.vercel.app",
    ]
