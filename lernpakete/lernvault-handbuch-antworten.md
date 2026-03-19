# LernVault Handbuch -- ANTWORTEN

---

```
A-001 | Grundlagen → K-001
LernVault ist eine selbst gehostete Lernkarten-App fuer erwachsene Professionals. Sie laeuft auf einem Raspberry Pi und bietet vier Lernmodi mit KI-Unterstuetzung durch ein lokales Sprachmodell (LM Studio). Ziel: Fachwissen gezielt und nachhaltig trainieren, ohne Cloud-Abhaengigkeit.
```

---

```
A-002 | Grundlagen → K-002
1. FastAPI (Python 3.11) als Backend mit SQLite-Datenbank
2. Svelte 5 als Frontend (SPA mit Hash-Routing)
3. Docker Compose fuer Deployment (Backend-Container + Frontend-Container)

Optional: LM Studio als lokaler KI-Server fuer MC-Generierung und Freitext-Bewertung.
```

---

```
A-003 | Grundlagen → K-003
Ein Lernpaket ist eine abgeschlossene Themenwelt. Es muss mindestens zwei Markdown-Dateien enthalten:
1. Eine Fragen-Datei ({paket-id}-fragen.md)
2. Eine Antworten-Datei ({paket-id}-antworten.md)

Optional koennen Lernmaterial (Texte, Bilder, PDFs) und eine bundles.json beigelegt werden. Alles wird als ZIP hochgeladen.
```

---

```
A-004 | Grundlagen → K-004
1. Standard (Karteikarte): Frage sehen, Antwort aufdecken, selbst bewerten
2. Multiple Choice: KI generiert falsche Antwortoptionen, eine ist richtig
3. Freitext: Antwort frei eintippen, KI bewertet automatisch
4. Spaced Repetition (SRS): SM-2-Algorithmus steuert Wiederholungsintervalle
```

---

```
A-005 | Grundlagen → K-005
Lernmodus (Standard, SRS): Die Antwort kann vorher aufgedeckt werden. Es geht um Fleiß -- richtige und falsche Antworten bekommen die gleiche Basis-XP. Der Nutzer lernt durch Wiederholung.

Testmodus (MC, Freitext): Man kann nicht vorher nachschauen. Nur korrekte Antworten werden voll belohnt. Falsche Antworten geben nur 1 Trostpunkt. Hier wird tatsaechliches Wissen geprueft.
```

---

```
A-006 | Grundlagen → K-006
SRS steht fuer Spaced Repetition System. Es basiert auf dem SM-2-Algorithmus: Karten die man gut kann, kommen seltener (in Tagen/Wochen). Karten die man schlecht kann, kommen oefter (am naechsten Tag). Jede Bewertung veraendert den Ease-Faktor und das Intervall der Karte. Das Ziel: optimale Lerneffizienz durch gezielte Wiederholung kurz vor dem Vergessen.
```

---

```
A-007 | Theorie → K-007
Der SM-2-Algorithmus berechnet Wiederholungsintervalle:
1. Bewertung auf einer Skala (0-5, wobei 3+ als bestanden gilt)
2. Bei guter Bewertung: Intervall wird verlaengert (Faktor * vorheriges Intervall)
3. Bei schlechter Bewertung: Intervall wird auf 1 Tag zurueckgesetzt
4. Der Ease-Faktor passt sich an: gute Bewertungen erhoehen ihn, schlechte senken ihn
5. Minimum-Ease: 1.3 (verhindert zu kurze Intervalle bei schweren Karten)
```

---

```
A-008 | Theorie → K-008
Der Ease-Faktor (EF) ist ein persoenlicher Schwierigkeitsindikator pro Karte und Nutzer. Startwert: 2.5. Bei guten Bewertungen steigt er (max ~3.0), bei schlechten sinkt er (min 1.3). Ein niedriger EF bedeutet: die Karte ist fuer diesen Nutzer schwer, die Intervalle bleiben kuerzer. Ein hoher EF bedeutet: die Karte ist leicht, die Intervalle werden schnell laenger. In LernVault beeinflusst der EF auch die XP-Berechnung: schwere Karten (niedriger EF) geben mehr XP.
```

---

```
A-009 | Theorie → K-009
Die Self-Determination Theory (SDT) von Deci und Ryan beschreibt drei psychologische Grundbeduerfnisse:
1. Kompetenz: Das Gefuehl, besser zu werden (XP, Abzeichen, Fortschrittsanzeigen)
2. Autonomie: Selbst waehlen koennen (Modus, Paket, Tempo, Session-Laenge)
3. Soziale Eingebundenheit: Bei LernVault als Single-User-App ersetzt durch Selbstvergleich (Streaks, Meilensteine, Abzeichen)
```

---

```
A-010 | Theorie → K-010
Flow entsteht wenn Herausforderung und Faehigkeit im Gleichgewicht sind. LernVault setzt das so um:
- Schwere Karten geben mehr XP (1.4x), leichte weniger (0.7x)
- Der persoenliche Ease-Faktor sorgt dafuer, dass individuell schwere Karten staerker belohnt werden
- SRS haelt die Schwierigkeit im Sweet Spot: ~85% Erfolgsrate
- Speed-Bonus (3-5s) belohnt den Flow-Zustand, ohne Druck aufzubauen
```

---

```
A-011 | Theorie → K-011
Fixed-Ratio: Belohnung nach fester Anzahl Aktionen (z.B. 10 XP pro Karte). Vorhersagbar, gibt Sicherheit.

Variable-Ratio: Belohnung variiert (z.B. Speed-Bonus, Combo, Perfekte Session). Erzeugt hoechstes Engagement und Verhaltensresistenz gegen Extinktion.

LernVault nutzt beides: Basis-XP sind Fixed-Ratio (vorhersagbar), Boni sind Variable-Ratio (abhaengig vom eigenen Lernverhalten, nicht vom Zufall -- kein Slot-Machine-Design).
```

---

```
A-012 | Praxis → K-012
1. ZIP-Datei erstellen mit Fragen- und Antworten-Datei (siehe Paketformat)
2. In der App unter "Lernpakete" den Upload-Bereich nutzen
3. ZIP per Drag-and-Drop oder Klick hochladen
4. Die App erkennt automatisch Fragen, Antworten und optionales Lernmaterial
5. Das Paket erscheint sofort in der Sidebar und kann genutzt werden
```

---

```
A-013 | Praxis → K-013
1. "Lernen" in der Sidebar klicken
2. Optional ein bestimmtes Paket waehlen (oder "Alle")
3. Lernmodus waehlen (Standard, MC, Freitext, SRS)
4. Optional Kategorien filtern
5. Kartenanzahl waehlen (5, 10, 20, 30, 50 oder alle)
6. Auf den Start-Button klicken

Bei MC und Freitext muss LM Studio online sein.
```

---

```
A-014 | Praxis → K-014
Im Freitext-Modus tippt man die Antwort frei ein, ohne Antwortoptionen. Die lokale KI (LM Studio) bewertet dann automatisch: Was war richtig, was fehlte, was war falsch. Man bekommt einen Score und detailliertes Feedback. Optional kann man die Musterloesung anzeigen.

Besonders sinnvoll fuer: Pruefungsvorbereitung, Free Recall (nachweislich bessere Langzeitretention als Recognition), und wenn man sicher sein will, dass man den Stoff wirklich beherrscht.
```

---

```
A-015 | Praxis → K-015
Der Result-Screen zeigt:
- Prozent-Ring (farbcodiert: gruen ab 80%, rot unter 50%)
- Verdict-Text (Makellos/Ausgezeichnet/Sehr gut/Gut gemacht/Solide Basis/Weiter ueben)
- Statistik: Richtig, Falsch, Uebersprungen, Combo-Peak
- Silber-Muenzen verdient (animiertes Hochzaehlen) + Completion-Bonus
- Streak-Anzeige (Tagesstraehne)

Aktionen: Neue Session starten, Fehler analysieren (bei Fehlern), Zurueck zur Uebersicht.
```

---

```
A-016 | Praxis → K-016
Nach einer Session mit Fehlern erscheint der Button "X Fehler analysieren". Beim Klick werden die falsch beantworteten Karten an die KI (LM Studio) geschickt, zusammen mit den zugehoerigen Dokumenten-Chunks. Die KI identifiziert die relevanten Textstellen in den Lernmaterialien und erklaert, welche Konzepte nachgearbeitet werden sollten.
```

---

```
A-017 | Verfahren → K-017
XP = floor(Basis * Schwierigkeitsfaktor * Modusfaktor * Fortschrittsfaktor * Streak-Faktor) + Speed-Bonus

1. Basis: 10 (richtig/falsch im Lernmodus), 1 (skip)
2. Schwierigkeitsfaktor: Karten-Schwierigkeit (0.7/1.0/1.4) * persoenlicher Ease (2.8/ease)
3. Modusfaktor: Standard 1.0, SRS 1.2, MC 1.3, Freitext 1.5
4. Fortschrittsfaktor: 1.0 bis 1.5 je nach Intervall seit letztem Review
5. Streak-Faktor: 1.0 + 0.05 pro Combo (max 2.0)

Plus Speed-Bonus: +5 bei korrekter Antwort in 3-5 Sekunden.
```

---

```
A-018 | Verfahren → K-018
Lernmodus (Standard/SRS):
- Richtig: 10 Basis-XP (volle Formel)
- Falsch: 10 Basis-XP (gleich wie richtig -- Fleiß wird belohnt)
- Skip: 1 XP

Testmodus (MC/Freitext):
- Richtig: 10 Basis-XP (volle Formel mit hoeherem Modusfaktor)
- Falsch: 1 Trostpunkt (kein voller Durchlauf der Formel)
- Skip: 0 XP

Begruendung: Im Lernmodus kann man nachschauen, daher zaehlt Fleiß. Im Testmodus wird echtes Wissen geprueft.
```

---

```
A-019 | Verfahren → K-019
Der Anti-Gaming-Schutz verhindert, dass Nutzer durch schnelles Durchklicken XP sammeln. Wenn eine Frage in unter 3 Sekunden beantwortet wird (ausser bei Skip), bekommt der Nutzer stillschweigend 0 XP. Es gibt keinen sichtbaren Hinweis -- der Nutzer merkt nur, dass die XP-Anzeige sich nicht bewegt. So wird Durchklicken unattraktiv, ohne den Nutzer zu beschaemen.
```

---

```
A-020 | Verfahren → K-020
Das Waehrungssystem ist rein im Frontend implementiert:
- Silber: 1 XP = 1 Silber (Grundwaehrung)
- Gold: 1000 Silber = 1 Gold (angezeigt ab 1000 XP)
- Diamant: 1000 Gold = 1 Diamant (ab 1.000.000 XP)

Das Backend speichert nur den rohen XP-Integer. Die Umrechnung passiert im Frontend:
Diamanten = floor(xp / 1.000.000)
Gold = floor((xp % 1.000.000) / 1000)
Silber = xp % 1000
```

---

```
A-021 | Verfahren → K-021
Der Completion-Bonus wird am Session-Ende berechnet:

Stufe 1: +1 Silber wenn mindestens 5 Karten beantwortet wurden (egal ob richtig oder falsch)

Stufe 2: +20 Silber wenn mindestens 20 Karten beantwortet wurden UND alle fehlerfrei sind (0 Fehler). Dieser Bonus ersetzt den +1 Bonus.

Wichtig: Der 20er-Bonus erfordert null Fehler -- eine einzige falsche Antwort reduziert den Bonus auf +1.
```

---

```
A-022 | Verfahren → K-022
1. correct.mp3: Korrekte Antwort -- kurzer positiver Ton, spielt mit der Muenz-Float-Animation
2. error.mp3: Falsche Antwort -- sanfter Fehlerton
3. coin.mp3: Muenzenregen im Ergebnis-Screen (600ms nach Session-Ende)
4. bonus.mp3: Bonus-Sound beim XP-Hochzaehlen im Ergebnis (300ms nach Session-Ende)
5. perfect.mp3: Perfekte Session mit mindestens 20 Karten fehlerfrei (1200ms nach Session-Ende)

Alle abschaltbar per Sound-Toggle in den Einstellungen. Web Audio API, keine HTML-Audio-Elemente.
```

---

```
A-023 | Verfahren → K-023
Ebene 1 -- Karten-Schwierigkeit (aus der Karten-Definition, fuer alle Nutzer gleich):
- Leicht (1) = 0.7x
- Mittel (2) = 1.0x
- Schwer (3) = 1.4x

Ebene 2 -- Persoenlicher Ease-Faktor (SM-2, individuell pro Nutzer und Karte):
- Formel: 2.8 / max(ease, 1.3)
- Neue Karten (ease 2.5) = 1.12x
- Persoenlich schwere Karten (ease 1.3) = 2.15x

Beide werden multipliziert: difficulty_factor = card_diff_mult * personal_diff
Beispiel: Schwere Karte (1.4) mit persoenlich niedrigem Ease (1.65) = 2.31x XP.
```

---

```
A-024 | Verfahren → K-024
Fragen-Datei ({paket-id}-fragen.md):
Jede Frage in einem Codeblock mit Karten-ID und Kategorie:
K-001 | Grundlagen
Hier steht die Frage?

Antworten-Datei ({paket-id}-antworten.md):
Jede Antwort verweist auf ihre Frage:
A-001 | Grundlagen -> K-001
Hier steht die Antwort.

Regeln: Karten-IDs fortlaufend (K-001, K-002...), nie recyceln. Kategorien als Kurzcode (GB, TH, PX, VF, PR, VT, AL) oder voller Name. ZIP-Name: {paket-id}-v{major}.{minor}.zip
```

---

```
A-025 | Pruefung → K-025
1. GB (Grundlagen): Definitionen, Konzepte, Fachbegriffe
2. TH (Theorie): Theoretisches Wissen, Zusammenhaenge
3. PX (Praxis): Praktische Anwendung, Uebungen
4. VF (Verfahren): Ablaeufe, Prozesse, Methoden
5. PR (Pruefung): Pruefungsrelevante Fragen
6. VT (Vertiefung): Weiterfuehrende, schwierige Themen
7. AL (Allgemein): Alles was in keine andere Kategorie passt
```

---

```
A-026 | Pruefung → K-026
Berechnung fuer Standard-Modus, difficulty=3, korrekt, 4s, ease=2.5:

Basis: 10 (korrekt im Lernmodus)
Karten-Schwierigkeit: 1.4 (schwer)
Persoenlicher Ease: 2.8 / 2.5 = 1.12
Schwierigkeitsfaktor: 1.4 * 1.12 = 1.57
Modusfaktor: 1.0 (Standard)
Fortschrittsfaktor: 1.0 (neue Karte, interval <= 1)
Streak: 1.0 (kein Combo)
Speed-Bonus: +5 (korrekt in 3-5s)

XP = floor(10 * 1.57 * 1.0 * 1.0 * 1.0) + 5 = 15 + 5 = 20 XP
```

---

```
A-027 | Pruefung → K-027
Im Multiple-Choice-Modus (Testmodus) bekommt der Nutzer bei einer falschen Antwort nur 1 Trostpunkt. Die volle XP-Formel wird nicht durchlaufen. Begruendung: Im Testmodus kann man nicht vorher nachschauen -- es wird echtes Wissen geprueft, nicht Fleiß. Falsche Antworten sollen nicht gleich belohnt werden wie richtige.
```

---

```
A-028 | Pruefung → K-028
Wenn eine Frage in unter 3 Sekunden beantwortet wird (und es kein Skip ist), greift der Anti-Gaming-Schutz: Der Nutzer bekommt stillschweigend 0 XP. Es gibt keinen sichtbaren Hinweis oder Fehlermeldung. Die Antwort wird trotzdem gezaehlt (richtig/falsch/skip), nur die XP werden nicht vergeben. So wird schnelles Durchklicken unattraktiv.
```

---

```
A-029 | Pruefung → K-029
Der Completion-Bonus betraegt +20 Silber. Bedingung: mindestens 20 Karten beantwortet UND alle fehlerfrei (0 falsche Antworten). 25 Karten alle korrekt erfuellt beide Bedingungen.
```

---

```
A-030 | Pruefung → K-030
Karten-Schwierigkeitsfaktor: Wird vom Paket-Ersteller festgelegt (Leicht=1, Mittel=2, Schwer=3). Ist fuer alle Nutzer gleich und aendert sich nie. Beeinflusst die XP: Leicht 0.7x, Mittel 1.0x, Schwer 1.4x.

Persoenlicher Ease-Faktor: Wird vom SM-2-Algorithmus berechnet, individuell pro Nutzer und Karte. Startwert 2.5, aendert sich mit jeder Bewertung. Spiegelt wider, wie schwer DIESE Karte fuer DIESEN Nutzer ist. Niedriger Ease = mehr XP (bis 2.15x).
```

---

```
A-031 | Vertiefung → K-031
Das Abzeichen-System hat 30 Level in 7 Farbstufen:
- Weiß (1-3), Blau (4-6), Gruen (7-9), Rot (10-12/15)
- Schwarz (16-18), Bronze (19-21), Silber (22-24)
- Gold (25-27), Platin (28-30)

Jede Stufe hat 3 Sterne. Die 6 Abzeichen-Typen:
1. Ausdauer: Anzahl abgeschlossener Sessions
2. Wissenssammler: Anzahl korrekte Antworten
3. Serie: Laengste Richtig-Serie am Stueck
4. Entdecker: Anzahl verschiedener Karten gesehen
5. Makellos: Anzahl perfekte Sessions (100%)
6. Bestaendig: Anzahl verschiedener Lerntage
```

---

```
A-032 | Vertiefung → K-032
Docker Compose mit zwei Services:
1. Backend-Container: FastAPI + SQLite, Port 8030
2. Frontend-Container: Svelte 5 (Vite Build), Port 8031

Persistente Daten: data/lernvault.db und uploads/ als Host-Mounts -- ueberleben Container-Neustarts und Updates. Die Lernpakete liegen unter lernpakete/ (read-only gemountet). Updates per update.sh: nur Code-Dateien werden ersetzt, Datenbank bleibt unangetastet.
```

---

```
A-033 | Vertiefung → K-033
LM Studio ist ein lokaler KI-Server (laeuft auf dem Mac/PC, nicht in der Cloud). LernVault nutzt ihn fuer:
1. MC-Optionen generieren: Erzeugt plausible falsche Antwortoptionen
2. Freitext-Bewertung: Bewertet freie Antworten gegen die Musterloesung
3. KI-Erklaerungen: Erklaert Karten basierend auf den Lernmaterialien
4. Fehleranalyse: Identifiziert relevante Stellen in Dokumenten

Anbindung: HTTP API auf Port 1234 (kompatibel mit OpenAI-Format). Das Modell wird automatisch erkannt. LM Studio ist optional -- ohne ihn funktionieren Standard und SRS.
```

---

```
A-034 | Vertiefung → K-034
Der Spacing Effect beschreibt, dass Information besser behalten wird, wenn das Lernen ueber Zeit verteilt stattfindet (statt massiertem Lernen). LernVault nutzt dies durch:
1. SRS-Modus: SM-2 berechnet optimale Wiederholungszeitpunkte
2. Fortschrittsfaktor in der XP-Formel: Spaete Reviews (7-90 Tage) werden mit 1.1x bis 1.5x belohnt
3. "Faellig heute"-Anzeige in der Sidebar: Zeigt an, welche Karten zur Wiederholung anstehen
4. Das System belohnt bewusst Langzeit-Retention staerker als kurzfristiges Auswendiglernen
```

---

```
A-035 | Vertiefung → K-035
LernVault nutzt SQLite FTS5 (Full-Text Search 5) fuer die Suche. Features:
- Echtzeit-Suche waehrend des Tippens
- Durchsucht Fragen, Antworten, Lexikon-Eintraege und Dokumente
- Filter nach Paket moeglich
- Ergebnisse werden in 50er-Batches nachgeladen
- Ranking nach Relevanz (BM25-Algorithmus von FTS5)
- Unterstuetzt auch Teilwort-Suche und Phrasen
```

---

```
A-036 | Vertiefung → K-036
Das Combo-System ist rein Frontend-basiert (kein Backend noetig):
- Bei jeder richtigen Antwort: combo++
- Bei falscher Antwort: combo = 0
- Anzeige in der SessionBar ab 3er-Combo (Blitz-Icon + Zahl)
- Combo-Flash-Animation bei Erreichen einer neuen 3er-Stufe (0.5s Pulse)
- comboPeak wird gespeichert und im Result-Screen als "Combo" angezeigt
- Der Combo-Wert beeinflusst auch den Streak-Faktor in der XP-Formel (indirekt ueber card_streak in card_stats)
```

---

```
A-037 | Vertiefung → K-037
Das Streak-System zaehlt zusammenhaengende Tage mit mindestens einer Session:
- Backend berechnet: aktuelle Straehne, laengste Straehne, ob heute schon gelernt
- Sidebar zeigt Flammen-Icon + Tageszahl
- Warnung (Dreieck-Icon) wenn heute noch keine Session war
- Result-Screen zeigt Streak mit Feuer-Animation (pulsierend bei Streak >= 5)

Motivationspsychologisch wirksam weil: Verlust-Aversion (man will die Straehne nicht verlieren) ist staerker als Gewinn-Motivation. Duolingo nutzt dasselbe Prinzip als wichtigsten Retention-Treiber.
```

---

```
A-038 | Allgemein → K-038
Persistente Daten die nie geloescht werden duerfen:
1. data/lernvault.db (oder lbt.db) -- die komplette Datenbank mit Nutzerdaten, Fortschritt, Karten, Reviews
2. uploads/ -- hochgeladene Dateien (Lernmaterial, Dokumente)

Diese werden als Host-Mounts in Docker eingebunden und ueberleben Container-Neustarts, Rebuilds und Updates. Der Befehl "docker compose down -v" wuerde die Volumes loeschen und darf nie ohne explizite Bestaetigung ausgefuehrt werden.
```

---

```
A-039 | Allgemein → K-039
In der Verwaltung (Sidebar: Zahnrad-Icon) gibt es zwei Tabs:

Einstellungen:
- Sound an/aus (Coin-Sound, Fehler-Sound, etc.)
- Tagesziel (XP pro Tag: 50-300)
- Bevorzugter Lernmodus (Standard, MC, Freitext, SRS)
- Karten pro Session (5-50)
- Anzeigename aendern
- Passwort aendern

Benutzer (Admin):
- Benutzerverwaltung
```

---

```
A-040 | Allgemein → K-040
Erlaubt:
- Dunkles, scharfes Design (#09090b als Basis)
- Harte Kanten (border-radius max 4px)
- Monospace-Schrift fuer IDs, Zahlen, Code
- Klare Hierarchie, wenig Farbe
- Orbitron Bold fuer Gamification-Zahlen

Verboten:
- Runde Bubbles oder aufgeplusterte Cards
- Bunte Gradienten
- Emoji als UI-Element
- Verspieltes oder kindliches Layout
- Uebertriebene Animationen

Die App richtet sich an erwachsene Professionals in technischen Berufen.
```
