# Learning-By-Tooling

Selbst gehostete Lernkarten-Plattform mit Mehrbenutzersystem.
Kein Cloud-Zwang, kein Tracking, keine Abos -- alles läuft lokal.

**Stack:** Python 3.11 / FastAPI - Svelte 5 / Vite - SQLite / FTS5 - Docker Compose
**Sprachmodell:** LM Studio (lokal, kein API-Key nötig)
**Ports:** Backend :8030 - Frontend :8031

---

## Features

### Paketsystem
- Unbegrenzte Pakete, jedes mit Farbe und Icon
- One-Click-Install aus serverseitigen Bundles (bundles.json)
- ZIP-Upload per Drag & Drop -- Paketname wird automatisch erkannt
- Sauberes Zurückziehen -- löscht Karten, Dokumente, Fortschritt, Lexikon atomar
- Neuinstallation nach Zurückziehen ohne Chaos

### Lernkarten
- Import aus Markdown-Dateien (K-001 | GB / A-001 | GB Format)
- ZIP-Import (Fragen + Antworten zusammen)
- Generierung aus hochgeladenen Dokumenten (Entwürfe mit Freigabe-Workflow)
- Manuelle Erstellung und Bearbeitung in der App
- 12 Kategoriecodes: GB AK GS AP HA OA TC MO KA FE DB + AL
- FTS5-Volltextsuche über alle Karten

### Lernmodi
- **Karteikarte** -- Aufdecken, Selbsteinschätzung (Richtig / Fast / Falsch)
- **Freitext** -- Antwort eintippen, optionale Bewertung per Sprachmodell
- **Spaced Repetition (SRS)** -- SM-2 Algorithmus, nur fällige Karten

### Sprachmodell-Funktionen (faktenbasiert, kein Halluzinieren)
- Karten-Erklärung auf Basis der Paket-Lerndokumente
- Freitext-Bewertung gegen korrekte Antwort
- Karten-Generierung aus Dokument-Chunks (TXT, MD, PDF, DOCX)
- Fehleranalyse nach Lernsession mit Quellverweisen
- Auto-Modell-Erkennung aus LM Studio

### Mehrbenutzersystem
- Token-basierte Authentifizierung (JWT)
- Eigener Lernfortschritt pro Benutzer (Sessions, Reviews, SRS-Daten)
- Gemeinsame Pakete und Karteninhalte

### Dokumente
- Upload: TXT, Markdown, PDF, DOCX
- Automatisches Chunking in überlappende Abschnitte
- Abschnitte einzeln oder alle für Generierung auswählen
- Entwürfe-Workflow: Karten prüfen vor Freigabe

### Weitere Features
- Fortschritt: globale Stats, Abzeichen, Lernhistorie
- Lexikon: Glossar pro Paket mit Volltextsuche
- Lernpfade: geordnete Kartensequenzen
- Guide: In-App 5-Schritt-Workflow-Anleitung

---

## Architektur

```
backend/
    main.py             FastAPI, alle Endpunkte + Auth
    auth.py             JWT-Token, Passwort-Hashing, Benutzerverwaltung
    db.py               SQLite Schema + Migration
    services.py         Sprachmodell-Anbindung, Chunker, SM-2
    requirements.txt
frontend/src/
    app.css             Design-System, CSS-Variablen auf :root
    App.svelte          Root, Navigation, Routing, Login
    lib/components/
        Login.svelte            Anmeldebildschirm
        Packages.svelte         Startseite: Bundles, ZIP-Upload, Paket-Grid
        PackageDetail.svelte    Tabs: Uebersicht/Dokumente/Karten/Lexikon/Pfade/Import
        Learn.svelte            3 Lernmodi + Ergebnis + Fehleranalyse
        MistakeAnalysis.svelte  2-Tab-Fehleranalyse (Auszüge / Dokument)
        Progress.svelte         Fortschritt, Abzeichen, Verlauf
        Guide.svelte            Workflow-Anleitung
        Dashboard.svelte        Globale Statistik
        Documents.svelte        Dokument-Upload + Chunks
        Cards.svelte            Kartenansicht + Bearbeitung
        Lexicon.svelte          Glossar
        Paths.svelte            Lernpfade
        Search.svelte           Globale Volltextsuche
docker-compose.yml
start-mac.sh
update.sh
```

---

## Installation

### Erstinstallation (Raspberry Pi)

```bash
cd ~
mkdir -p data uploads
docker compose up -d
```

`http://192.168.178.49:8031`

Standard-Login: `admin@example.com` / `admin`

### Entwicklung (Mac)

```bash
chmod +x start-mac.sh && ./start-mac.sh
```

---

## Updates

Das Update-Script ersetzt nur Code -- niemals `data/` oder `uploads/`.
DB-Backup wird vor jedem Update angelegt.

---

## Lernpakete

### ZIP hochladen
Startseite -> Bereich "Paket aus ZIP installieren" -> Datei reinziehen -> Installieren.
Format: siehe `PAKETSPEZIFIKATION.md`

### Serverseitige Bundles
Dateien in `lernpakete/` + `bundles.json` eintragen -> Docker neu starten.

### Paket zurückziehen und neu einrichten
1. Paket-Karte -> Mülleimer -> Bestätigen
2. ZIP erneut hochladen -> Installieren

---

## Sprachmodell

**Verbindung:** LM Studio auf `192.168.178.45:1234`

Auto-Erkennung: Nimmt das erste geladene Modell.
Status: grüner Punkt in Sidebar = erreichbar + Modell geladen.

### Kontext-Prinzip
Das Sprachmodell bekommt Fakten geliefert -- es halluziniert nicht:

| Funktion | Mitgelieferter Kontext |
|----------|------------------------|
| Karte erklären | Alle Paket-Lerndokumente (bis 80.000 Zeichen) |
| Freitext bewerten | Korrekte Antwort + Dokumentkontext |
| Karten generieren | Chunk + Gesamtdokument-Orientierung |
| Fehleranalyse | Alle Dokument-Chunks mit IDs |

---

## Datenpersistenz

```
data/      Datenbank -- überlebt alles
uploads/   Dokumente -- überlebt alles
```

**Niemals löschen:** `data/` und `uploads/`

---

## Umgebungsvariablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| DB_PATH | ./lbt.db | SQLite-Pfad |
| UPLOAD_DIR | ../uploads | Dokument-Upload-Verzeichnis |
| BUNDLES_PATH | ../lernpakete | Bundle-Verzeichnis |
| JWT_SECRET | (dev-default) | Geheimer Schlüssel für Token-Signierung |
| TOKEN_EXPIRE_HOURS | 168 | Token-Gültigkeit in Stunden (Standard: 7 Tage) |

API-Doku (Swagger): `http://localhost:8030/docs`
