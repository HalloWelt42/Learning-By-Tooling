<script>
  /**
   * Learn.svelte -- Orchestrator
   * Steuert Session-Lifecycle: Setup -> Learning -> Result
   * Delegiert Kartenlogik an isolierte Komponenten pro Modus.
   * Session-Zustand wird vollstaendig vom Backend kontrolliert.
   */
  import { categories, aiOnline, activeSession, showToast, loadGlobal, packages, activePackageId } from '../../stores/index.js'
  import { apiGet, apiPost, apiDelete } from '../../utils/api.js'
  import MistakeAnalysis from './MistakeAnalysis.svelte'
  import SessionBar from './SessionBar.svelte'
  import CardStandard from './CardStandard.svelte'
  import CardMC from './CardMC.svelte'
  import CardWrite from './CardWrite.svelte'
  import CardSRS from './CardSRS.svelte'
  import { onMount } from 'svelte'

  // -- Phase --
  let phase = $state('setup')  // setup | learning | result

  // -- Session State (Backend ist Source of Truth) --
  let sessionId   = $state(null)
  let sessionMode = $state('standard')
  let card        = $state(null)
  let totalCards  = $state(0)
  let progress    = $state({ reviewed:0, correct:0, wrong:0, skipped:0, total:0, current_index:0 })
  let results     = $state([])
  let wrongCards  = $state([])

  // -- Setup State --
  let mode        = $state('standard')
  let catFilter   = $state([])
  let cardLimit   = $state(10)
  let useAI       = $state(true)  // Standard: KI-Bewertung an (Kern des Freitext-Modus)
  let pendingSession = $state(null)
  let showAnalysis = $state(false)

  // -- MC Setup --
  let mcPrepProgress = $state(0)
  let mcPrepText     = $state('')
  let mcStatus       = $state(null)

  $effect(() => {
    if (mode === 'mc' && $activePackageId) {
      apiGet(`/api/mc/status/${$activePackageId}`).then(s => mcStatus = s).catch(() => mcStatus = null)
    }
  })

  async function prepareMcOptions() {
    if (!$aiOnline) { showToast('LM Studio offline', 'warn'); return }
    const pkgId = $activePackageId || null
    if (!pkgId) { showToast('Paket auswählen', 'warn'); return }
    const status = await apiGet(`/api/mc/status/${pkgId}`).catch(() => null)
    if (!status || status.missing === 0) {
      showToast('Alle MC-Optionen sind bereits im Cache', 'success'); mcStatus = status; return
    }
    const total = status.missing
    mcPrepProgress = 5; mcPrepText = `${total} Karten werden generiert...`
    const poll = setInterval(async () => {
      const s = await apiGet(`/api/mc/status/${pkgId}`).catch(() => null)
      if (s) { mcPrepProgress = Math.max(5, Math.round((s.cached - status.cached) / total * 100)); mcPrepText = `${s.cached - status.cached} / ${total} Karten...` }
    }, 2000)
    const res = await apiPost('/api/mc/generate-batch', { package_id: pkgId, limit: total }).catch(() => null)
    clearInterval(poll)
    if (res) { mcPrepProgress = 100; mcPrepText = `${res.generated} MC-Optionen generiert`; showToast(`${res.generated} MC-Optionen erstellt`, 'success') }
    else { mcPrepProgress = 0; mcPrepText = ''; showToast('Generierung fehlgeschlagen', 'error') }
    mcStatus = await apiGet(`/api/mc/status/${pkgId}`).catch(() => null)
  }

  // -- Kategorien --
  let localCats = $state([])
  async function loadCats() {
    const p = $activePackageId ? `?package_id=${$activePackageId}` : ''
    try { localCats = await apiGet(`/api/categories${p}`) } catch(e) { localCats = $categories || [] }
  }
  $effect(() => { const _ = $activePackageId; loadCats() })

  let totalCatCards    = $derived((localCats || []).reduce((s, c) => s + (c.card_count || 0), 0))
  let selectedCatCards = $derived(catFilter.length === 0 ? totalCatCards : (localCats || []).filter(c => catFilter.includes(c.code)).reduce((s, c) => s + (c.card_count || 0), 0))

  $effect(() => {
    if (selectedCatCards > 0 && cardLimit > selectedCatCards) cardLimit = selectedCatCards
    if (selectedCatCards > 0 && cardLimit === 0) cardLimit = Math.min(selectedCatCards, 10)
  })

  // Derived
  let correct = $derived(progress.correct)
  let wrong   = $derived(progress.wrong)
  let skipped = $derived(progress.skipped)

  // -- Mount: offene Session pruefen --
  onMount(async () => {
    try {
      const active = await apiGet('/api/sessions/active')
      if (active && active.current_index < active.total) pendingSession = active
    } catch(e) {}
  })

  async function resumeSession() {
    if (!pendingSession) return
    sessionId = pendingSession.session_id
    sessionMode = pendingSession.mode || 'standard'
    mode = sessionMode
    totalCards = pendingSession.total
    activeSession.set({ session_id: sessionId })
    results = []; wrongCards = []
    progress = {
      reviewed: pendingSession.reviewed, correct: pendingSession.correct,
      wrong: pendingSession.wrong, skipped: pendingSession.skipped,
      total: pendingSession.total, current_index: pendingSession.current_index,
    }
    await loadCurrentCard()
    phase = 'learning'
    pendingSession = null
  }

  async function cancelPending() {
    await apiDelete('/api/sessions/active').catch(() => {})
    pendingSession = null; activeSession.set(null)
  }

  // -- Session starten --
  async function startSession() {
    try {
      const data = await apiPost('/api/sessions', {
        mode, package_id: $activePackageId || null,
        category_filter: catFilter, card_limit: cardLimit,
        srs_mode: mode === 'srs',
      })
      if (data.total === 0) { showToast('Keine Karten -- Filter anpassen', 'warn'); return }
      sessionId = data.session_id
      sessionMode = mode
      totalCards = data.total
      activeSession.set(data)
      results = []; wrongCards = []
      progress = { reviewed:0, correct:0, wrong:0, skipped:0, total:data.total, current_index:0 }
      await loadCurrentCard()
      phase = 'learning'
    } catch(e) {
      showToast(`Session-Start fehlgeschlagen: ${e.message}`, 'error')
    }
  }

  // -- Aktuelle Karte vom Backend holen --
  async function loadCurrentCard() {
    try {
      const resp = await apiGet(`/api/sessions/${sessionId}/current-card`)
      if (resp.done) { await finishSession(); return }
      card = resp.card
      if (resp.progress) progress = resp.progress
    } catch(e) {
      showToast('Karte konnte nicht geladen werden', 'error')
    }
  }

  // -- Callback fuer Card-Komponenten: Review ans Backend senden --
  async function handleReview(data) {
    try {
      const resp = await apiPost(`/api/sessions/${sessionId}/review-and-next`, data)
      results = [...results, { card_id: card.card_id, result: resp.result }]
      if (resp.result === 'wrong' && card) recordWrong(card)
      if (resp.progress) progress = resp.progress
      return resp
    } catch(e) {
      showToast(`Bewertung fehlgeschlagen: ${e.message}`, 'error')
      throw e
    }
  }

  // -- Callback fuer Card-Komponenten: Zur naechsten Karte wechseln --
  function handleAdvance(resp) {
    if (resp.done) {
      finishSession()
    } else if (resp.next_card) {
      card = resp.next_card
    } else {
      loadCurrentCard()
    }
  }

  function recordWrong(c) {
    if (c && !wrongCards.find(w => w.card_id === c.card_id)) {
      wrongCards = [...wrongCards, c]
    }
  }

  async function finishSession() {
    await apiPost(`/api/sessions/${sessionId}/end`, {}).catch(() => {})
    activeSession.set(null)
    await loadGlobal()
    phase = 'result'
  }

  function endSession() { finishSession() }

  function reset() {
    if (sessionId) apiPost(`/api/sessions/${sessionId}/end`, {}).catch(() => {})
    activeSession.set(null)
    phase = 'setup'; sessionId = null; card = null; results = []; wrongCards = []; showAnalysis = false
    totalCards = 0; pendingSession = null
    progress = { reviewed:0, correct:0, wrong:0, skipped:0, total:0, current_index:0 }
  }
</script>

<div class="page">

<!-- SETUP -->
{#if phase === 'setup'}
  <div class="page-hd">
    <div>
      <h1 class="page-title"><i class="fa-solid fa-play"></i> Lernen</h1>
      <p class="page-sub">Modus wählen und Session starten</p>
    </div>
  </div>

  {#if pendingSession}
    <div class="card-box pending-session" style="margin-bottom:20px;display:flex;align-items:center;gap:14px;justify-content:space-between">
      <div>
        <div style="font-size:13px;font-weight:700;color:var(--text0)">
          <i class="fa-solid fa-clock-rotate-left" style="color:var(--warn)"></i> Offene Session
        </div>
        <div style="font-size:12px;color:var(--text2);margin-top:3px">
          {pendingSession.reviewed} von {pendingSession.total} Karten beantwortet --
          {pendingSession.correct} richtig, {pendingSession.wrong} falsch
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-shrink:0">
        <button class="btn btn-ghost btn-sm" onclick={cancelPending}>Verwerfen</button>
        <button class="btn btn-primary" onclick={resumeSession}>
          <i class="fa-solid fa-forward"></i> Fortsetzen
        </button>
      </div>
    </div>
  {/if}

  {#if $packages && $packages.length > 1}
    <div class="card-box" style="margin-bottom:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <div class="section-label" style="margin:0">Paket</div>
      <div class="pkg-select">
        <button class="pkg-chip" class:active={!$activePackageId} onclick={() => activePackageId.set(null)}>
          <i class="fa-solid fa-layer-group"></i> Alle
        </button>
        {#each $packages as p (p.id)}
          <button class="pkg-chip" class:active={$activePackageId === p.id} onclick={() => activePackageId.set(p.id)}
                  style="--pkg-c:{p.color || 'var(--accent)'}">
            <i class="fa-solid {p.icon || 'fa-box'}"></i> {p.name}
          </button>
        {/each}
      </div>
    </div>
  {:else if $packages?.length === 1}
    <div class="card-box" style="margin-bottom:16px;display:flex;align-items:center;gap:10px">
      <i class="fa-solid {$packages[0].icon || 'fa-box'}" style="color:{$packages[0].color || 'var(--accent)'}"></i>
      <span style="font-size:13px;font-weight:700">{$packages[0].name}</span>
    </div>
  {/if}

  <div class="setup-grid">
    <!-- Modus -->
    <div class="card-box">
      <div class="section-label">Lernmodus</div>
      <div class="modes">
        {#each [
          ['standard','fa-layer-group','Karteikarte','Aufdecken und selbst bewerten', false],
          ['mc',      'fa-list-check', 'Multiple Choice','KI generiert Antwortoptionen', true],
          ['write',   'fa-keyboard',   'Freitext',   'KI bewertet deine Antwort', true],
          ['srs',     'fa-brain',      'Spaced Repetition','Schwache Karten öfter, starke seltener', false],
        ] as [id,fa,lbl,desc,needsAI]}
          {@const locked = needsAI && !$aiOnline}
          <button class="mode-btn" class:active={mode===id} class:mode-locked={locked}
            onclick={() => { if (!locked) mode = id }}
            disabled={locked}>
            <i class="fa-solid {fa} mode-icon"></i>
            <div class="mode-info">
              <span class="mode-lbl">{lbl}</span>
              <span class="mode-desc">{desc}</span>
              {#if locked}
                <span class="mode-lock-hint"><i class="fa-solid fa-lock"></i> LM Studio nicht erreichbar</span>
              {/if}
            </div>
          </button>
        {/each}
      </div>

      <div class="mode-explain">
        {#if mode === 'standard'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Du siehst die Frage und überlegst dir die Antwort. Dann deckst du auf und bewertest selbst: Richtig, Falsch oder Übersprungen.</p>
        {:else if mode === 'mc'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Pro Frage werden dir mehrere Antwortmöglichkeiten angezeigt. Die falschen Optionen werden von der lokalen KI (LM Studio) erzeugt.</p>
          {#if !$aiOnline}
            <p class="mode-warn"><i class="fa-solid fa-triangle-exclamation"></i> LM Studio ist gerade nicht erreichbar.</p>
          {/if}
        {:else if mode === 'write'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Du tippst deine Antwort frei ein. Die lokale KI (LM Studio) bewertet deine Antwort: Was richtig war, was gefehlt hat, was falsch war. Du siehst sofort einen Score und detailliertes Feedback. Die Musterlösung kannst du optional dazuschalten.</p>
          {#if !$aiOnline}
            <p class="mode-warn"><i class="fa-solid fa-triangle-exclamation"></i> LM Studio ist nicht erreichbar. Ohne KI funktioniert nur der Selbstvergleich -- du siehst die richtige Antwort, musst aber selbst bewerten.</p>
          {/if}
          <label class="check-row" style="margin-top:8px">
            <input type="checkbox" bind:checked={useAI} disabled={!$aiOnline} />
            <span>{$aiOnline ? 'KI-Bewertung (empfohlen)' : 'KI-Bewertung (LM Studio nicht erreichbar)'}</span>
          </label>
        {:else if mode === 'srs'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Karten die du schlecht beantwortest kommen öfter. Gut gekonnte erst nach Tagen oder Wochen wieder.</p>
        {/if}
      </div>

      {#if mode === 'mc'}
        <div class="mc-setup-box">
          {#if !$aiOnline}
            <div class="mc-status err"><i class="fa-solid fa-circle-xmark"></i> LM Studio offline</div>
          {:else if !$activePackageId}
            <div class="mc-status"><i class="fa-solid fa-circle-info" style="color:var(--warn)"></i> <span>Wähle ein Paket aus.</span></div>
          {:else if mcPrepProgress > 0 && mcPrepProgress < 100}
            <div class="mc-status">
              <i class="fa-solid fa-brain aip-pulse" style="color:var(--accent)"></i>
              <span>KI erstellt Optionen: {mcPrepText}</span>
              <span class="mono" style="font-weight:800;color:var(--accent)">{mcPrepProgress}%</span>
            </div>
            <div style="height:4px;background:var(--bg3);border-radius:2px;overflow:hidden;margin-top:8px">
              <div style="height:100%;background:var(--accent);border-radius:2px;transition:width .3s;width:{mcPrepProgress}%"></div>
            </div>
          {:else if mcStatus && mcStatus.missing === 0}
            <div class="mc-status ok"><i class="fa-solid fa-circle-check"></i> Alle {mcStatus.total} Karten bereit.</div>
          {:else if mcStatus}
            <div class="mc-status"><i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent)"></i> <span>{mcStatus.cached}/{mcStatus.total} Karten haben MC-Optionen</span></div>
            <button class="btn btn-ghost btn-sm" style="margin-top:8px" onclick={prepareMcOptions}>
              <i class="fa-solid fa-bolt"></i> {mcStatus.missing} fehlende generieren
            </button>
          {:else}
            <div class="mc-status"><i class="fa-solid fa-spinner fa-spin"></i> <span>Status wird geladen...</span></div>
          {/if}
        </div>
      {:else if mode === 'srs'}
        <div class="srs-info">
          <i class="fa-solid fa-circle-info" style="color:var(--accent)"></i>
          Karten die du schlecht kannst kommen öfter.
        </div>
      {/if}
    </div>

    <!-- Kategorien + Start -->
    <div class="card-box" style="display:flex;flex-direction:column">
      <div class="section-label">Kategorien <span class="cat-sum mono">{selectedCatCards}/{totalCatCards} Karten</span></div>
      <div class="cat-checks">
        {#each localCats as cat (cat.code)}
          <label class="cat-row" style="--c:{cat.color}">
            <input type="checkbox" bind:group={catFilter} value={cat.code} />
            <i class="fa-solid {cat.icon} cat-em"></i>
            <span class="cat-nm">{cat.name}</span>
            <span class="cat-cnt mono">{cat.card_count}</span>
          </label>
        {/each}
      </div>
      <div style="margin-top:auto;padding-top:12px;border-top:1px solid var(--border)">
        <div class="section-label" style="margin-bottom:8px">Session starten mit ... Karten</div>
        <div class="limit-row">
          {#each [5,10,20,30,50,100].filter(n => n <= selectedCatCards) as n}
            <button class="limit-chip" onclick={() => { cardLimit = n; startSession() }}>
              <i class="fa-solid fa-play"></i> {n}
            </button>
          {/each}
          {#if selectedCatCards > 0 && ![5,10,20,30,50,100].includes(selectedCatCards)}
            <button class="limit-chip" onclick={() => { cardLimit = selectedCatCards; startSession() }}>
              <i class="fa-solid fa-play"></i> Alle ({selectedCatCards})
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>

<!-- LEARNING -->
{:else if phase === 'learning' && card}

  <SessionBar {card} {progress} {totalCards} {sessionMode} />

  <!-- Card-Komponente je nach Modus, {#key} erzwingt Neu-Mount bei Kartenwechsel -->
  {#key card.card_id}
    {#if sessionMode === 'standard'}
      <CardStandard {card} onReview={handleReview} onAdvance={handleAdvance} />
    {:else if sessionMode === 'mc'}
      <CardMC {card} onReview={handleReview} onAdvance={handleAdvance} />
    {:else if sessionMode === 'write'}
      <CardWrite {card} useAI={useAI && $aiOnline} onReview={handleReview} onAdvance={handleAdvance} />
    {:else if sessionMode === 'srs'}
      <CardSRS {card} onReview={handleReview} onAdvance={handleAdvance} />
    {/if}
  {/key}

  <div style="padding:0 32px 24px">
    <button class="btn btn-ghost btn-sm" onclick={endSession}>
      <i class="fa-solid fa-flag-checkered"></i> Session beenden
    </button>
  </div>

<!-- RESULT -->
{:else if phase === 'result'}
  <div class="result-wrap">
    <div class="page-hd" style="justify-content:center">
      <h1 class="page-title"><i class="fa-solid fa-flag-checkered"></i> Abgeschlossen</h1>
    </div>
    <div class="result-card">
    <div class="res-ring">
      <svg viewBox="0 0 80 80" width="120" height="120">
        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--border)" stroke-width="7"/>
        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--accent)" stroke-width="7"
          stroke-dasharray="{totalCards>0?(correct/totalCards)*213.6:0} 213.6"
          stroke-dashoffset="53.4" stroke-linecap="round" transform="rotate(-90 40 40)"/>
      </svg>
      <div class="res-pct">{totalCards > 0 ? Math.round(correct/totalCards*100) : 0}%</div>
    </div>
    <div class="res-details">
      <div class="rd-item ok"><i class="fa-solid fa-circle-check"></i> <strong>{correct}</strong> richtig</div>
      <div class="rd-item err"><i class="fa-solid fa-circle-xmark"></i> <strong>{wrong}</strong> falsch</div>
      <div class="rd-item muted"><i class="fa-solid fa-forward"></i> <strong>{skipped}</strong> übersprungen</div>
    </div>
    <div class="res-actions">
      <button class="btn btn-primary btn-lg" onclick={reset}>
        <i class="fa-solid fa-rotate-right"></i> Neue Session
      </button>
      <button class="btn btn-ghost btn-lg" onclick={reset}>
        <i class="fa-solid fa-arrow-left"></i> Zurück
      </button>
      {#if wrongCards.length > 0}
        <button class="btn btn-ghost btn-lg" onclick={() => showAnalysis = true}>
          <i class="fa-solid fa-magnifying-glass-chart" style="color:var(--ac2)"></i>
          Fehler analysieren
          <span class="res-wrong-badge">{wrongCards.length}</span>
        </button>
      {/if}
    </div>
  </div>
  </div>
{/if}

{#if showAnalysis}
  <MistakeAnalysis wrongCards={wrongCards} packageId={$activePackageId} onClose={() => showAnalysis = false} />
{/if}
</div>

<style>
/* -- Setup -- */
.pkg-select { display:flex;gap:6px;flex-wrap:wrap; }
.pkg-chip {
  display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:4px;
  border:1px solid var(--border);background:transparent;font-size:12px;font-weight:600;
  color:var(--text2);cursor:pointer;transition:all .15s;font-family:inherit;
}
.pkg-chip:hover { border-color:var(--pkg-c, var(--accent));color:var(--text0); }
.pkg-chip.active { border-color:var(--pkg-c, var(--accent));background:var(--glow);color:var(--pkg-c, var(--accent)); }
.pkg-chip i { font-size:11px; }

.setup-grid { display:grid;grid-template-columns:1fr 1fr;gap:16px; }
.modes { display:flex;flex-direction:column;gap:6px; }
.mode-btn {
  display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:4px;
  border:1px solid var(--border);background:transparent;text-align:left;transition:all .15s;
}
.mode-btn:hover { border-color:var(--accent); }
.mode-btn.active { border-color:var(--accent);background:var(--glow); }
.mode-btn.mode-locked { opacity:0.4;cursor:not-allowed;border-color:var(--border); }
.mode-btn.mode-locked:hover { border-color:var(--border); }
.mode-lock-hint { font-size:10px;color:var(--err);display:flex;align-items:center;gap:4px;margin-top:2px; }
.mode-icon { font-size:16px;color:var(--accent);width:18px;text-align:center;flex-shrink:0; }
.mode-info { display:flex;flex-direction:column;flex:1;gap:2px; }
.mode-lbl  { font-size:13px;font-weight:600;color:var(--text0); }
.mode-desc { font-size:11px;color:var(--text2); }
.check-row { display:flex;align-items:center;gap:8px;cursor:pointer;font-size:12px;color:var(--text2); }
.check-row input { width:auto; }
.srs-info { margin-top:12px;font-size:11px;color:var(--text2);background:var(--glow);border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);padding:8px 12px;border-radius:4px;display:flex;align-items:center;gap:8px; }

.mode-explain { margin-top:12px;padding:12px;background:var(--bg2);border:1px solid var(--border);border-radius:4px; }
.mode-explain-title { font-size:11px;font-weight:700;color:var(--accent);display:flex;align-items:center;gap:6px;margin-bottom:8px; }
.mode-explain p { font-size:12px;color:var(--text2);line-height:1.6;margin-bottom:6px; }
.mode-explain p:last-of-type { margin-bottom:0; }
.mode-warn { color:var(--warn) !important;font-weight:600; }
.mc-setup-box { margin-top:12px;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:12px; }
.mc-status { display:flex;align-items:center;gap:8px;font-size:11px;color:var(--text1); }
.mc-status.ok { color:var(--ok); }
.mc-status.err { color:var(--err); }

.cat-checks { display:flex;flex-direction:column;gap:4px;max-height:280px;overflow-y:auto; }
.cat-row { display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:4px;cursor:pointer;transition:background .12s; }
.cat-row:hover { background:var(--bg2); }
.cat-em { font-size:14px; }
.cat-nm { flex:1;font-size:12px;font-weight:500;color:var(--text1); }
.cat-cnt { font-size:10px;color:var(--text3); }
.cat-sum { font-size:10px;color:var(--text2);margin-left:auto;font-weight:400; }
.limit-row { display:flex;align-items:center;gap:8px;flex-wrap:wrap; }
.limit-chip {
  padding:6px 14px;border-radius:4px;border:1px solid var(--border);background:none;
  font-size:13px;font-weight:700;color:var(--text2);cursor:pointer;font-family:inherit;transition:all .15s;
}
.limit-chip:hover { border-color:var(--accent);color:var(--text0); }

/* -- Result -- */
.result-wrap { display:flex;flex-direction:column;align-items:center;width:100%; }
.result-card { background:var(--bg1);border:1px solid var(--border);border-radius:4px;padding:48px;display:flex;flex-direction:column;align-items:center;gap:24px;max-width:380px;width:100%; }
.res-ring { position:relative;display:flex;align-items:center;justify-content:center; }
.res-pct { position:absolute;font-size:26px;font-weight:800;color:var(--accent);letter-spacing:-.02em;font-family:'JetBrains Mono',monospace; }
.res-details { display:flex;gap:20px; }
.rd-item { display:flex;align-items:center;gap:7px;font-size:13px;font-weight:600; }
.rd-item.ok { color:var(--ok); }
.rd-item.err { color:var(--err); }
.rd-item.muted { color:var(--text3); }
.res-actions { display:flex;flex-direction:column;align-items:center;gap:10px;width:100%; }
.res-wrong-badge { background:var(--err);color:#fff;font-size:11px;font-weight:700;padding:1px 7px;border-radius:4px;margin-left:4px; }
</style>
