"""helpers.py -- Geteilte Hilfsfunktionen für alle Router."""

import re
import json
from pathlib import Path

from db import get_db
from services import chunk_text, extract_text_from_file


def next_card_id(conn) -> str:
    """Nächste freie Karten-ID im Format K-001."""
    row = conn.execute("SELECT card_id FROM cards ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        m = re.search(r"(\d+)$", row["card_id"])
        n = int(m.group(1)) + 1 if m else 1
    else:
        n = 1
    return f"K-{n:03d}"


def rebuild_fts(conn):
    """FTS-Index für Karten neu aufbauen."""
    conn.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")
    conn.commit()


# Mapping: volle Kategorie-Namen -> Codes (beides akzeptiert)
_CAT_NAME_MAP = {
    "grundlagen": "GB", "theorie": "TH", "praxis": "PX",
    "verfahren": "VF", "pruefung": "PR", "prüfung": "PR",
    "vertiefung": "VT", "allgemein": "AL",
}


def resolve_category(raw: str) -> str:
    """Akzeptiert Code (GB) oder vollen Namen (Grundlagen) und gibt den Code zurück."""
    clean = raw.strip().upper()
    if len(clean) == 2:
        return clean  # Schon ein Code
    return _CAT_NAME_MAP.get(raw.strip().lower(), "AL")


def import_markdown_internal(fragen: str, antworten: str, package_id: int) -> dict:
    """Importiert Fragen/Antworten aus Markdown-Strings in die DB."""
    card_pat = re.compile(r"```\s*\n(K-\w+)\s*\|\s*([^\n]+?)\s*\n([\s\S]*?)```", re.MULTILINE)
    ans_pat  = re.compile(r"```\s*\n(A-\w+)\s*\|[^\n]*\n([\s\S]*?)```",           re.MULTILINE)
    questions = {m.group(1): (resolve_category(m.group(2)), m.group(3).strip()) for m in card_pat.finditer(fragen)}
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
    rebuild_fts(conn)
    conn.close()
    return {"created": created, "skipped": skipped, "total": len(questions)}
