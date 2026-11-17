"""StockFlow settings for local SQLite and Supabase PostgreSQL."""
import os
from datetime import timedelta
from pathlib import Path

from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "local-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'instance' / 'inventory.db'}"
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    if SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+psycopg://", 1)
    SQLALCHEMY_ENGINE_OPTIONS = {}
    if SQLALCHEMY_DATABASE_URI.startswith("postgresql+psycopg://"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"sslmode": "require"},
            "pool_pre_ping": True,
        }
        if os.getenv("DB_TRANSACTION_POOLER") == "1":
            SQLALCHEMY_ENGINE_OPTIONS["poolclass"] = NullPool
            # Supabase shared transaction pooler does not support prepared statements.
            SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["prepare_threshold"] = None
    MAX_CONTENT_LENGTH = 1024 * 1024
    MAX_FORM_PARTS = 200
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("VERCEL") == "1" or os.getenv("APP_ENV") == "production"
