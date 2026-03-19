# Learning-By-Tooling

Selbst gehostete Lernkarten-Plattform mit Mehrbenutzersystem.
Kein Cloud-Zwang, kein Tracking, keine Abos -- alles läuft lokal.

**Stack:** Python 3.11 / FastAPI - Svelte 5 / Vite - SQLite / FTS5 - Docker Compose
**Sprachmodell:** LM Studio (lokal, kein API-Key nötig)
**Ports:** Backend :8030 - Frontend :8031
**Version:** 0.4.0

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
- Kategorien: GB, TH, PX, VF, PR, VT, AL (Grundlagen bis Allgemein)
- FTS5-Volltextsuche über alle Karten

### Lernmodi
- **Karteikarte** -- Aufdecken, Selbsteinschätzung (Richtig / Skip / Falsch), 2-Spalten-Layout
- **Multiple Choice** -- 4 Optionen (1 richtig + 3 KI-generierte Distraktoren), Auto-Bewertung
- **Freitext** -- Antwort eintippen, KI bewertet mit Score + detailliertem Feedback
- **Spaced Repetition (SRS)** -- SM-2 Algorithmus, Quality-Bewertung (Blackout bis Perfekt)

Alle Modi nutzen Backend-strikte Sessions: Kartenreihenfolge und Fortschritt werden serverseitig gespeichert. Kein State-Verlust bei Seitenwechsel oder Browser-Neustart.

### Sprachmodell-Funktionen (faktenbasiert, kein Halluzinieren)
- Karten-Erklärung auf Basis der Paket-Lerndokumente
- Freitext-Bewertung gegen korrekte Antwort (Score 0-100% + Feedback)
- MC-Distraktoren: plausible falsche Antworten generieren und cachen
- Karten-Generierung aus Dokument-Chunks (TXT, MD, PDF, DOCX)
- Fehleranalyse nach Lernsession mit Quellverweisen in Dokumenten
- Auto-Modell-Erkennung aus LM Studio

### Mehrbenutzersystem
- Token-basierte Authentifizierung (JWT)
- Eigener Lernfortschritt pro Benutzer (Sessions, Reviews, SRS-Daten)
- Gemeinsame Pakete und Karteninhalte
- Passwort-Änderung in der App

### Dokumente
- Upload: TXT, Markdown, PDF, DOCX
- Automatisches Chunking in überlappende Abschnitte
- Abschnitte einzeln oder alle für Generierung auswählen
- Entwürfe-Workflow: Karten prüfen vor Freigabe

### Fortschritt und Abzeichen
- 6 Abzeichen-Kategorien: Ausdauer, Wissenssammler, Serie, Entdecker, Makellos, Beständig
- 30-Stufen-System mit 10 Farben (Weiß bis Platin) und je 3 Sternen
- Lernhistorie: alle Sessions mit Ergebnis und Modus
- Qualitäts- und Zeitmessung pro Karte (Rolling Average)

### Weitere Features
- Lexikon: Glossar pro Paket mit Volltextsuche
- Lernpfade: geordnete Kartensequenzen mit Kapiteln
- Globale Volltextsuche über Karten, Lexikon, Dokumente
- Guide: In-App 5-Schritt-Workflow-Anleitung

---

## Architektur

```
backend/
    main.py               FastAPI App + CORS + Router
    auth.py               JWT-Token, Passwort-Hashing, Benutzerverwaltung
    db.py                 SQLite Schema + Migrationen
    schemas.py            Pydantic-Modelle (Request/Response)
    services.py           Sprachmodell-Anbindung, Chunker, SM-2
    helpers.py            FTS-Rebuild, Karten-ID-Generator
    routes/
        ai.py             KI-Endpunkte (Erklärung, Hint, MC-Generierung)
        auth.py           Login, Passwort, Benutzerverwaltung
        cards.py          Karten CRUD + Statistik
        import_export.py  ZIP/Markdown-Import, Bundle-Install
        packages.py       Pakete, Dokumente, Lexikon, Pfade
        sessions.py       Sessions, Reviews, Achievements
    requirements.txt
frontend/src/
    app.css               Design-System, CSS-Variablen auf :root
    App.svelte            Root, Sidebar, Hash-Router, Login
    lib/
        components/
            learn/
                Learn.svelte            Orchestrator: Setup, Routing, Ergebnis
                SessionBar.svelte       Fortschritt, Score, Breadcrumb
                CardStandard.svelte     Aufdecken + Selbstbewertung
                CardMC.svelte           Multiple Choice (4 Optionen)
                CardWrite.svelte        Freitext + KI-Bewertung
                CardSRS.svelte          Spaced Repetition (SM-2)
                AiProcess.svelte        KI-Fortschrittsanzeige
                MistakeAnalysis.svelte  Fehleranalyse mit Dokumentverweisen
            packages/
                Packages.svelte         Startseite: Bundles, ZIP-Upload, Grid
                PackageDetail.svelte    Tabs: Übersicht/Dokumente/Karten/Lexikon/Pfade
            progress/
                Progress.svelte         Abzeichen + Lernhistorie
                ShieldBadge.svelte      Badge-Rendering (4 Tier-Stufen)
            shared/
                Login.svelte            Anmeldebildschirm
                Search.svelte           Globale Volltextsuche
                Guide.svelte            Workflow-Anleitung
                Admin.svelte            Verwaltung
        stores/index.js     Globale Stores (packages, categories, aiOnline, etc.)
        utils/
            api.js          HTTP-Wrapper (GET/POST/DELETE mit Auth)
            router.js       Hash-Router
            version.js      VERSION = '0.4.0'
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
| MC-Distraktoren | Frage + korrekte Antwort |
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
