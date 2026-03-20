"""routes/packages.py -- CRUD, Stats, Share, Users, Export, Uninstall, Reinstall, Kategorien, Lexikon, Lernpfade."""

from __future__ import annotations
import json, re, io, zipfile, os
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from db import get_db, row_to_dict
from auth import get_current_user
from helpers import rebuild_fts, next_card_id
from schemas import (
    PackageCreate, PackageUpdate, CategoryCreate, DraftAction,
    LexiconCreate, PathCreate, ChapterCreate, ChapterUpdate,
)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).parent.parent.parent / "uploads")))

router = APIRouter(tags=["packages"])


# -- Pakete --------------------------------------------------------------------

@router.get("/api/packages")
def get_packages(user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*,
            (SELECT COUNT(*) FROM cards c WHERE c.package_id=p.id AND c.active=1)   as card_count,
            (SELECT COUNT(*) FROM documents d WHERE d.package_id=p.id)               as doc_count,
            (SELECT COUNT(*) FROM card_drafts cd WHERE cd.package_id=p.id AND cd.status='pending') as draft_count,
            up.role as user_role
        FROM packages p
        JOIN user_packages up ON up.package_id=p.id AND up.user_id=?
        ORDER BY p.created_at ASC
    """, (uid,)).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.get("/api/packages/{pkg_id}")
def get_package(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Paket nicht gefunden")
    return row_to_dict(row)


@router.post("/api/packages")
def create_package(data: PackageCreate, user: dict = Depends(get_current_user)):
    uid = user["id"]
    conn = get_db()
    conn.execute(
        "INSERT INTO packages (name,description,color,icon) VALUES (?,?,?,?)",
        (data.name, data.description, data.color, data.icon)
    )
    conn.commit()
    pkg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO user_packages (user_id, package_id, role) VALUES (?,?,'owner')", (uid, pkg_id))
    conn.commit()
    pkg = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    conn.close()
    return row_to_dict(pkg)


@router.put("/api/packages/{pkg_id}")
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


@router.delete("/api/packages/{pkg_id}")
def delete_package(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("UPDATE cards SET active=0 WHERE package_id=?", (pkg_id,))
    conn.execute("DELETE FROM user_packages WHERE package_id=?", (pkg_id,))
    conn.execute("DELETE FROM packages WHERE id=?", (pkg_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# -- Paket-Freigabe ----------------------------------------------------------

@router.get("/api/packages/{pkg_id}/users")
def get_package_users(pkg_id: int, user: dict = Depends(get_current_user)):
    """Zeigt alle User die Zugriff auf ein Paket haben."""
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id, u.email, u.display_name, up.role, up.created_at
        FROM user_packages up JOIN users u ON u.id=up.user_id
        WHERE up.package_id=?
    """, (pkg_id,)).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.post("/api/packages/{pkg_id}/share")
def share_package(pkg_id: int, data: dict, user: dict = Depends(get_current_user)):
    """Gibt ein Paket fuer einen anderen User frei. Nur Owner darf teilen."""
    uid = user["id"]
    conn = get_db()
    own = conn.execute("SELECT role FROM user_packages WHERE user_id=? AND package_id=?", (uid, pkg_id)).fetchone()
    if not own or own["role"] != "owner":
        conn.close()
        raise HTTPException(403, "Nur der Besitzer kann Pakete freigeben")
    target_email = data.get("email")
    target_role = data.get("role", "learner")
    if target_role not in ("learner", "owner"):
        raise HTTPException(400, "Rolle muss 'learner' oder 'owner' sein")
    target = conn.execute("SELECT id FROM users WHERE email=?", (target_email,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "Benutzer nicht gefunden")
    conn.execute("INSERT OR REPLACE INTO user_packages (user_id, package_id, role) VALUES (?,?,?)", (target["id"], pkg_id, target_role))
    conn.commit()
    conn.close()
    return {"ok": True, "shared_with": target_email, "role": target_role}


@router.delete("/api/packages/{pkg_id}/share/{target_user_id}")
def unshare_package(pkg_id: int, target_user_id: int, user: dict = Depends(get_current_user)):
    """Entzieht einem User den Zugriff auf ein Paket."""
    uid = user["id"]
    conn = get_db()
    own = conn.execute("SELECT role FROM user_packages WHERE user_id=? AND package_id=?", (uid, pkg_id)).fetchone()
    if not own or own["role"] != "owner":
        conn.close()
        raise HTTPException(403, "Nur der Besitzer kann Freigaben entziehen")
    conn.execute("DELETE FROM user_packages WHERE user_id=? AND package_id=?", (target_user_id, pkg_id))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/api/packages/{pkg_id}/stats")
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
    # SRS-Stapel: Neu, Faellig, Lernphase (<7d), Gefestigt (7-30d), Gemeistert (>30d)
    today = date.today().isoformat()
    srs_rows = conn.execute("""
        SELECT c.card_id, cs.interval_days, cs.due_date, cs.times_shown
        FROM cards c
        LEFT JOIN card_stats cs ON cs.card_id=c.card_id AND cs.user_id=?
        WHERE c.package_id=? AND c.active=1
    """, (uid, pkg_id)).fetchall()
    stacks = {"new":0, "due":0, "learning":0, "solid":0, "mastered":0}
    for r in srs_rows:
        if not r["times_shown"] or r["times_shown"] == 0:
            stacks["new"] += 1
        elif r["due_date"] and r["due_date"] <= today:
            stacks["due"] += 1
        elif r["interval_days"] and r["interval_days"] > 30:
            stacks["mastered"] += 1
        elif r["interval_days"] and r["interval_days"] >= 7:
            stacks["solid"] += 1
        else:
            stacks["learning"] += 1

    conn.close()
    return {
        "total_cards":    total,
        "total_docs":     docs,
        "pending_drafts": drafts,
        "total_reviews":  rev[0] or 0,
        "total_correct":  rev[1] or 0,
        "due_today":      due,
        "by_category":    [row_to_dict(r) for r in by_cat],
        "srs_stacks":     stacks,
    }


# -- Kategorien ----------------------------------------------------------------

@router.get("/api/categories")
def get_categories(package_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    conn = get_db()
    if package_id:
        rows = conn.execute("""
            SELECT c.*, COUNT(ca.id) as card_count
            FROM categories c
            LEFT JOIN cards ca ON ca.category_code=c.code AND ca.active=1 AND ca.package_id=?
            GROUP BY c.id ORDER BY c.code
        """, (package_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT c.*, COUNT(ca.id) as card_count
            FROM categories c
            LEFT JOIN cards ca ON ca.category_code=c.code AND ca.active=1
            GROUP BY c.id ORDER BY c.code
        """).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.post("/api/categories")
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


# -- Dokumente -----------------------------------------------------------------

@router.get("/api/packages/{pkg_id}/documents")
def get_documents(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM documents WHERE package_id=? ORDER BY created_at DESC", (pkg_id,)
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.get("/api/packages/{pkg_id}/media")
def get_package_media(pkg_id: int, user: dict = Depends(get_current_user)):
    """Listet Bilder und andere Medien eines Pakets auf."""

    pkg_dir = UPLOAD_DIR / str(pkg_id)
    if not pkg_dir.exists():
        return []
    img_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf"}
    files = []
    for f in sorted(pkg_dir.iterdir()):
        if f.suffix.lower() in img_exts:
            files.append({
                "name": f.name,
                "type": f.suffix.lower().lstrip("."),
                "size": f.stat().st_size,
                "url": f"/uploads/{pkg_id}/{f.name}",
            })
    return files


@router.post("/api/packages/{pkg_id}/documents/upload")
async def upload_document(
    pkg_id:   int,
    file:     UploadFile = File(...),
    title:    str        = Form(default=""),
    category: str        = Form(default="AL"),
    user: dict = Depends(get_current_user),
):
    from services import chunk_text, extract_text_from_file
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


@router.get("/api/documents/{doc_id}/chunks")
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


@router.post("/api/documents/{doc_id}/generate")
async def generate_from_doc(doc_id: int, body: dict, user: dict = Depends(get_current_user)):
    from services import generate_cards_from_chunk, get_ai_setting
    chunk_ids       = body.get("chunk_ids")
    category        = body.get("category", "AL")
    cards_per_chunk = int(body.get("cards_per_chunk", 3))
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not doc:
        conn.close(); raise HTTPException(404)
    pkg_id = doc["package_id"]
    # User-Settings laden
    settings = {}
    try:
        srow = conn.execute("SELECT settings FROM users WHERE id=?", (user["id"],)).fetchone()
        if srow and srow["settings"]:
            settings = json.loads(srow["settings"])
    except Exception:
        pass
    # cards_per_chunk aus Settings falls nicht explizit gesetzt
    if cards_per_chunk == 3:
        cards_per_chunk = get_ai_setting(settings, "cards_per_chunk")
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
    base_temp = get_ai_setting(settings, "temperature_cardgen")
    for chunk in chunks:
        pkg_nm = ""
        try:
            p = conn.execute("SELECT name FROM packages WHERE id=?", (pkg_id,)).fetchone()
            if p: pkg_nm = p["name"]
        except Exception:
            pass
        cards = await generate_cards_from_chunk(
            chunk["text"], category, cards_per_chunk,
            package_name=pkg_nm, base_temp=base_temp,
            settings=settings
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


@router.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM document_chunks WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM card_drafts WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# -- Entwuerfe -----------------------------------------------------------------

@router.get("/api/packages/{pkg_id}/drafts")
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


@router.put("/api/drafts/{draft_id}")
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
        card_id = next_card_id(conn)
        conn.execute(
            "INSERT INTO cards (card_id,package_id,category_code,question,answer,hint,difficulty,source) VALUES (?,?,?,?,?,?,?,?)",
            (card_id, package_id, category_code, question, answer, hint, difficulty, 'ai')
        )
        rebuild_fts(conn)
        conn.execute("UPDATE card_drafts SET status='approved' WHERE id=?", (draft_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# -- Lexikon -------------------------------------------------------------------

@router.get("/api/packages/{pkg_id}/lexicon")
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


@router.post("/api/lexicon")
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


# -- Lernpfade (Kapitel-basiert) -----------------------------------------------

@router.get("/api/packages/{pkg_id}/paths")
def get_paths(pkg_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM learning_paths WHERE package_id=? ORDER BY sort_order, id", (pkg_id,)).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@router.post("/api/paths")
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


@router.get("/api/paths/{path_id}")
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


@router.post("/api/paths/{path_id}/chapters")
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


@router.put("/api/chapters/{chapter_id}")
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


@router.delete("/api/chapters/{chapter_id}")
def delete_chapter(chapter_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM path_chapters WHERE id=?", (chapter_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.delete("/api/paths/{path_id}")
def delete_path(path_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM path_chapters WHERE path_id=?", (path_id,))
    conn.execute("DELETE FROM learning_paths WHERE id=?", (path_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# -- Paket exportieren (ZIP mit Fragen + Antworten Markdown) ------------------

@router.get("/api/packages/{pkg_id}/export")
def export_package(pkg_id: int, token: str = Query(None), user: dict = Depends(get_current_user)):
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

    # Bundle-Metadaten fuer Re-Import
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


# -- Paket zurueckziehen (saubere Deinstallation) ------------------------------

@router.delete("/api/packages/{pkg_id}/uninstall")
def uninstall_package(pkg_id: int, user: dict = Depends(get_current_user)):

    conn = get_db()
    try:
        pkg = conn.execute("SELECT * FROM packages WHERE id=?", (pkg_id,)).fetchone()
    except Exception:
        conn.close()
        raise HTTPException(500, "Datenbankfehler beim Lesen des Pakets")
    if not pkg:
        conn.close()
        raise HTTPException(404, "Paket nicht gefunden")

    stats = {}

    # 1. Lernstatistik bleibt erhalten (gelernt ist gelernt)

    # 2. Alle Karten loeschen
    r = conn.execute("DELETE FROM cards WHERE package_id=?", (pkg_id,))
    stats["cards_deleted"] = r.rowcount

    # 3. Hochgeladene Dokumente: Dateien loeschen
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

    # 4. Dokumente aus DB loeschen
    doc_ids = [d["id"] for d in docs]
    if doc_ids:
        pl = ",".join("?" * len(doc_ids))
        conn.execute(f"DELETE FROM document_chunks WHERE document_id IN ({pl})", doc_ids)
    r = conn.execute("DELETE FROM documents WHERE package_id=?", (pkg_id,))
    stats["documents_deleted"] = r.rowcount

    # 5. Entwuerfe loeschen
    r = conn.execute("DELETE FROM card_drafts WHERE package_id=?", (pkg_id,))
    stats["drafts_deleted"] = r.rowcount

    # 6. Lexikon-Eintraege loeschen
    try:
        r = conn.execute("DELETE FROM lexicon WHERE package_id=?", (pkg_id,))
        stats["lexicon_deleted"] = r.rowcount
    except Exception:
        stats["lexicon_deleted"] = 0

    # 7. Lernpfade und Kapitel loeschen
    try:
        paths = conn.execute("SELECT id FROM learning_paths WHERE package_id=?", (pkg_id,)).fetchall()
        for p in paths:
            conn.execute("DELETE FROM path_chapters WHERE path_id=?", (p["id"],))
        r = conn.execute("DELETE FROM learning_paths WHERE package_id=?", (pkg_id,))
        stats["paths_deleted"] = r.rowcount
    except Exception:
        stats["paths_deleted"] = 0

    # 8. MC-Optionen-Cache loeschen
    try:
        r = conn.execute("DELETE FROM mc_options WHERE package_id=?", (pkg_id,))
        stats["mc_options_deleted"] = r.rowcount
    except Exception:
        stats["mc_options_deleted"] = 0

    # 9. FTS-Index aktualisieren
    try:
        rebuild_fts(conn)
    except Exception:
        pass

    # 10. Sessions entkoppeln (Statistik bleibt, Paket-Referenz wird entfernt)
    try:
        conn.execute("UPDATE sessions SET package_id=NULL WHERE package_id=?", (pkg_id,))
    except Exception:
        pass

    # 11. User-Zuordnungen loeschen
    try:
        conn.execute("DELETE FROM user_packages WHERE package_id=?", (pkg_id,))
    except Exception:
        pass

    # 13. Paket selbst loeschen
    try:
        conn.execute("DELETE FROM packages WHERE id=?", (pkg_id,))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(500, f"Fehler beim Löschen des Pakets: {str(e)}")
    conn.close()

    stats["package_name"] = pkg["name"]
    stats["ok"] = True
    return stats


@router.post("/api/packages/{pkg_id}/reinstall")
def reinstall_package(pkg_id: int, bundle_id: str = None, user: dict = Depends(get_current_user)):
    from routes.import_export import install_bundle as _install_bundle
    conn = get_db()
    pkg = conn.execute("SELECT name FROM packages WHERE id=?", (pkg_id,)).fetchone()
    conn.close()

    if not pkg:
        raise HTTPException(404, "Paket nicht gefunden")

    uninstall_package(pkg_id, user)

    if not bundle_id:
        raise HTTPException(400, "bundle_id erforderlich fuer Reinstall")

    return _install_bundle(bundle_id, user)
