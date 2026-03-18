"""services.py -- LM Studio Anbindung mit Dokument-Kontext-Injektion

Prinzip: LM Studio bekommt Fakten als Kontext und formuliert daraus.
Kein eigenes Wissen, kein Halluzinieren.
"""

import re, json, httpx

LM_BASE = "http://192.168.178.45:1234"
LM_URL  = f"{LM_BASE}/v1/chat/completions"
_MODEL  = None
MAX_CTX = 80_000

RULES = (
    "Schreibe auf Deutsch. "
    "Nutze Markdown für Formatierung (Überschriften, Listen, Fettdruck). "
    "Keine Einleitungsfloskeln (kein 'Gerne', 'Natuerlich', 'Sicher', 'Hier ist'). "
    "Keine Zusammenfassung am Ende. "
    "Direkt zur Sache."
)


async def get_model() -> str:
    global _MODEL
    if _MODEL:
        return _MODEL
    try:
        async with httpx.AsyncClient(timeout=4.0) as c:
            r = await c.get(f"{LM_BASE}/v1/models")
            if r.status_code == 200:
                models = r.json().get("data", [])
                if models:
                    _MODEL = models[0]["id"]
                    return _MODEL
    except Exception:
        pass
    return "local-model"


async def ai_online() -> bool:
    global _MODEL
    try:
        async with httpx.AsyncClient(timeout=4.0) as c:
            r = await c.get(f"{LM_BASE}/v1/models")
            if r.status_code != 200:
                return False
            models = r.json().get("data", [])
            if not models:
                return False
            _MODEL = models[0]["id"]
            return True
    except Exception:
        return False


async def _chat(user: str, system: str = "", max_tokens: int = 500,
                temperature: float = 0.3, timeout: float = 30.0) -> str | None:
    model = await get_model()
    msgs  = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(LM_URL, json={
                "model": model, "messages": msgs,
                "max_tokens": max_tokens, "temperature": temperature,
            })
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None


def _strip_json(raw: str) -> str:
    raw = re.sub(r"^```json\s*", "", raw.strip())
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"\s*```$",     "", raw)
    return raw.strip()


async def explain_card(question: str, answer: str,
                       doc_context: str = "", package_name: str = "") -> str:
    ctx = doc_context[:MAX_CTX]
    if ctx:
        system = (
            f'Lernassistent für "{package_name or "unbekannt"}".\n'
            f'Wissensquelle:\n---\n{ctx}\n---\n'
            f'Nur aus dieser Quelle antworten. Nichts erfinden.\n{RULES}'
        )
    else:
        system = f'Lernassistent für "{package_name or "unbekannt"}". {RULES}'

    user = (
        f"Erklaere diese Lernkarte sachlich, maximal 4 Saetze.\n\n"
        f"Frage: {question}\nAntwort: {answer}"
    )
    return await _chat(user, system, max_tokens=400, temperature=0.3, timeout=20.0) \
           or "LM Studio nicht erreichbar."


async def evaluate_answer(question: str, correct_answer: str,
                          user_answer: str, doc_context: str = "") -> dict:
    ctx      = doc_context[:20_000]
    ctx_hint = f"\nKontext:\n{ctx}" if ctx else ""
    system   = f"Lernkarten-Korrektor. Antworte NUR mit JSON.{ctx_hint}"

    user = (
        f"Frage: {question}\n"
        f"Richtige Antwort: {correct_answer}\n"
        f"Benutzerantwort: {user_answer}\n\n"
        f"Bewertung: score 0.0-1.0, feedback auf Deutsch (max 2 Saetze, sachlich, kein 'Leider').\n"
        f'Antworte NUR mit: {{"score": 0.0, "correct": false, "feedback": "..."}}'
    )
    result = await _chat(user, system, max_tokens=150, temperature=0.1, timeout=15.0)
    if not result:
        return {"score": 0.5, "correct": None, "feedback": "Bewertung nicht verfügbar."}
    try:
        d = json.loads(_strip_json(result))
        return {
            "score":    max(0.0, min(1.0, float(d.get("score", 0.5)))),
            "correct":  bool(d.get("correct", False)),
            "feedback": str(d.get("feedback", "")),
        }
    except Exception:
        return {"score": 0.5, "correct": None, "feedback": "Auswertung fehlgeschlagen."}


async def generate_cards_from_chunk(chunk: str, category: str = "GB",
                                    count: int = 3, package_name: str = "",
                                    full_doc_context: str = "") -> list[dict]:
    ctx    = f"\nGesamtdokument:\n{full_doc_context[:5000]}" if full_doc_context else ""
    system = f'Lernkarten-Generator für "{package_name or "unbekannt"}". Nur Fakten aus dem Text. Antwort: ausschließlich JSON.{ctx}'

    user = (
        f"Erstelle genau {count} Lernkarten aus diesem Text:\n---\n{chunk[:2000]}\n---\n"
        f"Regeln: Verstaendnis testen, selbsterklaerende Antworten.\n"
        f"difficulty: 1=leicht 2=mittel 3=schwer\n"
        f'Antwort NUR als JSON-Array:\n'
        f'[{{"question":"...","answer":"...","hint":"...oder null","difficulty":2}}]'
    )
    result = await _chat(user, system, max_tokens=1000, temperature=0.4, timeout=40.0)
    if not result:
        return []
    try:
        cards = json.loads(_strip_json(result))
        return [
            {"category_code": category,
             "question":      c["question"].strip(),
             "answer":        c["answer"].strip(),
             "hint":          c.get("hint") or None,
             "difficulty":    int(c.get("difficulty", 2))}
            for c in (cards if isinstance(cards, list) else [])
            if isinstance(c, dict) and c.get("question") and c.get("answer")
        ]
    except Exception:
        return []


async def analyze_mistakes(wrong_cards: list[dict], documents: list[dict]) -> list[dict]:
    if not wrong_cards or not documents:
        return []

    chunk_map      = {}
    doc_text_parts = []
    for doc in documents:
        for chunk in doc.get("chunks", []):
            chunk_map[chunk["chunk_id"]] = {
                "doc_id":    doc["doc_id"],
                "doc_title": doc["title"],
                "chunk_id":  chunk["chunk_id"],
                "chunk_idx": chunk["chunk_index"],
                "text":      chunk["text"],
            }
            doc_text_parts.append(
                f'[DOC:{doc["doc_id"]}|CHUNK:{chunk["chunk_id"]}|TITEL:{doc["title"]}]\n{chunk["text"]}'
            )

    full_context = "\n\n---\n\n".join(doc_text_parts)[:MAX_CTX]
    cards_text   = "\n".join(
        f"KARTE-{c['card_id']}: {c['question']} | {c['answer']}"
        for c in wrong_cards
    )

    system = (
        f"Analysiere falsch beantwortete Lernkarten und finde relevante Passagen.\n"
        f"Dokumente:\n---\n{full_context}\n---\n"
        f"Antworte NUR mit JSON. {RULES}"
    )

    user = (
        f"Falsch beantwortete Karten:\n{cards_text}\n\n"
        f"Finde pro Karte 1-3 relevante Textpassagen.\n"
        f"Antwort NUR als JSON:\n"
        f'[{{"card_id":1,"references":[{{"doc_id":1,"chunk_id":5,'
        f'"passage":"Exakter Textauszug max 300 Zeichen",'
        f'"explanation":"Warum relevant (1 Satz)"}}]}}]'
    )

    result = await _chat(user, system, max_tokens=2000, temperature=0.2, timeout=60.0)
    if not result:
        return []

    try:
        data    = json.loads(_strip_json(result))
        card_map = {c["card_id"]: c for c in wrong_cards}
        output  = []
        for item in (data if isinstance(data, list) else []):
            cid  = item.get("card_id")
            card = card_map.get(cid)
            if not card:
                continue
            refs = []
            for ref in item.get("references", [])[:3]:
                cid2     = ref.get("chunk_id")
                info     = chunk_map.get(cid2, {})
                refs.append({
                    "doc_id":      ref.get("doc_id") or info.get("doc_id"),
                    "doc_title":   info.get("doc_title", "Unbekannt"),
                    "chunk_id":    cid2,
                    "chunk_index": info.get("chunk_idx", 0),
                    "passage":     ref.get("passage", "")[:400],
                    "full_text":   info.get("text", ""),
                    "explanation": ref.get("explanation", ""),
                })
            output.append({
                "card_id":    cid,
                "question":   card["question"],
                "answer":     card["answer"],
                "category":   card.get("category_code", ""),
                "references": refs,
            })
        return output
    except Exception:
        return []


async def generate_hint(question: str, answer: str) -> str:
    """Erstellt eine Merkhilfe/Eselsbrücke für eine schwierige Karte."""
    system = (
        RULES + " "
        "Erstelle eine kurze Merkhilfe oder Eselsbrücke. "
        "Maximal 2 Sätze. Einprägsam und bildhaft."
    )
    user_msg = f"Frage: {question}\nAntwort: {answer}\n\nMerkhilfe:"
    try:
        return await _chat(user_msg, system=system, max_tokens=150)
    except Exception:
        return ""


async def summarize_topic(cards: list[dict], topic: str = "") -> str:
    """Fasst eine Gruppe von Karten zu einer kompakten Zusammenfassung zusammen."""
    card_texts = "\n".join(f"- {c['question']} -> {c['answer']}" for c in cards[:20])
    system = (
        RULES + " "
        "Fasse die folgenden Lernkarten zu einer kompakten Zusammenfassung zusammen. "
        "Strukturiere nach Themenblöcken. Maximal 300 Wörter."
    )
    user_msg = f"Thema: {topic}\n\nKarten:\n{card_texts}\n\nZusammenfassung:"
    try:
        return await _chat(user_msg, system=system, max_tokens=600)
    except Exception:
        return ""


async def suggest_related(question: str, answer: str, all_cards: list[dict], limit: int = 3) -> list[str]:
    """Schlägt thematisch verwandte Karten-IDs vor (basierend auf Schlüsselwörtern)."""
    # Einfache Keyword-Matching-Strategie ohne KI (funktioniert auch offline)
    keywords = set(re.findall(r'\b[A-Za-zÄÖÜäöüß]{4,}\b', f"{question} {answer}".lower()))
    scored = []
    for c in all_cards:
        if c.get("card_id") == "":
            continue
        text = f"{c.get('question','')} {c.get('answer','')}".lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, c.get("card_id", "")))
    scored.sort(key=lambda x: -x[0])
    return [cid for _, cid in scored[:limit]]


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    text       = re.sub(r'\n{3,}', '\n\n', text.strip())
    # Nur horizontale Whitespace-Duplikate entfernen, Zeilenumbrüche erhalten
    text       = re.sub(r'[^\S\n]+', ' ', text)
    paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        is_heading = para.startswith('#')
        # Überschriften starten immer einen neuen Chunk
        if is_heading and current:
            chunks.append(current)
            current = para
        elif len(current) + len(para) + 2 <= size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return [c for c in chunks if len(c.strip()) > 50]


def extract_text_from_file(content: bytes, filetype: str) -> str:
    if filetype in ("txt", "md"):
        return content.decode("utf-8", errors="replace")
    if filetype == "pdf":
        try:
            import io
            from pypdf import PdfReader
            return "\n\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
        except ImportError:
            pass
    if filetype == "docx":
        try:
            import io, zipfile, xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                with z.open("word/document.xml") as f:
                    tree = ET.parse(f)
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            return "\n".join("".join(t.text or "" for t in p.iter(f"{ns}t"))
                             for p in tree.iter(f"{ns}p"))
        except Exception:
            pass
    return content.decode("utf-8", errors="replace")


def sm2_update(ease: float, interval: int, reps: int, quality: int) -> tuple:
    if quality < 3:
        reps, interval = 0, 1
    else:
        interval = 1 if reps == 0 else 6 if reps == 1 else max(1, round(interval * ease))
        reps += 1
    ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return ease, interval, reps
