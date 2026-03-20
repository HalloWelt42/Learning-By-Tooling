<script>
  /**
   * CardMC -- Multiple Choice: 4 Optionen, Auto-Bewertung
   * Kein Fallback: MC-Optionen müssen vorhanden sein.
   * Wenn nicht, wird die Karte übersprungen.
   */
  import { apiGet } from '../../utils/api.js'
  import { showToast } from '../../stores/index.js'
  import { DL, DC } from '../../utils/difficulty.js'

  let { card, onReview, onAdvance, onReport } = $props()

  const startTime = Date.now()
  let mcOptions  = $state([])
  let mcSelected = $state(null)
  let mcRevealed = $state(false)
  let mcLoading  = $state(true)
  let mcError    = $state(false)
  let busy       = $state(false)
  let pendingResp = $state(null)

  // MC-Optionen beim Mount laden
  async function init() {
    mcLoading = true
    mcError = false
    try {
      const mc = await apiGet(`/api/mc/${card.card_id}?package_id=${card.package_id}`)
      const correctText = card.answer.split('\n')[0].substring(0, 150)
      const opts = [
        { text: correctText, correct: true },
        ...mc.options.slice(0, 3).map(t => ({ text: t, correct: false }))
      ]
      // Fisher-Yates Mischen
      for (let j = opts.length - 1; j > 0; j--) {
        const k = Math.floor(Math.random() * (j + 1));
        [opts[j], opts[k]] = [opts[k], opts[j]]
      }
      mcOptions = opts
    } catch(e) {
      mcOptions = []
      mcError = true
      showToast('MC-Optionen nicht verfügbar -- Karte wird übersprungen', 'warn')
      // Automatisch überspringen
      try {
        const resp = await onReview({ result: 'skip', time_ms: 0, mc_used: true })
        onAdvance(resp)
      } catch(e2) {}
    }
    mcLoading = false
  }
  init()

  async function selectOption(i) {
    if (mcRevealed || busy) return
    busy = true
    mcSelected = i
    mcRevealed = true
    const result = mcOptions[i].correct ? 'correct' : 'wrong'
    try {
      pendingResp = await onReview({ result, time_ms: Date.now() - startTime, mc_used: true })
    } catch(e) {
      pendingResp = { result, done: false }
    }
    busy = false
  }

  function next() {
    if (pendingResp) onAdvance(pendingResp)
  }
</script>

<div class="card-area">
  <div class="fc">
    <div class="fc-meta">
      <span class="mono fc-id">{card.card_id}</span>
      <span class="{DC[card.difficulty]} fc-diff">
        <i class="fa-solid {card.difficulty===1?'fa-gauge-simple':card.difficulty===2?'fa-gauge':'fa-gauge-high'}"></i>
        {DL[card.difficulty]}
      </span>
    </div>

    <div class="fc-q">{card.question}</div>

    {#if card.hint}
      <div class="fc-hint">
        <i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i>
        {card.hint}
      </div>
    {/if}

    {#if mcLoading}
      <div class="mc-loading">
        <i class="fa-solid fa-brain aip-pulse" style="font-size:18px;color:var(--accent)"></i>
        <div>
          <div style="font-size:13px;font-weight:600;color:var(--text0)">Antwortoptionen werden geladen</div>
          <div style="font-size:11px;color:var(--text3);margin-top:2px">Optionen aus Cache...</div>
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
            onclick={() => selectOption(i)}
          >
            <span class="mc-letter">{['A','B','C','D'][i]}</span>
            <span class="mc-text">{opt.text}</span>
          </button>
        {/each}
      </div>
      {#if mcRevealed}
        <button class="btn btn-primary" style="margin-top:12px" onclick={next}>
          <i class="fa-solid fa-forward"></i> Weiter
        </button>
      {/if}
    {:else if mcError}
      <div class="mc-error">
        <i class="fa-solid fa-circle-xmark"></i>
        MC-Optionen nicht verfügbar -- Karte wird übersprungen
      </div>
    {/if}

    {#if onReport}
      <button class="btn btn-ghost btn-sm btn-report" onclick={onReport} style="margin-top:12px">
        <i class="fa-solid fa-flag"></i> Fehler melden
      </button>
    {/if}
  </div>
</div>

<style>
/* Alle MC-Styles: siehe app.css */
</style>
