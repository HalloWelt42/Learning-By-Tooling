<script>
  /**
   * CardStandard -- Karteikarte aufdecken + selbst bewerten (Falsch/Skip/Richtig)
   * 2-Spalten-Layout nach Flip: links Frage, rechts Antwort + Bewertung
   */
  import { aiOnline, activePackageId } from '../../stores/index.js'
  import { marked } from 'marked'
  import AiProcess from './AiProcess.svelte'
  import { apiPost } from '../../utils/api.js'
  import { DL, DC } from '../../utils/difficulty.js'

  let { card, onReview, onAdvance } = $props()

  const startTime = Date.now()
  let flipped  = $state(false)
  let busy     = $state(false)
  let aiState  = $state('idle')
  let aiStep   = $state(0)
  let aiExplanation = $state('')
  let relatedIds    = $state([])
  let relatedLoading = $state(false)

  const EXPLAIN_STEPS = [
    { label: 'Kontext verstehen', sublabel: 'Frage und Antwort lesen' },
    { label: 'Erklaerung ausarbeiten', sublabel: 'Beispiele suchen' },
    { label: 'Antwort formulieren', sublabel: 'Auf Deutsch schreiben' },
  ]

  function flip() { flipped = true }

  async function rate(result) {
    if (busy) return
    busy = true
    try {
      const resp = await onReview({ result, time_ms: Date.now() - startTime })
      onAdvance(resp)
    } catch(e) { busy = false }
  }

  async function getExplanation() {
    aiState = 'loading'; aiStep = 0
    const timer = setInterval(() => { aiStep = Math.min(aiStep + 1, EXPLAIN_STEPS.length - 1) }, 1000)
    try {
      const data = await apiPost('/api/ai/explain', { card_id: card.card_id })
      clearInterval(timer); aiStep = EXPLAIN_STEPS.length
      aiExplanation = data.explanation; aiState = 'done'
    } catch(e) {
      clearInterval(timer); aiExplanation = 'LM Studio nicht erreichbar.'; aiState = 'error'
    }
  }

  async function getRelated() {
    relatedLoading = true
    try {
      const data = await apiPost('/api/ai/related', {
        question: card.question, answer: card.answer,
        package_id: $activePackageId || null, limit: 3
      })
      relatedIds = data.related || []
    } catch(e) { relatedIds = [] }
    relatedLoading = false
  }
</script>

<div class="card-area">
  <div class="fc" class:fc-split={flipped}>
    <!-- LINKS: Frage -->
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

    <!-- RECHTS: Antwort + Bewertung (nur nach Flip) -->
    {#if flipped}
      <div class="fc-col fc-col-right">
        <div class="fc-ans-lbl">
          <i class="fa-solid fa-square-check" style="color:var(--accent)"></i> Musterloesung
        </div>
        <div class="fc-ans markdown">{@html marked(card.answer)}</div>

        {#if aiState === 'idle' && !aiExplanation && $aiOnline}
          <button class="btn btn-ghost btn-sm ai-explain-btn" onclick={getExplanation}>
            <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Erklaerung laden
          </button>
        {:else if aiState === 'loading'}
          <AiProcess title="KI erklaert die Antwort" steps={EXPLAIN_STEPS} active={aiStep} />
        {:else if aiExplanation}
          <div class="ai-explain">
            <div class="ae-header">
              <i class="fa-solid fa-wand-magic-sparkles" style="color:var(--ac2)"></i> KI-Erklaerung
            </div>
            <div class="markdown">{@html marked(aiExplanation)}</div>
          </div>
        {/if}

        <div class="ai-assist-row">
          <button class="btn btn-ghost btn-sm" onclick={getRelated} disabled={relatedLoading}>
            <i class="fa-solid fa-link"></i> {relatedLoading ? 'Suche...' : 'Verwandte Karten'}
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

        <div class="rate-row">
          <button class="rate-btn rb-err" onclick={() => rate('wrong')} disabled={busy}>
            <i class="fa-solid fa-xmark"></i> Falsch
          </button>
          <button class="rate-btn rb-skip" onclick={() => rate('skip')} disabled={busy}>
            <i class="fa-solid fa-forward"></i> Skip
          </button>
          <button class="rate-btn rb-ok" onclick={() => rate('correct')} disabled={busy}>
            <i class="fa-solid fa-check"></i> Richtig
          </button>
        </div>

        {#if $activePackageId}
          <button class="btn btn-ghost btn-sm mat-link"
            onclick={() => window.open(`/#/packages/${$activePackageId}?tab=documents`, '_blank')}>
            <i class="fa-solid fa-book-open"></i> Im Material nachlesen
          </button>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
.card-area { display:flex;justify-content:center;padding:28px 32px; }
.fc {
  width:100%;max-width:640px;background:var(--bg1);border:1px solid var(--border);border-radius:4px;
  padding:28px;box-shadow:0 4px 24px var(--shadow);display:flex;flex-direction:column;
  transition:max-width .3s,border-color .3s,box-shadow .3s;
}
.fc.fc-split {
  display:grid;grid-template-columns:1fr 1fr;max-width:960px;gap:0;
  border-color:color-mix(in srgb,var(--accent) 55%,transparent);
  box-shadow:0 8px 40px var(--glow);
}
.fc-col { display:flex;flex-direction:column; }
.fc-col-right { border-left:1px solid var(--border);padding-left:28px; }
.fc-meta { display:flex;justify-content:space-between;align-items:center;margin-bottom:18px; }
.fc-id { font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace; }
.fc-diff { font-size:11px;font-weight:600;display:flex;align-items:center;gap:4px; }
.fc-q { font-size:18px;font-weight:600;color:var(--text0);line-height:1.5;margin-bottom:18px; }
.fc-hint { font-size:12px;color:var(--text2);background:var(--bg2);border-radius:4px;padding:7px 12px;margin-bottom:14px;display:flex;align-items:center;gap:7px; }
.flip-btn { width:100%;justify-content:center;padding:13px;font-size:14px; }
.fc-ans-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;display:flex;align-items:center;gap:6px; }
.fc-ans { font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7;color:var(--text1);background:var(--bg2);border-radius:4px;padding:12px 16px;white-space:pre-wrap;margin-bottom:14px; }

.ai-explain-btn { margin-bottom:14px; }
.ai-explain { background:var(--bg2);border:1px solid color-mix(in srgb,var(--ac2) 40%,transparent);border-radius:4px;padding:12px 16px;margin-bottom:14px; }
.ae-header { font-size:11px;font-weight:700;color:var(--ac2);letter-spacing:.07em;display:flex;align-items:center;gap:6px;margin-bottom:8px;text-transform:uppercase; }
.ai-explain :global(p) { font-size:12px;color:var(--text1);line-height:1.65; }
.ai-assist-row { display:flex;gap:6px;margin:10px 0 6px;flex-wrap:wrap; }
.ai-related-box { display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px; }
.related-tag { font-size:10px;background:var(--bg2);border:1px solid var(--border);border-radius:3px;padding:2px 8px;color:var(--accent); }

.rate-row { display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px; }
.rate-btn { padding:12px 10px;border-radius:4px;font-size:12px;font-weight:600;border:2px solid;transition:all .15s;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px; }
.rate-btn:disabled { opacity:0.5;cursor:default; }
.rb-ok  { border-color:var(--ok);color:var(--ok);background:transparent; }
.rb-ok:hover:not(:disabled)  { background:var(--ok);color:#fff; }
.rb-err { border-color:var(--err);color:var(--err);background:transparent; }
.rb-err:hover:not(:disabled) { background:var(--err);color:#fff; }
.rb-skip { border-color:var(--text3);color:var(--text2);background:transparent; }
.rb-skip:hover:not(:disabled) { background:var(--bg3); }
.mat-link { margin-top:10px;font-size:11px; }
</style>
