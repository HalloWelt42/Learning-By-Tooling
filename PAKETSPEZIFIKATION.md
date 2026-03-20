# Lernpakete erstellen -- Anleitung

---

## Was ist ein Lernpaket?

Ein Lernpaket ist eine abgeschlossene Themenwelt. Es enthält:
- **Lernkarten** (Frage + Antwort)
- **Lernmaterial** (Texte, Bilder, PDFs) -- optional
- **Lexikon-Einträge** -- optional

Du kannst Lernpakete selbst erstellen oder von anderen übernehmen.

---

## So erstellst du ein Lernpaket

### Schritt 1: Thema festlegen

Überlege dir ein Thema und einen kurzen Namen.
- Beispiel: "Python Grundlagen", "Erste-Hilfe-Kurs", "Projektmanagement"

### Schritt 2: Fragen und Antworten schreiben

Du brauchst zwei Textdateien:
- Eine Datei mit Fragen
- Eine Datei mit Antworten

Beide Dateien folgen einem einfachen Format (siehe unten).

### Schritt 3: Als ZIP hochladen

Packe beide Dateien in eine ZIP-Datei und lade sie in der App hoch.
Die App erkennt automatisch was Fragen und was Antworten sind.

---

## Das Karten-Format

### Fragen-Datei

Jede Frage steht in einem eigenen Block:

````
```
K-001 | Grundlagen
Was bedeutet API?
```
````

Aufbau:
- `K-001` -- Karten-Nummer (fortlaufend)
- `Grundlagen` -- Kategorie (siehe Tabelle unten, voller Name oder Kurzcode)
- Danach der Fragetext (kann auch mehrere Zeilen lang sein)

### Antworten-Datei

Jede Antwort verweist auf ihre Frage:

````
```
A-001 | Grundlagen -> K-001
API steht für Application Programming Interface.
Es ist eine Schnittstelle über die Programme
miteinander kommunizieren.
```
````

Aufbau:
- `A-001` -- Antwort-Nummer (gleiche Nummer wie die Frage)
- `-> K-001` -- Verknüpfung zur Frage
- Danach der Antworttext (beliebig lang)

---

## Kategorien

Jede Karte gehört zu einer Kategorie. Du kannst aus diesen wählen:

| Code | Name         | Wofür geeignet                              |
|------|--------------|---------------------------------------------|
| GB   | Grundlagen   | Definitionen, Konzepte, Fachbegriffe        |
| TH   | Theorie      | Theoretisches Wissen, Zusammenhänge         |
| PX   | Praxis       | Praktische Anwendung, Übungen               |
| VF   | Verfahren    | Abläufe, Prozesse, Methoden                 |
| PR   | Prüfung      | Prüfungsrelevante Fragen                    |
| VT   | Vertiefung   | Weiterführende, schwierige Themen           |
| AL   | Allgemein    | Alles was in keine andere Kategorie passt   |

Wenn du unsicher bist, nimm einfach AL (Allgemein).

---

## Lernmaterial hinzufügen (optional)

Du kannst zusätzlich Lernmaterial in die ZIP-Datei packen:

- **Texte** (.md, .txt) -- werden automatisch als Lernmaterial erkannt
- **Bilder** (.png, .jpg) -- werden in der Medien-Ansicht angezeigt
- **PDFs** (.pdf) -- werden als Download-Links bereitgestellt

Das Material wird dem Paket zugeordnet und steht beim Lernen
über den "Im Material nachlesen"-Link zur Verfügung.

---

## ZIP-Datei zusammenbauen

So sieht eine fertige ZIP-Datei aus:

```
mein-thema-v1.0.zip
  |- mein-thema-fragen.md       (Pflicht)
  |- mein-thema-antworten.md    (Pflicht)
  |- einfuehrung.md             (optional -- Lernmaterial)
  |- diagramm.png               (optional -- Bild)
  |- zusammenfassung.pdf        (optional -- PDF)
```

### Namensregeln:
- Kleinbuchstaben, Bindestrich statt Leerzeichen
- Keine Sonderzeichen, keine Umlaute im Dateinamen
- Versionsnummer im ZIP-Namen: v1.0, v1.1, v2.0 usw.

---

## Lernpaket mit KI erstellen (z.B. Claude, ChatGPT)

Du kannst eine KI nutzen um schnell hochwertige Lernkarten zu erstellen.
So geht es:

### 1. Prompt für die Fragen

Kopiere diesen Text und passe ihn an dein Thema an:

```
Erstelle 20 Lernkarten zum Thema "[DEIN THEMA]".

Nutze dieses Format für jede Frage:

---

```                          (drei Backticks)
K-001 | GB
[Fragetext]
```                          (drei Backticks)

---

Regeln:
- Nummeriere fortlaufend: K-001, K-002, K-003 usw.
- Nutze diese Kategorien als vollen Namen nach dem Pipe-Zeichen:
  Grundlagen, Theorie, Praxis, Verfahren, Prüfung, Vertiefung, Allgemein
- Fragen sollen klar und eindeutig beantwortbar sein
- Mische leichte und schwere Fragen
- Keine Multiple-Choice -- offene Fragen
```

### 2. Prompt für die Antworten

Wenn du die Fragen hast, nutze diesen Prompt:

```
Erstelle zu jeder der folgenden Fragen eine präzise Antwort.

Nutze dieses Format:

---

```                          (drei Backticks)
A-001 | GB -> K-001
[Antworttext]
```                          (drei Backticks)

---

Regeln:
- A-Nummer = K-Nummer der zugehörigen Frage
- Antworten sollen knapp aber vollständig sein
- Keine Einleitungen wie "Die Antwort lautet..."
- Direkt zur Sache

Hier sind die Fragen:

[FRAGEN HIER EINFÜGEN]
```

### 3. Prompt für Lernmaterial

Optional kannst du die KI auch bitten, ein Begleitdokument zu erstellen:

```
Schreibe einen kompakten Lehrtext zum Thema "[DEIN THEMA]".

Regeln:
- Maximal 2000 Wörter
- Strukturiere mit Überschriften
- Erkläre die wichtigsten Konzepte
- Nutze Beispiele
- Kein Markdown-Overkill, halte es lesbar
- Der Text dient als Nachschlagewerk für die Lernkarten

Speichere den Text als .md Datei.
```

### 4. Qualität prüfen

Wichtig: Lies die generierten Inhalte durch!
Die KI kann Fehler machen. Prüfe besonders:
- Sind die Fakten korrekt?
- Sind die Antworten eindeutig?
- Gibt es Widersprüche zwischen Fragen und Antworten?
- Ist die Schwierigkeit angemessen?

### 5. ZIP bauen und hochladen

Speichere die Dateien und packe sie als ZIP:
- `mein-thema-fragen.md`
- `mein-thema-antworten.md`
- `mein-thema-lehrtext.md` (optional)

Hochladen: In der App auf "Lernpakete" -> "Paket aus ZIP installieren".

---

## Tipps für gute Lernkarten

1. **Eine Frage, ein Konzept** -- nicht mehrere Themen in eine Frage packen
2. **Konkret fragen** -- "Was ist X?" statt "Erkläre X"
3. **Schwierigkeit mischen** -- leichte Einstiegsfragen und anspruchsvolle Vertiefung
4. **Praxisbezug** -- "Wann nutzt man X?" ist besser als "Definiere X"
5. **Keine Ja/Nein-Fragen** -- die sind zu einfach zu raten
6. **Antworten knapp halten** -- 1-5 Sätze, kein Roman

---

## Checkliste

```
[ ] Fragen-Datei: Jede Karte hat K-Nummer und Kategorie
[ ] Antworten-Datei: Jede Antwort verweist auf ihre Frage (A-001 -> K-001)
[ ] Jede Frage hat genau eine Antwort
[ ] Keine doppelten Karten-Nummern
[ ] ZIP-Datei erstellt mit allen Dateien
[ ] Inhalte auf Korrektheit geprüft
```
