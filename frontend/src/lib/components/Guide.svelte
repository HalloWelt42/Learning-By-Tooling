<!--
  Guide.svelte -- In-App Workflow-Dokumentation
  Zeigt den kompletten Ablauf: Paket anlegen, Dokumente hochladen,
  Karten importieren, Lernen starten.
-->
<script>
  let activeStep = $state(0)

  const STEPS = [
    {
      icon: 'fa-box-archive',
      color: '#2196F3',
      title: '1. Paket anlegen',
      sub: 'Jedes Thema bekommt ein eigenes Paket',
      content: `Ein Paket ist eine abgeschlossene Lernwelt. Alle Karten, Dokumente und Lernpfade eines Themas gehören in ein Paket -- so bleibt alles getrennt und übersichtlich.`,
      steps: [
        'Auf "Alle Pakete" in der Sidebar klicken',
        '"Neues Paket" oben rechts klicken',
        'Name, Farbe und Icon wählen',
        'Paket anlegen -- fertig',
      ],
      tip: 'Jedes Paket bekommt eine eigene Farbe -- so erkennst du auf einen Blick, wozu eine Karte gehört.',
      example: 'Beispiele: "API Grundlagen", "Python Kurs", "Zertifizierung 2026"',
    },
    {
      icon: 'fa-file-import',
      color: '#4CAF50',
      title: '2. Karten importieren',
      sub: 'Fertige Lernkarten aus Markdown-Dateien laden',
      content: `Der schnellste Weg um loszulegen. Fragen und Antworten liegen als Markdown-Dateien vor -- beide zusammen in den Import-Tab einfügen, einmal klicken.`,
      steps: [
        'Paket öffnen -> Tab "Import"',
        'Inhalt der Fragen-Datei (z.B. mein-kurs-fragen.md) links einfuegen',
        'Inhalt der Antworten-Datei rechts einfügen',
        '"Importieren" klicken',
        'Ergebnis prüfen: wie viele importiert, wie viele übersprungen',
      ],
      tip: 'Bereits vorhandene Karten (gleiche ID) werden automatisch übersprungen -- kein doppelter Import.',
      format: true,
    },
    {
      icon: 'fa-file-lines',
      color: '#FF9800',
      title: '3. Dokument hochladen',
      sub: 'KI generiert Lernkarten aus eigenem Material',
      content: `Eigene Texte, PDFs oder Markdown-Dokumente hochladen. Die KI (LM Studio) liest jeden Abschnitt und generiert daraus Frage-Antwort-Paare als Entwürfe.`,
      steps: [
        'Paket öffnen -> Tab "Dokumente"',
        '"Hochladen" klicken',
        'Datei auswählen (TXT, MD, PDF oder DOCX)',
        'Kategorie und Karten pro Abschnitt wählen',
        '"KI-Generierung direkt starten" anhaken wenn LM Studio läuft',
        'Hochladen -- KI generiert automatisch Entwürfe',
        'Im selben Tab unter "Entwürfe prüfen": freigeben, bearbeiten oder ablehnen',
      ],
      tip: 'LM Studio muss auf 192.168.178.45:1234 laufen. Status: grüner Punkt unten links in der Sidebar.',
      example: 'Geeignet für: API-Dokumentation, Handbücher, Spec-Dokumente, eigene Notizen',
    },
    {
      icon: 'fa-layer-group',
      color: '#9C27B0',
      title: '4. Karten prüfen',
      sub: 'Entwürfe freigeben, bearbeiten oder ablehnen',
      content: `KI-generierte Karten sind Entwürfe -- sie müssen einmal geprüft werden bevor sie ins Lernen eingehen. Das geht schnell: Freigeben, Bearbeiten oder Ablehnen.`,
      steps: [
        'Paket -> Tab "Dokumente" -> Sektion "Entwürfe prüfen"',
        'Frage und Antwort lesen',
        '"Freigeben" wenn korrekt -- Karte ist sofort lernbar',
        '"Bearbeiten" um Frage oder Antwort zu korrigieren',
        '"Alle freigeben" für schnellen Bulk-Approve',
      ],
      tip: 'Offene Entwürfe zeigt die Sidebar als orangefarbenes Badge am Paketnamen.',
    },
    {
      icon: 'fa-play',
      color: '#F44336',
      title: '5. Lernen',
      sub: 'Session starten und Karten lernen',
      content: `Drei Lernmodi stehen zur Wahl. Standardmodus zum Aufdecken, Freitext zum Eintippen der Antwort, SRS (Spaced Repetition) zum effizienten Wiederholen.`,
      steps: [
        'Paket öffnen -> "Lernen" Button oben rechts',
        'Oder: "Lernen" in der Sidebar (alle Pakete gemischt)',
        'Modus wählen: Karteikarte, Freitext oder Spaced Rep.',
        'Optional: Kategorien filtern',
        'Anzahl der Karten wählen',
        'Session starten',
      ],
      tip: 'SRS zeigt nur Karten die heute fällig sind -- fällige Karten erscheinen als Zahl beim "Lernen" Nav-Punkt.',
    },
  ]
</script>

<div class="guide-wrap">
  <div class="guide-header">
    <div>
      <h1 class="page-title">
        <i class="fa-solid fa-map"></i> Workflow-Übersicht
      </h1>
      <p class="page-sub">Von Paket anlegen bis Lernen starten -- der komplette Ablauf</p>
    </div>
  </div>

  <!-- Schritt-Leiste -->
  <div class="step-bar">
    {#each STEPS as step, i}
      <button
        class="step-pill"
        class:active={activeStep === i}
        style="--c:{step.color}"
        onclick={() => activeStep = i}
      >
        <div class="step-pill-dot">
          <i class="fa-solid {step.icon}"></i>
        </div>
        <span class="step-pill-n">{i + 1}</span>
      </button>
      {#if i < STEPS.length - 1}
        <div class="step-connector" class:done={i < activeStep}></div>
      {/if}
    {/each}
  </div>

  <!-- Aktiver Schritt Detail -->
  {#each STEPS as step, i}
    {#if activeStep === i}
      <div class="step-detail">
        <div class="step-detail-head" style="--c:{step.color}">
          <div class="step-detail-icon" style="background:{step.color}">
            <i class="fa-solid {step.icon}"></i>
          </div>
          <div>
            <h2 class="step-detail-title">{step.title}</h2>
            <p class="step-detail-sub">{step.sub}</p>
          </div>
        </div>

        <div class="step-detail-body">
          <p class="step-intro">{step.content}</p>

          <div class="step-howto">
            <div class="section-label">So geht es</div>
            <div class="howto-list">
              {#each step.steps as s, si}
                <div class="howto-item">
                  <div class="howto-num">{si + 1}</div>
                  <span class="howto-text">{s}</span>
                </div>
              {/each}
            </div>
          </div>

          {#if step.tip}
            <div class="step-tip">
              <i class="fa-solid fa-lightbulb"></i>
              <span>{step.tip}</span>
            </div>
          {/if}

          {#if step.example}
            <div class="step-example">
              <i class="fa-solid fa-circle-info"></i>
              <span>{step.example}</span>
            </div>
          {/if}

          {#if step.format}
            <div class="format-box">
              <div class="section-label">Dateiformat</div>
              <div class="format-cols">
                <div>
                  <div class="format-file-label">
                    <i class="fa-solid fa-circle-question" style="color:var(--accent)"></i>
                    Fragen-Datei
                  </div>
                  <div class="format-code">
{`\`\`\`
K-001 | GB
Was ist eine DoC?
\`\`\`

\`\`\`
K-002 | AP
Welchen HTTP-Code gibt /health zurück?
\`\`\``}
                  </div>
                </div>
                <div>
                  <div class="format-file-label">
                    <i class="fa-solid fa-circle-check" style="color:var(--ok)"></i>
                    Antworten-Datei
                  </div>
                  <div class="format-code">
{`\`\`\`
A-001 | GB -> K-001
Declaration of Consent --
Einwilligungserklärung
\`\`\`

\`\`\`
A-002 | AP -> K-002
HTTP 200 mit {"status":"ok"}
\`\`\``}
                  </div>
                </div>
              </div>
              <div class="format-rules">
                <div class="format-rule">
                  <i class="fa-solid fa-check text-ok"></i>
                  <span><strong>K-ID</strong> verknüpft Frage und Antwort -- muss übereinstimmen</span>
                </div>
                <div class="format-rule">
                  <i class="fa-solid fa-check text-ok"></i>
                  <span><strong>Kategoriecode</strong> muss in der App vorhanden sein (GB, AP, HA, OA, TC, MO, KA, FE, DB, AK, GS, AL)</span>
                </div>
                <div class="format-rule">
                  <i class="fa-solid fa-check text-ok"></i>
                  <span>Mehrere Karten pro Datei möglich -- einfach untereinander mit <code>---</code> trennen</span>
                </div>
              </div>
            </div>
          {/if}
        </div>

        <!-- Navigation -->
        <div class="step-nav">
          {#if i > 0}
            <button class="btn btn-ghost" onclick={() => activeStep = i - 1}>
              <i class="fa-solid fa-arrow-left"></i> Zurück
            </button>
          {:else}
            <div></div>
          {/if}
          {#if i < STEPS.length - 1}
            <button class="btn btn-primary" onclick={() => activeStep = i + 1}>
              Weiter <i class="fa-solid fa-arrow-right"></i>
            </button>
          {:else}
            <button class="btn btn-ok" onclick={() => activeStep = 0}>
              <i class="fa-solid fa-rotate-left"></i> Von vorne
            </button>
          {/if}
        </div>
      </div>
    {/if}
  {/each}

</div>

<style>
.guide-wrap { padding: 28px 32px; max-width: 900px; }

.step-bar {
  display: flex;
  align-items: center;
  margin-bottom: 28px;
  padding: 20px 24px;
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
}
.step-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.step-pill-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--text3);
  transition: all .2s;
  background: var(--bg2);
}
.step-pill.active .step-pill-dot {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 25%, var(--bg1));
  color: var(--accent);
}
.step-pill:not(.active):hover .step-pill-dot {
  border-color: var(--text2);
  color: var(--text1);
}
.step-pill-n {
  font-size: 10px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
}
.step-pill.active .step-pill-n { color: var(--c); }
.step-connector {
  flex: 1;
  height: 2px;
  background: var(--border);
  margin: 0 4px;
  margin-bottom: 14px;
  transition: background .3s;
}
.step-connector.done { background: var(--ok); }

.step-detail {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  margin-bottom: 20px;
  overflow: hidden;
}
.step-detail-head {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: color-mix(in srgb, var(--c) 8%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--c) 20%, transparent);
}
.step-detail-icon {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  flex-shrink: 0;
  box-shadow: 0 2px 10px rgba(0,0,0,.2);
}
.step-detail-title { font-size: 18px; font-weight: 700; color: var(--text0); }
.step-detail-sub   { font-size: 13px; color: var(--text2); margin-top: 2px; }

.step-detail-body { padding: 24px; display: flex; flex-direction: column; gap: 20px; }
.step-intro { font-size: 14px; color: var(--text1); line-height: 1.7; }

.step-howto {}
.howto-list { display: flex; flex-direction: column; gap: 8px; }
.howto-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.howto-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--accent) 20%, var(--bg1));
  border: 1px solid var(--accent);
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}
.howto-text { font-size: 13px; color: var(--text1); line-height: 1.5; }

.step-tip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  background: color-mix(in srgb, var(--warn) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--warn) 35%, transparent);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text1);
  line-height: 1.6;
}
.step-tip i { color: var(--warn); flex-shrink: 0; margin-top: 1px; }

.step-example {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  background: var(--glow);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text1);
}
.step-example i { color: var(--accent); flex-shrink: 0; margin-top: 1px; }

/* Format Box */
.format-box {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 18px;
}
.format-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 14px;
}
.format-file-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.format-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text1);
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 12px;
  white-space: pre;
  line-height: 1.6;
}
.format-rules { display: flex; flex-direction: column; gap: 6px; padding-top: 12px; border-top: 1px solid var(--border); }
.format-rule {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--text1);
  line-height: 1.5;
}
.format-rule i { flex-shrink: 0; margin-top: 2px; }
.format-rule code { font-family: 'JetBrains Mono', monospace; font-size: 11px; background: var(--bg3); padding: 1px 5px; border-radius: 3px; }

.step-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  background: var(--bg2);
}

/* Kategorien-Referenz */
.cat-ref { margin-top: 4px; }
.cat-ref-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
}
.cat-ref-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  background: var(--bg2);
}
.cat-ref-icon {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.cat-ref-icon i { font-size: 12px; }
.cat-ref-code { font-size: 11px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.cat-ref-name { font-size: 11px; color: var(--text2); }

.text-ok { color: var(--ok); }
</style>
