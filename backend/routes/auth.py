"""routes/auth.py -- Login, Register, Me, Change-Password, Settings."""

import json
from fastapi import APIRouter, HTTPException, Depends

from db import get_db
from auth import get_current_user, authenticate, create_user, create_token
from schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(data: LoginRequest):
    user = authenticate(data.email, data.password)
    if not user:
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    token = create_token(user["id"], user["email"])
    return {"token": token, "user": user}


@router.post("/register")
def register(data: RegisterRequest):
    user = create_user(data.email, data.password, data.display_name or "")
    token = create_token(user["id"], user["email"])
    return {"token": token, "user": user}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT id, email, display_name, is_admin, password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
    conn.close()
    # Pruefe ob Standard-Passwort aktiv (Hash des Worts "admin")
    is_default_pw = False
    if row:
        from auth import _hash_password
        try:
            salt = bytes.fromhex(row["password_hash"].split(":")[0])
            is_default_pw = _hash_password("admin", salt) == row["password_hash"]
        except Exception:
            pass
    return {**user, "default_password": is_default_pw}


@router.post("/change-password")
def change_password(data: dict, user: dict = Depends(get_current_user)):
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")
    if not new_pw or len(new_pw) < 4:
        raise HTTPException(400, "Neues Passwort muss mindestens 4 Zeichen haben")
    conn = get_db()
    stored = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
    if not stored:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")
    from auth import _verify_password, _hash_password
    if not _verify_password(old_pw, stored["password_hash"]):
        conn.close()
        raise HTTPException(400, "Altes Passwort ist falsch")
    new_hash = _hash_password(new_pw)
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}


# -- Einstellungen -------------------------------------------------------------

_SETTINGS_DEFAULTS = {
    "sound_enabled": True,
    "daily_goal": 100,
    "preferred_mode": "standard",
    "session_size": 10,
    # KI-Einstellungen
    "ai_temperature": 0.3,
    "ai_temperature_creative": 0.6,
    "ai_temperature_cardgen": 0.4,
    "ai_max_tokens_explain": 250,
    "ai_max_tokens_evaluate": 400,
    "ai_max_tokens_mc": 300,
    "ai_max_tokens_hint": 150,
    "ai_max_tokens_summarize": 400,
    "ai_max_tokens_cardgen": 400,
    "ai_cards_per_chunk": 3,
    "ai_cardgen_retries": 3,
}


@router.get("/settings")
def get_settings(user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT settings FROM users WHERE id=?", (user["id"],)).fetchone()
    conn.close()
    raw = {}
    if row and row["settings"]:
        try:
            raw = json.loads(row["settings"])
        except Exception:
            pass
    return {**_SETTINGS_DEFAULTS, **raw}


@router.patch("/settings")
def update_settings(data: dict, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT settings FROM users WHERE id=?", (user["id"],)).fetchone()
    current = {}
    if row and row["settings"]:
        try:
            current = json.loads(row["settings"])
        except Exception:
            pass
    # Nur erlaubte Keys akzeptieren
    allowed = set(_SETTINGS_DEFAULTS.keys())
    for k, v in data.items():
        if k in allowed:
            current[k] = v
    conn.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(current), user["id"]))
    conn.commit()
    conn.close()
    return {**_SETTINGS_DEFAULTS, **current}


@router.post("/settings/reset-ai")
def reset_ai_settings(user: dict = Depends(get_current_user)):
    """Setzt alle KI-Einstellungen auf Standardwerte zurück."""
    conn = get_db()
    row = conn.execute("SELECT settings FROM users WHERE id=?", (user["id"],)).fetchone()
    current = {}
    if row and row["settings"]:
        try:
            current = json.loads(row["settings"])
        except Exception:
            pass
    # Alle ai_* Keys entfernen
    current = {k: v for k, v in current.items() if not k.startswith("ai_")}
    conn.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(current), user["id"]))
    conn.commit()
    conn.close()
    return {**_SETTINGS_DEFAULTS, **current}


@router.get("/settings/defaults")
def get_settings_defaults():
    """Gibt die Standard-Einstellungen zurück (ohne Auth, für UI-Reset-Anzeige)."""
    return _SETTINGS_DEFAULTS


@router.patch("/display-name")
def update_display_name(data: dict, user: dict = Depends(get_current_user)):
    name = (data.get("display_name") or "").strip()
    if not name:
        raise HTTPException(400, "Name darf nicht leer sein")
    conn = get_db()
    conn.execute("UPDATE users SET display_name=? WHERE id=?", (name, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True, "display_name": name}
