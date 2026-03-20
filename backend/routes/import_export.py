"""routes/import_export.py -- ZIP-Import, Markdown-Import, Bundle-Install."""

from __future__ import annotations
import json, re
from pathlib import Path
from typing import Optional
import os

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from db import get_db, row_to_dict
from auth import get_current_user
from helpers import rebuild_fts, resolve_category, import_markdown_internal
from schemas import MarkdownImport
from services import chunk_text, extract_text_from_file

router = APIRouter(tags=["import_export"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).parent.parent.parent / "uploads")))
BUNDLES_PATH = Path(os.environ.get("BUNDLES_PATH", str(Path(__file__).parent.parent.parent / "lernpakete")))


# -- Bundles (vorgefertigte Lernpakete) ----------------------------------------

@router.get("/api/bundles")
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
        # Karten und Kategorien aus Fragen-Datei zaehlen
        files = b.get("files", {})
        fragen_file = BUNDLES_PATH / (files.get("questions") or b.get("fragen_file", ""))
        if fragen_file.exists():
            text = fragen_file.read_text()
            cats: dict[str, int] = {}
            count = 0
            for m in re.finditer(r"^##\s+K-\d+\s*\|\s*(\w+)", text, re.MULTILINE):
                count += 1
                code = m.group(1).upper()
                cats[code] = cats.get(code, 0) + 1
            b["card_count"] = count
            b["categories"] = cats
        else:
            b["card_count"] = 0
            b["categories"] = {}
    return bundles


@router.post("/api/bundles/{bundle_id}/install")
def install_bundle(bundle_id: str, user: dict = Depends(get_current_user)):
    meta_file = BUNDLES_PATH / "bundles.json"
    if not meta_file.exists():
        raise HTTPException(404, "bundles.json nicht gefunden")

    bundles = json.loads(meta_file.read_text())
    bundle  = next((b for b in bundles if b["id"] == bundle_id), None)
    if not bundle:
        raise HTTPException(404, f"Bundle '{bundle_id}' nicht gefunden")

    files = bundle.get("files", {})
    fragen_file  = BUNDLES_PATH / (files.get("questions") or bundle.get("fragen_file", ""))
    antwort_file = BUNDLES_PATH / (files.get("answers") or bundle.get("antwort_file", ""))

    if not fragen_file.exists() or not antwort_file.exists():
        raise HTTPException(500, "Bundle-Dateien fehlen auf dem Server")

    fragen   = fragen_file.read_text()
    antworten = antwort_file.read_text()

    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM packages WHERE name=?", (bundle["name"],)
    ).fetchone()

    uid = user["id"]
    if existing:
        pkg_id = existing["id"]
    else:
        conn.execute(
            "INSERT INTO packages (name,description,color,icon) VALUES (?,?,?,?)",
            (bundle["name"], bundle.get("description",""), bundle.get("color","#2196F3"), bundle.get("icon","fa-graduation-cap"))
        )
        conn.commit()
        pkg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # User dem Paket zuordnen (owner bei Neuinstall, learner bei bestehendem)
    role = "owner" if not existing else "learner"
    conn.execute("INSERT OR IGNORE INTO user_packages (user_id, package_id, role) VALUES (?,?,?)", (uid, pkg_id, role))
    conn.commit()
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


# -- ZIP-Import ----------------------------------------------------------------

@router.post("/api/import/zip")
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
        uid = user["id"]
        if existing:
            package_id = existing["id"]
        else:
            conn.execute(
                "INSERT INTO packages (name,color,icon) VALUES (?,?,?)",
                (pkg_name, "#2196F3", "fa-graduation-cap")
            )
            conn.commit()
            package_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # User dem Paket zuordnen
        conn.execute("INSERT OR IGNORE INTO user_packages (user_id, package_id, role) VALUES (?,?,'owner')", (uid, package_id))
        conn.commit()
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

    # Bilder importieren (in uploads/ speichern)
    img_exts = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
    img_files = [
        n for n in names
        if any(n.lower().endswith(ext) for ext in img_exts)
        and not n.startswith("__") and not n.startswith(".")
    ]
    images_imported = 0
    pkg_upload_dir = UPLOAD_DIR / str(package_id)
    pkg_upload_dir.mkdir(parents=True, exist_ok=True)
    for img_name in img_files:
        filename = img_name.split("/")[-1]
        target = pkg_upload_dir / filename
        target.write_bytes(zf.read(img_name))
        images_imported += 1

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
    result["images_imported"] = images_imported

    # Erweiterte Daten aus paket-extra.json importieren (Lexikon, Lernpfade)
    extra_name = next((n for n in names if n.lower() == "paket-extra.json"), None)
    if extra_name:
        try:
            extra = json.loads(zf.read(extra_name).decode("utf-8"))
        except Exception:
            extra = {}

        conn = get_db()
        lex_imported = 0
        if "lexicon" in extra:
            for entry in extra["lexicon"]:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO lexicon (package_id,term,definition,category_code) VALUES (?,?,?,?)",
                        (package_id, entry["term"], entry["definition"], entry.get("category_code"))
                    )
                    lex_imported += 1
                except Exception:
                    pass
            conn.commit()
            try:
                conn.execute("INSERT INTO lexicon_fts(lexicon_fts) VALUES('rebuild')")
                conn.commit()
            except Exception:
                pass

        paths_imported = 0
        if "paths" in extra:
            for p in extra["paths"]:
                try:
                    conn.execute(
                        "INSERT INTO learning_paths (package_id,name,description,sort_order) VALUES (?,?,?,0)",
                        (package_id, p["name"], p.get("description"))
                    )
                    conn.commit()
                    path_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    for ch in p.get("chapters", []):
                        conn.execute(
                            "INSERT INTO path_chapters (path_id,sort_order,title,description,document_ids,card_ids,pass_threshold) VALUES (?,?,?,?,?,?,?)",
                            (path_id, ch.get("sort_order", 0), ch["title"], ch.get("description"),
                             json.dumps(ch.get("document_ids", [])), json.dumps(ch.get("card_ids", [])),
                             ch.get("pass_threshold", 0.7))
                        )
                    conn.commit()
                    paths_imported += 1
                except Exception:
                    pass

        conn.close()
        result["lexicon_imported"] = lex_imported
        result["paths_imported"] = paths_imported

    return result


# -- Markdown Import -----------------------------------------------------------

def _parse_markdown(fragen: str, antworten: str):
    """Parse Markdown-Karten und gibt strukturierte Daten zurueck."""
    card_pat = re.compile(r"```\s*\n(K-\d+)\s*\|\s*([^\n]+?)\s*\n([\s\S]*?)```", re.MULTILINE)
    ans_pat  = re.compile(r"```\s*\n(A-\d+)\s*\|[^\n]*\n([\s\S]*?)```",         re.MULTILINE)
    questions = {m.group(1): (resolve_category(m.group(2)), m.group(3).strip()) for m in card_pat.finditer(fragen)}
    answers   = {m.group(1).replace("A-","K-"): m.group(2).strip() for m in ans_pat.finditer(antworten)}
    return questions, answers


@router.post("/api/import/preview")
def import_preview(data: MarkdownImport, user: dict = Depends(get_current_user)):
    """Parsed Markdown und gibt Vorschau zurueck ohne zu importieren."""
    questions, answers = _parse_markdown(data.fragen, data.antworten)
    conn = get_db()
    existing_ids = set()
    if data.package_id:
        rows = conn.execute("SELECT card_id FROM cards WHERE package_id=?", (data.package_id,)).fetchall()
        existing_ids = {r["card_id"] for r in rows}
    conn.close()

    cards = []
    errors = []
    for card_id, (cat, question) in questions.items():
        answer = answers.get(card_id, "")
        status = "new"
        if card_id in existing_ids:
            status = "duplicate"
        elif not answer:
            status = "no_answer"
        cards.append({
            "card_id": card_id,
            "category_code": cat,
            "question": question.strip(),
            "answer": answer.strip(),
            "status": status,
        })

    # Fragen ohne Antwort und Antworten ohne Frage
    orphan_answers = set(answers.keys()) - set(questions.keys())
    for oid in orphan_answers:
        errors.append(f"Antwort {oid.replace('K-','A-')} hat keine passende Frage")

    cards.sort(key=lambda c: c["card_id"])
    return {
        "cards": cards,
        "total": len(cards),
        "new": sum(1 for c in cards if c["status"] == "new"),
        "duplicates": sum(1 for c in cards if c["status"] == "duplicate"),
        "no_answer": sum(1 for c in cards if c["status"] == "no_answer"),
        "errors": errors,
    }


@router.post("/api/import/markdown")
def import_markdown(data: MarkdownImport, user: dict = Depends(get_current_user)):
    questions, answers = _parse_markdown(data.fragen, data.antworten)
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
    rebuild_fts(conn)
    conn.close()
    return {"created": created, "skipped": skipped, "total": len(questions)}
