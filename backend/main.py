"""
Learn-e-Versum Backend
Paket-zentrierte Lernplattform mit Mehrbenutzersystem.
Port: 8030
"""

from __future__ import annotations
import json, re
from datetime import datetime, date, timedelta
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db import get_db, init_db, row_to_dict
from services import (
    chunk_text, extract_text_from_file,
    generate_cards_from_chunk, evaluate_answer,
    explain_card, analyze_mistakes, ai_online as _ai_online, sm2_update,
)
from auth import (
    get_current_user, authenticate, create_user, create_token, seed_admin,
)

app = FastAPI(title="Learning-By-Tooling", version="3.0.0")

# CORS -- großzügig für die Entwicklungsphase
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["*"],
)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).parent.parent / "uploads")))
UPLOAD_DIR.mkdir(exist_ok=True)

init_db()
seed_admin()

# -- Schemas -------------------------------------------------------------------

class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterRequest(BaseModel):
    email:        str
    password:     str
    display_name: Optional[str] = None

class PackageCreate(BaseModel):
    name:        str
    description: Optional[str]  = None
    color:       Optional[str]  = "#2196F3"
    icon:        Optional[str]  = "fa-graduation-cap"

class PackageUpdate(BaseModel):
    name:        Optional[str]  = None
    description: Optional[str]  = None
    color:       Optional[str]  = None
    icon:        Optional[str]  = None

class CardCreate(BaseModel):
    card_id:       Optional[str]  = None
    package_id:    Optional[int]  = None
    category_code: str
    question:      str
    answer:        str
    hint:          Optional[str]  = None
    tags:          Optional[list] = []
    difficulty:    Optional[int]  = 2

class CardUpdate(BaseModel):
    package_id:    Optional[int]  = None
    category_code: Optional[str]  = None
    question:      Optional[str]  = None
    answer:        Optional[str]  = None
    hint:          Optional[str]  = None
    tags:          Optional[list] = None
    difficulty:    Optional[int]  = None
    active:        Optional[int]  = None

class CategoryCreate(BaseModel):
    code:        str
    name:        str
    description: Optional[str]  = None
    color:       Optional[str]  = "#2196F3"
    icon:        Optional[str]  = "fa-layer-group"

class SessionCreate(BaseModel):
    mode:            Optional[str]  = "standard"
    package_id:      Optional[int]  = None
    category_filter: Optional[list] = []
    card_limit:      Optional[int]  = 20
    srs_mode:        Optional[bool] = False

class ReviewSubmit(BaseModel):
    session_id:  int
    card_id:     str
    result:      str
    user_answer: Optional[str]  = None
    use_ai:      Optional[bool] = False

class SRSReview(BaseModel):
    card_id: str
    quality: int

class LexiconCreate(BaseModel):
    package_id:    Optional[int]  = None
    term:          str
    definition:    str
    category_code: Optional[str]  = None
    related_cards: Optional[list] = []

class PathCreate(BaseModel):
    package_id:     Optional[int]  = None
    name:           str
    description:    Optional[str]  = None
    category_codes: Optional[list] = []
    card_ids:       Optional[list] = []

class DraftAction(BaseModel):
    action:        str
    question:      Optional[str]  = None
    answer:        Optional[str]  = None
    hint:          Optional[str]  = None
    difficulty:    Optional[int]  = None
    category_code: Optional[str]  = None
    package_id:    Optional[int]  = None

class MarkdownImport(BaseModel):
    fragen:     str
    antworten:  str
    package_id: Optional[int] = None

class MistakeAnalysisRequest(BaseModel):
    card_ids:   list[int]
    package_id: int

# -- Helpers -------------------------------------------------------------------

def _next_card_id(conn) -> str:
    row = conn.execute("SELECT card_id FROM cards ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        m = re.search(r"(\d+)$", row["card_id"])
        n = int(m.group(1)) + 1 if m else 1
    else:
        n = 1
    return f"K-{n:03d}"

def _rebuild_fts(conn):
    conn.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")
    conn.commit()

# -- Auth (öffentlich) ---------------------------------------------------------

@app.post("/api/auth/login")
def login(data: LoginRequest):
    user = authenticate(data.email, data.password)
    if not user:
        raise HTTPException(401, "E-Mail oder Passwort falsch")
    token = create_token(user["id"], user["email"])
    return {"token": token, "user": user}

@app.post("/api/auth/register")
def register(data: RegisterRequest):
    user = create_user(data.email, data.password, data.display_name or "")
    token = create_token(user["id"], user["email"])
    return {"token": token, "user": user}

@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user

# -- Health (öffentlich) -------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "3.0.0", "app": "Learning-By-Tooling"}

@app.get("/api/ai/status")
async def ai_status():
    return {"online": await _ai_online()}

# -- Pakete --------------------------------------------------------------------

@app.get("/api/packages")
def get_packages(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*,
            (SELECT COUNT(*) FROM cards c WHERE c.package_id=p.id AND c.active=1)   as card_count,
            (SELECT COUNT(*) FROM documents d WHERE d.package_id=p.id)               as doc_count,
            (SELECT COUNT(*) FROM card_drafts cd WHERE cd.package_id=p.id AND cd.status='pending') as draft_count
        FROM packages p ORDER BY p.created_at ASC
    """).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.get("/api/packages/{pkg_id}")
def get_package(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Paket nicht gefunden")
    return row_to_dict(row)

@app.post("/api/packages")
def create_package(data: PackageCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO packages (name,description,color,icon) VALUES (?,?,?,?)",
        (data.name, data.description, data.color, data.icon)
    )
    conn.commit()
    row = conn.execute("SELECT last_insert_rowid()").fetchone()
    pkg = conn.execute("SELECT * FROM packages WHERE id=?", (row[0],)).fetchone()
    conn.close()
    return row_to_dict(pkg)

@app.put("/api/packages/{pkg_id}")
def update_package(pkg_id: int, data: PackageUpdate, user: dict = Depends(get_current_user)):
    conn = get_db()
    updates: dict = {}
    if data.name        is not None: updates["name"]        = data.name
    if data.description is not None: updates["description"] = data.description
    if data.color       is not None: updates["color"]       = data.color
    if data.icon        is not None: updates["icon"]        = data.icon
    if not updates:
        raise HTTPException(400, "Keine Änderungen")
    updates["updated_at"] = datetime.now().isoformat()
    sets = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE packages SET {sets} WHERE id=?", list(updates.values()) + [pkg_id])
    conn.commit()
    row = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    conn.close()
    return row_to_dict(row)

@app.delete("/api/packages/{pkg_id}")
def delete_package(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("UPDATE cards SET active=0 WHERE package_id=?", (pkg_id,))
    conn.execute("DELETE FROM packages WHERE id=?", (pkg_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/packages/{pkg_id}/stats")
def get_package_stats(pkg_id: int, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM cards WHERE package_id=? AND active=1", (pkg_id,)).fetchone()[0]
    docs  = conn.execute("SELECT COUNT(*) FROM documents WHERE package_id=?", (pkg_id,)).fetchone()[0]
    drafts= conn.execute("SELECT COUNT(*) FROM card_drafts WHERE package_id=? AND status='pending'", (pkg_id,)).fetchone()[0]
    rev   = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(r.result='correct'),0)
        FROM reviews r JOIN cards c ON c.card_id=r.card_id
        WHERE c.package_id=? AND r.user_id=?
    """, (pkg_id, uid)).fetchone()
    due   = conn.execute("""
        SELECT COUNT(*) FROM cards c
        LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
        WHERE c.package_id=? AND c.active=1
        AND (cs.due_date IS NULL OR cs.due_date <= ?)
    """, (uid, pkg_id, date.today().isoformat())).fetchone()[0]
    by_cat = conn.execute("""
        SELECT cat.code, cat.name, cat.color, cat.icon,
               COUNT(c.id) as count,
               COALESCE(SUM(cs.times_correct),0) as correct,
               COALESCE(SUM(cs.times_shown),0) as shown
        FROM categories cat
        LEFT JOIN cards c ON c.category_code=cat.code AND c.package_id=? AND c.active=1
        LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
        GROUP BY cat.code
    """, (pkg_id, uid)).fetchall()
    conn.close()
    return {
        "total_cards":    total,
        "total_docs":     docs,
        "pending_drafts": drafts,
        "total_reviews":  rev[0] or 0,
        "total_correct":  rev[1] or 0,
        "due_today":      due,
        "by_category":    [row_to_dict(r) for r in by_cat],
    }

# -- Kategorien ----------------------------------------------------------------

@app.get("/api/categories")
def get_categories(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, COUNT(ca.id) as card_count
        FROM categories c
        LEFT JOIN cards ca ON ca.category_code=c.code AND ca.active=1
        GROUP BY c.id ORDER BY c.code
    """).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.post("/api/categories")
def create_category(data: CategoryCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO categories (code,name,description,color,icon) VALUES (?,?,?,?,?)",
            (data.code.upper(), data.name, data.description, data.color, data.icon)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM categories WHERE code=?", (data.code.upper(),)).fetchone()
        return row_to_dict(row)
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()

# -- Karten --------------------------------------------------------------------

@app.get("/api/cards")
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
        rows = conn.execute("""
            SELECT c.* FROM cards c
            JOIN cards_fts f ON c.card_id=f.card_id
            WHERE cards_fts MATCH ?
            AND (? IS NULL OR c.package_id=?)
            AND (? IS NULL OR c.category_code=?)
            AND (? = 0 OR c.active=1)
            LIMIT ? OFFSET ?
        """, (search, package_id, package_id, category, category, int(active_only), limit, offset)).fetchall()
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

@app.get("/api/cards/{card_id}")
def get_card(card_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404)
    return row_to_dict(row)

@app.post("/api/cards")
def create_card(data: CardCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    if not data.card_id:
        data.card_id = _next_card_id(conn)
    try:
        conn.execute(
            "INSERT INTO cards (card_id,package_id,category_code,question,answer,hint,tags,difficulty) VALUES (?,?,?,?,?,?,?,?)",
            (data.card_id, data.package_id, data.category_code, data.question,
             data.answer, data.hint, json.dumps(data.tags or []), data.difficulty)
        )
        conn.commit()
        _rebuild_fts(conn)
        return row_to_dict(conn.execute("SELECT * FROM cards WHERE card_id=?", (data.card_id,)).fetchone())
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()

@app.put("/api/cards/{card_id}")
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
    _rebuild_fts(conn)
    row = conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()
    conn.close()
    return row_to_dict(row)

@app.delete("/api/cards/{card_id}")
def delete_card(card_id: str, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM cards WHERE card_id=?", (card_id,))
    conn.commit()
    _rebuild_fts(conn)
    conn.close()
    return {"ok": True}

# -- Stats (global, pro Benutzer) ----------------------------------------------

@app.get("/api/stats")
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

@app.get("/api/cards/{card_id}/stats")
def get_card_stats(card_id: str, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    row = conn.execute("SELECT * FROM card_stats WHERE card_id=? AND user_id=?", (card_id, uid)).fetchone()
    conn.close()
    return row_to_dict(row) if row else {"card_id": card_id, "times_shown":0, "times_correct":0, "streak":0}

@app.get("/api/srs/due")
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

@app.post("/api/srs/review")
def srs_review(data: SRSReview, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    stats = conn.execute("SELECT * FROM card_stats WHERE card_id=? AND user_id=?", (data.card_id, uid)).fetchone()
    ease     = float(stats["ease_factor"])   if stats and stats["ease_factor"]   else 2.5
    interval = int(stats["interval_days"])   if stats and stats["interval_days"] else 1
    reps     = int(stats["times_shown"])     if stats and stats["times_shown"]   else 0
    ease, interval, reps = sm2_update(ease, interval, reps, data.quality)
    due = (date.today() + timedelta(days=interval)).isoformat()
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
    conn.commit()
    conn.close()
    return {"due_date": due, "interval_days": interval}

# -- Sessions ------------------------------------------------------------------

@app.post("/api/sessions")
def start_session(data: SessionCreate, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    if data.srs_mode:
        q = """
            SELECT c.card_id FROM cards c
            LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
            WHERE c.active=1 AND (cs.due_date IS NULL OR cs.due_date <= ?)
        """
        p: list = [uid, date.today().isoformat()]
        if data.package_id is not None:
            q += " AND c.package_id=?"; p.append(data.package_id)
        q += " ORDER BY COALESCE(cs.due_date,'1970-01-01') ASC, RANDOM() LIMIT ?"
        p.append(data.card_limit)
    else:
        q = "SELECT card_id FROM cards WHERE active=1"
        p = []
        if data.package_id is not None:
            q += " AND package_id=?"; p.append(data.package_id)
        if data.category_filter:
            pl = ",".join("?" * len(data.category_filter))
            q += f" AND category_code IN ({pl})"; p.extend(data.category_filter)
        q += " ORDER BY RANDOM() LIMIT ?"; p.append(data.card_limit)

    rows    = conn.execute(q, p).fetchall()
    card_ids = [r["card_id"] for r in rows]
    pkg_id_val = data.package_id if data.package_id else None
    conn.execute(
        "INSERT INTO sessions (user_id,mode,package_id,category_filter,total_cards) VALUES (?,?,?,?,?)",
        (uid, data.mode, pkg_id_val, json.dumps(data.category_filter), len(card_ids))
    )
    session_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"session_id": session_id, "card_ids": card_ids, "total": len(card_ids)}

@app.get("/api/sessions/active")
def get_active_session(user: dict = Depends(get_current_user)):
    """Gibt die aktive (nicht beendete) Session des Users zurück, falls vorhanden."""
    uid = user["id"]
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE user_id=? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (uid,)
    ).fetchone()
    if not session:
        conn.close()
        return None
    # Reviews dieser Session laden
    reviews = conn.execute(
        "SELECT card_id, result FROM reviews WHERE session_id=? AND user_id=?",
        (session["id"], uid)
    ).fetchall()
    reviewed_ids = [r["card_id"] for r in reviews]
    correct = sum(1 for r in reviews if r["result"] == "correct")
    wrong = sum(1 for r in reviews if r["result"] == "wrong")
    skipped = sum(1 for r in reviews if r["result"] == "skip")
    # Alle Karten der Session (aus der Gesamt-Auswahl) laden
    cat_filter = json.loads(session["category_filter"]) if session["category_filter"] else []
    q = "SELECT card_id FROM cards WHERE active=1"
    p = []
    if session["package_id"]:
        q += " AND package_id=?"; p.append(session["package_id"])
    if cat_filter:
        pl = ",".join("?" * len(cat_filter))
        q += f" AND category_code IN ({pl})"; p.extend(cat_filter)
    q += " ORDER BY RANDOM() LIMIT ?"
    p.append(session["total_cards"])
    all_cards = [r["card_id"] for r in conn.execute(q, p).fetchall()]
    # Noch nicht beantwortete Karten
    remaining = [c for c in all_cards if c not in reviewed_ids]
    conn.close()
    return {
        "session_id": session["id"],
        "mode": session["mode"],
        "package_id": session["package_id"],
        "total": session["total_cards"],
        "reviewed": len(reviewed_ids),
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "remaining_ids": remaining,
        "started_at": session["started_at"],
    }

@app.delete("/api/sessions/active")
def cancel_active_session(user: dict = Depends(get_current_user)):
    """Bricht die aktive Session ab (beendet sie ohne Ergebnis)."""
    uid = user["id"]
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET ended_at=? WHERE user_id=? AND ended_at IS NULL",
        (datetime.now().isoformat(), uid)
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/api/sessions/{session_id}/end")
def end_session(session_id: int, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    s = conn.execute(
        "SELECT COUNT(*) as t, SUM(result='correct') as c, SUM(result='skip') as sk FROM reviews WHERE session_id=? AND user_id=?",
        (session_id, uid)
    ).fetchone()
    conn.execute(
        "UPDATE sessions SET ended_at=?, correct=?, skipped=? WHERE id=? AND user_id=?",
        (datetime.now().isoformat(), s["c"] or 0, s["sk"] or 0, session_id, uid)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "correct": s["c"] or 0, "total": s["t"]}

@app.post("/api/reviews")
async def submit_review(data: ReviewSubmit, user: dict = Depends(get_current_user)):
    uid = user["id"]
    ai_score = ai_feedback = None
    result   = data.result
    if data.use_ai and data.user_answer:
        conn = get_db()
        card = conn.execute("SELECT * FROM cards WHERE card_id=?", (data.card_id,)).fetchone()
        if card:
            eval_ctx = ""
            try:
                doc_rows = conn.execute(
                    "SELECT dc.text FROM document_chunks dc JOIN documents d ON d.id=dc.document_id WHERE d.package_id=? ORDER BY d.id, dc.chunk_index LIMIT 20",
                    (card["package_id"],)
                ).fetchall()
                eval_ctx = "\n\n".join(r["text"] for r in doc_rows if r["text"])
            except Exception:
                pass
            ev = await evaluate_answer(
                card["question"], card["answer"], data.user_answer,
                doc_context=eval_ctx
            )
            ai_score = ev["score"]; ai_feedback = ev["feedback"]
            if data.result == "unknown":
                result = "correct" if ev["score"] >= 0.6 else "wrong"
        conn.close()
    conn = get_db()
    conn.execute(
        "INSERT INTO reviews (user_id,session_id,card_id,result,user_answer,ai_score,ai_feedback) VALUES (?,?,?,?,?,?,?)",
        (uid, data.session_id, data.card_id, result, data.user_answer, ai_score, ai_feedback)
    )
    conn.execute("""
        INSERT INTO card_stats (user_id,card_id,times_shown,times_correct,times_wrong,last_reviewed,streak)
        VALUES (?,?,1,?,?,?,?)
        ON CONFLICT(user_id,card_id) DO UPDATE SET
            times_shown=times_shown+1,
            times_correct=times_correct+excluded.times_correct,
            times_wrong=times_wrong+excluded.times_wrong,
            last_reviewed=excluded.last_reviewed,
            streak=CASE WHEN excluded.times_correct=1 THEN streak+1 ELSE 0 END
    """, (uid, data.card_id, 1 if result=="correct" else 0, 1 if result=="wrong" else 0,
          datetime.now().isoformat(), 1 if result=="correct" else 0))
    conn.commit()
    conn.close()
    return {"ok": True, "ai_score": ai_score, "ai_feedback": ai_feedback, "result": result}

# -- Dokumente -----------------------------------------------------------------

@app.get("/api/packages/{pkg_id}/documents")
def get_documents(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM documents WHERE package_id=? ORDER BY created_at DESC", (pkg_id,)
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.post("/api/packages/{pkg_id}/documents/upload")
async def upload_document(
    pkg_id:   int,
    file:     UploadFile = File(...),
    title:    str        = Form(default=""),
    category: str        = Form(default="AL"),
    user: dict = Depends(get_current_user),
):
    content  = await file.read()
    filename = file.filename or "upload.txt"
    ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    if ext not in ("txt","md","pdf","docx"):
        raise HTTPException(400, f"Dateityp '{ext}' nicht unterstützt")
    text = extract_text_from_file(content, ext)
    if not text.strip():
        raise HTTPException(400, "Dokument ist leer")
    chunks    = chunk_text(text)
    doc_title = title.strip() or filename
    conn = get_db()
    conn.execute(
        "INSERT INTO documents (package_id,filename,title,filetype,filesize,chunk_count,status) VALUES (?,?,?,?,?,?,?)",
        (pkg_id, filename, doc_title, ext, len(content), len(chunks), "ready")
    )
    doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i, chunk in enumerate(chunks):
        conn.execute(
            "INSERT INTO document_chunks (document_id,chunk_index,text) VALUES (?,?,?)",
            (doc_id, i, chunk)
        )
    conn.commit()
    conn.close()
    return {"document_id": doc_id, "chunk_count": len(chunks), "title": doc_title}

@app.get("/api/documents/{doc_id}/chunks")
def get_chunks(doc_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    doc    = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        conn.close()
        raise HTTPException(404, "Dokument nicht gefunden")
    chunks = conn.execute(
        "SELECT id, chunk_index, text FROM document_chunks WHERE document_id=? ORDER BY chunk_index", (doc_id,)
    ).fetchall()
    conn.close()
    return {
        "doc_id":   doc_id,
        "title":    doc["title"],
        "filetype": doc["filetype"],
        "chunks":   [dict(c) for c in chunks],
    }

@app.post("/api/documents/{doc_id}/generate")
async def generate_from_doc(doc_id: int, body: dict, user: dict = Depends(get_current_user)):
    chunk_ids       = body.get("chunk_ids")
    category        = body.get("category", "AL")
    cards_per_chunk = int(body.get("cards_per_chunk", 3))
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        conn.close(); raise HTTPException(404)
    pkg_id = doc["package_id"]
    if chunk_ids:
        pl = ",".join("?" * len(chunk_ids))
        chunks = conn.execute(
            f"SELECT * FROM document_chunks WHERE document_id=? AND id IN ({pl})",
            [doc_id] + chunk_ids
        ).fetchall()
    else:
        chunks = conn.execute(
            "SELECT * FROM document_chunks WHERE document_id=? AND processed=0", (doc_id,)
        ).fetchall()
    created = errors = 0
    for chunk in chunks:
        pkg_nm = ""
        try:
            p = conn.execute("SELECT name FROM packages WHERE id=?", (pkg_id,)).fetchone()
            if p: pkg_nm = p["name"]
        except Exception:
            pass
        cards = await generate_cards_from_chunk(
            chunk["text"], category, cards_per_chunk,
            package_name=pkg_nm
        )
        for c in cards:
            try:
                conn.execute(
                    "INSERT INTO card_drafts (document_id,package_id,chunk_id,category_code,question,answer,hint,difficulty) VALUES (?,?,?,?,?,?,?,?)",
                    (doc_id, pkg_id, chunk["id"], c["category_code"],
                     c["question"], c["answer"], c.get("hint"), c.get("difficulty",2))
                )
                created += 1
            except Exception:
                errors += 1
        conn.execute("UPDATE document_chunks SET processed=1 WHERE id=?", (chunk["id"],))
    conn.execute("UPDATE documents SET card_count=card_count+? WHERE id=?", (created, doc_id))
    conn.commit()
    conn.close()
    return {"created": created, "errors": errors, "chunks_processed": len(chunks)}

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM document_chunks WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM card_drafts WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

# -- Entwürfe -----------------------------------------------------------------

@app.get("/api/packages/{pkg_id}/drafts")
def get_package_drafts(pkg_id: int, status: str = "pending", user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("""
        SELECT cd.*, d.title as doc_title
        FROM card_drafts cd
        LEFT JOIN documents d ON d.id=cd.document_id
        WHERE cd.package_id=? AND cd.status=?
        ORDER BY cd.document_id, cd.id
    """, (pkg_id, status)).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.put("/api/drafts/{draft_id}")
def handle_draft(draft_id: int, data: DraftAction, user: dict = Depends(get_current_user)):
    conn = get_db()
    draft = conn.execute("SELECT * FROM card_drafts WHERE id=?", (draft_id,)).fetchone()
    if not draft:
        conn.close(); raise HTTPException(404)
    if data.action == "reject":
        conn.execute("UPDATE card_drafts SET status='rejected' WHERE id=?", (draft_id,))
    elif data.action in ("approve","edit"):
        question      = data.question      or draft["question"]
        answer        = data.answer        or draft["answer"]
        hint          = data.hint          if data.hint is not None else draft["hint"]
        difficulty    = data.difficulty    or draft["difficulty"]
        category_code = data.category_code or draft["category_code"]
        package_id    = data.package_id    or draft["package_id"]
        card_id = _next_card_id(conn)
        conn.execute(
            "INSERT INTO cards (card_id,package_id,category_code,question,answer,hint,difficulty) VALUES (?,?,?,?,?,?,?)",
            (card_id, package_id, category_code, question, answer, hint, difficulty)
        )
        _rebuild_fts(conn)
        conn.execute("UPDATE card_drafts SET status='approved' WHERE id=?", (draft_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

# -- Lexikon -------------------------------------------------------------------

@app.get("/api/packages/{pkg_id}/lexicon")
def get_lexicon(pkg_id: int, search: Optional[str] = None, user: dict = Depends(get_current_user)):
    conn = get_db()
    if search:
        rows = conn.execute("""
            SELECT l.* FROM lexicon l
            JOIN lexicon_fts lf ON l.id=lf.rowid
            WHERE lexicon_fts MATCH ? AND l.package_id=?
        """, (search, pkg_id)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM lexicon WHERE package_id=? ORDER BY term", (pkg_id,)
        ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.post("/api/lexicon")
def create_lexicon_entry(data: LexiconCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO lexicon (package_id,term,definition,category_code,related_cards) VALUES (?,?,?,?,?)",
            (data.package_id, data.term, data.definition, data.category_code, json.dumps(data.related_cards or []))
        )
        conn.commit()
        conn.execute("INSERT INTO lexicon_fts(lexicon_fts) VALUES('rebuild')")
        conn.commit()
        return row_to_dict(conn.execute("SELECT * FROM lexicon WHERE term=?", (data.term,)).fetchone())
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        conn.close()

# -- Lernfehler-Analyse -------------------------------------------------------

@app.post("/api/learn/analyze-mistakes")
async def analyze_learning_mistakes(data: MistakeAnalysisRequest, user: dict = Depends(get_current_user)):
    conn = get_db()
    if not data.card_ids:
        conn.close()
        return []
    placeholders = ",".join("?" * len(data.card_ids))
    cards = conn.execute(
        f"SELECT id as card_id, question, answer, category_code FROM cards WHERE id IN ({placeholders})",
        data.card_ids
    ).fetchall()
    wrong_cards = [dict(c) for c in cards]

    docs_raw = conn.execute(
        "SELECT id as doc_id, title FROM documents WHERE package_id=?",
        (data.package_id,)
    ).fetchall()

    documents = []
    for doc in docs_raw:
        chunks = conn.execute(
            "SELECT id as chunk_id, chunk_index, text FROM document_chunks WHERE document_id=? ORDER BY chunk_index",
            (doc["doc_id"],)
        ).fetchall()
        documents.append({
            "doc_id": doc["doc_id"],
            "title":  doc["title"],
            "chunks": [dict(c) for c in chunks],
        })

    conn.close()

    if not documents:
        return {"error": "Keine Dokumente im Paket. Lade zuerst Lerndokumente hoch.", "results": []}

    results = await analyze_mistakes(wrong_cards, documents)
    return {"results": results, "doc_count": len(documents)}

# -- Globale Suche -------------------------------------------------------------

@app.get("/api/search")
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

# -- Lernpfade (Kapitel-basiert) -----------------------------------------------

class ChapterCreate(BaseModel):
    title:          str
    description:    Optional[str]  = None
    document_ids:   Optional[list] = []
    card_ids:       Optional[list] = []
    pass_threshold: Optional[float] = 0.7
    sort_order:     Optional[int]  = 0

class ChapterUpdate(BaseModel):
    title:          Optional[str]   = None
    description:    Optional[str]   = None
    document_ids:   Optional[list]  = None
    card_ids:       Optional[list]  = None
    pass_threshold: Optional[float] = None
    sort_order:     Optional[int]   = None

@app.get("/api/packages/{pkg_id}/paths")
def get_paths(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM learning_paths WHERE package_id=? ORDER BY sort_order, id", (pkg_id,)).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

@app.post("/api/paths")
def create_path(data: PathCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO learning_paths (package_id,name,description,sort_order) VALUES (?,?,?,?)",
        (data.package_id, data.name, data.description, 0)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM learning_paths ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row_to_dict(row)

@app.get("/api/paths/{path_id}")
def get_path_detail(path_id: int, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    path = conn.execute("SELECT * FROM learning_paths WHERE id=?", (path_id,)).fetchone()
    if not path:
        conn.close()
        raise HTTPException(404)
    chapters = conn.execute(
        "SELECT * FROM path_chapters WHERE path_id=? ORDER BY sort_order, id", (path_id,)
    ).fetchall()
    result = row_to_dict(path)
    result["chapters"] = []
    for ch in chapters:
        ch_dict = row_to_dict(ch)
        # Fortschritt berechnen aus card_stats
        cids = ch_dict.get("card_ids", [])
        if cids:
            pl = ",".join("?" * len(cids))
            mastered = conn.execute(
                f"SELECT COUNT(*) FROM card_stats WHERE user_id=? AND card_id IN ({pl}) AND times_correct > 0",
                [uid] + cids
            ).fetchone()[0]
            ch_dict["progress"] = mastered / len(cids) if cids else 0
            ch_dict["mastered"] = mastered
            ch_dict["total_cards"] = len(cids)
        else:
            ch_dict["progress"] = 0
            ch_dict["mastered"] = 0
            ch_dict["total_cards"] = 0
        ch_dict["passed"] = ch_dict["progress"] >= (ch_dict.get("pass_threshold") or 0.7)
        result["chapters"].append(ch_dict)
    conn.close()
    return result

@app.post("/api/paths/{path_id}/chapters")
def add_chapter(path_id: int, data: ChapterCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO path_chapters (path_id,sort_order,title,description,document_ids,card_ids,pass_threshold) VALUES (?,?,?,?,?,?,?)",
        (path_id, data.sort_order, data.title, data.description,
         json.dumps(data.document_ids or []), json.dumps(data.card_ids or []), data.pass_threshold)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM path_chapters ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row_to_dict(row)

@app.put("/api/chapters/{chapter_id}")
def update_chapter(chapter_id: int, data: ChapterUpdate, user: dict = Depends(get_current_user)):
    conn = get_db()
    ch = conn.execute("SELECT * FROM path_chapters WHERE id=?", (chapter_id,)).fetchone()
    if not ch:
        conn.close()
        raise HTTPException(404)
    updates = {}
    if data.title is not None:          updates["title"] = data.title
    if data.description is not None:    updates["description"] = data.description
    if data.document_ids is not None:   updates["document_ids"] = json.dumps(data.document_ids)
    if data.card_ids is not None:       updates["card_ids"] = json.dumps(data.card_ids)
    if data.pass_threshold is not None: updates["pass_threshold"] = data.pass_threshold
    if data.sort_order is not None:     updates["sort_order"] = data.sort_order
    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE path_chapters SET {sets} WHERE id=?", list(updates.values()) + [chapter_id])
        conn.commit()
    row = conn.execute("SELECT * FROM path_chapters WHERE id=?", (chapter_id,)).fetchone()
    conn.close()
    return row_to_dict(row)

@app.delete("/api/chapters/{chapter_id}")
def delete_chapter(chapter_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM path_chapters WHERE id=?", (chapter_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/paths/{path_id}")
def delete_path(path_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM path_chapters WHERE path_id=?", (path_id,))
    conn.execute("DELETE FROM learning_paths WHERE id=?", (path_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

# -- Erklaerungen -------------------------------------------------------------

@app.post("/api/ai/explain")
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
    result = await explain_card(
        card["question"], card["answer"],
        doc_context=doc_ctx, package_name=pkg_name
    )
    return {"explanation": result or ""}

# -- Abzeichen mit Levelsystem -------------------------------------------------

# Farben: Weiß(0) Gelb(1) Grün(2) Blau(3) Rot(4) Schwarz(5) Bronze(6) Silber(7) Gold(8) Platin(9)
# Pro Farbe 3 Sterne -> 30 Stufen total
_BELT_COLORS = [
    {"name":"Weiß",    "hex":"#aaaaaa"},
    {"name":"Gelb",    "hex":"#f0c040"},
    {"name":"Grün",    "hex":"#40b060"},
    {"name":"Blau",    "hex":"#4080e0"},
    {"name":"Rot",     "hex":"#e04040"},
    {"name":"Schwarz", "hex":"#404040"},
    {"name":"Bronze",  "hex":"#cd7f32"},
    {"name":"Silber",  "hex":"#c0c0c0"},
    {"name":"Gold",    "hex":"#ffd700"},
    {"name":"Platin",  "hex":"#b0b8d0"},
]

_ACHIEVEMENTS = [
    {"id":"sessions",  "name":"Ausdauer",       "desc":"Sessions absolviert",            "icon":"fa-dumbbell",
     "thresholds":[1,3,5,10,15,25,40,60,100,150,200,300,400,500,750,1000,1500,2000,2500,3000,4000,5000,6000,8000,10000,12000,15000,18000,22000,25000]},
    {"id":"correct",   "name":"Wissenssammler",  "desc":"Richtige Antworten",             "icon":"fa-brain",
     "thresholds":[5,15,30,50,100,200,350,500,750,1000,1500,2000,3000,4500,6000,8000,10000,13000,16000,20000,25000,30000,40000,50000,65000,80000,100000,125000,150000,200000]},
    {"id":"streak",    "name":"Serie",           "desc":"Längste Korrekt-Serie",          "icon":"fa-fire",
     "thresholds":[3,5,7,10,15,20,25,30,40,50,60,75,90,100,120,150,175,200,250,300,350,400,500,600,700,800,900,1000,1200,1500]},
    {"id":"cards",     "name":"Entdecker",       "desc":"Verschiedene Karten gesehen",    "icon":"fa-compass",
     "thresholds":[5,10,20,30,50,75,100,150,200,300,400,500,650,800,1000,1250,1500,2000,2500,3000,4000,5000,6500,8000,10000,12500,15000,18000,22000,25000]},
    {"id":"perfect",   "name":"Makellos",        "desc":"Perfekte Sessions (100%)",       "icon":"fa-trophy",
     "thresholds":[1,2,3,5,8,12,18,25,35,50,65,80,100,130,170,220,280,350,450,550,700,850,1000,1200,1500,1800,2200,2700,3300,4000]},
    {"id":"days",      "name":"Beständig",       "desc":"Tage mit Lernaktivität",         "icon":"fa-calendar-check",
     "thresholds":[1,3,5,7,14,21,30,45,60,90,120,150,180,220,270,330,400,500,600,730,900,1100,1300,1500,1800,2200,2600,3000,3500,4000]},
]

# Stern-Farben: Bronze/Silber/Gold je nach Stern-Nummer
_STAR_COLORS = ["#cd7f32", "#c0c0c0", "#ffd700"]  # 1=Bronze, 2=Silber, 3=Gold

def _calc_level(value: int, thresholds: list[int]) -> dict:
    level = 0
    for t in thresholds:
        if value >= t:
            level += 1
        else:
            break
    if level == 0:
        return {"level":0, "stars":0, "color_idx":0, "color":_BELT_COLORS[0],
                "star_colors":[], "next_at":thresholds[0] if thresholds else 0}
    color_idx = min((level - 1) // 3, 9)
    stars = ((level - 1) % 3) + 1
    next_at = thresholds[level] if level < len(thresholds) else None
    star_colors = [_STAR_COLORS[i] for i in range(stars)]
    return {"level":level, "stars":stars, "color_idx":color_idx, "color":_BELT_COLORS[color_idx],
            "star_colors":star_colors, "next_at":next_at}

@app.get("/api/achievements")
def get_achievements(user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    sessions = conn.execute("SELECT COUNT(*) FROM sessions WHERE ended_at IS NOT NULL AND user_id=?", (uid,)).fetchone()[0]
    correct  = conn.execute("SELECT COUNT(*) FROM reviews WHERE result='correct' AND user_id=?", (uid,)).fetchone()[0]
    max_str  = conn.execute("SELECT COALESCE(MAX(streak),0) FROM card_stats WHERE user_id=?", (uid,)).fetchone()[0]
    seen     = conn.execute("SELECT COUNT(*) FROM card_stats WHERE times_shown>0 AND user_id=?", (uid,)).fetchone()[0]
    perfect  = conn.execute("""
        SELECT COUNT(*) FROM sessions
        WHERE ended_at IS NOT NULL AND user_id=? AND total_cards>0 AND correct=total_cards
    """, (uid,)).fetchone()[0]
    days     = conn.execute("""
        SELECT COUNT(DISTINCT date(reviewed_at)) FROM reviews WHERE user_id=?
    """, (uid,)).fetchone()[0]
    conn.close()

    values = {"sessions":sessions, "correct":correct, "streak":max_str, "cards":seen, "perfect":perfect, "days":days}
    result = []
    for a in _ACHIEVEMENTS:
        val = values.get(a["id"], 0)
        lvl = _calc_level(val, a["thresholds"])
        result.append({
            "id":     a["id"],
            "name":   a["name"],
            "desc":   a["desc"],
            "icon":   a["icon"],
            "value":  val,
            **lvl,
        })
    return result

@app.get("/api/achievements/levels")
def get_achievement_levels():
    """Gibt die komplette Stufentabelle zurück (für Admin-Ansicht)."""
    result = []
    for a in _ACHIEVEMENTS:
        levels = []
        for i, t in enumerate(a["thresholds"]):
            color_idx = min(i // 3, 9)
            stars = (i % 3) + 1
            levels.append({"level":i+1, "threshold":t, "stars":stars, "color":_BELT_COLORS[color_idx]["name"], "hex":_BELT_COLORS[color_idx]["hex"]})
        result.append({"id":a["id"], "name":a["name"], "desc":a["desc"], "icon":a["icon"], "levels":levels})
    return result

@app.get("/api/history")
def get_history(limit: int = 30, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, p.name as package_name, p.color as package_color, p.icon as package_icon
        FROM sessions s
        LEFT JOIN packages p ON p.id=s.package_id
        WHERE s.ended_at IS NOT NULL AND s.user_id=?
        ORDER BY s.started_at DESC LIMIT ?
    """, (uid, limit)).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

# -- Paket exportieren (ZIP mit Fragen + Antworten Markdown) ------------------

@app.get("/api/packages/{pkg_id}/export")
def export_package(pkg_id: int, token: str = Query(None), user: dict = Depends(get_current_user)):
    import io, zipfile
    conn = get_db()
    pkg = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    if not pkg:
        conn.close()
        raise HTTPException(404, "Paket nicht gefunden")

    cards = conn.execute(
        "SELECT card_id, category_code, question, answer, hint, difficulty FROM cards WHERE package_id=? AND active=1 ORDER BY card_id",
        (pkg_id,)
    ).fetchall()
    conn.close()

    if not cards:
        raise HTTPException(400, "Paket hat keine Karten zum Exportieren")

    pkg_name = pkg["name"]
    slug = re.sub(r'[^a-z0-9]+', '-', pkg_name.lower()).strip('-')

    # Fragen-Markdown
    fragen_lines = [f"# {pkg_name} -- Fragen\n"]
    for c in cards:
        fragen_lines.append("---\n")
        fragen_lines.append(f"```\n{c['card_id']} | {c['category_code']}\n{c['question']}\n```\n")
    fragen_md = "\n".join(fragen_lines)

    # Antworten-Markdown
    antworten_lines = [f"# {pkg_name} -- Antworten\n"]
    for c in cards:
        antworten_lines.append("---\n")
        answer_text = c["answer"]
        if c["hint"]:
            answer_text += f"\n\nHinweis: {c['hint']}"
        aid = c["card_id"].replace("K-", "A-")
        antworten_lines.append(f"```\n{aid} | {c['category_code']} -> {c['card_id']}\n{answer_text}\n```\n")
    antworten_md = "\n".join(antworten_lines)

    # Bundle-Metadaten für Re-Import
    cat_counts = {}
    for c in cards:
        cat_counts[c["category_code"]] = cat_counts.get(c["category_code"], 0) + 1

    bundle_meta = json.dumps([{
        "id": slug,
        "name": pkg_name,
        "description": pkg["description"] or "",
        "color": pkg["color"],
        "icon": pkg["icon"],
        "version": "1.0",
        "fragen_file": f"{slug}-fragen.md",
        "antwort_file": f"{slug}-antworten.md",
        "card_count": len(cards),
        "categories": cat_counts,
    }], ensure_ascii=False, indent=2)

    # ZIP erstellen
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}-fragen.md", fragen_md)
        zf.writestr(f"{slug}-antworten.md", antworten_md)
        zf.writestr("bundles.json", bundle_meta)
    buf.seek(0)

    filename = f"{slug}-v1.0.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# -- Paket zurückziehen (saubere Deinstallation) ------------------------------

@app.delete("/api/packages/{pkg_id}/uninstall")
def uninstall_package(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    pkg = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    if not pkg:
        conn.close()
        raise HTTPException(404, "Paket nicht gefunden")

    stats = {}

    # 1. Lernstatistik bleibt erhalten (gelernt ist gelernt)
    #    card_stats und reviews werden NICHT gelöscht.
    #    Bei Re-Import mit gleichen card_ids werden sie automatisch verknüpft.

    # 2. Alle Karten löschen
    r = conn.execute("DELETE FROM cards WHERE package_id=?", (pkg_id,))
    stats["cards_deleted"] = r.rowcount

    # 3. Hochgeladene Dokumente: Dateien löschen
    docs = conn.execute(
        "SELECT id, filename FROM documents WHERE package_id=?", (pkg_id,)
    ).fetchall()
    files_deleted = 0
    for doc in docs:
        fpath = UPLOAD_DIR / doc["filename"]
        if fpath.exists():
            fpath.unlink()
            files_deleted += 1
    stats["files_deleted"] = files_deleted

    # 4. Dokumente aus DB löschen
    doc_ids = [d["id"] for d in docs]
    if doc_ids:
        pl = ",".join("?" * len(doc_ids))
        conn.execute(f"DELETE FROM document_chunks WHERE document_id IN ({pl})", doc_ids)
    r = conn.execute("DELETE FROM documents WHERE package_id=?", (pkg_id,))
    stats["documents_deleted"] = r.rowcount

    # 5. Entwürfe löschen
    r = conn.execute("DELETE FROM card_drafts WHERE package_id=?", (pkg_id,))
    stats["drafts_deleted"] = r.rowcount

    # 6. Lexikon-Einträge löschen
    try:
        r = conn.execute("DELETE FROM lexicon WHERE package_id=?", (pkg_id,))
        stats["lexicon_deleted"] = r.rowcount
    except Exception:
        stats["lexicon_deleted"] = 0

    # 7. Lernpfade löschen
    try:
        r = conn.execute("DELETE FROM learning_paths WHERE package_id=?", (pkg_id,))
        stats["paths_deleted"] = r.rowcount
    except Exception:
        stats["paths_deleted"] = 0

    # 8. FTS-Index aktualisieren
    try:
        _rebuild_fts(conn)
    except Exception:
        pass

    # 9. Sessions entkoppeln (Statistik bleibt, Paket-Referenz wird entfernt)
    conn.execute("UPDATE sessions SET package_id=NULL WHERE package_id=?", (pkg_id,))

    # 10. Paket selbst löschen
    conn.execute("DELETE FROM packages WHERE id=?", (pkg_id,))
    conn.commit()
    conn.close()

    stats["package_name"] = pkg["name"]
    stats["ok"] = True
    return stats


@app.post("/api/packages/{pkg_id}/reinstall")
def reinstall_package(pkg_id: int, bundle_id: str = None, user: dict = Depends(get_current_user)):
    conn = get_db()
    pkg = conn.execute("SELECT name FROM packages WHERE id=?", (pkg_id,)).fetchone()
    conn.close()

    if not pkg:
        raise HTTPException(404, "Paket nicht gefunden")

    uninstall_package(pkg_id, user)

    if not bundle_id:
        raise HTTPException(400, "bundle_id erforderlich für Reinstall")

    return install_bundle(bundle_id, user)


# -- Bundles (vorgefertigte Lernpakete) ----------------------------------------

BUNDLES_PATH = Path(os.environ.get("BUNDLES_PATH", str(Path(__file__).parent.parent / "lernpakete")))

@app.get("/api/bundles")
def list_bundles(user: dict = Depends(get_current_user)):
    meta_file = BUNDLES_PATH / "bundles.json"
    if not meta_file.exists():
        return []
    bundles = json.loads(meta_file.read_text())
    conn = get_db()
    installed = {r[0] for r in conn.execute(
        "SELECT name FROM packages"
    ).fetchall()}
    conn.close()
    for b in bundles:
        b["installed"] = b["name"] in installed
    return bundles

@app.post("/api/bundles/{bundle_id}/install")
def install_bundle(bundle_id: str, user: dict = Depends(get_current_user)):
    meta_file = BUNDLES_PATH / "bundles.json"
    if not meta_file.exists():
        raise HTTPException(404, "bundles.json nicht gefunden")

    bundles = json.loads(meta_file.read_text())
    bundle  = next((b for b in bundles if b["id"] == bundle_id), None)
    if not bundle:
        raise HTTPException(404, f"Bundle '{bundle_id}' nicht gefunden")

    fragen_file  = BUNDLES_PATH / bundle["fragen_file"]
    antwort_file = BUNDLES_PATH / bundle["antwort_file"]

    if not fragen_file.exists() or not antwort_file.exists():
        raise HTTPException(500, "Bundle-Dateien fehlen auf dem Server")

    fragen   = fragen_file.read_text()
    antworten = antwort_file.read_text()

    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM packages WHERE name=?", (bundle["name"],)
    ).fetchone()

    if existing:
        pkg_id = existing["id"]
    else:
        conn.execute(
            "INSERT INTO packages (name,description,color,icon) VALUES (?,?,?,?)",
            (bundle["name"], bundle.get("description",""), bundle.get("color","#2196F3"), bundle.get("icon","fa-graduation-cap"))
        )
        conn.commit()
        pkg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.close()

    import_result = import_markdown_internal(fragen, antworten, pkg_id)

    return {
        "ok":        True,
        "package_id":pkg_id,
        "name":      bundle["name"],
        "created":   import_result["created"],
        "skipped":   import_result["skipped"],
        "total":     import_result["total"],
    }

def import_markdown_internal(fragen: str, antworten: str, package_id: int) -> dict:
    card_pat = re.compile(r"```\s*\n(K-\w+)\s*\|\s*(\w+)\s*\n([\s\S]*?)```", re.MULTILINE)
    ans_pat  = re.compile(r"```\s*\n(A-\w+)\s*\|[^\n]*\n([\s\S]*?)```",         re.MULTILINE)
    questions = {m.group(1): (m.group(2).strip(), m.group(3).strip()) for m in card_pat.finditer(fragen)}
    answers   = {m.group(1).replace("A-","K-"): m.group(2).strip() for m in ans_pat.finditer(antworten)}
    conn = get_db()
    created = skipped = 0
    for card_id, (cat, question) in questions.items():
        answer = answers.get(card_id, "")
        if not answer:
            skipped += 1
            continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO cards (card_id,package_id,category_code,question,answer) VALUES (?,?,?,?,?)",
                (card_id, package_id, cat, question.strip(), answer.strip())
            )
            created += 1
        except Exception:
            skipped += 1
    conn.commit()
    _rebuild_fts(conn)
    conn.close()
    return {"created": created, "skipped": skipped, "total": len(questions)}


# -- ZIP-Import ----------------------------------------------------------------

@app.post("/api/import/zip")
async def import_zip(
    file:       UploadFile = File(...),
    package_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    import zipfile, io

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, "Nur ZIP-Dateien erlaubt")

    data = await file.read()

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Ungueltige ZIP-Datei")

    names = zf.namelist()

    fragen_name  = next((n for n in names if "fragen"   in n.lower() and n.endswith(".md")), None)
    antwort_name = next((n for n in names if "antwort"  in n.lower() and n.endswith(".md")), None)

    if not fragen_name or not antwort_name:
        mds = [n for n in names if n.endswith(".md") and not n.lower().startswith("readme")]
        if len(mds) >= 2:
            fragen_name  = mds[0]
            antwort_name = mds[1]

    if not fragen_name or not antwort_name:
        raise HTTPException(400, f"Keine Fragen/Antworten .md Dateien im ZIP gefunden. Gefunden: {names}")

    fragen    = zf.read(fragen_name).decode("utf-8")
    antworten = zf.read(antwort_name).decode("utf-8")

    if not package_id:
        raw = file.filename.replace(".zip","")
        raw = re.sub(r'[-_]v[\d.]+$', '', raw, flags=re.IGNORECASE)
        raw = re.sub(r'^lernpakete[-_]?', '', raw, flags=re.IGNORECASE)
        pkg_name = raw.replace("-"," ").replace("_"," ").strip().title()
        if not pkg_name:
            pkg_name = "Importiertes Paket"

        conn = get_db()
        existing = conn.execute("SELECT id FROM packages WHERE name=?", (pkg_name,)).fetchone()
        if existing:
            package_id = existing["id"]
        else:
            conn.execute(
                "INSERT INTO packages (name,color,icon) VALUES (?,?,?)",
                (pkg_name, "#2196F3", "fa-graduation-cap")
            )
            conn.commit()
            package_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

    result = import_markdown_internal(fragen, antworten, package_id)
    result["package_id"] = package_id

    # Lernmaterial-Dateien als Dokumente importieren
    skip_names = {fragen_name, antwort_name}
    doc_exts = (".md", ".txt", ".pdf", ".docx")
    doc_files = [
        n for n in names
        if n not in skip_names
        and not n.lower().startswith("readme")
        and not n.lower().endswith("bundles.json")
        and any(n.lower().endswith(ext) for ext in doc_exts)
        and not n.startswith("__")
        and not n.startswith(".")
    ]

    docs_imported = 0
    for doc_name in doc_files:
        content = zf.read(doc_name)
        filename = doc_name.split("/")[-1]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        text = extract_text_from_file(content, ext)
        if not text.strip():
            continue
        chunks = chunk_text(text)
        doc_title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()
        conn = get_db()
        conn.execute(
            "INSERT INTO documents (package_id,filename,title,filetype,filesize,chunk_count,status) VALUES (?,?,?,?,?,?,?)",
            (package_id, filename, doc_title, ext, len(content), len(chunks), "ready")
        )
        doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for i, ch in enumerate(chunks):
            conn.execute(
                "INSERT INTO document_chunks (document_id,chunk_index,text) VALUES (?,?,?)",
                (doc_id, i, ch)
            )
        conn.commit()
        conn.close()
        docs_imported += 1

    result["docs_imported"] = docs_imported
    return result


# -- Markdown Import -----------------------------------------------------------

@app.post("/api/import/markdown")
def import_markdown(data: MarkdownImport, user: dict = Depends(get_current_user)):
    card_pat = re.compile(r"```\s*\n(K-\d+)\s*\|\s*(\w+)\s*\n([\s\S]*?)```", re.MULTILINE)
    ans_pat  = re.compile(r"```\s*\n(A-\d+)\s*\|[^\n]*\n([\s\S]*?)```",       re.MULTILINE)
    questions = {m.group(1): (m.group(2).strip(), m.group(3).strip()) for m in card_pat.finditer(data.fragen)}
    answers   = {m.group(1).replace("A-","K-"): m.group(2).strip() for m in ans_pat.finditer(data.antworten)}
    conn = get_db()
    created = skipped = 0
    for card_id, (cat, question) in questions.items():
        answer = answers.get(card_id,"")
        if not answer:
            skipped += 1; continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO cards (card_id,package_id,category_code,question,answer) VALUES (?,?,?,?,?)",
                (card_id, data.package_id, cat, question.strip(), answer.strip())
            )
            created += 1
        except Exception:
            skipped += 1
    conn.commit()
    _rebuild_fts(conn)
    conn.close()
    return {"created": created, "skipped": skipped, "total": len(questions)}
