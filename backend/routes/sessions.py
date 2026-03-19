"""routes/sessions.py -- Start, End, Active, Reviews, History, Achievements."""

from __future__ import annotations
import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from db import get_db, row_to_dict
from auth import get_current_user
from schemas import SessionCreate, ReviewSubmit, MistakeAnalysisRequest
from services import evaluate_answer

router = APIRouter(tags=["sessions"])


@router.post("/api/sessions")
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


@router.get("/api/sessions/active")
def get_active_session(user: dict = Depends(get_current_user)):
    """Gibt die aktive (nicht beendete) Session des Users zurueck, falls vorhanden."""
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


@router.delete("/api/sessions/active")
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


@router.post("/api/sessions/{session_id}/end")
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


@router.post("/api/reviews")
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


# -- Lernfehler-Analyse -------------------------------------------------------

@router.post("/api/learn/analyze-mistakes")
async def analyze_learning_mistakes(data: MistakeAnalysisRequest, user: dict = Depends(get_current_user)):
    from services import analyze_mistakes
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


# -- History -------------------------------------------------------------------

@router.get("/api/history")
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


# -- Abzeichen mit Levelsystem -------------------------------------------------

# Farben: Weiss(0) Gelb(1) Gruen(2) Blau(3) Rot(4) Schwarz(5) Bronze(6) Silber(7) Gold(8) Platin(9)
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


@router.get("/api/achievements")
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


@router.get("/api/achievements/levels")
def get_achievement_levels():
    """Gibt die komplette Stufentabelle zurueck (fuer Admin-Ansicht)."""
    result = []
    for a in _ACHIEVEMENTS:
        levels = []
        for i, t in enumerate(a["thresholds"]):
            color_idx = min(i // 3, 9)
            stars = (i % 3) + 1
            levels.append({"level":i+1, "threshold":t, "stars":stars, "color":_BELT_COLORS[color_idx]["name"], "hex":_BELT_COLORS[color_idx]["hex"]})
        result.append({"id":a["id"], "name":a["name"], "desc":a["desc"], "icon":a["icon"], "levels":levels})
    return result
