<script>
  /**
   * CardMC -- Multiple Choice: 4 Optionen, Auto-Bewertung
   * Bleibt einspaltig (MC-Optionen brauchen die volle Breite)
   */
  import { apiGet } from '../../utils/api.js'

  let { card, onReview, onAdvance } = $props()

  const startTime = Date.now()
  let mcOptions  = $state([])
  let mcSelected = $state(null)
  let mcRevealed = $state(false)
  let mcLoading  = $state(true)
  let busy       = $state(false)
  let pendingResp = $state(null)

  const DL = ['','Leicht','Mittel','Schwer']
  const DC = ['','d1','d2','d3']

  // MC-Optionen beim Mount laden
  async function init() {
    mcLoading = true
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
    } catch(e) { mcOptions = [] }
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
      pendingResp = await onReview({ result, time_ms: Date.now() - startTime })
    } catch(e) {
      // Fehler beim Review -- UI bleibt aufgedeckt, Weiter leitet trotzdem weiter
      pendingResp = { result, done: false }
    }
    busy = false
  }

  function next() {
    if (pendingResp) onAdvance(pendingResp)
  }

  // Fallback: Flip-Modus wenn keine MC-Optionen
  let fallbackFlipped = $state(false)
  async function fallbackRate(result) {
    if (busy) return
    busy = true
    const resp = await onReview({ result, time_ms: Date.now() - startTime })
    onAdvance(resp)
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
          <div style="font-size:11px;color:var(--text3);margin-top:2px">Optionen aus Cache oder KI...</div>
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
    {:else}
      <!-- Fallback: keine MC-Optionen vorhanden -->
      <div style="font-size:11px;color:var(--text3);padding:8px">MC nicht verfuegbar -- Fallback auf Karteikarte</div>
      {#if !fallbackFlipped}
        <button class="btn btn-primary flip-btn" onclick={() => fallbackFlipped = true}>
          <i class="fa-solid fa-eye"></i> Antwort zeigen
        </button>
      {:else}
        <div class="fc-ans-lbl">
          <i class="fa-solid fa-square-check" style="color:var(--accent)"></i> Antwort
        </div>
        <div class="fc-ans">{card.answer}</div>
        <div class="rate-row">
          <button class="rate-btn rb-err" onclick={() => fallbackRate('wrong')} disabled={busy}>
            <i class="fa-solid fa-xmark"></i> Falsch
          </button>
          <button class="rate-btn rb-skip" onclick={() => fallbackRate('skip')} disabled={busy}>
            <i class="fa-solid fa-forward"></i> Skip
          </button>
          <button class="rate-btn rb-ok" onclick={() => fallbackRate('correct')} disabled={busy}>
            <i class="fa-solid fa-check"></i> Richtig
          </button>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
.card-area { display:flex;justify-content:center;padding:28px 32px; }
.fc {
  width:100%;max-width:640px;background:var(--bg1);border:1px solid var(--border);border-radius:4px;
  padding:28px;box-shadow:0 4px 24px var(--shadow);display:flex;flex-direction:column;
}
.fc-meta { display:flex;justify-content:space-between;align-items:center;margin-bottom:18px; }
.fc-id { font-size:10px;color:var(--text3); }
.fc-diff { font-size:11px;font-weight:600;display:flex;align-items:center;gap:4px; }
.fc-q { font-size:18px;font-weight:600;color:var(--text0);line-height:1.5;margin-bottom:18px; }
.fc-hint { font-size:12px;color:var(--text2);background:var(--bg2);border-radius:4px;padding:7px 12px;margin-bottom:14px;display:flex;align-items:center;gap:7px; }
.flip-btn { width:100%;justify-content:center;padding:13px;font-size:14px; }
.fc-ans-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;display:flex;align-items:center;gap:6px; }
.fc-ans { font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7;color:var(--text1);background:var(--bg2);border-radius:4px;padding:12px 16px;white-space:pre-wrap;margin-bottom:14px; }

.mc-loading { display:flex;align-items:center;gap:14px;padding:20px;background:var(--bg2);border:1px solid var(--border);border-radius:4px; }
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

.rate-row { display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px; }
.rate-btn { padding:12px 10px;border-radius:4px;font-size:12px;font-weight:600;border:2px solid;transition:all .15s;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px; }
.rate-btn:disabled { opacity:0.5;cursor:default; }
.rb-ok  { border-color:var(--ok);color:var(--ok);background:transparent; }
.rb-ok:hover:not(:disabled)  { background:var(--ok);color:#fff; }
.rb-err { border-color:var(--err);color:var(--err);background:transparent; }
.rb-err:hover:not(:disabled) { background:var(--err);color:#fff; }
.rb-skip { border-color:var(--text3);color:var(--text2);background:transparent; }
.rb-skip:hover:not(:disabled) { background:var(--bg3); }
</style>
