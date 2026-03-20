"""routes/admin.py -- User-Verwaltung, Reset-Stats, FTS-Rebuild, Paketspez-Doku."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends

from db import get_db, row_to_dict
from auth import get_current_user, create_user
from helpers import rebuild_fts

router = APIRouter(tags=["admin"])


@router.get("/api/admin/users")
def admin_list_users(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id, u.email, u.display_name, u.is_admin, u.created_at,
            (SELECT COUNT(*) FROM sessions s WHERE s.user_id=u.id AND s.ended_at IS NOT NULL) as sessions,
            (SELECT COUNT(*) FROM reviews r WHERE r.user_id=u.id) as reviews,
            (SELECT COUNT(*) FROM user_packages up WHERE up.user_id=u.id) as packages
        FROM users u ORDER BY u.created_at ASC
    """).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.post("/api/admin/users")
def admin_create_user(data: dict, user: dict = Depends(get_current_user)):
    email = data.get("email", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "")
    if not email or not password:
        raise HTTPException(400, "E-Mail und Passwort erforderlich")
    try:
        new_user = create_user(email, password, display_name)
    except Exception:
        raise HTTPException(400, "E-Mail bereits registriert")
    # Alle bestehenden Pakete dem neuen User zuweisen
    conn = get_db()
    conn.execute("""
        INSERT OR IGNORE INTO user_packages (user_id, package_id, role)
        SELECT ?, p.id, 'learner' FROM packages p
    """, (new_user["id"],))
    conn.commit()
    conn.close()
    return new_user


@router.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, user: dict = Depends(get_current_user)):
    if user_id == user["id"]:
        raise HTTPException(400, "Du kannst dich nicht selbst entfernen")
    conn = get_db()
    conn.execute("DELETE FROM user_packages WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM card_stats WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM reviews WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, data: dict, user: dict = Depends(get_current_user)):
    new_pw = data.get("new_password", "")
    if not new_pw or len(new_pw) < 4:
        raise HTTPException(400, "Mindestens 4 Zeichen")
    from auth import _hash_password
    conn = get_db()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (_hash_password(new_pw), user_id))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/api/admin/users/{user_id}/toggle")
def admin_toggle_user(user_id: int, user: dict = Depends(get_current_user)):
    if user_id == user["id"]:
        raise HTTPException(400, "Du kannst dich nicht selbst deaktivieren")
    conn = get_db()
    current = conn.execute("SELECT disabled FROM users WHERE id=?", (user_id,)).fetchone()
    if not current:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")
    new_val = 0 if current["disabled"] else 1
    conn.execute("UPDATE users SET disabled=? WHERE id=?", (new_val, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "disabled": bool(new_val)}


# -- Reset-Funktionen (kein DB-Löschen, nur Lerndaten) -----------------------

@router.post("/api/reset/my-stats")
def reset_my_stats(data: dict, user: dict = Depends(get_current_user)):
    """Eigene Lernstatistik zurücksetzen (pro Paket oder alles)."""
    uid = user["id"]
    pkg_id = data.get("package_id")
    conn = get_db()
    if pkg_id:
        # Nur ein Paket
        card_ids = [r["card_id"] for r in conn.execute("SELECT card_id FROM cards WHERE package_id=?", (pkg_id,)).fetchall()]
        if card_ids:
            pl = ",".join("?" * len(card_ids))
            conn.execute(f"DELETE FROM card_stats WHERE user_id=? AND card_id IN ({pl})", [uid] + card_ids)
            conn.execute(f"DELETE FROM reviews WHERE user_id=? AND card_id IN ({pl})", [uid] + card_ids)
            conn.execute(f"DELETE FROM card_reports WHERE user_id=? AND card_id IN ({pl})", [uid] + card_ids)
            # Gemeldete Karten reaktivieren
            conn.execute(f"UPDATE cards SET reported=0, active=1 WHERE package_id=? AND reported=1", (pkg_id,))
        conn.execute("DELETE FROM sessions WHERE user_id=? AND package_id=?", (uid, pkg_id))
    else:
        # Alles
        conn.execute("DELETE FROM card_stats WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM reviews WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM card_reports WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM user_xp WHERE user_id=?", (uid,))
        # Alle gemeldeten Karten des Users reaktivieren
        conn.execute("UPDATE cards SET reported=0, active=1 WHERE reported=1 AND package_id IN (SELECT package_id FROM user_packages WHERE user_id=?)", (uid,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/api/admin/reset-user-stats/{target_id}")
def admin_reset_user_stats(target_id: int, user: dict = Depends(get_current_user)):
    """Admin: Lernstatistik eines Users komplett zurücksetzen."""
    conn = get_db()
    conn.execute("DELETE FROM card_stats WHERE user_id=?", (target_id,))
    conn.execute("DELETE FROM reviews WHERE user_id=?", (target_id,))
    conn.execute("DELETE FROM sessions WHERE user_id=?", (target_id,))
    conn.execute("DELETE FROM card_reports WHERE user_id=?", (target_id,))
    conn.execute("DELETE FROM user_xp WHERE user_id=?", (target_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/api/admin/rebuild-fts")
def admin_rebuild_fts(user: dict = Depends(get_current_user)):
    """Admin: FTS-Index neu aufbauen."""
    conn = get_db()
    rebuild_fts(conn)
    conn.close()
    return {"ok": True}


@router.get("/api/docs/paketspezifikation")
def get_paketspezifikation():
    """Gibt die Paketspezifikation als Markdown-Text zurück."""
    spec_path = Path(__file__).parent.parent.parent / "PAKETSPEZIFIKATION.md"
    if not spec_path.exists():
        raise HTTPException(404, "Paketspezifikation nicht gefunden")
    return {"content": spec_path.read_text(encoding="utf-8")}
