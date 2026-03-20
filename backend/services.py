"""services.py -- KI-Funktionen mit modularem Provider-System.

Prinzip: Provider kapselt die LLM-Kommunikation, Templates kommen aus der DB.
Kein eigenes Wissen, kein Halluzinieren.
"""

import re, json
from typing import Any

from ai_provider import get_provider, render_template, strip_json
from db import get_db

MAX_CTX = 80_000

# KI-Defaults (Abwaertskompatibilitaet fuer User-Settings)
AI_DEFAULTS = {
    "temperature":           0.3,
    "temperature_creative":  0.6,
    "temperature_cardgen":   0.4,
    "max_tokens_explain":    250,
    "max_tokens_evaluate":   400,
    "max_tokens_mc":         300,
    "max_tokens_hint":       150,
    "max_tokens_summarize":  400,
    "max_tokens_cardgen":    400,
    "cards_per_chunk":       3,
    "cardgen_retries":       3,
}

RULES = (
    "Schreibe auf Deutsch. "
    "Nutze Markdown f\u00fcr Formatierung (\u00dcberschriften, Listen, Fettdruck). "
    "Keine Einleitungsfloskeln (kein 'Gerne', 'Nat\u00fcrlich', 'Sicher', 'Hier ist'). "
    "Keine Zusammenfassung am Ende. "
    "Direkt zur Sache."
)


def get_ai_setting(settings: dict | None, key: str) -> Any:
    """Holt einen AI-Setting-Wert aus User-Settings oder Default."""
    if settings and f"ai_{key}" in settings:
        return settings[f"ai_{key}"]
    return AI_DEFAULTS.get(key, AI_DEFAULTS.get("temperature", 0.3))


def _load_template(slug: str) -> dict | None:
    """Laedt ein KI-Template aus der DB."""
    conn = get_db()
    row = conn.execute("SELECT * FROM ai_templates WHERE slug=?", (slug,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get("response_format"):
            try:
                d["response_format"] = json.loads(d["response_format"])
            except Exception:
                d["response_format"] = None
        return d
    return None


async def _call_template(slug: str, variables: dict,
                         settings: dict | None = None,
                         temperature_override: float | None = None,
                         timeout_override: float | None = None,
                         response_format_override: dict | None = None) -> str | None:
    """Laedt Template, rendert Prompts, ruft Provider auf."""
    tmpl = _load_template(slug)
    if not tmpl:
        return None

    system, user = render_template(tmpl, variables)

    provider = get_provider(settings)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    temp = temperature_override if temperature_override is not None else tmpl["temperature"]
    timeout = timeout_override if timeout_override is not None else tmpl["timeout"]
    max_tokens = tmpl["max_tokens"]
    resp_fmt = response_format_override if response_format_override is not None else tmpl.get("response_format")

    return await provider.chat(
        messages, max_tokens=max_tokens,
        temperature=temp, timeout=timeout,
        response_format=resp_fmt,
    )


async def ai_online() -> bool:
    """Pr\u00fcft ob der KI-Provider erreichbar ist."""
    provider = get_provider()
    return await provider.is_online()


async def get_model() -> str:
    """Gibt den Namen des aktuellen Modells zur\u00fcck."""
    provider = get_provider()
    return await provider.get_model_name()


async def explain_card(question: str, answer: str,
                       doc_context: str = "", package_name: str = "",
                       settings: dict | None = None) -> str:
    ctx = doc_context[:MAX_CTX]
    variables = {
        "question": question,
        "answer": answer,
        "doc_context": ctx,
        "package_name": package_name or "unbekannt",
        "RULES": RULES,
    }
    result = await _call_template(
        "explain_card", variables, settings=settings,
        temperature_override=get_ai_setting(settings, "temperature"),
    )
    return result or "LM Studio nicht erreichbar."


async def evaluate_answer(question: str, correct_answer: str,
                          user_answer: str, doc_context: str = "",
                          settings: dict | None = None) -> dict:
    # Leere oder nur Whitespace-Antwort sofort als falsch bewerten
    if not user_answer or not user_answer.strip():
        return {"score": 0.0, "correct": False,
                "feedback": f"Keine Antwort gegeben. Richtig w\u00e4re: {correct_answer[:200]}"}

    ctx = doc_context[:20_000]
    variables = {
        "question": question,
        "correct_answer": correct_answer,
        "user_answer": user_answer,
        "doc_context": ctx,
    }
    result = await _call_template("evaluate_answer", variables, settings=settings)
    if not result:
        return {"score": 0.5, "correct": None, "feedback": "Bewertung nicht verf\u00fcgbar."}
    try:
        d = json.loads(strip_json(result))
        return {
            "score":    max(0.0, min(1.0, float(d.get("score", 0.5)))),
            "correct":  bool(d.get("correct", False)),
            "feedback": str(d.get("feedback", "")),
        }
    except Exception:
        return {"score": 0.5, "correct": None, "feedback": "Auswertung fehlgeschlagen."}


async def _generate_single_card(chunk: str, card_num: int, total: int,
                                category: str, package_name: str,
                                full_doc_context: str, base_temp: float = 0.4,
                                settings: dict | None = None) -> dict | None:
    """Generiert eine einzelne Karte mit bis zu 3 Versuchen und variierender Temperatur."""
    variables = {
        "chunk": chunk[:2000],
        "card_num": str(card_num),
        "total": str(total),
        "package_name": package_name or "unbekannt",
        "full_doc_context": full_doc_context[:5000] if full_doc_context else "",
    }

    temps = [base_temp, base_temp + 0.15, base_temp - 0.1]
    for attempt, temp in enumerate(temps):
        temp = max(0.1, min(1.0, temp))
        result = await _call_template(
            "generate_card", variables, settings=settings,
            temperature_override=temp,
        )
        if not result:
            continue
        try:
            c = json.loads(strip_json(result))
            if isinstance(c, dict) and c.get("question", "").strip() and c.get("answer", "").strip():
                return {
                    "category_code": category,
                    "question":      c["question"].strip(),
                    "answer":        c["answer"].strip(),
                    "hint":          c.get("hint", "").strip() or None,
                    "difficulty":    max(1, min(3, int(c.get("difficulty", 2)))),
                }
        except Exception:
            continue
    return None


async def generate_cards_from_chunk(chunk: str, category: str = "GB",
                                    count: int = 3, package_name: str = "",
                                    full_doc_context: str = "",
                                    base_temp: float = 0.4,
                                    settings: dict | None = None) -> list[dict]:
    """Generiert Karten einzeln mit Retry statt als Batch."""
    cards = []
    retries = get_ai_setting(settings, "cardgen_retries")
    for i in range(count):
        card = await _generate_single_card(
            chunk, i + 1, count, category, package_name,
            full_doc_context, base_temp, settings,
        )
        if card:
            cards.append(card)
    return cards


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

    variables = {
        "full_context": full_context,
        "cards_text": cards_text,
        "RULES": RULES,
    }
    result = await _call_template("analyze_mistakes", variables)
    if not result:
        return []

    try:
        data    = json.loads(strip_json(result))
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


async def generate_mc_options(question: str, answer: str,
                              settings: dict | None = None) -> list[str]:
    """Generiert 3 plausible aber falsche MC-Optionen f\u00fcr eine Karte."""
    if not question or not answer or not question.strip() or not answer.strip():
        return []
    variables = {"question": question, "answer": answer}
    try:
        raw = await _call_template("generate_mc", variables, settings=settings)
        if not raw:
            return []
        cleaned = strip_json(raw)
        parsed = json.loads(cleaned)
        options = parsed.get("options", parsed) if isinstance(parsed, dict) else parsed
        if isinstance(options, list) and len(options) >= 3:
            return [str(o).strip() for o in options[:3]]
    except Exception:
        pass
    return []


async def generate_hint(question: str, answer: str,
                        settings: dict | None = None) -> str:
    """Erstellt eine Merkhilfe/Eselsbr\u00fccke f\u00fcr eine schwierige Karte."""
    variables = {"question": question, "answer": answer, "RULES": RULES}
    try:
        result = await _call_template("generate_hint", variables, settings=settings)
        return result or ""
    except Exception:
        return ""


async def summarize_topic(cards: list[dict], topic: str = "",
                          settings: dict | None = None) -> str:
    """Fasst eine Gruppe von Karten zu einer kompakten Zusammenfassung zusammen."""
    card_texts = "\n".join(f"- {c['question']} -> {c['answer']}" for c in cards[:20])
    variables = {"topic": topic, "card_texts": card_texts, "RULES": RULES}
    try:
        result = await _call_template("summarize_topic", variables, settings=settings)
        return result or ""
    except Exception:
        return ""


async def suggest_related(question: str, answer: str, all_cards: list[dict], limit: int = 3) -> list[str]:
    """Schl\u00e4gt thematisch verwandte Karten-IDs vor (basierend auf Schl\u00fcsselw\u00f6rtern)."""
    # Einfache Keyword-Matching-Strategie ohne KI (funktioniert auch offline)
    keywords = set(re.findall(r'\b[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]{4,}\b', f"{question} {answer}".lower()))
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
    # Nur horizontale Whitespace-Duplikate entfernen, Zeilenumbrueche erhalten
    text       = re.sub(r'[^\S\n]+', ' ', text)
    paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        is_heading = para.startswith('#')
        # Ueberschriften starten immer einen neuen Chunk
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
