"""routes/ai.py -- MC, Explain, Related, Hint, Summarize."""

from __future__ import annotations
import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from db import get_db, row_to_dict
from auth import get_current_user
from services import (
    ai_online as _ai_online,
    explain_card, generate_hint, summarize_topic,
    suggest_related, generate_mc_options,
)

router = APIRouter(tags=["ai"])


def _load_user_settings(user_id: int) -> dict:
    """Lädt User-Settings aus der DB (mit ai_* Feldern)."""
    conn = get_db()
    row = conn.execute("SELECT settings FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["settings"]:
        try:
            return json.loads(row["settings"])
        except Exception:
            pass
    return {}


@router.get("/api/ai/status")
async def ai_status():
    return {"online": await _ai_online()}


@router.post("/api/ai/explain")
async def ai_explain(body: dict, user: dict = Depends(get_current_user)):
    card_id = body.get("card_id")
    if not card_id:
        raise HTTPException(400)
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()
    if not card:
        conn.close()
        raise HTTPException(404)
    doc_ctx = ""
    pkg_name = ""
    try:
        pkg_row = conn.execute("SELECT name FROM packages WHERE id=?", (card["package_id"],)).fetchone()
        if pkg_row:
            pkg_name = pkg_row["name"]
        doc_rows = conn.execute(
            "SELECT dc.text FROM document_chunks dc JOIN documents d ON d.id=dc.document_id WHERE d.package_id=? ORDER BY d.id, dc.chunk_index LIMIT 30",
            (card["package_id"],)
        ).fetchall()
        doc_ctx = "\n\n".join(r["text"] for r in doc_rows if r["text"])
    except Exception:
        pass
    conn.close()
    settings = _load_user_settings(user["id"])
    result = await explain_card(
        card["question"], card["answer"],
        doc_context=doc_ctx, package_name=pkg_name,
        settings=settings
    )
    return {"explanation": result or ""}


@router.post("/api/ai/hint")
async def ai_hint(data: dict, user: dict = Depends(get_current_user)):
    """Erstellt eine Merkhilfe für eine Karte. Braucht LM Studio."""
    if not await _ai_online():
        raise HTTPException(503, "LM Studio nicht erreichbar")
    settings = _load_user_settings(user["id"])
    result = await generate_hint(data.get("question",""), data.get("answer",""),
                                 settings=settings)
    if not result:
        raise HTTPException(500, "Merkhilfe konnte nicht generiert werden")
    return {"hint": result}


@router.post("/api/ai/summarize")
async def ai_summarize(data: dict, user: dict = Depends(get_current_user)):
    """Fasst Karten zu einer Zusammenfassung zusammen. Braucht LM Studio."""
    if not await _ai_online():
        raise HTTPException(503, "LM Studio nicht erreichbar")
    cards = data.get("cards", [])
    topic = data.get("topic", "")
    if not cards:
        raise HTTPException(400, "Keine Karten übergeben")
    settings = _load_user_settings(user["id"])
    result = await summarize_topic(cards, topic, settings=settings)
    return {"summary": result}


@router.post("/api/ai/related")
async def ai_related(data: dict, user: dict = Depends(get_current_user)):
    """Schlaegt verwandte Karten vor (funktioniert auch ohne LM Studio)."""
    conn = get_db()
    pkg_id = data.get("package_id")
    q = "SELECT card_id, question, answer FROM cards WHERE active=1"
    p = []
    if pkg_id:
        q += " AND package_id=?"; p.append(pkg_id)
    all_cards = [row_to_dict(r) for r in conn.execute(q, p).fetchall()]
    conn.close()
    related = await suggest_related(data.get("question",""), data.get("answer",""), all_cards, limit=data.get("limit",3))
    return {"related": related}


@router.get("/api/mc/{card_id}")
async def get_mc_options_cached(card_id: str, package_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    """Holt MC-Optionen aus Cache oder generiert neu."""
    conn = get_db()
    if package_id is not None:
        card = conn.execute("SELECT question, answer, package_id FROM cards WHERE card_id=? AND package_id=? AND active=1", (card_id, package_id)).fetchone()
    else:
        card = conn.execute("SELECT question, answer, package_id FROM cards WHERE card_id=? AND active=1", (card_id,)).fetchone()
    if not card:
        conn.close()
        raise HTTPException(404, "Karte nicht gefunden")
    # Cache prüfen
    cached = conn.execute(
        "SELECT options, expires_at FROM mc_options WHERE card_id=? AND package_id=?",
        (card_id, card["package_id"])
    ).fetchone()
    today = date.today().isoformat()
    if cached and (not cached["expires_at"] or cached["expires_at"] > today):
        conn.close()
        return {"card_id": card_id, "options": json.loads(cached["options"]), "cached": True}
    # Nicht im Cache -- sofort 404 statt live generieren
    conn.close()
    raise HTTPException(404, "MC-Optionen nicht im Cache. Bitte zuerst generieren.")


@router.post("/api/mc/generate-batch")
async def generate_mc_batch(data: dict, user: dict = Depends(get_current_user)):
    """Generiert MC-Optionen für mehrere Karten eines Pakets (Batch)."""
    if not await _ai_online():
        raise HTTPException(503, "LM Studio nicht erreichbar")
    pkg_id = data.get("package_id")
    limit = data.get("limit", 20)
    conn = get_db()
    today = date.today().isoformat()
    # Karten ohne gültigen Cache
    cards = conn.execute("""
        SELECT c.card_id, c.question, c.answer FROM cards c
        LEFT JOIN mc_options mc ON mc.card_id=c.card_id AND mc.package_id=c.package_id
            AND (mc.expires_at IS NULL OR mc.expires_at > ?)
        WHERE c.package_id=? AND c.active=1 AND mc.id IS NULL
        LIMIT ?
    """, (today, pkg_id, limit)).fetchall()
    generated = 0
    failed = []
    settings = _load_user_settings(user["id"])
    for c in cards:
        try:
            options = await generate_mc_options(c["question"], c["answer"], settings=settings)
            if options and len(options) >= 3:
                expires = (date.today() + timedelta(days=7)).isoformat()
                conn.execute(
                    "INSERT OR REPLACE INTO mc_options (card_id, package_id, options, expires_at) VALUES (?,?,?,?)",
                    (c["card_id"], pkg_id, json.dumps(options), expires)
                )
                generated += 1
            else:
                failed.append({"card_id": c["card_id"], "reason": "Zu wenige Optionen generiert"})
        except Exception as e:
            failed.append({"card_id": c["card_id"], "reason": str(e)[:100]})
    conn.commit()
    conn.close()
    return {"generated": generated, "total": len(cards), "failed": failed}


@router.get("/api/mc/status/{package_id}")
def mc_cache_status(package_id: int, user: dict = Depends(get_current_user)):
    """Zeigt wie viele Karten MC-Optionen im Cache haben."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM cards WHERE package_id=? AND active=1", (package_id,)).fetchone()[0]
    today = date.today().isoformat()
    cached = conn.execute(
        "SELECT COUNT(*) FROM mc_options WHERE package_id=? AND (expires_at IS NULL OR expires_at > ?)",
        (package_id, today)
    ).fetchone()[0]
    conn.close()
    return {"total": total, "cached": cached, "missing": total - cached}


@router.delete("/api/mc/cache/{package_id}")
async def clear_mc_cache(package_id: int, user: dict = Depends(get_current_user)):
    """Löscht den MC-Cache für ein Paket (erzwingt Neugenerierung)."""
    conn = get_db()
    r = conn.execute("DELETE FROM mc_options WHERE package_id=?", (package_id,))
    conn.commit()
    conn.close()
    return {"deleted": r.rowcount}


@router.get("/api/mc/list/{package_id}")
def list_mc_options(package_id: int, user: dict = Depends(get_current_user)):
    """Listet alle gecachten MC-Optionen eines Pakets mit Kartendaten."""
    conn = get_db()
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT mc.card_id, mc.options, mc.expires_at,
               c.question, c.answer, c.category_code
        FROM mc_options mc
        JOIN cards c ON c.card_id = mc.card_id AND c.package_id = mc.package_id
        WHERE mc.package_id = ? AND (mc.expires_at IS NULL OR mc.expires_at > ?)
        ORDER BY mc.card_id
    """, (package_id, today)).fetchall()
    conn.close()
    return [
        {
            "card_id": r["card_id"],
            "question": r["question"],
            "answer": r["answer"],
            "category_code": r["category_code"],
            "options": json.loads(r["options"]),
            "expires_at": r["expires_at"],
        }
        for r in rows
    ]


@router.delete("/api/mc/option/{card_id}/{package_id}")
def delete_mc_option(card_id: str, package_id: int, user: dict = Depends(get_current_user)):
    """Löscht MC-Optionen für eine einzelne Karte."""
    conn = get_db()
    r = conn.execute(
        "DELETE FROM mc_options WHERE card_id=? AND package_id=?",
        (card_id, package_id)
    )
    conn.commit()
    conn.close()
    return {"deleted": r.rowcount}


@router.post("/api/mc/regenerate")
async def regenerate_mc_option(data: dict, user: dict = Depends(get_current_user)):
    """Generiert MC-Optionen für eine einzelne Karte neu."""
    if not await _ai_online():
        raise HTTPException(503, "LM Studio nicht erreichbar")
    card_id = data.get("card_id")
    pkg_id = data.get("package_id")
    if not card_id or not pkg_id:
        raise HTTPException(400, "card_id und package_id erforderlich")
    conn = get_db()
    card = conn.execute(
        "SELECT question, answer FROM cards WHERE card_id=? AND package_id=? AND active=1",
        (card_id, pkg_id)
    ).fetchone()
    if not card:
        conn.close()
        raise HTTPException(404, "Karte nicht gefunden")
    settings = _load_user_settings(user["id"])
    options = await generate_mc_options(card["question"], card["answer"], settings=settings)
    if not options or len(options) < 3:
        conn.close()
        raise HTTPException(500, "MC-Generierung fehlgeschlagen")
    expires = (date.today() + timedelta(days=7)).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO mc_options (card_id, package_id, options, expires_at) VALUES (?,?,?,?)",
        (card_id, pkg_id, json.dumps(options), expires)
    )
    conn.commit()
    conn.close()
    return {"card_id": card_id, "options": options}
