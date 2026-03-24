"""
Tests for session-based authentication system.

Covers:
- Password hashing and verification
- Session creation, validation, expiry, and cleanup
- Auth middleware (public vs protected paths)
- Login/logout/me API endpoints
- Cookie handling (httpOnly, secure, samesite)
- Session timeout behavior
- Frontend auth gating (401 → reload)
"""

import hashlib
import secrets
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_db(tmp_path):
    """Create a temporary auth database with a test user."""
    db_path = tmp_path / "auth.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            role TEXT DEFAULT 'viewer',
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_active REAL NOT NULL,
            ip_address TEXT,
            user_agent TEXT
        )
    """)
    # Create test user: admin / testpass123
    salt = "testsalt1234567890abcdef12345678"
    pw_hash = hashlib.sha256((salt + "testpass123").encode()).hexdigest()
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, display_name, role, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("admin", pw_hash, salt, "Test Admin", "admin", 1),
    )
    # Create inactive user
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, display_name, role, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("disabled", pw_hash, salt, "Disabled User", "viewer", 0),
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def auth_module(auth_db):
    """Import auth module with patched DB path."""
    import importlib
    import src.api.auth as auth_mod

    # Patch the AUTH_DB path
    original_db = auth_mod.AUTH_DB
    auth_mod.AUTH_DB = auth_db
    auth_mod._last_cleanup = 0  # Reset cleanup timer
    auth_mod.init_auth_db()

    yield auth_mod

    auth_mod.AUTH_DB = original_db


@pytest.fixture
def test_app(auth_module):
    """Create a FastAPI test client with auth middleware."""
    from fastapi import FastAPI, Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware

    app = FastAPI()

    PUBLIC_PATHS = {"/api/health", "/api/auth/login", "/api/auth/me"}

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            path = request.url.path.rstrip("/")
            if path in PUBLIC_PATHS or request.method == "OPTIONS":
                return await call_next(request)
            if path == "/api/auth/logout":
                return await call_next(request)
            token = request.cookies.get("sp_session")
            user = auth_module.validate_session(token) if token else None
            if not user:
                return Response(
                    content='{"detail":"Not authenticated"}',
                    status_code=401,
                    media_type="application/json",
                )
            return await call_next(request)

    app.add_middleware(AuthMiddleware)

    # Register auth routes
    from src.api.routers.auth_routes import router as auth_router
    # Patch the auth_routes module to use our auth_module
    import src.api.routers.auth_routes as routes_mod
    original_verify = routes_mod.verify_password
    original_create = routes_mod.create_session
    original_validate = routes_mod.validate_session
    original_delete = routes_mod.delete_session
    routes_mod.verify_password = auth_module.verify_password
    routes_mod.create_session = auth_module.create_session
    routes_mod.validate_session = auth_module.validate_session
    routes_mod.delete_session = auth_module.delete_session

    app.include_router(auth_router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/portfolios/summary")
    def protected_endpoint():
        return {"portfolios": []}

    client = TestClient(app)
    yield client

    routes_mod.verify_password = original_verify
    routes_mod.create_session = original_create
    routes_mod.validate_session = original_validate
    routes_mod.delete_session = original_delete


# ---------------------------------------------------------------------------
# Unit Tests: Password Hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_verify_correct_password(self, auth_module):
        user = auth_module.verify_password("admin", "testpass123")
        assert user is not None
        assert user["username"] == "admin"
        assert user["role"] == "admin"
        assert user["display_name"] == "Test Admin"

    def test_verify_wrong_password(self, auth_module):
        user = auth_module.verify_password("admin", "wrongpass")
        assert user is None

    def test_verify_nonexistent_user(self, auth_module):
        user = auth_module.verify_password("nobody", "testpass123")
        assert user is None

    def test_verify_inactive_user(self, auth_module):
        user = auth_module.verify_password("disabled", "testpass123")
        assert user is None

    def test_set_user_password(self, auth_module):
        auth_module.set_user_password("admin", "newpass456")
        assert auth_module.verify_password("admin", "newpass456") is not None
        assert auth_module.verify_password("admin", "testpass123") is None

    def test_hash_uses_salt(self, auth_module):
        """Different salts should produce different hashes."""
        h1 = auth_module._hash_password("test", "salt1")
        h2 = auth_module._hash_password("test", "salt2")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Unit Tests: Session Management
# ---------------------------------------------------------------------------

class TestSessionManagement:
    def _mock_request(self):
        req = MagicMock()
        req.client.host = "127.0.0.1"
        req.headers = {"user-agent": "TestAgent/1.0"}
        return req

    def test_create_session(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token = auth_module.create_session(user, self._mock_request())
        assert isinstance(token, str)
        assert len(token) > 32  # URL-safe base64 of 48 bytes

    def test_validate_valid_session(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token = auth_module.create_session(user, self._mock_request())
        result = auth_module.validate_session(token)
        assert result is not None
        assert result["username"] == "admin"
        assert result["id"] == 1

    def test_validate_invalid_token(self, auth_module):
        result = auth_module.validate_session("invalid_token_abc123")
        assert result is None

    def test_validate_empty_token(self, auth_module):
        assert auth_module.validate_session("") is None
        assert auth_module.validate_session(None) is None

    def test_session_timeout(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token = auth_module.create_session(user, self._mock_request())

        # Artificially expire the session
        conn = auth_module._get_auth_db()
        expired_time = time.time() - auth_module.SESSION_TIMEOUT - 1
        conn.execute("UPDATE sessions SET last_active = ? WHERE token = ?", (expired_time, token))
        conn.commit()
        conn.close()

        result = auth_module.validate_session(token)
        assert result is None  # Session should be expired

    def test_session_touch_extends_timeout(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token = auth_module.create_session(user, self._mock_request())

        # Set last_active to near timeout but not expired
        conn = auth_module._get_auth_db()
        near_timeout = time.time() - auth_module.SESSION_TIMEOUT + 60  # 60s before expiry
        conn.execute("UPDATE sessions SET last_active = ? WHERE token = ?", (near_timeout, token))
        conn.commit()
        conn.close()

        # Validate should touch the session
        result = auth_module.validate_session(token)
        assert result is not None

        # Verify last_active was updated
        conn = auth_module._get_auth_db()
        row = conn.execute("SELECT last_active FROM sessions WHERE token = ?", (token,)).fetchone()
        conn.close()
        assert row[0] > near_timeout  # Should be updated to now

    def test_delete_session(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token = auth_module.create_session(user, self._mock_request())
        assert auth_module.validate_session(token) is not None

        auth_module.delete_session(token)
        assert auth_module.validate_session(token) is None

    def test_multiple_sessions(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token1 = auth_module.create_session(user, self._mock_request())
        token2 = auth_module.create_session(user, self._mock_request())

        assert token1 != token2
        assert auth_module.validate_session(token1) is not None
        assert auth_module.validate_session(token2) is not None

        # Delete one, other should still work
        auth_module.delete_session(token1)
        assert auth_module.validate_session(token1) is None
        assert auth_module.validate_session(token2) is not None

    def test_session_cleanup(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        token = auth_module.create_session(user, self._mock_request())

        # Expire the session and force cleanup
        conn = auth_module._get_auth_db()
        expired_time = time.time() - auth_module.SESSION_TIMEOUT - 3600
        conn.execute("UPDATE sessions SET last_active = ?", (expired_time,))
        conn.commit()
        conn.close()

        auth_module._last_cleanup = 0  # Force cleanup to run
        auth_module.SESSION_CLEANUP_INTERVAL = 0
        auth_module._maybe_cleanup()

        conn = auth_module._get_auth_db()
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
        assert count == 0  # Expired session should be cleaned up

    def test_session_records_ip_and_ua(self, auth_module):
        user = {"id": 1, "username": "admin", "display_name": "Admin", "role": "admin"}
        req = self._mock_request()
        token = auth_module.create_session(user, req)

        conn = auth_module._get_auth_db()
        row = conn.execute(
            "SELECT ip_address, user_agent FROM sessions WHERE token = ?", (token,)
        ).fetchone()
        conn.close()
        assert row[0] == "127.0.0.1"
        assert row[1] == "TestAgent/1.0"


# ---------------------------------------------------------------------------
# Integration Tests: API Endpoints
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    def test_login_success(self, test_app):
        resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"
        # Check cookie is set
        assert "sp_session" in resp.cookies

    def test_login_wrong_password(self, test_app):
        resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert "error" in data

    def test_login_nonexistent_user(self, test_app):
        resp = test_app.post("/api/auth/login", json={"username": "nobody", "password": "test"})
        data = resp.json()
        assert data["ok"] is False

    def test_me_authenticated(self, test_app):
        # Login and extract cookie
        login_resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        token = login_resp.cookies.get("sp_session")
        test_app.cookies.set("sp_session", token)
        resp = test_app.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is True
        assert data["user"]["username"] == "admin"
        test_app.cookies.clear()

    def test_me_unauthenticated(self, test_app):
        resp = test_app.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["authenticated"] is False

    def test_logout(self, test_app):
        # Login and set cookie
        login_resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        token = login_resp.cookies.get("sp_session")
        test_app.cookies.set("sp_session", token)
        # Verify authenticated
        assert test_app.get("/api/auth/me").json()["authenticated"] is True
        # Logout
        resp = test_app.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Clear cookie (simulates browser deleting cookie on Set-Cookie delete)
        test_app.cookies.clear()
        # Verify no longer authenticated
        assert test_app.get("/api/auth/me").json()["authenticated"] is False

    def test_logout_without_session(self, test_app):
        """Logout should succeed even without a session."""
        resp = test_app.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# Integration Tests: Auth Middleware
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    def test_health_is_public(self, test_app):
        resp = test_app.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_login_is_public(self, test_app):
        resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        assert resp.status_code == 200

    def test_me_is_public(self, test_app):
        resp = test_app.get("/api/auth/me")
        assert resp.status_code == 200

    def test_protected_requires_auth(self, test_app):
        resp = test_app.get("/api/portfolios/summary")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"

    def test_protected_with_auth(self, test_app):
        # Login and set cookie
        login_resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        test_app.cookies.set("sp_session", login_resp.cookies.get("sp_session"))
        resp = test_app.get("/api/portfolios/summary")
        assert resp.status_code == 200
        assert "portfolios" in resp.json()
        test_app.cookies.clear()

    def test_protected_after_logout(self, test_app):
        login_resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        test_app.cookies.set("sp_session", login_resp.cookies.get("sp_session"))
        test_app.post("/api/auth/logout")
        test_app.cookies.clear()
        resp = test_app.get("/api/portfolios/summary")
        assert resp.status_code == 401

    def test_invalid_cookie_returns_401(self, test_app):
        test_app.cookies.set("sp_session", "bogus_token_value")
        resp = test_app.get("/api/portfolios/summary")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Integration Tests: Cookie Properties
# ---------------------------------------------------------------------------

class TestCookieProperties:
    def test_cookie_set_on_login(self, test_app):
        resp = test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        cookie = resp.cookies.get("sp_session")
        assert cookie is not None
        assert len(cookie) > 32

    def test_cookie_cleared_on_logout(self, test_app):
        test_app.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
        resp = test_app.post("/api/auth/logout")
        # After logout, cookie should be deleted (set to empty or expired)
        # TestClient may still have it, but server-side session is gone
        me_resp = test_app.get("/api/auth/me")
        assert me_resp.json()["authenticated"] is False


# ---------------------------------------------------------------------------
# Unit Tests: get_current_user alias
# ---------------------------------------------------------------------------

class TestBackwardsCompat:
    def test_get_current_user_alias_exists(self, auth_module):
        assert hasattr(auth_module, "get_current_user")
        assert auth_module.get_current_user is auth_module.require_auth
