<!--
  Guide.svelte -- In-App Workflow-Dokumentation
  Zeigt den kompletten Ablauf: Paket anlegen, Dokumente hochladen,
  Karten importieren, Lernen starten.
-->
<script>
  import { marked } from 'marked'
  marked.setOptions({ breaks: true, gfm: true })

  let guideTab = $state('workflow')
  let activeStep = $state(0)
  let specContent = $state('')

  import { apiGet } from '../../utils/api.js'

  async function loadSpec() {
    if (specContent) return
    try {
      const data = await apiGet('/api/docs/paketspezifikation')
      specContent = data.content || ''
    } catch(e) {
      specContent = 'Fehler beim Laden der Paketspezifikation.'
    }
  }

  const STEPS = [
    {
      icon: 'fa-box-archive',
      color: '#2196F3',
      title: '1. Lernpaket anlegen',
      sub: 'Jedes Thema bekommt ein eigenes Paket',
      content: `Ein Lernpaket ist eine abgeschlossene Themenwelt. Alle Karten, Dokumente und Lernmaterial eines Themas gehören in ein Paket.`,
      steps: [
        'Auf "Lernpakete" in der Sidebar klicken',
        '"Neues Paket" oben rechts oder ein fertiges Paket per ZIP hochladen',
        'Name, Farbe und Icon wählen',
        'Fertig -- du kannst sofort Inhalte hinzufügen',
      ],
      tip: 'Du kannst Pakete auch mit einer KI wie Claude erstellen lassen. Die Anleitung dazu findest du in der Paketspezifikation.',
      example: 'Beispiele: "Python Grundlagen", "Erste Hilfe", "Projektmanagement"',
    },
    {
      icon: 'fa-file-import',
      color: '#4CAF50',
      title: '2. Inhalte importieren',
      sub: 'Lernkarten, Dokumente, Lexikon und Lernpfade laden',
      content: `Am einfachsten geht es per ZIP-Datei: Fragen, Antworten und optionales Lernmaterial in eine ZIP packen und hochladen. Die App erkennt alles automatisch -- auch Lexikon-Einträge und Lernpfade.`,
      steps: [
        'Auf "Lernpakete" gehen',
        'ZIP-Datei in den Upload-Bereich ziehen oder klicken',
        'Die App importiert Karten, Dokumente, Bilder, Lexikon und Lernpfade automatisch',
        'Alternativ: Im Paket unter "Import" die Markdown-Dateien manuell einfügen',
      ],
      tip: 'ZIPs können eine paket-extra.json enthalten mit Lexikon-Einträgen und Lernpfaden. Beim Export wird diese Datei automatisch erstellt.',
      format: true,
    },
    {
      icon: 'fa-file-lines',
      color: '#FF9800',
      title: '3. Lernmaterial nutzen',
      sub: 'Texte, Bilder, Lexikon und Lernpfade',
      content: `Jedes Paket kann neben Lernkarten auch Begleitmaterial enthalten: Lehrtexte, Bilder, PDFs, ein Lexikon mit Fachbegriffen und geführte Lernpfade.`,
      steps: [
        'Paket öffnen -> Tab "Material" für Lehrtexte',
        'Tab "Medien" für Bilder und PDFs',
        'Tab "Lexikon" für Fachbegriffe -- mit Suche und Bearbeitung',
        'Tab "Lernpfade" für geführte Kapitel mit festgelegten Karten',
        'Beim Lernen: "Im Material nachlesen" verlinkt direkt ins Paket',
      ],
      tip: 'Wenn eine lokale KI (LM Studio) verfügbar ist, kann sie aus hochgeladenen Dokumenten automatisch Lernkarten-Entwürfe generieren.',
    },
    {
      icon: 'fa-book-open',
      color: '#00BCD4',
      title: '4. Lexikon und Lernpfade',
      sub: 'Fachbegriffe sammeln, Kapitel definieren',
      content: `Das Lexikon sammelt Fachbegriffe zu jedem Paket mit Definitionen und Kategorien. Lernpfade strukturieren Karten in geordnete Kapitel -- ideal um ein Thema schrittweise durchzuarbeiten.`,
      steps: [
        'Lexikon: Im Paket den Tab "Lexikon" öffnen',
        '"+ Eintrag" klicken, Begriff und Definition eingeben, speichern',
        'Einträge durchsuchen mit der Suchleiste, bearbeiten oder löschen per Klick',
        'Lernpfade: Tab "Lernpfade" öffnen, neuen Pfad mit Kapiteln erstellen',
        'Jedes Kapitel bekommt einen Titel und eine Auswahl an Karten (z.B. K-001, K-002)',
        '"Kapitel starten" öffnet eine Lernsession nur mit den zugewiesenen Karten',
      ],
      tip: 'Lexikon-Einträge und Lernpfade werden beim Export in die ZIP-Datei eingebettet und beim Import automatisch wiederhergestellt.',
    },
    {
      icon: 'fa-play',
      color: '#F44336',
      title: '5. Lernen',
      sub: 'Session starten und Wissen aufbauen',
      content: `Vier Lernmodi stehen zur Wahl. Jeder Modus erklärt sich beim Auswählen selbst -- probiere einfach aus was dir am besten liegt.`,
      steps: [
        '"Lernen" in der Sidebar klicken',
        'Paket wählen (oder "Alle" für paketübergreifendes Lernen)',
        'Modus wählen: Karteikarte, Multiple Choice, Freitext oder Spaced Repetition',
        'Optional: Kategorien einschränken',
        'Anzahl wählen und starten',
      ],
      tip: 'Multiple Choice und Freitext-Bewertung nutzen die lokale KI. Ohne KI funktionieren Karteikarte und Spaced Repetition genauso gut.',
    },
    {
      icon: 'fa-star',
      color: '#FFD700',
      title: '6. XP und Gamification',
      sub: 'Punkte sammeln, Combos aufbauen, Sounds geniessen',
      content: `Jede richtige Antwort bringt XP. Combos (mehrere richtige Antworten in Folge) erhöhen den Multiplikator. Bei richtiger Antwort dreht sich eine Goldmünze und es erklingt ein Coin-Sound.`,
      steps: [
        'XP werden automatisch bei jeder Session vergeben (10 XP pro richtige Antwort)',
        'Combos: Ab 3 richtigen Antworten in Folge steigt der XP-Multiplikator',
        'Speed-Bonus: Antworten unter 5 Sekunden bringen 5 Extra-XP',
        'Tagessträhne: Jeden Tag mindestens eine Session halten',
        'Sound-Toggle: In der Sidebar den Lautsprecher-Button klicken um Sounds ein/auszuschalten',
      ],
      tip: 'Die XP-Anzeige und der aktuelle Combo-Zähler sind während der Session oben in der Leiste sichtbar. Nach der Session folgt eine detaillierte Auswertung.',
    },
    {
      icon: 'fa-chart-line',
      color: '#9C27B0',
      title: '7. Fortschritt verfolgen',
      sub: 'Abzeichen sammeln und Lernverlauf sehen',
      content: `Die App merkt sich was du gelernt hast. Unter "Fortschritt" siehst du deine Abzeichen (Shield-Badges mit 30 Stufen), den Lernverlauf und deine Statistiken.`,
      steps: [
        '"Fortschritt" in der Sidebar klicken',
        'Abzeichen-Tab: 6 Abzeichen mit je 30 Levelstufen (Weiss bis Platin)',
        'Verlauf-Tab: Alle bisherigen Sessions mit Ergebnis',
        'Im Paket: "Lernstand (SRS)" zeigt wie gut du die Karten kannst',
        'Tagessträhne und Gesamt-XP in der Sidebar oben',
      ],
      tip: 'Die Shield-Badges oben links in der Sidebar zeigen deine besten Abzeichen auf einen Blick.',
    },
    {
      icon: 'fa-file-export',
      color: '#795548',
      title: '8. Export und Backup',
      sub: 'Pakete sichern und weitergeben',
      content: `Jedes Paket kann als ZIP exportiert werden -- mit allen Karten, Dokumenten, Medien, Lexikon-Einträgen und Lernpfaden. Die ZIP-Datei kann auf einer anderen LernVault-Instanz importiert werden.`,
      steps: [
        'Im Paket oben rechts auf das Export-Icon klicken',
        'Die ZIP enthält: Fragen, Antworten, Dokumente, Medien, Lexikon und Lernpfade',
        'Zum Importieren: ZIP auf der Startseite in den Upload-Bereich ziehen',
        'Bestehende Pakete werden erkannt und Karten ergänzt (keine Duplikate)',
      ],
      tip: 'Die paket-extra.json im ZIP enthält Lexikon und Lernpfade. Sie wird beim Export automatisch erstellt und beim Import gelesen.',
    },
    {
      icon: 'fa-user-group',
      color: '#607D8B',
      title: '9. Teilen und verwalten',
      sub: 'Pakete freigeben, Benutzer einladen',
      content: `Lernpakete können mit anderen Benutzern geteilt werden. Jeder lernt für sich -- Fortschritt und Statistiken sind getrennt, aber die Inhalte werden gemeinsam genutzt.`,
      steps: [
        'Paket öffnen -> "Teilen" neben dem Paketnamen',
        'E-Mail-Adresse des Benutzers eingeben',
        'Rolle wählen: Lerner (nur lernen) oder Besitzer (alles bearbeiten)',
        'Unter "Verwaltung" in der Sidebar: Benutzer anlegen und verwalten',
      ],
      tip: 'Neue Benutzer bekommen automatisch Zugang zu allen bestehenden Paketen.',
    },
  ]
</script>

<div class="guide-wrap">
  <div class="guide-header">
    <div>
      <h1 class="page-title">
        <i class="fa-solid fa-map"></i> Anleitung
      </h1>
      <p class="page-sub">Alles was du wissen musst</p>
    </div>
  </div>

  <div class="guide-tabs">
    <button class="guide-tab" class:active={guideTab === 'workflow'} onclick={() => guideTab = 'workflow'}>
      <i class="fa-solid fa-route"></i> Workflow
    </button>
    <button class="guide-tab" class:active={guideTab === 'pakete'} onclick={() => { guideTab = 'pakete'; loadSpec() }}>
      <i class="fa-solid fa-box-archive"></i> Pakete erstellen
    </button>
  </div>

  {#if guideTab === 'workflow'}

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
                  <span><strong>Kategoriecode</strong> muss in der App vorhanden sein (GB, TH, PX, VF, PR, VT, AL und weitere)</span>
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

  {:else}
    <!-- Pakete erstellen -->
    <div class="spec-content markdown">
      {#if specContent}
        {@html marked(specContent)}
      {:else}
        <p style="color:var(--text3)">Wird geladen...</p>
      {/if}
    </div>
  {/if}

</div>

<style>
.guide-wrap { padding: 28px 32px; max-width: 900px; }

.guide-tabs { display:flex;gap:2px;margin-bottom:0;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg0);z-index:10;padding-top:4px; }
.guide-tab {
  padding:9px 18px;font-size:12px;font-weight:700;color:var(--text2);
  border:none;border-bottom:2px solid transparent;background:none;
  cursor:pointer;font-family:inherit;transition:all .15s;letter-spacing:.03em;
}
.guide-tab.active { color:var(--accent);border-bottom-color:var(--accent); }
.guide-tab:hover { color:var(--text0); }

.spec-content {
  max-width:680px;margin:0 auto;font-size:14px;line-height:1.7;color:var(--text1);
}
.spec-content h1 { font-size:22px;font-weight:800;color:var(--text0);margin:32px 0 12px; }
.spec-content h2 { font-size:17px;font-weight:700;color:var(--text0);margin:28px 0 10px;padding-top:16px;border-top:1px solid var(--border); }
.spec-content h3 { font-size:14px;font-weight:700;color:var(--text0);margin:20px 0 6px; }
.spec-content p { margin-bottom:10px; }
.spec-content ul, .spec-content ol { margin:0 0 10px 20px; }
.spec-content li { margin-bottom:4px; }
.spec-content code { background:var(--bg2);padding:1px 5px;border-radius:3px;font-size:12px;font-family:'JetBrains Mono',monospace;color:var(--accent); }
.spec-content pre { background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:12px;margin:10px 0;overflow-x:auto; }
.spec-content pre code { background:none;padding:0;font-size:12px;color:var(--text1); }
.spec-content table { width:100%;border-collapse:collapse;margin:10px 0;font-size:13px; }
.spec-content th { text-align:left;padding:6px 10px;border-bottom:2px solid var(--border);color:var(--text0);font-weight:700; }
.spec-content td { padding:6px 10px;border-bottom:1px solid var(--border); }

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
