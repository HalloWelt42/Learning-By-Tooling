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
    return result


# -- Markdown Import -----------------------------------------------------------

@router.post("/api/import/markdown")
def import_markdown(data: MarkdownImport, user: dict = Depends(get_current_user)):
    card_pat = re.compile(r"```\s*\n(K-\d+)\s*\|\s*([^\n]+?)\s*\n([\s\S]*?)```", re.MULTILINE)
    ans_pat  = re.compile(r"```\s*\n(A-\d+)\s*\|[^\n]*\n([\s\S]*?)```",         re.MULTILINE)
    questions = {m.group(1): (resolve_category(m.group(2)), m.group(3).strip()) for m in card_pat.finditer(data.fragen)}
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
    rebuild_fts(conn)
    conn.close()
    return {"created": created, "skipped": skipped, "total": len(questions)}
