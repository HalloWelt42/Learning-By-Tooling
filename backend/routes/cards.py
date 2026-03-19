"""routes/cards.py -- CRUD, Suche, SRS-Review, Stats."""

from __future__ import annotations
import json
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from db import get_db, row_to_dict
from auth import get_current_user
from helpers import next_card_id, rebuild_fts
from schemas import CardCreate, CardUpdate, SRSReview
from services import sm2_update

router = APIRouter(tags=["cards"])


# -- Karten --------------------------------------------------------------------

@router.get("/api/cards")
def get_cards(
    package_id:  Optional[int] = None,
    category:    Optional[str] = None,
    active_only: bool          = True,
    search:      Optional[str] = None,
    difficulty:  Optional[int] = None,
    limit:       int           = 200,
    offset:      int           = 0,
    user: dict = Depends(get_current_user),
):
    conn = get_db()
    if search:
        q = """SELECT * FROM cards WHERE
            (card_id LIKE ? OR question LIKE ? OR answer LIKE ?)
            AND (? IS NULL OR package_id=?)
            AND (? IS NULL OR category_code=?)
            AND (? = 0 OR active=1)
            LIMIT ? OFFSET ?"""
        like = f"%{search}%"
        rows = conn.execute(q, (like, like, like, package_id, package_id, category, category, int(active_only), limit, offset)).fetchall()
    else:
        q = "SELECT * FROM cards WHERE 1=1"
        p: list = []
        if package_id is not None:
            q += " AND package_id=?";    p.append(package_id)
        if category:
            q += " AND category_code=?"; p.append(category)
        if active_only:
            q += " AND active=1"
        if difficulty:
            q += " AND difficulty=?";    p.append(difficulty)
        q += " ORDER BY card_id LIMIT ? OFFSET ?"
        p += [limit, offset]
        rows = conn.execute(q, p).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.get("/api/cards/{card_id}")
def get_card(card_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)


@router.post("/api/cards")
def create_card(data: CardCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    if not data.card_id:
        data.card_id = next_card_id(conn)
    try:
        conn.execute(
            "INSERT INTO cards (card_id,package_id,category_code,question,answer,hint,tags,difficulty) VALUES (?,?,?,?,?,?,?,?)",
            (data.card_id, data.package_id, data.category_code, data.question,
             data.answer, data.hint, json.dumps(data.tags or []), data.difficulty)
        )
        conn.commit()
        rebuild_fts(conn)
        return row_to_dict(conn.execute("SELECT * FROM cards WHERE card_id=?", (data.card_id,)).fetchone())
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()


@router.put("/api/cards/{card_id}")
def update_card(card_id: str, data: CardUpdate, user: dict = Depends(get_current_user)):
    conn = get_db()
    updates: dict = {}
    if data.package_id    is not None: updates["package_id"]    = data.package_id
    if data.category_code is not None: updates["category_code"] = data.category_code
    if data.question      is not None: updates["question"]      = data.question
    if data.answer        is not None: updates["answer"]        = data.answer
    if data.hint          is not None: updates["hint"]          = data.hint
    if data.tags          is not None: updates["tags"]          = json.dumps(data.tags)
    if data.difficulty    is not None: updates["difficulty"]    = data.difficulty
    if data.active        is not None: updates["active"]        = data.active
    if not updates:
        raise HTTPException(400, "Keine Änderungen")
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE cards SET {sets} WHERE card_id=?", list(updates.values()) + [card_id])
    conn.commit()
    rebuild_fts(conn)
    row = conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


@router.delete("/api/cards/{card_id}")
def delete_card(card_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM cards WHERE card_id=?", (card_id,))
    conn.commit()
    rebuild_fts(conn)
    conn.close()
    return {"ok": True}


# -- Stats (global, pro Benutzer) ----------------------------------------------

@router.get("/api/stats")
def get_stats(user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    total   = conn.execute("SELECT COUNT(*) FROM cards WHERE active=1").fetchone()[0]
    pkgs    = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    sessions= conn.execute("SELECT COUNT(*) FROM sessions WHERE ended_at IS NOT NULL AND user_id=?", (uid,)).fetchone()[0]
    rev     = conn.execute("SELECT COUNT(*), COALESCE(SUM(result='correct'),0) FROM reviews WHERE user_id=?", (uid,)).fetchone()
    due     = conn.execute("""
        SELECT COUNT(*) FROM cards c
        LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
        WHERE c.active=1 AND (cs.due_date IS NULL OR cs.due_date <= ?)
    """, (uid, date.today().isoformat())).fetchone()[0]
    drafts  = conn.execute("SELECT COUNT(*) FROM card_drafts WHERE status='pending'").fetchone()[0]
    cats    = conn.execute("""
        SELECT cat.code, cat.name, cat.color, cat.icon,
               COUNT(c.id) as count,
               COALESCE(SUM(cs.times_correct),0) as correct,
               COALESCE(SUM(cs.times_shown),0)   as shown
        FROM categories cat
        LEFT JOIN cards c ON c.category_code=cat.code AND c.active=1
        LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
        GROUP BY cat.code
    """, (uid,)).fetchall()
    conn.close()
    return {
        "total_cards":    total,
        "total_packages": pkgs,
        "total_sessions": sessions,
        "total_reviews":  rev[0] or 0,
        "total_correct":  rev[1] or 0,
        "due_today":      due,
        "pending_drafts": drafts,
        "by_category":    [row_to_dict(r) for r in cats],
    }


# -- Karten-Statistik / SRS ---------------------------------------------------

@router.get("/api/cards/{card_id}/stats")
def get_card_stats(card_id: str, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    row = conn.execute("SELECT * FROM card_stats WHERE card_id=? AND user_id=?", (card_id, uid)).fetchone()
    conn.close()
    return row_to_dict(row) if row else {"card_id": card_id, "times_shown":0, "times_correct":0, "streak":0}


@router.get("/api/srs/due")
def get_due_cards(limit: int = 20, package_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    today = date.today().isoformat()
    q = """
        SELECT c.*, cs.due_date, cs.streak, cs.ease_factor, cs.interval_days
        FROM cards c
        LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
        WHERE c.active=1 AND (cs.due_date IS NULL OR cs.due_date <= ?)
    """
    p: list = [uid, today]
    if package_id is not None:
        q += " AND c.package_id=?"; p.append(package_id)
    q += " ORDER BY COALESCE(cs.due_date,'1970-01-01') ASC, RANDOM() LIMIT ?"
    p.append(limit)
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.post("/api/srs/review")
def srs_review(data: SRSReview, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    # Karte pruefen
    card = conn.execute("SELECT id FROM cards WHERE card_id=? AND active=1", (data.card_id,)).fetchone()
    if not card:
        conn.close()
        raise HTTPException(404, "Karte nicht gefunden")
    stats = conn.execute("SELECT * FROM card_stats WHERE card_id=? AND user_id=?", (data.card_id, uid)).fetchone()
    ease     = float(stats["ease_factor"])   if stats and stats["ease_factor"]   else 2.5
    interval = int(stats["interval_days"])   if stats and stats["interval_days"] else 1
    reps     = int(stats["times_shown"])     if stats and stats["times_shown"]   else 0
    ease, interval, reps = sm2_update(ease, interval, reps, data.quality)
    due = (date.today() + timedelta(days=interval)).isoformat()
    result = "correct" if data.quality >= 3 else "wrong"
    # card_stats aktualisieren
    conn.execute("""
        INSERT INTO card_stats (user_id,card_id,times_shown,times_correct,times_wrong,last_reviewed,due_date,ease_factor,interval_days)
        VALUES (?,?,1,?,?,?,?,?,?)
        ON CONFLICT(user_id,card_id) DO UPDATE SET
            times_shown=times_shown+1,
            times_correct=times_correct+excluded.times_correct,
            times_wrong=times_wrong+excluded.times_wrong,
            last_reviewed=excluded.last_reviewed,
            due_date=excluded.due_date,
            ease_factor=excluded.ease_factor,
            interval_days=excluded.interval_days,
            streak=CASE WHEN excluded.times_correct=1 THEN streak+1 ELSE 0 END
    """, (uid, data.card_id, 1 if data.quality>=3 else 0, 1 if data.quality<3 else 0,
          datetime.now().isoformat(), due, ease, interval))
    # Auch in reviews schreiben (fuer Session-Ergebnis und Achievements)
    if data.session_id:
        conn.execute(
            "INSERT INTO reviews (user_id,session_id,card_id,result) VALUES (?,?,?,?)",
            (uid, data.session_id, data.card_id, result)
        )
    conn.commit()
    conn.close()
    return {"due_date": due, "interval_days": interval, "result": result}


# -- Globale Suche -------------------------------------------------------------

@router.get("/api/search")
def global_search(
    q:          str,
    pkg_id:     Optional[int] = None,
    category:   Optional[str] = None,
    difficulty: Optional[int] = None,
    limit:      int = 50,
    offset:     int = 0,
    user: dict = Depends(get_current_user),
):
    if not q or len(q.strip()) < 2:
        return {"total": 0, "items": [], "q": q}

    conn = get_db()
    q_clean = q.strip()

    base_q = """
        SELECT
            c.id as card_id, c.card_id as card_code,
            c.question, c.answer, c.category_code,
            c.package_id, c.difficulty,
            p.name as package_name, p.color as package_color, p.icon as package_icon,
            snippet(cards_fts, 0, '<em>', '</em>', '...', 12) as snippet_q,
            snippet(cards_fts, 1, '<em>', '</em>', '...', 16) as snippet_a
        FROM cards_fts
        JOIN cards c ON c.card_id = cards_fts.card_id
        LEFT JOIN packages p ON p.id = c.package_id
        WHERE cards_fts MATCH ?
        AND c.active = 1
    """
    params: list = [f'"{q_clean}"*']

    if pkg_id:
        base_q += " AND c.package_id = ?"
        params.append(pkg_id)
    if category:
        base_q += " AND c.category_code = ?"
        params.append(category)
    if difficulty:
        base_q += " AND c.difficulty = ?"
        params.append(difficulty)

    count_q = f"SELECT COUNT(*) FROM ({base_q})"
    total = conn.execute(count_q, params).fetchone()[0]

    items_q = base_q + " ORDER BY rank LIMIT ? OFFSET ?"
    rows = conn.execute(items_q, params + [limit, offset]).fetchall()

    conn.close()
    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "q":      q_clean,
        "items":  [dict(r) for r in rows],
    }
