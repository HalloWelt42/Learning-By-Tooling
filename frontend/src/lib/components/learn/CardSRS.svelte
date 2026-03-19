<script>
  /**
   * CardSRS -- Spaced Repetition: Aufdecken + Quality-Bewertung (SM-2)
   * 2-Spalten nach Flip: links Frage, rechts Antwort + Quality-Buttons
   */
  import { activePackageId } from '../../stores/index.js'
  import { marked } from 'marked'

  let { card, onReview, onAdvance } = $props()

  const startTime = Date.now()
  let flipped = $state(false)
  let busy    = $state(false)

  const DL = ['','Leicht','Mittel','Schwer']
  const DC = ['','d1','d2','d3']
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
          <i class="fa-solid fa-square-check" style="color:var(--accent)"></i> Musterloesung
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
            onclick={() => window.open(`/#/packages/${$activePackageId}?tab=material`, '_blank')}>
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
.fc-id { font-size:10px;color:var(--text3); }
.fc-diff { font-size:11px;font-weight:600;display:flex;align-items:center;gap:4px; }
.fc-q { font-size:18px;font-weight:600;color:var(--text0);line-height:1.5;margin-bottom:18px; }
.fc-hint { font-size:12px;color:var(--text2);background:var(--bg2);border-radius:4px;padding:7px 12px;margin-bottom:14px;display:flex;align-items:center;gap:7px; }
.flip-btn { width:100%;justify-content:center;padding:13px;font-size:14px; }
.fc-ans-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;display:flex;align-items:center;gap:6px; }
.fc-ans { font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7;color:var(--text1);background:var(--bg2);border-radius:4px;padding:12px 16px;white-space:pre-wrap;margin-bottom:14px; }

.srs-q-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;margin-top:4px; }
.srs-btns { display:grid;grid-template-columns:1fr 1fr;gap:8px; }
.rate-btn { padding:12px 10px;border-radius:4px;font-size:12px;font-weight:600;border:2px solid;transition:all .15s;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px; }
.rate-btn:disabled { opacity:0.5;cursor:default; }
.rb-ok   { border-color:var(--ok);color:var(--ok);background:transparent; }
.rb-ok:hover:not(:disabled)   { background:var(--ok);color:#fff; }
.rb-err  { border-color:var(--err);color:var(--err);background:transparent; }
.rb-err:hover:not(:disabled)  { background:var(--err);color:#fff; }
.rb-warn { border-color:var(--warn);color:var(--warn);background:transparent; }
.rb-warn:hover:not(:disabled) { background:var(--warn);color:#fff; }
.rb-star { border-color:var(--accent);color:var(--accent);background:transparent; }
.rb-star:hover:not(:disabled) { background:var(--accent);color:#fff; }
.mat-link { margin-top:10px;font-size:11px; }
</style>
