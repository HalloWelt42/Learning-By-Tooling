"""routes/sessions.py -- Start, End, Active, Reviews, History, Achievements."""

from __future__ import annotations
import json
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from db import get_db, row_to_dict
from auth import get_current_user
from schemas import SessionCreate, ReviewSubmit, SessionReviewNext, MistakeAnalysisRequest
from services import evaluate_answer, sm2_update

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
        "INSERT INTO sessions (user_id,mode,package_id,category_filter,total_cards,card_order,current_index) VALUES (?,?,?,?,?,?,0)",
        (uid, data.mode, pkg_id_val, json.dumps(data.category_filter), len(card_ids), json.dumps(card_ids))
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
    correct = sum(1 for r in reviews if r["result"] == "correct")
    wrong = sum(1 for r in reviews if r["result"] == "wrong")
    skipped = sum(1 for r in reviews if r["result"] == "skip")

    # card_order aus DB nutzen (strikte Session)
    card_order = json.loads(session["card_order"] or "[]")
    current_index = session["current_index"] or 0

    conn.close()
    return {
        "session_id": session["id"],
        "mode": session["mode"],
        "package_id": session["package_id"],
        "total": session["total_cards"],
        "reviewed": len(reviews),
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "card_order": card_order,
        "current_index": current_index,
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
        "SELECT COUNT(*) as t, SUM(result='correct') as c, SUM(result='wrong') as w, SUM(result='skip') as sk FROM reviews WHERE session_id=? AND user_id=?",
        (session_id, uid)
    ).fetchone()
    total_answered = (s["c"] or 0) + (s["w"] or 0)
    session_row = conn.execute("SELECT total_cards FROM sessions WHERE id=? AND user_id=?", (session_id, uid)).fetchone()
    total_cards = session_row["total_cards"] if session_row else 0

    conn.execute(
        "UPDATE sessions SET ended_at=?, correct=?, skipped=? WHERE id=? AND user_id=?",
        (datetime.now().isoformat(), s["c"] or 0, s["sk"] or 0, session_id, uid)
    )

    # -- Completion-Bonus (Silber) --
    # 20 Extra nur wenn alle mindestens 20 Karten FEHLERFREI geloest
    # 1 Extra wenn mindestens 5 Karten beantwortet (egal ob richtig/falsch)
    correct_count = s["c"] or 0
    wrong_count = s["w"] or 0
    bonus = 0
    if total_answered >= 20 and wrong_count == 0 and correct_count >= total_cards:
        bonus = 20
    elif total_answered >= 5:
        bonus = 1

    if bonus > 0:
        today_str = date.today().isoformat()
        conn.execute("""
            INSERT INTO user_xp (user_id, xp_total, xp_today, last_xp_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                xp_total = xp_total + ?,
                xp_today = CASE WHEN last_xp_date = ? THEN xp_today + ? ELSE ? END,
                last_xp_date = ?
        """, (uid, bonus, bonus, today_str, bonus, today_str, bonus, bonus, today_str))

    conn.commit()
    conn.close()
    return {"ok": True, "correct": s["c"] or 0, "total": s["t"], "bonus": bonus}


# -- Strikte Session-Steuerung ------------------------------------------------

def _load_card_data(conn, card_id: str) -> Optional[dict]:
    """Laedt eine Karte als dict oder None."""
    row = conn.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone()
    return row_to_dict(row) if row else None


def _session_progress(conn, session_id: int, uid: int, session: dict) -> dict:
    """Berechnet Fortschritt einer Session."""
    reviews = conn.execute(
        "SELECT card_id, result FROM reviews WHERE session_id=? AND user_id=?",
        (session_id, uid)
    ).fetchall()
    correct = sum(1 for r in reviews if r["result"] == "correct")
    wrong   = sum(1 for r in reviews if r["result"] == "wrong")
    skipped = sum(1 for r in reviews if r["result"] == "skip")
    return {
        "reviewed": len(reviews),
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "total": session["total_cards"],
    }


@router.get("/api/sessions/{session_id}/current-card")
def get_current_card(session_id: int, user: dict = Depends(get_current_user)):
    """Gibt die aktuelle Karte der Session zurueck (Backend-gesteuert)."""
    uid = user["id"]
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id=? AND user_id=?", (session_id, uid)
    ).fetchone()
    if not session:
        conn.close()
        raise HTTPException(404, "Session nicht gefunden")
    if session["ended_at"]:
        conn.close()
        return {"done": True, "card": None, "progress": None}

    card_order = json.loads(session["card_order"] or "[]")
    idx = session["current_index"] or 0

    if idx >= len(card_order):
        conn.close()
        return {"done": True, "card": None, "progress": None}

    card = _load_card_data(conn, card_order[idx])
    progress = _session_progress(conn, session_id, uid, session)
    progress["current_index"] = idx
    conn.close()
    return {
        "done": False,
        "card": card,
        "progress": progress,
        "mode": session["mode"],
        "package_id": session["package_id"],
    }


@router.post("/api/sessions/{session_id}/review-and-next")
async def review_and_next(session_id: int, data: SessionReviewNext, user: dict = Depends(get_current_user)):
    """Bewertet die aktuelle Karte und gibt die naechste zurueck.
    Ein einziger Endpoint fuer den gesamten Session-Ablauf."""
    uid = user["id"]
    conn = get_db()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id=? AND user_id=?", (session_id, uid)
    ).fetchone()
    if not session:
        conn.close()
        raise HTTPException(404, "Session nicht gefunden")
    if session["ended_at"]:
        conn.close()
        raise HTTPException(400, "Session bereits beendet")

    card_order = json.loads(session["card_order"] or "[]")
    idx = session["current_index"] or 0
    if idx >= len(card_order):
        conn.close()
        raise HTTPException(400, "Keine Karten mehr in dieser Session")

    current_card_id = card_order[idx]
    card = conn.execute("SELECT * FROM cards WHERE card_id=?", (current_card_id,)).fetchone()

    # -- KI-Bewertung (Freitext mit KI) --
    ai_score = ai_feedback = None
    result = data.result
    if data.use_ai and data.user_answer and card:
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

    # -- Review speichern (mit Antwortzeit) --
    time_ms = max(0, data.time_ms or 0)
    conn.execute(
        "INSERT INTO reviews (user_id,session_id,card_id,result,user_answer,ai_score,ai_feedback,time_ms) VALUES (?,?,?,?,?,?,?,?)",
        (uid, session_id, current_card_id, result, data.user_answer, ai_score, ai_feedback, time_ms)
    )

    # -- Qualitaets-Score: KI-Score oder 1.0/0.0 basierend auf Ergebnis --
    quality = ai_score if ai_score is not None else (1.0 if result == "correct" else 0.0 if result == "wrong" else 0.5)

    # -- card_stats aktualisieren (inkl. avg_quality, avg_time_ms) --
    conn.execute("""
        INSERT INTO card_stats (user_id,card_id,times_shown,times_correct,times_wrong,last_reviewed,streak,avg_quality,avg_time_ms)
        VALUES (?,?,1,?,?,?,?,?,?)
        ON CONFLICT(user_id,card_id) DO UPDATE SET
            times_shown=times_shown+1,
            times_correct=times_correct+excluded.times_correct,
            times_wrong=times_wrong+excluded.times_wrong,
            last_reviewed=excluded.last_reviewed,
            streak=CASE WHEN excluded.times_correct=1 THEN streak+1 ELSE 0 END,
            avg_quality=ROUND((avg_quality * (times_shown - 1) + ?) / times_shown, 3),
            avg_time_ms=CASE WHEN ?> 0 THEN ROUND((avg_time_ms * (times_shown - 1) + ?) / times_shown) ELSE avg_time_ms END
    """, (uid, current_card_id, 1 if result=="correct" else 0, 1 if result=="wrong" else 0,
          datetime.now().isoformat(), 1 if result=="correct" else 0, quality, time_ms,
          quality, time_ms, time_ms))

    # -- SRS-Update falls gewuenscht --
    if data.srs_quality is not None:
        stat = conn.execute(
            "SELECT ease_factor, interval_days, COALESCE(times_correct,0) as reps FROM card_stats WHERE user_id=? AND card_id=?",
            (uid, current_card_id)
        ).fetchone()
        if stat:
            new_ease, new_interval, new_reps = sm2_update(
                stat["ease_factor"], stat["interval_days"], stat["reps"], data.srs_quality
            )
            due = (date.today() + timedelta(days=new_interval)).isoformat()
            conn.execute(
                "UPDATE card_stats SET ease_factor=?, interval_days=?, due_date=? WHERE user_id=? AND card_id=?",
                (new_ease, new_interval, due, uid, current_card_id)
            )

    # -- Index vorruecken --
    next_idx = idx + 1
    conn.execute(
        "UPDATE sessions SET current_index=? WHERE id=?", (next_idx, session_id)
    )

    # -- XP berechnen (didaktisch fundiert, siehe .claude/xp-strategie.md) --
    #
    # Standard/SRS = Lernmodus: Fleiß belohnen, richtig UND falsch = gleiche Basis.
    # MC/Write = Testmodus: Nur korrekte Antworten bekommen volle XP,
    #   falsche Antworten bekommen nichts (man konnte nicht nachschauen).
    # Durchklicken (< 3s) wird stillschweigend nicht gewertet.

    session_mode = session["mode"] or "standard"
    is_test_mode = session_mode in ("mc", "write")

    # Anti-Gaming: unter 3 Sekunden = stillschweigend 0 XP (Durchklick-Schutz)
    if time_ms > 0 and time_ms < 3000 and result != "skip":
        xp_earned = 0
    elif is_test_mode and result != "correct":
        # Testmodus: nur korrekte Antworten werden belohnt
        xp_earned = 1 if result == "wrong" else 0  # Falsch = 1 Trostpunkt, Skip = 0
    else:
        # Lernmodus: Fleiß belohnen, nicht Ergebnis bestrafen
        base_xp = 10 if result in ("correct", "wrong") else 1  # Skip = 1

        # 2a) Karten-Schwierigkeit (aus der Karten-Definition: 1=Leicht, 2=Mittel, 3=Schwer)
        card_row = conn.execute(
            "SELECT difficulty FROM cards WHERE card_id=?", (current_card_id,)
        ).fetchone()
        card_difficulty = card_row["difficulty"] if card_row and card_row["difficulty"] else 2
        # Leicht=0.7x, Mittel=1.0x, Schwer=1.4x
        card_diff_mult = {1: 0.7, 2: 1.0, 3: 1.4}.get(card_difficulty, 1.0)

        # 2b) Persoenlicher Schwierigkeitsfaktor: basiert auf Ease-Faktor (SM-2)
        cs_row = conn.execute(
            "SELECT ease_factor, interval_days, streak FROM card_stats WHERE user_id=? AND card_id=?",
            (uid, current_card_id)
        ).fetchone()
        ease = cs_row["ease_factor"] if cs_row and cs_row["ease_factor"] else 2.5
        interval_days = cs_row["interval_days"] if cs_row and cs_row["interval_days"] else 0
        card_streak = cs_row["streak"] if cs_row and cs_row["streak"] else 0
        personal_diff = round(2.8 / max(ease, 1.3), 2)

        # Kombinierter Schwierigkeitsfaktor
        difficulty_factor = round(card_diff_mult * personal_diff, 2)

        # 3) Modusfaktor: Testen (Freitext/MC) > Lernen (SRS/Standard)
        #    Lernen = Antwort aufdecken, Testen = aus dem Kopf antworten
        mode_factors = {"write": 1.5, "mc": 1.3, "srs": 1.2, "standard": 1.0}
        mode_factor = mode_factors.get(session_mode, 1.0)

        # 4) Fortschrittsfaktor: spaete Reviews belohnen Langzeit-Retention
        if interval_days <= 1:
            progress_factor = 1.0
        elif interval_days <= 7:
            progress_factor = 1.1
        elif interval_days <= 30:
            progress_factor = 1.3
        elif interval_days <= 90:
            progress_factor = 1.5
        else:
            progress_factor = 1.2  # Ueberlernte Karten: leichter Abschlag

        # 5) Streak-Faktor (Combo in der Session)
        streak_mult = min(1.0 + card_streak * 0.05, 2.0)

        # 6) Speed-Bonus: schnelle korrekte Antwort (3-5s Sweet Spot)
        speed_bonus = 5 if result == "correct" and 3000 <= time_ms < 5000 else 0

        # Formel: floor(Basis * SF * MF * FF * Streak) + Speed-Bonus
        xp_earned = max(1, int(base_xp * difficulty_factor * mode_factor * progress_factor * streak_mult) + speed_bonus)

    # XP in user_xp speichern
    today_str = date.today().isoformat()
    conn.execute("""
        INSERT INTO user_xp (user_id, xp_total, xp_today, last_xp_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            xp_total = xp_total + ?,
            xp_today = CASE WHEN last_xp_date = ? THEN xp_today + ? ELSE ? END,
            last_xp_date = ?
    """, (uid, xp_earned, xp_earned, today_str, xp_earned, today_str, xp_earned, xp_earned, today_str))

    # -- Session beenden falls fertig --
    done = next_idx >= len(card_order)
    if done:
        s = conn.execute(
            "SELECT COUNT(*) as t, SUM(result='correct') as c, SUM(result='skip') as sk FROM reviews WHERE session_id=? AND user_id=?",
            (session_id, uid)
        ).fetchone()
        conn.execute(
            "UPDATE sessions SET ended_at=?, correct=?, skipped=? WHERE id=? AND user_id=?",
            (datetime.now().isoformat(), s["c"] or 0, s["sk"] or 0, session_id, uid)
        )

    conn.commit()

    # -- Naechste Karte laden oder Ende --
    next_card = None
    if not done:
        next_card = _load_card_data(conn, card_order[next_idx])

    progress = _session_progress(conn, session_id, uid, dict(session))
    progress["current_index"] = next_idx
    conn.close()

    return {
        "ok": True,
        "result": result,
        "ai_score": ai_score,
        "ai_feedback": ai_feedback,
        "done": done,
        "next_card": next_card,
        "progress": progress,
        "xp_earned": xp_earned,
    }


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
    # Platin (Lv28-30) erreichbar in 2-5 Jahren bei aktivem Lernen (2 Sessions/Tag, 5-6 Tage/Woche)
    {"id":"sessions",  "name":"Ausdauer",       "desc":"Sessions absolviert",            "icon":"fa-dumbbell",
     "thresholds":[1,3,5,10,20,35,50,80,120,175,250,350,500,700,900,1100,1300,1500,1750,2000,2250,2500,2750,3000,3100,3200,3350,3400,3500,3650]},
    {"id":"correct",   "name":"Wissenssammler",  "desc":"Richtige Antworten",             "icon":"fa-brain",
     "thresholds":[5,15,30,60,120,250,500,800,1200,1800,2500,3500,5000,7000,9000,11000,14000,17000,20000,23000,25000,28000,31000,35000,38000,42000,46000,48000,49000,50000]},
    {"id":"streak",    "name":"Serie",           "desc":"Längste Korrekt-Serie",          "icon":"fa-fire",
     "thresholds":[3,5,7,10,12,15,18,20,25,30,35,40,45,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,195,200]},
    {"id":"cards",     "name":"Entdecker",       "desc":"Verschiedene Karten gesehen",    "icon":"fa-compass",
     "thresholds":[5,10,20,35,50,75,100,150,200,300,400,500,650,800,1000,1200,1500,1800,2000,2300,2600,2800,3100,3500,3800,4100,4500,4700,4900,5000]},
    {"id":"perfect",   "name":"Makellos",        "desc":"Perfekte Sessions (100%)",       "icon":"fa-trophy",
     "thresholds":[1,2,3,5,8,12,18,25,35,50,65,80,100,130,170,220,280,350,400,450,500,550,600,700,750,800,900,950,975,1000]},
    {"id":"days",      "name":"Beständig",       "desc":"Tage mit Lernaktivität",         "icon":"fa-calendar-check",
     "thresholds":[1,3,5,7,14,21,30,45,60,90,120,150,180,250,365,450,550,700,800,900,1000,1100,1200,1400,1500,1600,1700,1750,1800,1825]},
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


# -- Streak + Stats ------------------------------------------------------------

@router.get("/api/stats/streak")
def get_streak(user: dict = Depends(get_current_user)):
    """Berechnet aktuelle Tagesstraehne und laengste Straehne."""
    uid = user["id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT date(reviewed_at) as d FROM reviews WHERE user_id=? ORDER BY d DESC",
        (uid,)
    ).fetchall()
    conn.close()

    if not rows:
        return {"current": 0, "longest": 0, "today": False}

    from datetime import date, timedelta
    dates = [date.fromisoformat(r["d"]) for r in rows if r["d"]]
    today = date.today()

    # Aktuelle Straehne: ab heute oder gestern rueckwaerts zaehlen
    current = 0
    check = today
    if dates and dates[0] == today:
        current = 1
        check = today - timedelta(days=1)
        idx = 1
    elif dates and dates[0] == today - timedelta(days=1):
        current = 1
        check = today - timedelta(days=2)
        idx = 1
    else:
        return {"current": 0, "longest": _longest_streak(dates), "today": False}

    while idx < len(dates) and dates[idx] == check:
        current += 1
        check -= timedelta(days=1)
        idx += 1

    return {
        "current": current,
        "longest": max(current, _longest_streak(dates)),
        "today": dates[0] == today if dates else False,
    }


def _longest_streak(dates: list) -> int:
    """Berechnet die laengste zusammenhaengende Tagesstraehne aus sortierten Daten (absteigend)."""
    if not dates:
        return 0
    from datetime import timedelta
    longest = 1
    current = 1
    for i in range(1, len(dates)):
        if dates[i-1] - dates[i] == timedelta(days=1):
            current += 1
            if current > longest:
                longest = current
        else:
            current = 1
    return longest


@router.get("/api/stats/xp")
def get_xp(user: dict = Depends(get_current_user)):
    """Gibt XP-Daten des Nutzers zurueck."""
    uid = user["id"]
    conn = get_db()
    row = conn.execute("SELECT * FROM user_xp WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    if not row:
        return {"xp_total": 0, "xp_today": 0, "daily_goal": 100}
    today_str = date.today().isoformat()
    xp_today = row["xp_today"] if row["last_xp_date"] == today_str else 0
    return {
        "xp_total": row["xp_total"] or 0,
        "xp_today": xp_today,
    }


@router.get("/api/stats/heatmap")
def get_heatmap(days: int = 365, user: dict = Depends(get_current_user)):
    """Lernaktivitaet pro Tag fuer Heatmap (letzte N Tage)."""
    uid = user["id"]
    conn = get_db()
    rows = conn.execute(
        """SELECT date(reviewed_at) as d, COUNT(*) as cnt
           FROM reviews WHERE user_id=? AND reviewed_at >= date('now', ?)
           GROUP BY d ORDER BY d""",
        (uid, f"-{days} days")
    ).fetchall()
    conn.close()
    return [{"date": r["d"], "count": r["cnt"]} for r in rows if r["d"]]
