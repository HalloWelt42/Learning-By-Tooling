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
K-001 | GB
Was bedeutet API?
```
````

Aufbau:
- `K-001` -- Karten-Nummer (fortlaufend)
- `GB` -- Kategorie (siehe Tabelle unten)
- Danach der Fragetext (kann auch mehrere Zeilen lang sein)

### Antworten-Datei

Jede Antwort verweist auf ihre Frage:

````
```
A-001 | GB -> K-001
API steht fuer Application Programming Interface.
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

Nutze dieses Format fuer jede Frage:

---

```                          (drei Backticks)
K-001 | GB
[Fragetext]
```                          (drei Backticks)

---

Regeln:
- Nummeriere fortlaufend: K-001, K-002, K-003 usw.
- Nutze diese Kategorien: GB (Grundlagen), TH (Theorie),
  PX (Praxis), VF (Verfahren), PR (Pruefung), AL (Allgemein)
- Fragen sollen klar und eindeutig beantwortbar sein
- Mische leichte und schwere Fragen
- Keine Multiple-Choice -- offene Fragen
```

### 2. Prompt für die Antworten

Wenn du die Fragen hast, nutze diesen Prompt:

```
Erstelle zu jeder der folgenden Fragen eine praezise Antwort.

Nutze dieses Format:

---

```                          (drei Backticks)
A-001 | GB -> K-001
[Antworttext]
```                          (drei Backticks)

---

Regeln:
- A-Nummer = K-Nummer der zugehoerigen Frage
- Antworten sollen knapp aber vollstaendig sein
- Keine Einleitungen wie "Die Antwort lautet..."
- Direkt zur Sache

Hier sind die Fragen:

[FRAGEN HIER EINFUEGEN]
```

### 3. Prompt für Lernmaterial

Optional kannst du die KI auch bitten, ein Begleitdokument zu erstellen:

```
Schreibe einen kompakten Lehrtext zum Thema "[DEIN THEMA]".

Regeln:
- Maximal 2000 Woerter
- Strukturiere mit Ueberschriften
- Erklaere die wichtigsten Konzepte
- Nutze Beispiele
- Kein Markdown-Overkill, halte es lesbar
- Der Text dient als Nachschlagewerk fuer die Lernkarten

Speichere den Text als .md Datei.
```

### 4. Qualitaet pruefen

Wichtig: Lies die generierten Inhalte durch!
Die KI kann Fehler machen. Pruefe besonders:
- Sind die Fakten korrekt?
- Sind die Antworten eindeutig?
- Gibt es Widersprueche zwischen Fragen und Antworten?
- Ist die Schwierigkeit angemessen?

### 5. ZIP bauen und hochladen

Speichere die Dateien und packe sie als ZIP:
- `mein-thema-fragen.md`
- `mein-thema-antworten.md`
- `mein-thema-lehrtext.md` (optional)

Hochladen: In der App auf "Lernpakete" -> "Paket aus ZIP installieren".

---

## Tipps fuer gute Lernkarten

1. **Eine Frage, ein Konzept** -- nicht mehrere Themen in eine Frage packen
2. **Konkret fragen** -- "Was ist X?" statt "Erklaere X"
3. **Schwierigkeit mischen** -- leichte Einstiegsfragen und anspruchsvolle Vertiefung
4. **Praxisbezug** -- "Wann nutzt man X?" ist besser als "Definiere X"
5. **Keine Ja/Nein-Fragen** -- die sind zu einfach zu raten
6. **Antworten knapp halten** -- 1-5 Saetze, kein Roman

---

## Checkliste

```
[ ] Fragen-Datei: Jede Karte hat K-Nummer und Kategorie
[ ] Antworten-Datei: Jede Antwort verweist auf ihre Frage (A-001 -> K-001)
[ ] Jede Frage hat genau eine Antwort
[ ] Keine doppelten Karten-Nummern
[ ] ZIP-Datei erstellt mit allen Dateien
[ ] Inhalte auf Korrektheit geprueft
```
