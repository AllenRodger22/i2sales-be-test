# config.py
import os
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
    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "change-me")
    JWT_ACCESS_TOKEN_EXPIRES = _parse_duration(os.getenv("JWT_EXPIRES", "7d"))

    # DB
    # Prefer DATABASE_URL (Render/Supabase padrão), caindo para SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("DATABASE_URL/SQLALCHEMY_DATABASE_URI não definida no ambiente/.env")

    # Corrige URLs antigas 'postgres://'
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql+psycopg2://", 1)

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
