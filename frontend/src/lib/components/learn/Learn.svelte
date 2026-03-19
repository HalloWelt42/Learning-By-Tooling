<script>
  import MistakeAnalysis from './MistakeAnalysis.svelte'
  /**
   * Learn.svelte -- Lernkarten (standard | write | srs)
   * KI-Prozesse voll visualisiert, FA-Icons überall
   */
  import { categories, aiOnline, activeSession, showToast, loadGlobal, packages, activePackageId } from '../../stores/index.js'
  import { apiGet, apiPost, apiDelete } from '../../utils/api.js'
  import { navigate } from '../../utils/router.js'
  import AiProcess from './AiProcess.svelte'
  import { onMount } from 'svelte'
  import { marked } from 'marked'
  marked.setOptions({ breaks: true, gfm: true })

  // ── State ──────────────────────────────────────────────────
  let phase       = $state('setup')   // setup | preparing | learning | result
  let pendingSession = $state(null)   // offene Session zum Fortsetzen
  let session = $state(null)
  let cardIds = $state([])
  let idx     = $state(0)
  let card    = $state(null)
  let flipped = $state(false)
  let results = $state([])

  // Setup
  let mode       = $state('standard')
  let sessionMode = $state('standard')  // Original-Modus der Session
  let catFilter  = $state([])
  let cardLimit  = $state(10)

  // Card interaction
  let userAnswer    = $state('')
  let aiState       = $state('idle')   // idle | loading | done | error
  let aiExplanation = $state('')
  let aiFeedback    = $state(null)     // {score, correct, feedback} von KI-Bewertung
  let useAI         = $state(false)
  let showAnalysis   = $state(false)
  let wrongCards     = $state([])
  let aiStep        = $state(0)     // which step is active in AiProcess

  // Multiple Choice
  let mcOptions     = $state([])    // [{text, correct}] -- 4 Optionen gemischt
  let mcSelected    = $state(null)  // Index der gewählten Option
  let mcLoading     = $state(false)
  let mcRevealed    = $state(false)
  let mcPrepProgress = $state(0)    // 0-100 Vorbereitung
  let mcPrepText     = $state('')
  let mcStatus       = $state(null) // {total, cached, missing}

  // MC-Status laden wenn Modus wechselt
  $effect(() => {
    if (mode === 'mc' && $activePackageId) {
      apiGet(`/api/mc/status/${$activePackageId}`).then(s => mcStatus = s).catch(() => mcStatus = null)
    }
  })

  async function prepareMcOptions() {
    if (!$aiOnline) { showToast('LM Studio offline', 'warn'); return }
    const pkgId = $activePackageId || null
    if (!pkgId) { showToast('Paket auswählen', 'warn'); return }

    // Karten-IDs holen die noch keine MC-Optionen haben
    const status = await apiGet(`/api/mc/status/${pkgId}`).catch(() => null)
    if (!status || status.missing === 0) {
      showToast('Alle MC-Optionen sind bereits im Cache', 'success')
      mcStatus = status
      return
    }

    const total = status.missing
    mcPrepProgress = 5
    mcPrepText = `${total} Karten werden generiert...`

    // Fortschritts-Polling parallel zum Batch starten
    const pollInterval = setInterval(async () => {
      const s = await apiGet(`/api/mc/status/${pkgId}`).catch(() => null)
      if (s) {
        const generated = s.cached - status.cached
        mcPrepProgress = Math.max(5, Math.round(generated / total * 100))
        mcPrepText = `${generated} / ${total} Karten...`
      }
    }, 2000)

    // Batch starten (dauert bei LM Studio mehrere Sekunden pro Karte)
    const batchResult = await apiPost('/api/mc/generate-batch', { package_id: pkgId, limit: total }).catch(() => null)
    clearInterval(pollInterval)

    if (batchResult) {
      mcPrepProgress = 100
      mcPrepText = `${batchResult.generated} MC-Optionen generiert`
      showToast(`${batchResult.generated} MC-Optionen erstellt`, 'success')
    } else {
      mcPrepProgress = 0
      mcPrepText = ''
      showToast('Generierung fehlgeschlagen', 'error')
    }
    mcStatus = await apiGet(`/api/mc/status/${pkgId}`).catch(() => null)
  }

  // KI-Assistenz
  let hintText      = $state('')
  let hintLoading   = $state(false)
  let relatedIds    = $state([])
  let relatedLoading = $state(false)

  // Steps for KI evaluation (write mode)
  const EVAL_STEPS = [
    { label: 'Antwort empfangen', sublabel: 'Eingabe wird vorbereitet' },
    { label: 'Frage & Antwort analysieren', sublabel: 'Vergleich mit Musterlösung' },
    { label: 'Kernaussagen prüfen', sublabel: 'Semantische Bewertung läuft' },
    { label: 'Feedback formulieren', sublabel: 'KI schreibt Rückmeldung' },
  ]
  // Steps for KI explanation
  const EXPLAIN_STEPS = [
    { label: 'Kontext verstehen', sublabel: 'Frage und Antwort lesen' },
    { label: 'Erklärung ausarbeiten', sublabel: 'Beispiele suchen' },
    { label: 'Antwort formulieren', sublabel: 'Auf Deutsch schreiben' },
  ]

  const SRS = [
    { q:0, label:'Blackout', icon:'fa-face-dizzy',     cls:'rb-err'  },
    { q:2, label:'Fast',     icon:'fa-face-meh',       cls:'rb-warn' },
    { q:3, label:'Richtig',  icon:'fa-face-smile',     cls:'rb-ok'   },
    { q:5, label:'Perfekt',  icon:'fa-face-grin-stars',cls:'rb-star' },
  ]
  const DL  = ['','Leicht','Mittel','Schwer']
  const DC  = ['','d1','d2','d3']

  let localCats = $state([])

  // Kategorien paketbezogen laden
  async function loadCats() {
    const pkgParam = $activePackageId ? `?package_id=${$activePackageId}` : ''
    try { localCats = await apiGet(`/api/categories${pkgParam}`) } catch(e) { localCats = $categories || [] }
  }

  // Bei Paketwechsel Kategorien neu laden
  $effect(() => { const _ = $activePackageId; loadCats() })

  let totalCatCards = $derived((localCats || []).reduce((s, c) => s + (c.card_count || 0), 0))
  let selectedCatCards = $derived(catFilter.length === 0 ? totalCatCards : (localCats || []).filter(c => catFilter.includes(c.code)).reduce((s, c) => s + (c.card_count || 0), 0))

  // cardLimit auf verfügbare Karten begrenzen
  $effect(() => {
    if (selectedCatCards > 0 && cardLimit > selectedCatCards) cardLimit = selectedCatCards
    if (selectedCatCards > 0 && cardLimit === 0) cardLimit = Math.min(selectedCatCards, 10)
  })

  let progress = $derived(cardIds.length > 0 ? idx / cardIds.length : 0)
  let correct  = $derived(results.filter(r => r.result === 'correct').length)
  let wrong    = $derived(results.filter(r => r.result === 'wrong').length)
  let skipped  = $derived(results.filter(r => r.result === 'skip').length)

  // ── Mount: Prüfe ob offene Session existiert ───────────────
  onMount(async () => {
    try {
      const active = await apiGet('/api/sessions/active')
      if (active && active.remaining_ids?.length > 0) {
        pendingSession = active
      }
    } catch(e) { /* keine offene Session */ }
  })

  async function resumeSession() {
    if (!pendingSession) return
    session = { session_id: pendingSession.session_id }
    cardIds = pendingSession.remaining_ids
    activeSession.set(session)
    results = []; idx = 0
    mode = pendingSession.mode || 'standard'
    await loadCard(0)
    phase = 'learning'
    pendingSession = null
  }

  async function cancelPending() {
    try {
      await apiDelete('/api/sessions/active')
      pendingSession = null
      activeSession.set(null)
    } catch(e) { /* ignore */ }
  }

  // ── Actions ────────────────────────────────────────────────
  async function startSession() {
    try {
      const data = await apiPost('/api/sessions', {
        mode,
        package_id:      $activePackageId || null,
        category_filter: catFilter,
        card_limit:      cardLimit,
        srs_mode:        mode === 'srs',
      })
      if (data.total === 0) { showToast('Keine Karten -- Filter anpassen', 'warn'); return }
      session = data
      cardIds = data.card_ids
      activeSession.set(data)
      results = []; idx = 0
      sessionMode = mode

      await loadCard(0)
      phase = 'learning'
    } catch(e) {
      showToast(`Session-Start fehlgeschlagen: ${e.message}`, 'error')
    }
  }

  async function loadCard(i) {
    if (i >= cardIds.length) { await endSession(); return }
    mode          = sessionMode  // Mode zurücksetzen (falls Fallback ihn geändert hat)
    card          = await apiGet(`/api/cards/${cardIds[i]}`).catch(()=>null)
    flipped       = false
    userAnswer    = ''
    aiExplanation = ''
    aiFeedback    = null
    aiState       = 'idle'
    hintText      = ''
    relatedIds    = []
    mcOptions     = []
    mcSelected    = null
    mcRevealed    = false
    // MC-Optionen laden wenn MC-Modus
    if (mode === 'mc' && card) {
      mcLoading = true
      try {
        const mc = await apiGet(`/api/mc/${card.card_id}`)
        const correctText = card.answer.split('\n')[0].substring(0, 150)
        // Immer 4 Optionen: 1 richtig + 3 falsch, gemischt
        const opts = [
          {text: correctText, correct: true},
          ...mc.options.slice(0, 3).map(t => ({text: t, correct: false}))
        ]
        // Mischen (Fisher-Yates)
        for (let j = opts.length - 1; j > 0; j--) {
          const k = Math.floor(Math.random() * (j + 1));
          [opts[j], opts[k]] = [opts[k], opts[j]]
        }
        mcOptions = opts
      } catch(e) {
        mcOptions = []
      }
      mcLoading = false
    }
  }

  function flip() { flipped = true }

  async function rate(result) {
    // Freitext mit KI: erst bewerten
    if (mode === 'write' && useAI && userAnswer && result === 'unknown') {
      await runAIReview()
      return
    }
    await submitReview(result)
    idx++
    await loadCard(idx)
  }

  async function runAIReview() {
    if (!card) return
    aiState = 'loading'
    aiFeedback = null
    aiStep = 0
    // Simulate step progression while waiting for API
    const stepTimer = setInterval(() => {
      aiStep = Math.min(aiStep + 1, EVAL_STEPS.length - 1)
    }, 900)
    try {
      const resp = await apiPost('/api/reviews', {
        session_id:  session.session_id,
        card_id:     card.card_id,
        result:      'unknown',
        user_answer: userAnswer,
        use_ai:      true,
      })
      aiFeedback = { score: resp.ai_score, feedback: resp.ai_feedback, result: resp.result }
      clearInterval(stepTimer)
      aiStep = EVAL_STEPS.length  // all done
      aiState = 'done'
      results = [...results, { card_id: card.card_id, result: resp.result }]
    } catch(e) {
      clearInterval(stepTimer)
      aiState = 'error'
      aiFeedback = { feedback: 'KI nicht erreichbar.', result: 'unknown' }
    }
  }

  async function afterAIFeedback() {
    idx++
    await loadCard(idx)
    aiState = 'idle'
    aiFeedback = null
  }

  async function submitReview(result) {
    results = [...results, { card_id: card.card_id, result }]
    if (result === 'wrong' && card) recordWrong(card)
    await apiPost('/api/reviews', {
      session_id: session.session_id,
      card_id:    card.card_id,
      result,
      use_ai:     false,
    }).catch(()=>{})
  }

  async function rateSRS(quality) {
    results = [...results, { card_id: card.card_id, result: quality >= 3 ? 'correct' : 'wrong' }]
    if (quality < 3 && card) recordWrong(card)
    await apiPost('/api/srs/review', { card_id: card.card_id, quality, session_id: session?.session_id }).catch(()=>{})
    idx++
    await loadCard(idx)
  }

  async function getExplanation() {
    aiState = 'loading'
    aiStep = 0
    const stepTimer = setInterval(() => {
      aiStep = Math.min(aiStep + 1, EXPLAIN_STEPS.length - 1)
    }, 1000)
    try {
      const data = await apiPost('/api/ai/explain', { card_id: card.card_id })
      clearInterval(stepTimer)
      aiStep = EXPLAIN_STEPS.length
      aiExplanation = data.explanation
      aiState = 'done'
    } catch(e) {
      clearInterval(stepTimer)
      aiExplanation = 'LM Studio nicht erreichbar.'
      aiState = 'error'
    }
  }

  async function getHint() {
    hintLoading = true
    try {
      const data = await apiPost('/api/ai/hint', { question: card.question, answer: card.answer })
      hintText = data.hint
    } catch(e) {
      hintText = 'Merkhilfe nicht verfügbar.'
    }
    hintLoading = false
  }

  async function getRelated() {
    relatedLoading = true
    try {
      const data = await apiPost('/api/ai/related', {
        question: card.question, answer: card.answer,
        package_id: $activePackageId || null, limit: 3
      })
      relatedIds = data.related || []
    } catch(e) {
      relatedIds = []
    }
    relatedLoading = false
  }

  async function endSession() {
    await apiPost(`/api/sessions/${session.session_id}/end`, {}).catch(()=>{})
    activeSession.set(null)
    await loadGlobal()
    phase = 'result'
  }

  function reset() {
    if (session?.session_id) {
      apiPost(`/api/sessions/${session.session_id}/end`, {}).catch(() => {})
    }
    activeSession.set(null)
    phase='setup'; session=null; cardIds=[]; idx=0; card=null; results=[]; wrongCards=[]; showAnalysis=false
    pendingSession = null
  }
</script>

<div class="page">

<!-- ── SETUP ──────────────────────────────────────────────── -->
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
          <i class="fa-solid fa-clock-rotate-left" style="color:var(--warn)"></i>
          Offene Session
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

  <!-- Paketauswahl -->
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
          ['standard','fa-layer-group','Karteikarte','Aufdecken und selbst bewerten'],
          ['mc',      'fa-list-check', 'Multiple Choice','Antwort aus mehreren Optionen wählen'],
          ['write',   'fa-keyboard',   'Freitext',   'Antwort frei eintippen'],
          ['srs',     'fa-brain',      'Spaced Repetition','Schwache Karten öfter, starke seltener'],
        ] as [id,fa,lbl,desc]}
          <button class="mode-btn" class:active={mode===id} onclick={() => mode=id}>
            <i class="fa-solid {fa} mode-icon"></i>
            <div class="mode-info">
              <span class="mode-lbl">{lbl}</span>
              <span class="mode-desc">{desc}</span>
            </div>
          </button>
        {/each}
      </div>

      <!-- Erklärung zum gewählten Modus -->
      <div class="mode-explain">
        {#if mode === 'standard'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Du siehst die Frage und überlegst dir die Antwort. Dann deckst du auf und bewertest selbst: Richtig, Falsch oder Übersprungen. Keine KI nötig, funktioniert immer.</p>
        {:else if mode === 'mc'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Pro Frage werden dir mehrere Antwortmöglichkeiten angezeigt. Die falschen Optionen werden von einer lokalen KI (LM Studio) erzeugt, die auf deinem Rechner im Netzwerk läuft -- deine Daten verlassen nie das lokale Netz.</p>
          <p>Die Optionen werden einmal generiert und 7 Tage zwischengespeichert. Danach werden sie auf Wunsch neu erstellt, damit es nicht langweilig wird.</p>
          {#if !$aiOnline}
            <p class="mode-warn"><i class="fa-solid fa-triangle-exclamation"></i> LM Studio ist gerade nicht erreichbar. Starte es, damit dieser Modus funktioniert.</p>
          {/if}
        {:else if mode === 'write'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Du tippst deine Antwort frei ein. Optional kann die lokale KI (LM Studio) deine Antwort mit der Musterlösung vergleichen und dir Feedback geben: Wie nah du dran warst und was gefehlt hat.</p>
          <p>Ohne KI funktioniert der Modus trotzdem -- du siehst dann einfach die richtige Antwort zum Vergleich.</p>
          <label class="check-row" style="margin-top:8px">
            <input type="checkbox" bind:checked={useAI} disabled={!$aiOnline} />
            <span>KI-Bewertung {$aiOnline ? 'aktivieren' : '(LM Studio nicht erreichbar)'}</span>
          </label>
        {:else if mode === 'srs'}
          <div class="mode-explain-title"><i class="fa-solid fa-circle-info"></i> So funktioniert es</div>
          <p>Das System merkt sich wie gut du jede Karte kannst. Karten die du schlecht beantwortest kommen schon morgen wieder. Karten die du gut kennst erst in einer Woche oder später.</p>
          <p>So lernst du effizient: Du verbringst die meiste Zeit mit dem was du noch nicht kannst, statt immer alles zu wiederholen.</p>
        {/if}
      </div>
      {#if mode === 'mc'}
        <div class="mc-setup-box">
          {#if !$aiOnline}
            <div class="mc-status err">
              <i class="fa-solid fa-circle-xmark"></i>
              LM Studio offline -- MC-Optionen können nicht generiert werden.
            </div>
          {:else if !$activePackageId}
            <div class="mc-status">
              <i class="fa-solid fa-circle-info" style="color:var(--warn)"></i>
              <span>Wähle ein Paket aus um MC-Optionen zu generieren.</span>
            </div>
          {:else if mcPrepProgress > 0 && mcPrepProgress < 100}
            <div class="mc-status">
              <i class="fa-solid fa-brain aip-pulse" style="color:var(--accent)"></i>
              <span>KI erstellt Antwortoptionen: {mcPrepText}</span>
              <span class="mono" style="font-weight:800;color:var(--accent)">{mcPrepProgress}%</span>
            </div>
            <div style="height:4px;background:var(--bg3);border-radius:2px;overflow:hidden;margin-top:8px">
              <div style="height:100%;background:var(--accent);border-radius:2px;transition:width .3s;width:{mcPrepProgress}%"></div>
            </div>
          {:else if mcStatus && mcStatus.missing === 0}
            <div class="mc-status ok">
              <i class="fa-solid fa-circle-check"></i>
              Alle {mcStatus.total} Karten haben MC-Optionen. Bereit.
            </div>
          {:else if mcStatus}
            <div class="mc-status">
              <i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent)"></i>
              <span>{mcStatus.cached} von {mcStatus.total} Karten haben MC-Optionen</span>
            </div>
            <button class="btn btn-ghost btn-sm" style="margin-top:8px" onclick={prepareMcOptions}>
              <i class="fa-solid fa-bolt"></i> {mcStatus.missing} fehlende generieren
            </button>
          {:else}
            <div class="mc-status">
              <i class="fa-solid fa-spinner fa-spin"></i>
              <span>Status wird geladen...</span>
            </div>
          {/if}
        </div>
      {:else if mode === 'srs'}
        <div class="srs-info">
          <i class="fa-solid fa-circle-info" style="color:var(--accent)"></i>
          Karten die du schlecht kannst kommen öfter. Gut gekonnte erst nach Tagen oder Wochen wieder.
        </div>
      {/if}
    </div>

    <!-- Kategorien + Anzahl + Start -->
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
      <!-- Schnellstart -->
      <div style="margin-top:auto;padding-top:12px;border-top:1px solid var(--border)">
        <div class="section-label" style="margin-bottom:8px">Session starten mit ... Karten</div>
        <div class="limit-row">
          {#each [5, 10, 20, 30, 50, 100].filter(n => n <= selectedCatCards) as n}
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

<!-- ── LEARNING ────────────────────────────────────────────── -->
{:else if phase === 'learning' && card}

  <!-- Progress Bar -->
  <!-- Kontext-Breadcrumb -->
  <div class="ctx-bar">
    <div class="ctx-breadcrumb">
      {#if $packages && $activePackageId}
        {@const pkg = $packages.find(p => p.id === $activePackageId)}
        {@const cat = $categories?.find(c => c.code === card.category_code)}
        {#if pkg}
          <span class="ctx-pkg" style="--c:{pkg.color}">
            <i class="fa-solid {pkg.icon}"></i>
            {pkg.name}
          </span>
          <span class="ctx-sep">/</span>
        {/if}
        {#if cat}
          <span class="ctx-cat" style="color:{cat.color}">
            {cat.name}
          </span>
        {/if}
      {/if}
      <span class="ctx-mode">
        {mode === 'standard' ? 'Karteikarte' : mode === 'write' ? 'Freitext' : 'SRS'}
      </span>
    </div>
    <div class="ctx-pos">
      <span class="ctx-num">{idx + 1}</span>
      <span class="ctx-of">/ {cardIds.length}</span>
      <span class="ctx-id">{card.card_id}</span>
    </div>
  </div>

  <div class="learn-bar">
    <div class="lb-info">
      <span class="lb-cat" style="color:{$categories.find(c=>c.code===card.category_code)?.color||'var(--accent)'}">
        <i class="fa-solid {$categories.find(c=>c.code===card.category_code)?.icon||'fa-tag'}"></i>
        {$categories.find(c=>c.code===card.category_code)?.name||card.category_code}
      </span>
    </div>
    <div class="lb-track">
      <div class="lb-fill" style="width:{progress*100}%"></div>
    </div>
    <div class="lb-score">
      <span class="ls ok"><i class="fa-solid fa-check"></i>{correct}</span>
      <span class="ls err"><i class="fa-solid fa-xmark"></i>{wrong}</span>
      <span class="ls skip"><i class="fa-solid fa-forward"></i>{skipped}</span>
    </div>
  </div>

  <div class="card-area">
    <div class="flashcard" class:flipped>

      <!-- Meta -->
      <div class="fc-meta">
        <span style="font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace">{card.card_id}</span>
        <span class="{DC[card.difficulty]}" style="font-size:11px;font-weight:600;display:flex;align-items:center;gap:4px">
          <i class="fa-solid {card.difficulty===1?'fa-gauge-simple':card.difficulty===2?'fa-gauge':'fa-gauge-high'}"></i>
          {DL[card.difficulty]}
        </span>
      </div>

      <!-- Frage -->
      <div class="fc-q">{card.question}</div>

      <!-- Hinweis -->
      {#if card.hint && !flipped}
        <div class="fc-hint">
          <i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i>
          {card.hint}
        </div>
      {/if}

      <!-- Freitext-Eingabe -->
      {#if mode === 'write' && !flipped}
        <textarea class="fc-input" placeholder="Deine Antwort…" bind:value={userAnswer} rows="4"></textarea>
      {/if}

      <!-- Multiple Choice -->
      {#if mode === 'mc' && !flipped}
        {#if mcLoading}
          <div class="mc-loading">
            <i class="fa-solid fa-brain aip-pulse" style="font-size:18px;color:var(--accent)"></i>
            <div>
              <div style="font-size:13px;font-weight:600;color:var(--text0)">Antwortoptionen werden erstellt</div>
              <div style="font-size:11px;color:var(--text3);margin-top:2px">Die lokale KI generiert plausible Alternativen...</div>
            </div>
          </div>
        {:else if mcOptions.length === 4}
          <div class="mc-grid">
            {#each mcOptions as opt, i}
              <button
                class="mc-opt"
                class:mc-selected={mcSelected === i}
                class:mc-correct={mcRevealed && opt.correct}
                class:mc-wrong={mcRevealed && mcSelected === i && !opt.correct}
                disabled={mcRevealed}
                onclick={async () => {
                  mcSelected = i
                  mcRevealed = true
                  const result = opt.correct ? 'correct' : 'wrong'
                  results = [...results, { card_id: card.card_id, result }]
                  if (!opt.correct) recordWrong(card)
                  await apiPost('/api/reviews', {
                    session_id: session.session_id,
                    card_id: card.card_id,
                    result,
                    time_ms: 0
                  }).catch(() => {})
                }}
              >
                <span class="mc-letter">{['A','B','C','D'][i]}</span>
                <span class="mc-text">{opt.text}</span>
              </button>
            {/each}
          </div>
          {#if mcRevealed}
            <button class="btn btn-primary" style="margin-top:12px" onclick={() => { idx++; loadCard(idx) }}>
              <i class="fa-solid fa-forward"></i> Weiter
            </button>
          {/if}
        {:else}
          <div style="font-size:11px;color:var(--text3);padding:8px">MC nicht verfügbar -- Fallback auf Karteikarte</div>
          <button class="btn btn-primary flip-btn" onclick={() => { mode = 'standard'; flip() }}>
            <i class="fa-solid fa-eye"></i> Antwort zeigen
          </button>
        {/if}
      {/if}

      <!-- Aufdecken / Bewerten -->
      {#if !flipped && mode !== 'mc'}
        {#if mode === 'write' && useAI && $aiOnline && userAnswer.trim()}
          <!-- Freitext: KI bewerten vor Aufdecken -->
          {#if aiState === 'idle' && !aiFeedback}
            <button class="btn btn-primary flip-btn" onclick={rate.bind(null, 'unknown')}>
              <i class="fa-solid fa-wand-magic-sparkles"></i> Antwort bewerten
            </button>
            <button class="btn btn-ghost" style="margin-top:6px" onclick={flip}>
              <i class="fa-solid fa-eye"></i> Ohne Bewertung aufdecken
            </button>
          {:else if aiState === 'loading'}
            <AiProcess
              title="KI bewertet deine Antwort"
              steps={EVAL_STEPS}
              active={aiStep}
            />

          {:else if aiFeedback}
            <div class="ai-feedback" class:fb-ok={aiFeedback.score >= 0.6} class:fb-err={aiFeedback.score < 0.6}>
              <div class="fb-header">
                <i class="fa-solid {aiFeedback.score>=0.6?'fa-circle-check':'fa-circle-xmark'}"></i>
                <span class="fb-score">{Math.round(aiFeedback.score*100)}%</span>
                <span class="fb-verdict">{aiFeedback.score>=0.6?'Richtig!':'Noch nicht ganz'}</span>
              </div>
              {#if aiFeedback.feedback}
                <div class="fb-text markdown">{@html marked(aiFeedback.feedback)}</div>
              {/if}
              <button class="btn btn-primary" onclick={flip} style="margin-top:10px">
                <i class="fa-solid fa-eye"></i> Richtige Antwort zeigen
              </button>
            </div>
          {/if}
        {:else}
          <button class="btn btn-primary flip-btn" onclick={flip}>
            <i class="fa-solid fa-eye"></i> Antwort zeigen
          </button>
        {/if}

      {:else if mode !== 'mc'}
        <!-- Antwort aufgedeckt (nicht im MC-Modus) -->
        <div class="fc-ans-lbl">
          <i class="fa-solid fa-square-check" style="color:var(--accent)"></i> Antwort
        </div>
        <div class="fc-ans markdown">{@html marked(card.answer)}</div>

        {#if mode === 'write' && aiFeedback}
          <div class="ai-feedback" class:fb-ok={aiFeedback.score >= 0.6} class:fb-err={aiFeedback.score < 0.6} style="margin-top:10px">
            <div class="fb-header">
              <i class="fa-solid {aiFeedback.score>=0.6?'fa-circle-check':'fa-circle-xmark'}"></i>
              <span class="fb-score">{Math.round(aiFeedback.score*100)}%</span>
              <span class="fb-verdict">{aiFeedback.score>=0.6?'Richtig!':'Noch nicht ganz'}</span>
            </div>
            {#if aiFeedback.feedback}
              <div class="fb-text markdown">{@html marked(aiFeedback.feedback)}</div>
            {/if}
          </div>
        {/if}

        {#if aiState === 'idle' && !aiExplanation && $aiOnline}
          <button class="btn btn-ghost btn-sm ai-explain-btn" onclick={getExplanation}>
            <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Erklärung laden
          </button>

        {:else if aiState === 'loading' && !aiFeedback}
          <AiProcess
            title="KI erklärt die Antwort"
            steps={EXPLAIN_STEPS}
            active={aiStep}
          />

        {:else if aiExplanation}
          <div class="ai-explain">
            <div class="ae-header">
              <i class="fa-solid fa-wand-magic-sparkles" style="color:var(--ac2)"></i>
              KI-Erklärung
            </div>
            <div class="markdown">{@html marked(aiExplanation)}</div>
          </div>
        {/if}

        <!-- KI-Assistenz (optional) -->
        <div class="ai-assist-row">
          <button class="btn btn-ghost btn-sm" onclick={getRelated} disabled={relatedLoading}>
            <i class="fa-solid fa-link"></i> {relatedLoading ? 'Suche…' : 'Verwandte Karten'}
          </button>
        </div>
        {#if relatedIds.length > 0}
          <div class="ai-related-box">
            <span style="font-size:10px;color:var(--text3)">Verwandte Karten:</span>
            {#each relatedIds as rid}
              <span class="related-tag mono">{rid}</span>
            {/each}
          </div>
        {/if}

        <!-- Bewertungs-Buttons -->
        {#if mode === 'srs'}
          <div class="srs-q-lbl">Wie gut wusstest du es?</div>
          <div class="srs-btns">
            {#each SRS as o}
              <button class="rate-btn {o.cls}" onclick={() => rateSRS(o.q)}>
                <i class="fa-solid {o.icon}"></i>
                {o.label}
              </button>
            {/each}
          </div>

        {:else}
          <!-- Standard + Write: Falsch/Skip/Richtig -->
          {#if aiState !== 'loading'}
            <div class="rate-row">
              <button class="rate-btn rb-err"  onclick={() => rate('wrong')}>
                <i class="fa-solid fa-xmark"></i> Falsch
              </button>
              <button class="rate-btn rb-skip" onclick={() => rate('skip')}>
                <i class="fa-solid fa-forward"></i> Skip
              </button>
              <button class="rate-btn rb-ok"   onclick={() => rate('correct')}>
                <i class="fa-solid fa-check"></i> Richtig
              </button>
            </div>
          {/if}
        {/if}

        <!-- Nachlesen-Link zum Lernmaterial -->
        {#if $activePackageId}
          <button class="btn btn-ghost btn-sm" style="margin-top:10px;font-size:11px"
            onclick={() => window.open(`/#/packages/${$activePackageId}?tab=material`, '_blank')}>
            <i class="fa-solid fa-book-open"></i> Im Material nachlesen
          </button>
        {/if}
      {/if}
    </div>
  </div>

  <div style="padding:0 32px 24px">
    <button class="btn btn-ghost btn-sm" onclick={endSession}>
      <i class="fa-solid fa-flag-checkered"></i> Session beenden
    </button>
  </div>

<!-- ── RESULT ──────────────────────────────────────────────── -->
{:else if phase === 'result'}
  <div class="page-hd">
    <h1 class="page-title">
      <i class="fa-solid fa-flag-checkered"></i> Abgeschlossen
    </h1>
  </div>
  <div class="result-card">
    <div class="res-ring">
      <svg viewBox="0 0 80 80" width="120" height="120">
        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--border)" stroke-width="7"/>
        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--accent)" stroke-width="7"
          stroke-dasharray="{cardIds.length>0?(correct/cardIds.length)*213.6:0} 213.6"
          stroke-dashoffset="53.4" stroke-linecap="round" transform="rotate(-90 40 40)"/>
      </svg>
      <div class="res-pct">
        {cardIds.length > 0 ? Math.round(correct/cardIds.length*100) : 0}%
      </div>
    </div>
    <div class="res-details">
      <div class="rd-item ok">
        <i class="fa-solid fa-circle-check"></i>
        <strong>{correct}</strong> richtig
      </div>
      <div class="rd-item err">
        <i class="fa-solid fa-circle-xmark"></i>
        <strong>{wrong}</strong> falsch
      </div>
      <div class="rd-item muted">
        <i class="fa-solid fa-forward"></i>
        <strong>{skipped}</strong> übersprungen
      </div>
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
{/if}

{#if showAnalysis}
  <MistakeAnalysis
    wrongCards={wrongCards}
    packageId={$activePackageId}
    onClose={() => showAnalysis = false}
  />
{/if}
</div>

<style>
/* ── Paketauswahl ──────────────────────────────────── */
.pkg-select { display:flex;gap:6px;flex-wrap:wrap; }
.pkg-chip {
  display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:4px;
  border:1px solid var(--border);background:transparent;font-size:12px;font-weight:600;
  color:var(--text2);cursor:pointer;transition:all .15s;font-family:inherit;
}
.pkg-chip:hover { border-color:var(--pkg-c, var(--accent));color:var(--text0); }
.pkg-chip.active { border-color:var(--pkg-c, var(--accent));background:var(--glow);color:var(--pkg-c, var(--accent)); }
.pkg-chip i { font-size:11px; }
/* ── Setup ─────────────────────────────────────────── */
.setup-grid { display:grid;grid-template-columns:1fr 1fr;gap:16px; }
.modes { display:flex;flex-direction:column;gap:6px; }
.mode-btn {
  display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius: 4px;
  border:1px solid var(--border);background:transparent;text-align:left;transition:all .15s;
}
.mode-btn:hover { border-color:var(--accent); }
.mode-btn.active { border-color:var(--accent);background:var(--glow); }
.mode-icon { font-size:16px;color:var(--accent);width:18px;text-align:center;flex-shrink:0; }
.mode-info { display:flex;flex-direction:column;flex:1;gap:2px; }
.mode-lbl  { font-size:13px;font-weight:600;color:var(--text0); }
.mode-desc { font-size:11px;color:var(--text2); }
.mode-check{ font-size:11px;color:var(--accent); }
.check-row { display:flex;align-items:center;gap:8px;cursor:pointer;font-size:12px;color:var(--text2); }
.check-row input { width:auto; }
.srs-info  { margin-top:12px;font-size:11px;color:var(--text2);background:var(--glow);border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);padding:8px 12px;border-radius: 4px;display:flex;align-items:center;gap:8px; }
.cat-checks { display:flex;flex-direction:column;gap:4px;max-height:280px;overflow-y:auto; }
.cat-row { display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius: 4px;cursor:pointer;transition:background .12s; }
.cat-row:hover { background:var(--bg2); }
.cat-em { font-size:14px; }
.cat-nm { flex:1;font-size:12px;font-weight:500;color:var(--text1); }
.cat-cnt { font-size:10px;color:var(--text3); }
.cat-sum { font-size:10px;color:var(--text2);margin-left:auto;font-weight:400; }
.setup-bot { grid-column:1/-1; }
.limit-row { display:flex;align-items:center;gap:8px;flex-wrap:wrap; }
.limit-chip {
  padding:6px 14px;border-radius:4px;border:1px solid var(--border);background:none;
  font-size:13px;font-weight:700;color:var(--text2);cursor:pointer;font-family:inherit;
  transition:all .15s;
}
.limit-chip:hover { border-color:var(--accent);color:var(--text0); }
.limit-chip.active { border-color:var(--accent);background:var(--glow);color:var(--accent); }
.start-btn { margin-left:auto; }
.limit-wrap { display:flex;align-items:center;gap:12px; }
.limit-n   { font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text0);width:54px;text-align:center; }
.start-btn { align-self:flex-end; }

/* ── Learn Bar ─────────────────────────────────────── */
.learn-bar { padding:14px 32px;display:flex;align-items:center;gap:16px;border-bottom:1px solid var(--border);background:var(--bg1);position:sticky;top:0;z-index:10; }
.lb-info   { display:flex;align-items:center;gap:10px;min-width:130px; }
.lb-cat    { font-size:11px;font-weight:600;letter-spacing:.06em; }
.lb-track  { flex:1;height:4px;background:var(--bg3);border-radius: 2px;overflow:hidden; }
.lb-fill   { height:100%;background:var(--accent);border-radius: 2px;transition:width .4s ease; }
.lb-score  { display:flex;gap:10px; }
.ls        { font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace;display:flex;align-items:center;gap:4px; }
.ls.ok  { color:var(--ok); }   .ls.err  { color:var(--err); }   .ls.skip { color:var(--text3); }

/* ── Flashcard ─────────────────────────────────────── */
.card-area  { display:flex;justify-content:center;padding:28px 32px; }
.flashcard  { width:100%;max-width:640px;background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:28px;box-shadow:0 4px 24px var(--shadow);transition:border-color .3s,box-shadow .3s;display:flex;flex-direction:column;gap:0; }
.flashcard.flipped { border-color:color-mix(in srgb,var(--accent) 55%,transparent);box-shadow:0 8px 40px var(--glow); }
.fc-meta   { display:flex;justify-content:space-between;align-items:center;margin-bottom:18px; }
.fc-q      { font-size:18px;font-weight:600;color:var(--text0);line-height:1.5;margin-bottom:18px; }
.fc-hint   { font-size:12px;color:var(--text2);background:var(--bg2);border-radius: 4px;padding:7px 12px;margin-bottom:14px;display:flex;align-items:center;gap:7px; }
.fc-input  { margin-bottom:14px;font-size:13px;padding:12px;border-radius: 4px; }
.flip-btn  { width:100%;justify-content:center;padding:13px;font-size:14px; }
.fc-ans-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;display:flex;align-items:center;gap:6px; }
.fc-ans    { font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7;color:var(--text1);background:var(--bg2);border-radius: 4px;padding:12px 16px;white-space:pre-wrap;margin-bottom:14px; }

/* ── KI Prozess ────────────────────────────────────── */
.ai-process { background:var(--glow);border:1px solid color-mix(in srgb,var(--accent) 35%,transparent);border-radius: 4px;padding:12px 16px;margin-bottom:14px;display:flex;flex-direction:column;gap:8px; }
.ai-proc-header { display:flex;align-items:center;gap:10px;font-size:12px;font-weight:500;color:var(--accent); }
.ai-proc-bar  { height:3px;background:var(--bg3);border-radius: 2px;overflow:hidden; }
.ai-proc-fill { height:100%;background:var(--accent);border-radius: 2px;animation:scan 1.8s ease-in-out infinite; }
@keyframes scan { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }

.ai-feedback { border-radius: 4px;padding:14px 16px;margin-bottom:12px;border:1px solid; }
.ai-feedback.fb-ok  { border-color:color-mix(in srgb,var(--ok) 40%,transparent);background:var(--glowok); }
.ai-feedback.fb-err { border-color:color-mix(in srgb,var(--err) 40%,transparent);background:color-mix(in srgb,var(--err) 8%,transparent); }
.fb-header { display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:14px;font-weight:600; }
.fb-ok  .fb-header i,.fb-ok  .fb-header { color:var(--ok); }
.fb-err .fb-header i,.fb-err .fb-header { color:var(--err); }
.fb-score   { font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700; }
.fb-verdict { font-size:13px; }
.fb-text    { font-size:12px;color:var(--text1);line-height:1.6; }

.ai-explain-btn { margin-bottom:14px; }
.ai-explain { background:var(--bg2);border:1px solid color-mix(in srgb,var(--ac2) 40%,transparent);border-radius: 4px;padding:12px 16px;margin-bottom:14px; }
.ae-header  { font-size:11px;font-weight:700;color:var(--ac2);letter-spacing:.07em;display:flex;align-items:center;gap:6px;margin-bottom:8px;text-transform:uppercase; }
.ai-explain p { font-size:12px;color:var(--text1);line-height:1.65; }

/* ── Modus-Erklärung ──────────────────────────────── */
.mode-explain { margin-top:12px;padding:12px;background:var(--bg2);border:1px solid var(--border);border-radius:4px; }
.mode-explain-title { font-size:11px;font-weight:700;color:var(--accent);display:flex;align-items:center;gap:6px;margin-bottom:8px; }
.mode-explain p { font-size:12px;color:var(--text2);line-height:1.6;margin-bottom:6px; }
.mode-explain p:last-of-type { margin-bottom:0; }
.mode-warn { color:var(--warn) !important;font-weight:600; }

.mc-loading {
  display:flex;align-items:center;gap:14px;padding:20px;
  background:var(--bg2);border:1px solid var(--border);border-radius:4px;
}

/* ── MC Setup ─────────────────────────────────────── */
.mc-setup-box { margin-top:12px;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:12px; }
.mc-status { display:flex;align-items:center;gap:8px;font-size:11px;color:var(--text1); }
.mc-status.ok { color:var(--ok); }
.mc-status.err { color:var(--err); }

/* ── Multiple Choice ──────────────────────────────── */
.mc-grid { display:flex;flex-direction:column;gap:8px;margin-top:8px; }
.mc-opt {
  display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:4px;
  border:1px solid var(--border);background:transparent;text-align:left;cursor:pointer;
  transition:all .15s;font-family:inherit;font-size:13px;color:var(--text1);line-height:1.4;
}
.mc-opt:hover:not(:disabled) { border-color:var(--accent);background:var(--glow); }
.mc-opt:disabled { cursor:default; }
.mc-selected { border-color:var(--accent); }
.mc-correct { border-color:var(--ok) !important;background:color-mix(in srgb, var(--ok) 10%, transparent) !important; }
.mc-correct .mc-letter { background:var(--ok);color:#fff; }
.mc-wrong { border-color:var(--err) !important;background:color-mix(in srgb, var(--err) 10%, transparent) !important; }
.mc-wrong .mc-letter { background:var(--err);color:#fff; }
.mc-letter {
  width:24px;height:24px;border-radius:3px;background:var(--bg3);color:var(--text2);
  display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;flex-shrink:0;
  font-family:'Orbitron',sans-serif;
}
.mc-text { flex:1; }

/* ── KI-Assistenz ─────────────────────────────────── */
.ai-assist-row { display:flex;gap:6px;margin:10px 0 6px;flex-wrap:wrap; }
.ai-hint-box { display:flex;align-items:flex-start;gap:8px;font-size:12px;color:var(--text1);background:var(--bg2);border:1px solid color-mix(in srgb,var(--warn) 30%,transparent);border-radius:4px;padding:10px 14px;margin-bottom:8px;line-height:1.5; }
.ai-related-box { display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px; }
.related-tag { font-size:10px;background:var(--bg2);border:1px solid var(--border);border-radius:3px;padding:2px 8px;color:var(--accent); }

/* ── Rate Buttons ──────────────────────────────────── */
.rate-row  { display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px; }
.rate-btn  { padding:12px 10px;border-radius: 4px;font-size:12px;font-weight:600;border:2px solid;transition:all .15s;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px; }
.rb-ok   { border-color:var(--ok);color:var(--ok);background:transparent; }
.rb-ok:hover   { background:var(--ok);color:#fff; }
.rb-err  { border-color:var(--err);color:var(--err);background:transparent; }
.rb-err:hover  { background:var(--err);color:#fff; }
.rb-skip { border-color:var(--text3);color:var(--text2);background:transparent; }
.rb-skip:hover { background:var(--bg3); }
.rb-warn { border-color:var(--warn);color:var(--warn);background:transparent; }
.rb-warn:hover { background:var(--warn);color:#fff; }
.rb-star { border-color:var(--accent);color:var(--accent);background:transparent; }
.rb-star:hover { background:var(--accent);color:#fff; }
.srs-q-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;margin-top:4px; }
.srs-btns  { display:grid;grid-template-columns:1fr 1fr;gap:8px; }

/* ── Result ────────────────────────────────────────── */
.result-card { background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:48px;display:flex;flex-direction:column;align-items:center;gap:24px;max-width:380px; }
.res-ring    { position:relative;display:flex;align-items:center;justify-content:center; }
.res-pct     { position:absolute;font-size:26px;font-weight:800;color:var(--accent);letter-spacing:-.02em;font-family:'JetBrains Mono',monospace; }
.res-details { display:flex;gap:20px; }
.rd-item     { display:flex;align-items:center;gap:7px;font-size:13px;font-weight:600; }
.rd-item.ok   { color:var(--ok); }
.rd-item.err  { color:var(--err); }
.rd-item.muted{ color:var(--text3); }

.res-actions { display:flex;flex-direction:column;align-items:center;gap:10px;width:100%; }
.res-wrong-badge {
  background:var(--err);color:#fff;font-size:11px;font-weight:700;
  padding:1px 7px;border-radius: 4px;margin-left:4px;
}


/* ── Kontext-Breadcrumb ────────────────────────── */
.ctx-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0 6px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
.ctx-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text2);
  flex-wrap: wrap;
}
.ctx-pkg {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
  color: var(--c, var(--accent));
}
.ctx-cat {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}
.ctx-sep  { font-size: 9px; color: var(--text3); }
.ctx-mode { color: var(--text3); font-size: 11px; }
.ctx-pos  {
  display: flex;
  align-items: baseline;
  gap: 3px;
  font-family: 'JetBrains Mono', monospace;
}
.ctx-num { font-size: 16px; font-weight: 700; color: var(--text0); }
.ctx-of  { font-size: 11px; color: var(--text3); }
.ctx-id  {
  font-size: 10px;
  color: var(--text3);
  background: var(--bg3);
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
}

</style>
