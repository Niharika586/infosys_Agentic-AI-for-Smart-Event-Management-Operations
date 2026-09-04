"""
conftest.py
------------
Shared pytest fixtures for the Milestone 4 end-to-end test suite.

Uses a completely isolated temp SQLite database (via the DATABASE_PATH
environment variable, honored by database.py) so tests never touch the
real deployed database.db.
"""

import os
import sys
import tempfile

import pytest

# Make sure the project root is importable when running `pytest` from
# either the project root or the tests/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp_dir = tempfile.mkdtemp(prefix="registerai_test_")
os.environ["DATABASE_PATH"] = os.path.join(_tmp_dir, "test_database.db")
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key"

import database as db  # noqa: E402  (must import after env vars are set)

db.init_db(force=True)

import app as flask_app_module  # noqa: E402


@pytest.fixture(scope="session")
def app():
    flask_app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield flask_app_module.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(client):
    """A test client already logged in as the default System Admin."""
    client.post("/login", data={"email": "admin@springboard.ai", "password": "admin123", "role": "admin"},
                follow_redirects=True)
    return client
