# Learning-By-Tooling -- Paketspezifikation v1.0

---

## 1. Zweck dieses Dokuments

Dieses Dokument definiert verbindlich wie Lernpakete erstellt,
benannt, versioniert und verwaltet werden müssen.

---

## 2. Paket-ID

Jedes Paket hat eine eindeutige, unveränderliche ID.

### Regeln:
- Nur Kleinbuchstaben, Zahlen und Bindestrich
- Kein Leerzeichen, kein Unterstrich, kein Punkt
- Format: `{thema}-{untertitel}` (ohne Versionsnummer)
- Länge: 3-50 Zeichen
- Einmal vergeben -> NIEMALS ändern

### Korrekt:
```
python-grundlagen
rest-api-kurs
docker-basics
```

### Falsch:
```
Python_Grundlagen     <- Grossbuchstaben, Unterstrich
python-grundlagen-v2  <- Versionsnummer in der ID
python grundlagen     <- Leerzeichen
python.grundlagen     <- Punkt
```

---

## 3. Dateinamen

### Pflichtschema:
```
{paket-id}-fragen.md
{paket-id}-antworten.md
```

### Korrekt:
```
python-grundlagen-fragen.md
python-grundlagen-antworten.md
```

### Falsch:
```
fragen.md                         <- Kein Paket-Prefix
python-fragen-v2.md               <- Versionsnummer im Dateinamen
Python-Grundlagen-Fragen.md       <- Grossbuchstaben
python_grundlagen_fragen.md       <- Unterstrich statt Bindestrich
```

---

## 4. ZIP-Dateiname

### Pflichtschema:
```
{paket-id}-v{major}.{minor}.zip
```

### Korrekt:
```
python-grundlagen-v1.0.zip
rest-api-kurs-v2.1.zip
docker-basics-v1.3.zip
```

---

## 5. ZIP-Inhalt

### Mindestinhalt:
```
{paket-id}-v{major}.{minor}.zip
  |- {paket-id}-fragen.md        (Pflicht)
  +- {paket-id}-antworten.md     (Pflicht)
```

### Optional erlaubt:
```
  +- README.md                   (Beschreibung des Pakets)
```

### VERBOTEN im ZIP:
- Unterordner
- Andere Dateitypen außer .md und .txt
- Mehrere Fragen-Dateien
- Mehrere Antworten-Dateien
- bundles.json (gehört nicht in User-ZIPs)

---

## 6. Karten-ID

### Format:
```
K-{NNN}
```

Wobei {NNN} eine Zahl mit mindestens einer Stelle ist.
Führende Nullen empfohlen für Sortierbarkeit.

### Korrekt:
```
K-001   K-042   K-100   K-310
```

### Falsch:
```
K001        <- Bindestrich fehlt
k-001       <- Kleinbuchstabe
KARTE-001   <- Falscher Prefix
001         <- Kein K-Prefix
```

### Eindeutigkeit:
- Innerhalb eines Pakets muss jede K-ID eindeutig sein
- Zwischen Paketen dürfen K-IDs übereinstimmen
- Einmal vergeben -> NIEMALS recyceln
- Neue Karten bekommen immer neue IDs

---

## 7. Fragen-Format

### Vollständiges Format:
````
```
K-{NNN} | {KATEGORIE}
{Fragetext -- beliebig mehrzeilig}
```
````

### Regeln:
- Exakt drei Backticks öffnen und schließen
- Erste Zeile: K-ID, Pipe, Kategoriecode -- NICHTS sonst
- Fragetext ab zweiter Zeile
- Keine Leerzeile zwischen Kopfzeile und Fragetext

---

## 8. Antworten-Format

### Vollständiges Format:
````
```
A-{NNN} | {KATEGORIE} -> K-{NNN}
{Antworttext -- beliebig mehrzeilig, Code erlaubt}
```
````

### Regeln:
- A-Nummer muss zur K-Nummer passen: A-042 gehört zu K-042
- Kategorie muss identisch zur Frage sein
- Antworttext darf Codeblocks, Listen, Tabellen enthalten

---

## 9. Kategorie-Codes

### Erlaubte Codes (Standard-Installation):
```
GB   Grundbegriffe
AK   Akteure
GS   Geschaeftsprozesse
AP   API
HA   Hash
OA   OAuth2
TC   Test Cases
MO   Mock
KA   Kafka
FE   Fehler
DB   Datenmodell
AL   Allgemein
```

### Regeln:
- Immer GROSSBUCHSTABEN
- Immer genau 2 Zeichen
- Nur aus der obigen Liste
- Kein eigener Code erlaubt ohne vorherige Registrierung in db.py

---

## 10. bundles.json -- nur für serverseitige Pakete

bundles.json gehört ausschließlich in den `lernpakete/`-Ordner
der Server-Installation. Sie darf NICHT in User-ZIPs enthalten sein.

### Pflichtfelder pro Bundle:
```json
{
  "id":           "mein-paket",
  "name":         "Mein Paket",
  "description":  "Beschreibung für den Nutzer",
  "color":        "#2196F3",
  "icon":         "fa-graduation-cap",
  "version":      "1.0",
  "fragen_file":  "mein-paket-fragen.md",
  "antwort_file": "mein-paket-antworten.md"
}
```

---

## 11. Vollständigkeitsprüfung

Jede Frage MUSS eine Antwort haben. Jede Antwort MUSS eine Frage haben.

---

## 12. Versionierung

- Jede inhaltliche Änderung erhöht die Minor-Version: 1.0 -> 1.1
- Jede Neustrukturierung erhöht Major: 1.x -> 2.0
- IDs werden NIEMALS wiederverwendet

---

## 13. Checkliste vor Einreichung

```
[ ] Paket-ID: kleinbuchstaben-mit-bindestrich, keine Version in der ID
[ ] Dateinamen: {paket-id}-fragen.md und {paket-id}-antworten.md
[ ] ZIP-Name: {paket-id}-v{major}.{minor}.zip
[ ] Karten-IDs: K-001 Format, keine Luecken, keine Duplikate
[ ] Jede K-ID hat genau eine A-ID (gleiche Nummer)
[ ] Kategoriecodes: Nur 2-stellige Grossbuchstaben aus der erlaubten Liste
[ ] Validierungsskript ausgefuehrt: 0 fehlend, 0 verwaist
[ ] Kein Unterordner im ZIP
[ ] Keine bundles.json im ZIP
```
