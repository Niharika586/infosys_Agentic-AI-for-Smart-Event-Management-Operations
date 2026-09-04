"""
config.py
----------
MILESTONE 4 — Production-friendly configuration.

Supports Development / Production / Testing via the FLASK_ENV / APP_ENV
environment variable. Never hard-codes secrets — all sensitive values come
from environment variables with safe local-dev fallbacks only.
"""

import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "springboard-milestone1-secret-key-2026")
    DATABASE_PATH = os.environ.get("DATABASE_PATH")  # None -> database.py default
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only force Secure cookies when actually served over HTTPS (Render does this).
    SESSION_COOKIE_SECURE = os.environ.get("FORCE_HTTPS", "0") == "1"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB request body cap


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False


def get_config():
    env = os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "production"
    env = env.lower()
    if env.startswith("dev"):
        return DevelopmentConfig
    if env.startswith("test"):
        return TestingConfig
    return ProductionConfig
