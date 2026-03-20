<script>
  /**
   * Learn.svelte -- Orchestrator
   * Steuert Session-Lifecycle: Setup -> Learning -> Result
   * Delegiert Kartenlogik an isolierte Komponenten pro Modus.
   * Session-Zustand wird vollstaendig vom Backend kontrolliert.
   */
  import { categories, aiOnline, activeSession, showToast, loadGlobal, packages, activePackageId, streakData, loadStreak, loadXp, playCoinSound, playBonusSound, playErrorSound, playCoinRainSound, playPerfectSound, userSettings } from '../../stores/index.js'
  import { apiGet, apiPost, apiDelete } from '../../utils/api.js'
  import MistakeAnalysis from './MistakeAnalysis.svelte'
  import SessionBar from './SessionBar.svelte'
  import CardStandard from './CardStandard.svelte'
  import CardMC from './CardMC.svelte'
  import CardWrite from './CardWrite.svelte'
  import CardSRS from './CardSRS.svelte'
  import { onMount } from 'svelte'
  import { tweened } from 'svelte/motion'
  import { cubicOut } from 'svelte/easing'

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
  let combo       = $state(0)
  let comboPeak   = $state(0)
  let comboFlash  = $state(false)
  let sessionXp   = $state(0)
  let xpFlashFlag = $state(false)
  let xpFloats    = $state([])  // [{id, amount, x}]
  let xpCountUp   = tweened(0, { duration: 2200, easing: cubicOut })
  let completionBonus = $state(0)
  let showCoinRain = $state(false)
  let showConfetti = $state(false)
  let showPerfectStar = $state(false)
  let showStreakFire = $state(false)
  let materialUsed  = $state(false)

  let hasMaterial = $derived((() => {
    const pkg = ($packages || []).find(p => p.id === $activePackageId)
    return pkg && pkg.doc_count > 0
  })())

  function openMaterial() {
    materialUsed = true
    window.open(`/#/packages/${$activePackageId}?tab=material`, '_blank')
  }

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
      // Offene Session beenden bevor neue startet
      await apiDelete('/api/sessions/active').catch(() => {})
      const data = await apiPost('/api/sessions', {
        mode, package_id: $activePackageId || null,
        category_filter: catFilter, card_limit: cardLimit,
        srs_mode: mode === 'srs',
      })
      if (data.total === 0) { showToast('Keine Karten -- Filter anpassen', 'warn'); return }
      sessionId = data.session_id
      sessionMode = mode
      combo = 0; comboPeak = 0; sessionXp = 0; xpFloats = []
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
      if (resp.mode) sessionMode = resp.mode
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
      // Combo-System
      if (resp.result === 'correct') {
        combo++
        if (combo > comboPeak) comboPeak = combo
        if (combo >= 3) { comboFlash = true; setTimeout(() => comboFlash = false, 800) }
      } else {
        combo = 0
      }
      // XP-Animation + Sound
      if (resp.xp_earned && resp.xp_earned > 0) {
        sessionXp += resp.xp_earned
        xpFlashFlag = true; setTimeout(() => xpFlashFlag = false, 600)
        if (resp.result === 'correct') {
          playCoinSound($userSettings)
          const id = Date.now()
          xpFloats = [...xpFloats, { id, amount: resp.xp_earned }]
          setTimeout(() => { xpFloats = xpFloats.filter(f => f.id !== id) }, 1200)
        }
      }
      // Fehlersound bei falscher Antwort
      if (resp.result === 'wrong') {
        playErrorSound($userSettings)
      }
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
    const endResp = await apiPost(`/api/sessions/${sessionId}/end`, {}).catch(() => ({}))
    activeSession.set(null)
    await loadGlobal()
    loadStreak()
    loadXp()

    // Completion-Bonus aus Backend-Antwort
    completionBonus = endResp?.bonus || 0

    // Counter-Animation: von 0 hochzaehlen
    xpCountUp.set(0, { duration: 0 })
    showCoinRain = false
    showConfetti = false
    showPerfectStar = false
    showStreakFire = false
    phase = 'result'

    const pct = totalCards > 0 ? Math.round(correct / totalCards * 100) : 0

    // Material-Strafe: XP halbieren (aufgerundet) -- nur bei Testmodi (MC, Freitext)
    const isTestMode = sessionMode === 'mc' || sessionMode === 'write'
    if (materialUsed && isTestMode) {
      sessionXp = Math.ceil(sessionXp / 2)
      completionBonus = Math.ceil(completionBonus / 2)
    }

    // Spektakel-Kaskade mit Timing
    setTimeout(() => {
      xpCountUp.set(sessionXp + completionBonus)
      // Bonus-Sound beim Hochzaehlen
      playBonusSound($userSettings)
    }, 300)

    // Muenzenregen bei XP > 0
    if (sessionXp > 0) {
      setTimeout(() => {
        showCoinRain = true
        playCoinRainSound($userSettings)
        setTimeout(() => showCoinRain = false, 3000)
      }, 600)
    }

    // Confetti bei 100%
    if (pct === 100 && totalCards >= 5) {
      setTimeout(() => {
        showConfetti = true
        showPerfectStar = true
        // Perfect-Sound bei mindestens 20 Karten fehlerfrei
        if (totalCards >= 20) {
          playPerfectSound($userSettings)
        }
        setTimeout(() => showConfetti = false, 4000)
      }, 1200)
    }

    // Streak-Feuer bei Streak >= 5
    if ($streakData.current >= 5) {
      setTimeout(() => {
        showStreakFire = true
        setTimeout(() => showStreakFire = false, 3000)
      }, 1800)
    }
  }

  function endSession() { finishSession() }

  function reset() {
    if (sessionId) apiPost(`/api/sessions/${sessionId}/end`, {}).catch(() => {})
    activeSession.set(null)
    phase = 'setup'; sessionId = null; card = null; results = []; wrongCards = []; showAnalysis = false
    totalCards = 0; pendingSession = null; combo = 0; comboPeak = 0; sessionXp = 0; xpFloats = []; materialUsed = false
    completionBonus = 0; xpCountUp.set(0, { duration: 0 })
    showCoinRain = false; showConfetti = false; showPerfectStar = false; showStreakFire = false
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

  <SessionBar {card} {progress} {totalCards} {sessionMode} {combo} {comboFlash} xpEarned={sessionXp} xpFlash={xpFlashFlag} {materialUsed} onOpenMaterial={hasMaterial ? openMaterial : null} />

  <!-- XP Float Animation -->
  {#each xpFloats as fl (fl.id)}
    <div class="xp-float-anim">
      <span class="xp-coin-anim"></span>
      <span>+{fl.amount}</span>
    </div>
  {/each}

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
  {@const rawPct = totalCards > 0 ? Math.round(correct/totalCards*100) : 0}
  {@const isTest = sessionMode === 'mc' || sessionMode === 'write'}
  {@const pctVal = materialUsed && isTest ? Math.ceil(rawPct / 2) : rawPct}

  <!-- Muenzenregen-Overlay -->
  {#if showCoinRain}
    <div class="coin-rain" aria-hidden="true">
      {#each Array(12) as _, i}
        <div class="rain-coin" style="--delay:{i * 0.18}s;--x:{10 + Math.random() * 80}%;--rot:{Math.random() * 720}deg;--dur:{1.8 + Math.random() * 1.2}s"></div>
      {/each}
    </div>
  {/if}

  <!-- Confetti-Overlay bei 100% -->
  {#if showConfetti}
    <div class="confetti-wrap" aria-hidden="true">
      {#each Array(40) as _, i}
        <div class="confetti-piece" style="
          --x:{5 + Math.random() * 90}%;
          --delay:{Math.random() * 0.8}s;
          --dur:{2 + Math.random() * 2}s;
          --rot:{Math.random() * 720}deg;
          --color:{['var(--ok)','var(--accent)','#FFD700','#ff6b35','#4FC3F7','#E040FB'][i % 6]};
          --size:{4 + Math.random() * 6}px;
        "></div>
      {/each}
    </div>
  {/if}

  <div class="result-wrap">

    <!-- Perfekt-Stern bei 100% -->
    {#if showPerfectStar}
      <div class="perfect-badge">
        <i class="fa-solid fa-star"></i>
        <span>Perfekt</span>
      </div>
    {/if}

    <!-- Grosser Score-Ring -->
    <div class="res-hero">
      <div class="res-ring" class:ring-glow-ok={pctVal === 100} class:ring-glow-warn={pctVal < 50}>
        <svg viewBox="0 0 100 100" width="160" height="160">
          <circle cx="50" cy="50" r="42" fill="none" stroke="var(--bg3)" stroke-width="6"/>
          <circle cx="50" cy="50" r="42" fill="none"
            stroke="{pctVal >= 80 ? 'var(--ok)' : pctVal >= 50 ? 'var(--accent)' : 'var(--err)'}"
            stroke-width="6"
            stroke-dasharray="{(correct/Math.max(totalCards,1))*263.9} 263.9"
            stroke-linecap="round" transform="rotate(-90 50 50)"
            class="res-ring-fill"/>
        </svg>
        <div class="res-pct">{pctVal}<span class="res-pct-sign">%</span></div>
      </div>
      <div class="res-verdict">
        {#if pctVal === 100}Makellos
        {:else if pctVal >= 90}Ausgezeichnet
        {:else if pctVal >= 80}Sehr gut
        {:else if pctVal >= 60}Gut gemacht
        {:else if pctVal >= 40}Solide Basis
        {:else}Weiter üben{/if}
      </div>
    </div>

    <!-- Stats-Zeile -->
    <div class="res-stats">
      <div class="rs ok">
        <span class="rs-num">{correct}</span>
        <span class="rs-label">richtig</span>
      </div>
      <div class="rs-sep"></div>
      <div class="rs err">
        <span class="rs-num">{wrong}</span>
        <span class="rs-label">falsch</span>
      </div>
      <div class="rs-sep"></div>
      <div class="rs muted">
        <span class="rs-num">{skipped}</span>
        <span class="rs-label">übersprungen</span>
      </div>
      {#if comboPeak >= 3}
        <div class="rs-sep"></div>
        <div class="rs combo">
          <span class="rs-num">{comboPeak}x</span>
          <span class="rs-label"><i class="fa-solid fa-bolt"></i> Combo</span>
        </div>
      {/if}
    </div>

    {#if materialUsed && isTest}
      <div class="res-penalty">
        <i class="fa-solid fa-book-open"></i>
        Material verwendet -- Score und XP halbiert
      </div>
    {/if}

    <!-- Belohnungs-Zeile -->
    <div class="res-rewards">
      {#if sessionXp > 0 || completionBonus > 0}
        <div class="rw-item silver">
          <div class="rw-coin silver"></div>
          <div class="rw-val">
            <span class="rw-num">{Math.round($xpCountUp)}</span>
            {#if completionBonus > 0}
              <span class="rw-bonus">+{completionBonus}</span>
            {/if}
          </div>
          <span class="rw-label">Silber</span>
        </div>
      {/if}
      {#if $streakData.current > 0}
        <div class="rw-item streak" class:streak-fire={showStreakFire}>
          <div class="rw-icon"><i class="fa-solid fa-fire"></i></div>
          <div class="rw-val">
            <span class="rw-num">{$streakData.current}</span>
          </div>
          <span class="rw-label">{$streakData.current === 1 ? 'Tag' : 'Tage'}</span>
        </div>
      {/if}
    </div>

    <!-- Aktionen -->
    <div class="res-actions">
      <button class="btn btn-primary btn-lg" onclick={reset}>
        <i class="fa-solid fa-rotate-right"></i> Neue Session
      </button>
      {#if wrongCards.length > 0}
        <button class="btn btn-ghost btn-lg" onclick={() => showAnalysis = true}>
          <i class="fa-solid fa-magnifying-glass-chart" style="color:var(--ac2)"></i>
          {wrongCards.length} Fehler analysieren
        </button>
      {/if}
      <button class="btn btn-ghost btn-sm" onclick={reset} style="margin-top:4px">
        <i class="fa-solid fa-arrow-left"></i> Zurück zur Übersicht
      </button>
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
.result-wrap {
  display:flex;flex-direction:column;align-items:center;width:100%;
  padding:40px 20px 60px;gap:32px;overflow:hidden;
  animation:res-fade-in .6s ease both;
  position:relative;
}
@keyframes res-fade-in {
  0% { opacity:0;transform:translateY(20px); }
  100% { opacity:1;transform:translateY(0); }
}

/* Hero: Ring + Verdict */
.res-hero { display:flex;flex-direction:column;align-items:center;gap:14px; }
.res-ring {
  position:relative;display:flex;align-items:center;justify-content:center;
  transition:filter .6s ease;
}
.res-ring.ring-glow-ok { filter:drop-shadow(0 0 16px rgba(52,199,106,.4)); }
.res-ring.ring-glow-warn { filter:drop-shadow(0 0 12px rgba(232,84,84,.3)); }
.res-ring-fill { transition:stroke-dasharray 1.5s ease; }
.res-pct {
  position:absolute;font-size:36px;font-weight:900;color:var(--text0);
  font-family:'Orbitron',sans-serif;display:flex;align-items:baseline;
}
.res-pct-sign { font-size:18px;font-weight:700;color:var(--text2);margin-left:1px; }
.res-verdict {
  font-size:14px;font-weight:700;color:var(--text1);letter-spacing:.1em;
  text-transform:uppercase;
}

/* Perfect Badge */
.perfect-badge {
  display:flex;align-items:center;gap:8px;
  padding:6px 18px;border-radius:4px;
  background:linear-gradient(135deg, rgba(255,215,0,.12), rgba(255,107,53,.08));
  border:1px solid rgba(255,215,0,.3);
  color:#FFD700;font-size:13px;font-weight:800;letter-spacing:.08em;
  text-transform:uppercase;
  animation:perfect-appear .8s ease 1.2s both;
}
.perfect-badge i { font-size:16px;animation:star-rotate 2s ease infinite; }
@keyframes perfect-appear {
  0% { opacity:0;transform:scale(0.5) translateY(10px); }
  60% { opacity:1;transform:scale(1.1) translateY(-2px); }
  100% { opacity:1;transform:scale(1) translateY(0); }
}
@keyframes star-rotate {
  0%,100% { transform:rotate(0deg) scale(1); }
  25% { transform:rotate(15deg) scale(1.15); }
  75% { transform:rotate(-10deg) scale(1.05); }
}

/* Stats-Zeile */
.res-stats { display:flex;align-items:center;gap:20px; }
.rs { display:flex;flex-direction:column;align-items:center;gap:2px; }
.rs-num { font-size:20px;font-weight:900;font-family:'Orbitron',sans-serif; }
.rs-label { font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em; }
.rs-label i { font-size:9px; }
.rs.ok .rs-num { color:var(--ok); }
.rs.err .rs-num { color:var(--err); }
.rs.muted .rs-num { color:var(--text3); }
.rs.combo .rs-num { color:#ffa500; }
.rs-sep { width:1px;height:28px;background:var(--border); }

.res-penalty {
  display:flex;align-items:center;gap:8px;
  font-size:12px;color:var(--warn);
  padding:6px 14px;background:color-mix(in srgb, var(--warn) 10%, transparent);
  border:1px solid color-mix(in srgb, var(--warn) 30%, transparent);
  border-radius:4px;margin-bottom:4px;
}

/* Belohnungs-Zeile */
.res-rewards {
  display:flex;align-items:stretch;gap:0;
  border:1px solid var(--border);border-radius:4px;overflow:hidden;
}
.rw-item {
  display:flex;align-items:center;gap:10px;padding:14px 24px;
  background:var(--bg1);transition:all .3s ease;
}
.rw-item + .rw-item { border-left:1px solid var(--border); }
.rw-coin {
  width:28px;height:28px;border-radius:50%;flex-shrink:0;
  animation:coin-idle 3s ease-in-out infinite;
}
@keyframes coin-idle {
  0%,100% { transform:scale(1); }
  50% { transform:scale(1.05); }
}
.rw-coin.silver {
  background:radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
  border:2px solid #A0A0A0;
}
.rw-icon { font-size:22px;color:#ff6b35; }
.rw-val { display:flex;align-items:baseline;gap:4px; }
.rw-num { font-size:26px;font-weight:900;font-family:'Orbitron',sans-serif;color:var(--text0); }
.rw-item.silver .rw-num { color:#C0C0C0; }
.rw-bonus {
  font-size:14px;font-weight:800;color:var(--ok);font-family:'Orbitron',sans-serif;
  animation:bonus-pop .6s ease 1s both;
}
@keyframes bonus-pop {
  0%   { opacity:0;transform:scale(0.5); }
  60%  { opacity:1;transform:scale(1.2); }
  100% { opacity:1;transform:scale(1); }
}
.rw-label { font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em; }

/* Streak-Feuer-Animation */
.rw-item.streak-fire {
  background:linear-gradient(135deg, rgba(255,107,53,.1), rgba(255,165,0,.05));
  border-color:rgba(255,107,53,.3);
}
.rw-item.streak-fire .rw-icon {
  animation:fire-pulse 0.6s ease infinite alternate;
}
@keyframes fire-pulse {
  0% { transform:scale(1);filter:brightness(1); }
  100% { transform:scale(1.2);filter:brightness(1.3); }
}

/* Aktionen */
.res-actions { display:flex;flex-direction:column;align-items:center;gap:10px;width:100%;max-width:320px; }

/* XP Float Animation (In-Session) */
.xp-float-anim {
  position:fixed;top:80px;right:40px;z-index:100;
  display:flex;align-items:center;gap:6px;
  font-size:16px;font-weight:800;color:#C0C0C0;
  font-family:'Orbitron',sans-serif;
  animation:xp-float-up 1.6s ease-out forwards;
  pointer-events:none;
}
@keyframes xp-float-up {
  0%   { opacity:1;transform:translateY(0) scale(1); }
  60%  { opacity:1;transform:translateY(-30px) scale(1.2); }
  100% { opacity:0;transform:translateY(-60px) scale(0.8); }
}
.xp-coin-anim {
  display:inline-block;width:24px;height:24px;border-radius:50%;
  background:radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
  border:2px solid #A0A0A0;box-shadow:0 0 8px rgba(192,192,192,0.4);
  animation:coin-spin .8s ease-out;
}
@keyframes coin-spin {
  0%   { transform:rotateY(0deg) scale(1); }
  50%  { transform:rotateY(900deg) scale(1.2); }
  100% { transform:rotateY(1800deg) scale(1); }
}

/* ===== Muenzenregen ===== */
.coin-rain {
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:200;overflow:hidden;
}
.rain-coin {
  position:absolute;top:-30px;left:var(--x);
  width:20px;height:20px;border-radius:50%;
  background:radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
  border:2px solid #A0A0A0;
  box-shadow:0 0 6px rgba(192,192,192,0.3);
  animation:coin-fall var(--dur) ease-in var(--delay) forwards;
}
@keyframes coin-fall {
  0%   { transform:translateY(0) rotate(0deg) scale(0.6);opacity:0; }
  10%  { opacity:1;transform:translateY(10vh) rotate(90deg) scale(1); }
  80%  { opacity:1; }
  100% { transform:translateY(105vh) rotate(var(--rot)) scale(0.8);opacity:0; }
}

/* ===== Confetti ===== */
.confetti-wrap {
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:210;overflow:hidden;
}
.confetti-piece {
  position:absolute;top:-10px;left:var(--x);
  width:var(--size);height:calc(var(--size) * 1.6);
  background:var(--color);border-radius:1px;
  animation:confetti-fall var(--dur) ease-in var(--delay) forwards;
}
@keyframes confetti-fall {
  0%   { transform:translateY(0) rotate(0deg) scale(0);opacity:0; }
  8%   { opacity:1;transform:translateY(5vh) rotate(90deg) scale(1); }
  70%  { opacity:1; }
  100% { transform:translateY(110vh) rotate(var(--rot)) scale(0.5);opacity:0; }
}
</style>
