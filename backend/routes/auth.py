"""routes/auth.py -- Login, Register, Me, Change-Password."""

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
