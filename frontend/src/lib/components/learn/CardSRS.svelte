<script>
  /**
   * CardSRS -- Spaced Repetition: Aufdecken + Quality-Bewertung (SM-2)
   * 2-Spalten nach Flip: links Frage, rechts Antwort + Quality-Buttons
   */
  import { activePackageId } from '../../stores/index.js'
  import { marked } from 'marked'
  import { DL, DC } from '../../utils/difficulty.js'

  let { card, onReview, onAdvance, onReport } = $props()

  const startTime = Date.now()
  let flipped = $state(false)
  let busy    = $state(false)

  const QUALITIES = [
    { q:0, label:'Blackout', icon:'fa-face-dizzy',      cls:'rb-err'  },
    { q:2, label:'Fast',     icon:'fa-face-meh',        cls:'rb-warn' },
    { q:3, label:'Richtig',  icon:'fa-face-smile',      cls:'rb-ok'   },
    { q:5, label:'Perfekt',  icon:'fa-face-grin-stars', cls:'rb-star' },
  ]

  function flip() { flipped = true }

  async function rate(quality) {
    if (busy) return
    busy = true
    try {
      const result = quality >= 3 ? 'correct' : 'wrong'
      const resp = await onReview({ result, srs_quality: quality, time_ms: Date.now() - startTime })
      onAdvance(resp)
    } catch(e) { busy = false }
  }
</script>

<div class="card-area">
  <div class="fc" class:fc-split={flipped}>
    <div class="fc-col">
      <div class="fc-meta">
        <span class="mono fc-id">{card.card_id}</span>
        <span class="{DC[card.difficulty]} fc-diff">
          <i class="fa-solid {card.difficulty===1?'fa-gauge-simple':card.difficulty===2?'fa-gauge':'fa-gauge-high'}"></i>
          {DL[card.difficulty]}
        </span>
      </div>
      <div class="fc-q">{card.question}</div>
      {#if card.hint && !flipped}
        <div class="fc-hint">
          <i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i>
          {card.hint}
        </div>
      {/if}
      {#if !flipped}
        <button class="btn btn-primary flip-btn" onclick={flip}>
          <i class="fa-solid fa-eye"></i> Antwort zeigen
        </button>
      {/if}
    </div>

    {#if flipped}
      <div class="fc-col fc-col-right">
        <div class="fc-ans-lbl">
          <i class="fa-solid fa-square-check" style="color:var(--accent)"></i> Musterlösung
        </div>
        <div class="fc-ans markdown">{@html marked(card.answer)}</div>

        <div class="srs-q-lbl">Wie gut wusstest du es?</div>
        <div class="srs-btns">
          {#each QUALITIES as o}
            <button class="rate-btn {o.cls}" onclick={() => rate(o.q)} disabled={busy}>
              <i class="fa-solid {o.icon}"></i>
              {o.label}
            </button>
          {/each}
        </div>

        {#if $activePackageId}
          <button class="btn btn-ghost btn-sm mat-link"
            onclick={() => window.open(`/#/packages/${$activePackageId}?tab=documents`, '_blank')}>
            <i class="fa-solid fa-book-open"></i> Im Material nachlesen
          </button>
        {/if}

        {#if onReport}
          <button class="btn btn-ghost btn-sm btn-report" onclick={onReport}>
            <i class="fa-solid fa-flag"></i> Fehler melden
          </button>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
/* Karten-Layout, rate-btn, flip-btn, mat-link: siehe app.css */
.srs-q-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;margin-top:4px; }
.srs-btns { display:grid;grid-template-columns:1fr 1fr;gap:8px; }
</style>
