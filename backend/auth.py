"""auth.py -- Token-basierte Authentifizierung (JWT)"""

import os
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db import get_db

# Geheimer Schluessel -- in Produktion per Umgebungsvariable setzen
SECRET = os.environ.get("JWT_SECRET", "learn-e-versum-dev-secret-2024")
TOKEN_EXPIRE_HOURS = int(os.environ.get("TOKEN_EXPIRE_HOURS", "168"))  # 7 Tage

_bearer = HTTPBearer(auto_error=False)


# -- Passwort-Hashing (PBKDF2, keine externen Abhängigkeiten) -----------------

def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    parts = stored.split(":")
    if len(parts) != 2:
        return False
    salt = bytes.fromhex(parts[0])
    expected = _hash_password(password, salt)
    return hmac.compare_digest(expected, stored)


# -- JWT (minimale eigene Implementierung, kein pyjwt nötig) ------------------

def _b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    import base64
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def create_token(user_id: int, email: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url(json.dumps({
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + TOKEN_EXPIRE_HOURS * 3600,
    }).encode())
    sig_input = f"{header}.{payload}".encode()
    sig = _b64url(hmac.new(SECRET.encode(), sig_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def decode_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        sig_input = f"{parts[0]}.{parts[1]}".encode()
        expected_sig = _b64url(hmac.new(SECRET.encode(), sig_input, hashlib.sha256).digest())
        if not hmac.compare_digest(expected_sig, parts[2]):
            return None
        payload = json.loads(_b64url_decode(parts[1]))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# -- FastAPI Dependency --------------------------------------------------------

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token fehlt")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ungueltig oder abgelaufen")
    conn = get_db()
    user = conn.execute("SELECT id, email, display_name FROM users WHERE id=?", (payload["sub"],)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Benutzer nicht gefunden")
    return dict(user)


# -- Benutzer-Verwaltung ------------------------------------------------------

def authenticate(email: str, password: str) -> Optional[dict]:
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if not user:
        return None
    if not _verify_password(password, user["password_hash"]):
        return None
    try:
        if user["disabled"]:
            return None
    except (KeyError, IndexError):
        pass
    return {"id": user["id"], "email": user["email"], "display_name": user["display_name"]}


def create_user(email: str, password: str, display_name: str = "") -> dict:
    pw_hash = _hash_password(password)
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?,?,?)",
            (email, pw_hash, display_name or email.split("@")[0])
        )
        conn.commit()
        user = conn.execute("SELECT id, email, display_name FROM users WHERE email=?", (email,)).fetchone()
        return dict(user)
    except Exception as e:
        raise HTTPException(400, "E-Mail bereits registriert")
    finally:
        conn.close()


def seed_admin():
    """Erstellt den Admin-Benutzer falls noch nicht vorhanden."""
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email='admin@example.com'").fetchone()
    if not existing:
        pw_hash = _hash_password("admin")
        conn.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?,?,?)",
            ("admin@example.com", pw_hash, "Admin")
        )
        conn.commit()
    conn.close()
