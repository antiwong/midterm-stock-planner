"""Authentication module: session-based auth with SQLite backend."""

import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

from fastapi import Cookie, HTTPException, Request

DATA_DIR = Path(__file__).parent.parent.parent / "data"
AUTH_DB = DATA_DIR / "auth.db"

# Session config
SESSION_TIMEOUT = 8 * 3600  # 8 hours
SESSION_CLEANUP_INTERVAL = 3600  # clean expired sessions every hour
_last_cleanup = 0


def _get_auth_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(AUTH_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_auth_db():
    """Ensure sessions table exists."""
    conn = _get_auth_db()
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
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(username: str, password: str) -> Optional[dict]:
    """Verify credentials. Returns user dict or None."""
    conn = _get_auth_db()
    row = conn.execute(
        "SELECT id, username, password_hash, salt, display_name, role, is_active "
        "FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if not row:
        return None
    if not row["is_active"]:
        return None

    expected = _hash_password(password, row["salt"])
    if not secrets.compare_digest(expected, row["password_hash"]):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
    }


def create_session(user: dict, request: Request) -> str:
    """Create a new session token for the user."""
    token = secrets.token_urlsafe(48)
    now = time.time()
    conn = _get_auth_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, username, created_at, last_active, ip_address, user_agent) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            token,
            user["id"],
            user["username"],
            now,
            now,
            request.client.host if request.client else "",
            request.headers.get("user-agent", "")[:200],
        ),
    )
    # Update last_login on user
    conn.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    _maybe_cleanup()
    return token


def validate_session(token: str) -> Optional[dict]:
    """Validate session token. Returns user info or None if expired/invalid."""
    if not token:
        return None

    conn = _get_auth_db()
    row = conn.execute(
        "SELECT token, user_id, username, created_at, last_active FROM sessions WHERE token = ?",
        (token,),
    ).fetchone()

    if not row:
        conn.close()
        return None

    now = time.time()
    if now - row["last_active"] > SESSION_TIMEOUT:
        # Session expired — delete it
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    # Touch session
    conn.execute("UPDATE sessions SET last_active = ? WHERE token = ?", (now, token))
    conn.commit()
    conn.close()

    return {"id": row["user_id"], "username": row["username"]}


def delete_session(token: str):
    """Delete a session (logout)."""
    conn = _get_auth_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def _maybe_cleanup():
    """Periodically clean expired sessions."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < SESSION_CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    conn = _get_auth_db()
    cutoff = now - SESSION_TIMEOUT
    conn.execute("DELETE FROM sessions WHERE last_active < ?", (cutoff,))
    conn.commit()
    conn.close()


def require_auth(request: Request, sp_session: Optional[str] = Cookie(None)) -> dict:
    """FastAPI dependency: require valid session. Returns user dict or raises 401."""
    user = validate_session(sp_session) if sp_session else None
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# Alias for backwards compatibility with existing routers (e.g. settings.py)
get_current_user = require_auth


def set_user_password(username: str, password: str):
    """Set/reset a user's password (for CLI use)."""
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    conn = _get_auth_db()
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (pw_hash, salt, username),
    )
    conn.commit()
    conn.close()
