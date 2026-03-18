# Learning-By-Tooling -- Entwicklerdokumentation

## Übersicht

Learning-By-Tooling ist eine selbst gehostete Lernkarten-Plattform (FastAPI + Svelte 5, Docker). Drittanbieter können fertige Lernpakete als ZIP-Dateien erstellen und bereitstellen. Nutzer installieren diese Pakete mit einem Klick direkt in der App.

---

## 1. Paketformat

Ein Lernpaket ist eine ZIP-Datei mit zwei Markdown-Dateien:

```
mein-paket-v1.0.zip
  |- mein-paket-fragen.md      (Fragen)
  +- mein-paket-antworten.md   (Antworten)
```

Die App erkennt die Dateien automatisch anhand des Namens:
- Datei mit `fragen` im Namen -> Fragen
- Datei mit `antwort` im Namen -> Antworten
- Fallback: erste und zweite `.md` Datei

Der Paketname wird aus dem ZIP-Dateinamen abgeleitet:
- `lernpakete-python-basics-v1.0.zip` -> `Python Basics`
- `api-kurs-v2.zip` -> `Api Kurs`

---

## 2. Fragen-Format

Jede Karte ist ein Markdown-Codeblock:

```markdown
```
K-001 | GB
Was ist eine REST API?
```
```

**Aufbau:**
```
K-{NR} | {KATEGORIE}
{FRAGETEXT}
```

- `K-{NR}` -- Eindeutige Karten-ID. Numerisch, dreistellig mit führenden Nullen empfohlen (K-001, K-042, K-105).
- `{KATEGORIE}` -- Zweistelliger Kategoriecode. Muss in der Ziel-Installation existieren.
- `{FRAGETEXT}` -- Beliebiger Text, auch mehrzeilig.

**Mehrere Karten:** Mit `---` oder Leerzeile trennen (optional, der Parser findet Blöcke automatisch).

**Vollständiges Beispiel:**
```markdown
# Python Grundlagen -- Fragen

---

```
K-001 | GB
Was ist Python?
```

---

```
K-002 | GB
Welche Datentypen gibt es in Python?
```

---

```
K-003 | AP
Wie öffnet man eine Datei in Python?
```
```

---

## 3. Antworten-Format

```markdown
```
A-001 | GB -> K-001
Eine interpretierte, dynamisch typisierte Programmiersprache.
Entwickelt von Guido van Rossum, erschienen 1991.
```
```

**Aufbau:**
```
A-{NR} | {KATEGORIE} -> K-{NR}
{ANTWORTTEXT}
```

- `A-{NR}` -- Antwort-ID. Muss zur K-ID passen.
- `{KATEGORIE}` -- Gleicher Code wie in der Frage.
- `-> K-{NR}` -- Verknüpfung zur Frage. Pflicht.
- `{ANTWORTTEXT}` -- Beliebiger Text, auch mehrzeilig, Code-Blöcke erlaubt.

**Vollständiges Beispiel:**
```markdown
# Python Grundlagen -- Antworten

---

```
A-001 | GB -> K-001
Interpretierte, dynamisch typisierte Hochsprache.
Erschienen 1991, entwickelt von Guido van Rossum.
Philosophie: Lesbarkeit und Einfachheit (PEP 20).
```

---

```
A-002 | GB -> K-002
Eingebaute Datentypen:
- int, float, complex (Zahlen)
- str (Text)
- list, tuple (Sequenzen)
- dict (Wörterbuch)
- set, frozenset (Mengen)
- bool (True/False)
- None (kein Wert)
```

---

```
A-003 | AP -> K-003
with open('datei.txt', 'r') as f:
    inhalt = f.read()

Modes: 'r' lesen, 'w' schreiben, 'a' anhängen, 'rb' binär lesen.
with-Statement schliesst die Datei automatisch.
```
```

---

## 4. Kategorie-Codes

Standard-Kategorien in jeder Installation:

| Code | Name | Verwendung |
|------|------|------------|
| `GB` | Grundbegriffe | Definitionen, Konzepte, Fachvokabular |
| `AK` | Akteure | Rollen, Personen, Organisationen |
| `GS` | Geschäftsprozesse | Abläufe, Workflows |
| `AP` | API | Endpunkte, Parameter, HTTP |
| `HA` | Hash | Kryptographie, Hashing |
| `OA` | OAuth2 | Authentifizierung, Token |
| `TC` | Test Cases | Tests, Zertifizierung |
| `MO` | Mock | Testumgebungen |
| `KA` | Kafka | Messaging, Events |
| `FE` | Fehler | Fehlerbehandlung, Debugging |
| `DB` | Datenmodell | Schemas, Datenstrukturen |
| `AL` | Allgemein | Alles was nicht passt |

Für themenspezifische Pakete: `GB` und `AL` verwenden wenn die spezifischen Codes nicht passen.

---

## 5. Schwierigkeitsgrade

Karten haben keinen Schwierigkeitsgrad im Import-Format -- der wird automatisch auf `Mittel (2)` gesetzt. Nutzer können ihn nachträglich anpassen.

---

## 6. ZIP-Datei erstellen

**macOS/Linux:**
```bash
zip mein-paket-v1.0.zip mein-paket-fragen.md mein-paket-antworten.md
```

**Namenskonvention:**
```
{thema}-{untertitel}-v{major}.{minor}.zip
```

Beispiele:
- `python-grundlagen-v1.0.zip`
- `rest-api-kurs-v2.1.zip`
- `docker-basics-v1.0.zip`

---

## 7. REST API

Die API ist unter `:8030` erreichbar. Swagger-Doku: `http://localhost:8030/docs`

**Authentifizierung:** Alle Endpunkte (außer `/api/auth/login` und `/api/health`) erfordern einen Bearer-Token im Header:
```
Authorization: Bearer <token>
```

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "admin"
}
```

**Antwort:**
```json
{
  "token": "eyJ...",
  "user": {"id": 1, "email": "admin@example.com", "display_name": "Admin"}
}
```

### Paket installieren (ZIP)

```http
POST /api/import/zip
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <zip-datei>
package_id: <optional, int>
```

**Antwort:**
```json
{
  "created": 105,
  "skipped": 0,
  "total": 105,
  "package_id": 3
}
```

### Paket installieren (Text)

```http
POST /api/import/markdown
Authorization: Bearer <token>
Content-Type: application/json

{
  "fragen": "<inhalt fragen.md>",
  "antworten": "<inhalt antworten.md>",
  "package_id": 3
}
```

### Pakete auflisten

```http
GET /api/packages
Authorization: Bearer <token>
```

**Antwort:**
```json
[
  {
    "id": 1,
    "name": "Python Grundlagen",
    "description": "...",
    "color": "#2196F3",
    "icon": "fa-graduation-cap",
    "card_count": 105,
    "doc_count": 0,
    "draft_count": 0
  }
]
```

---

## 8. Validierung

Bevor du ein Paket veröffentlichst, prüfe mit diesem Python-Script:

```python
import re

def validate_bundle(fragen_path, antworten_path):
    card_pat = re.compile(
        r"```\s*\n(K-\w+)\s*\|\s*(\w+)\s*\n([\s\S]*?)```",
        re.MULTILINE
    )
    ans_pat = re.compile(
        r"```\s*\n(A-\w+)\s*\|[^\n]*\n([\s\S]*?)```",
        re.MULTILINE
    )

    fragen    = open(fragen_path).read()
    antworten = open(antworten_path).read()

    questions = {m.group(1): m.group(2) for m in card_pat.finditer(fragen)}
    answers   = {m.group(1).replace("A-","K-") for m in ans_pat.finditer(antworten)}

    missing = set(questions.keys()) - answers
    orphans = answers - set(questions.keys())

    print(f"Fragen:    {len(questions)}")
    print(f"Antworten: {len(answers)}")

    if missing:
        print(f"FEHLER -- Fragen ohne Antwort: {sorted(missing)}")
    if orphans:
        print(f"FEHLER -- Antworten ohne Frage: {sorted(orphans)}")
    if not missing and not orphans:
        print("OK -- Alle Karten vollständig")

validate_bundle("mein-paket-fragen.md", "mein-paket-antworten.md")
```

---

## 9. Vollständiges Minimal-Beispiel

**fragen.md:**
```markdown
# Mein Kurs -- Fragen

```
K-001 | GB
Was ist X?
```

```
K-002 | GB
Wie funktioniert Y?
```
```

**antworten.md:**
```markdown
# Mein Kurs -- Antworten

```
A-001 | GB -> K-001
X ist eine Methode zur...
```

```
A-002 | GB -> K-002
Y funktioniert indem...
```
```

**ZIP erstellen:**
```bash
zip mein-kurs-v1.0.zip fragen.md antworten.md
```

**Importieren:**
1. App öffnen -> Alle Pakete
2. ZIP-Datei in das Ablage-Feld ziehen
3. Installieren klicken
4. Fertig -- Paket erscheint in der Liste

---

## 10. Technische Details

| Eigenschaft | Wert |
|-------------|------|
| Backend | Python 3.11, FastAPI |
| Frontend | Svelte 5, Vite |
| Datenbank | SQLite mit FTS5 |
| Port Backend | 8030 |
| Port Frontend | 8031 |
| Deployment | Docker Compose |
| API-Doku | http://localhost:8030/docs |

---

## 11. Eigene Bundles bereitstellen

Wenn du Bundles serverseitig bereitstellen willst (erscheinen automatisch unter "Lernpakete installieren"):

1. Dateien in den `lernpakete/`-Ordner legen
2. `bundles.json` anpassen:

```json
[
  {
    "id": "mein-paket",
    "name": "Mein Paket",
    "description": "Beschreibung fuer den Nutzer",
    "color": "#2196F3",
    "icon": "fa-graduation-cap",
    "version": "1.0",
    "fragen_file": "mein-paket-fragen.md",
    "antwort_file": "mein-paket-antworten.md"
  }
]
```

3. Docker-Container neu starten -- Bundle erscheint sofort in der App.

**Icons:** Beliebige `fa-*` Klassen aus FontAwesome 6 Free.
**Farben:** Hex-Werte empfohlen.
