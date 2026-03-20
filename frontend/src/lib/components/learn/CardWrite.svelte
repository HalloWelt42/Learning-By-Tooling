<script>
  /**
   * CardWrite -- Freitext: Antwort eintippen, KI bewertet oder Selbstvergleich
   *
   * Ablauf MIT KI:
   *   1. Antwort tippen
   *   2. "Antwort pruefen" -> KI bewertet (= die Bewertung, KEINE manuellen Buttons)
   *   3. KI-Feedback sichtbar (Score + Text)
   *   4. Optional: "Musterloesung anzeigen" aufklappen
   *   5. Optional: "Im Material nachlesen"
   *   6. "Weiter" -> naechste Karte
   *
   * Ablauf OHNE KI:
   *   1. Antwort tippen
   *   2. "Antwort vergleichen" -> Musterloesung aufdecken
   *   3. Selbstbewertung: "Gewusst" / "Nicht gewusst" (nur 2 Optionen)
   *
   * 2-Spalten-Layout nach Bewertung: links Frage+Eingabe, rechts Ergebnis+Aktionen
   */
  import { aiOnline, activePackageId } from '../../stores/index.js'
  import { marked } from 'marked'
  import AiProcess from './AiProcess.svelte'
  import { DL, DC } from '../../utils/difficulty.js'

  let { card, useAI, onReview, onAdvance } = $props()

  // Interner State
  const startTime = Date.now()
  let userAnswer  = $state('')
  let flipped     = $state(false)
  let aiFeedback  = $state(null)   // {score, feedback, result}
  let aiState     = $state('idle') // idle | loading | done | error
  let aiStep      = $state(0)
  let busy        = $state(false)
  let pendingResp = $state(null)

  const EVAL_STEPS = [
    { label: 'Antwort empfangen', sublabel: 'Eingabe wird vorbereitet' },
    { label: 'Frage & Antwort analysieren', sublabel: 'Vergleich mit Musterloesung' },
    { label: 'Kernaussagen pruefen', sublabel: 'Semantische Bewertung laeuft' },
    { label: 'Feedback formulieren', sublabel: 'KI schreibt Rueckmeldung' },
  ]

  // Zeigt rechte Spalte wenn: KI-Feedback da ODER Karte aufgedeckt
  let showRight = $derived(!!aiFeedback || flipped)

  // -- Write + KI: Antwort pruefen --
  async function submitAI() {
    if (!userAnswer.trim() || aiState === 'loading') return
    aiState = 'loading'
    aiStep = 0
    const timer = setInterval(() => {
      aiStep = Math.min(aiStep + 1, EVAL_STEPS.length - 1)
    }, 900)
    try {
      const resp = await onReview({
        result: 'unknown',
        user_answer: userAnswer,
        use_ai: true,
        time_ms: Date.now() - startTime,
      })
      clearInterval(timer)
      aiStep = EVAL_STEPS.length
      aiFeedback = { score: resp.ai_score, feedback: resp.ai_feedback, result: resp.result }
      pendingResp = resp
      aiState = 'done'
    } catch(e) {
      clearInterval(timer)
      aiState = 'error'
      // KI ausgefallen: Fallback auf Selbstvergleich, Session laeuft weiter
      aiFeedback = null
      aiOfflineFallback = true
      flipped = true
    }
  }

  // KI-Ausfall waehrend Session: User bewertet selbst
  let aiOfflineFallback = $state(false)

  // -- Write + KI: Weiter nach Feedback --
  function afterFeedback() {
    if (pendingResp) onAdvance(pendingResp)
  }

  // -- Write ohne KI: Antwort aufdecken --
  function showAnswer() {
    flipped = true
  }

  // -- Write ohne KI: Selbstbewertung --
  async function rateSelf(result) {
    if (busy) return
    busy = true
    try {
      const resp = await onReview({ result, user_answer: userAnswer, time_ms: Date.now() - startTime })
      onAdvance(resp)
    } catch(e) { busy = false }
  }

  // -- Direkt aufdecken (KI ueberspringen) --
  async function directFlip() {
    flipped = true
    // Kein Review hier -- User muss noch bewerten
  }

  // Wenn KI aktiv war UND User direkt aufdeckt, braucht er trotzdem Buttons
  // Aber: submitAI schickt bereits den Review. Also "Direkt aufdecken" = ohne KI weiter.
  async function directFlipAndRate(result) {
    if (busy) return
    busy = true
    const resp = await onReview({ result, user_answer: userAnswer, time_ms: Date.now() - startTime })
    onAdvance(resp)
  }
</script>

<div class="card-area">
  <div class="fc" class:fc-split={showRight}>

    <!-- LINKS: Frage + Eingabe -->
    <div class="fc-col">
      <div class="fc-meta">
        <span class="mono fc-id">{card.card_id}</span>
        <span class="{DC[card.difficulty]} fc-diff">
          <i class="fa-solid {card.difficulty===1?'fa-gauge-simple':card.difficulty===2?'fa-gauge':'fa-gauge-high'}"></i>
          {DL[card.difficulty]}
        </span>
      </div>

      <div class="fc-q">{card.question}</div>

      {#if card.hint && !showRight}
        <div class="fc-hint">
          <i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i>
          {card.hint}
        </div>
      {/if}

      <!-- Textarea: nur vor Bewertung/Flip -->
      {#if !showRight}
        <textarea class="fc-input" placeholder="Deine Antwort..." bind:value={userAnswer} rows="4"></textarea>

        <!-- Aktions-Buttons -->
        {#if useAI && $aiOnline}
          {#if userAnswer.trim()}
            {#if aiState === 'idle'}
              <button class="btn btn-primary flip-btn" onclick={submitAI}>
                <i class="fa-solid fa-wand-magic-sparkles"></i> Antwort pruefen
              </button>
              <button class="btn btn-ghost" style="margin-top:6px" onclick={showAnswer}>
                <i class="fa-solid fa-eye"></i> Direkt aufdecken
              </button>
            {:else if aiState === 'loading'}
              <AiProcess title="KI bewertet deine Antwort" steps={EVAL_STEPS} active={aiStep} />
            {/if}
          {:else}
            <div class="write-hint">
              <i class="fa-solid fa-pen" style="color:var(--text3)"></i>
              Tippe zuerst deine Antwort ein
            </div>
          {/if}
        {:else}
          <!-- Ohne KI -->
          {#if userAnswer.trim()}
            <button class="btn btn-primary flip-btn" onclick={showAnswer}>
              <i class="fa-solid fa-eye"></i> Antwort vergleichen
            </button>
          {:else}
            <div class="write-hint">
              <i class="fa-solid fa-pen" style="color:var(--text3)"></i>
              Tippe zuerst deine Antwort ein
            </div>
          {/if}
        {/if}
      {:else}
        <!-- Nach Bewertung: eigene Antwort anzeigen -->
        {#if userAnswer}
          <div class="fc-ans-lbl" style="color:var(--text2)">
            <i class="fa-solid fa-pen" style="color:var(--text3)"></i> Deine Antwort
          </div>
          <div class="fc-user-ans">{userAnswer}</div>
        {/if}
      {/if}
    </div>

    <!-- RECHTS: Ergebnis + Aktionen -->
    {#if showRight}
      <div class="fc-col fc-col-right">

        <!-- KI-Feedback (Write+KI Modus) -->
        {#if aiFeedback}
          <div class="ai-feedback" class:fb-ok={aiFeedback.score >= 0.6} class:fb-err={aiFeedback.score < 0.6}>
            <div class="fb-header">
              <i class="fa-solid {aiFeedback.score >= 0.6 ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
              <span class="fb-score">{Math.round(aiFeedback.score * 100)}%</span>
              <span class="fb-verdict">{aiFeedback.score >= 0.6 ? 'Richtig!' : 'Noch nicht ganz'}</span>
            </div>
            {#if aiFeedback.feedback}
              <div class="fb-text markdown">{@html marked(aiFeedback.feedback)}</div>
            {/if}
          </div>
        {/if}

        <!-- Musterloesung (nach Flip) -->
        {#if flipped}
          <div class="fc-ans-lbl">
            <i class="fa-solid fa-square-check" style="color:var(--accent)"></i> Musterloesung
          </div>
          <div class="fc-ans markdown">{@html marked(card.answer)}</div>
        {/if}

        <!-- Aktionen je nach Modus -->
        {#if aiFeedback}
          <!-- KI hat bewertet: Musterloesung optional, Material optional, Weiter -->
          <div class="write-actions">
            {#if !flipped}
              <button class="btn btn-ghost" onclick={() => flipped = true}>
                <i class="fa-solid fa-eye"></i> Musterloesung anzeigen
              </button>
            {/if}
            {#if $activePackageId}
              <button class="btn btn-ghost btn-sm" style="font-size:11px"
                onclick={() => window.open(`/#/packages/${$activePackageId}?tab=material`, '_blank')}>
                <i class="fa-solid fa-book-open"></i> Im Material nachlesen
              </button>
            {/if}
            <button class="btn btn-primary" onclick={afterFeedback}>
              <i class="fa-solid fa-forward"></i> Weiter
            </button>
          </div>
        {:else if flipped}
          <!-- Ohne KI / KI-Ausfall: Selbstbewertung -->
          {#if aiOfflineFallback}
            <div class="ai-offline-warn">
              <i class="fa-solid fa-triangle-exclamation"></i>
              KI kurzzeitig nicht erreichbar. Vergleiche selbst mit der Musterloesung.
            </div>
          {/if}
          <div class="rate-row-write">
            <button class="rate-btn rb-err" onclick={() => rateSelf('wrong')} disabled={busy}>
              <i class="fa-solid fa-xmark"></i> Nicht gewusst
            </button>
            <button class="rate-btn rb-ok" onclick={() => rateSelf('correct')} disabled={busy}>
              <i class="fa-solid fa-check"></i> Gewusst
            </button>
          </div>
          {#if $activePackageId}
            <button class="btn btn-ghost btn-sm mat-link"
              onclick={() => window.open(`/#/packages/${$activePackageId}?tab=material`, '_blank')}>
              <i class="fa-solid fa-book-open"></i> Im Material nachlesen
            </button>
          {/if}
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
.fc-input { margin-bottom:14px;font-size:13px;padding:12px;border-radius:4px; }
.flip-btn { width:100%;justify-content:center;padding:13px;font-size:14px; }
.write-hint { font-size:12px;color:var(--text3);display:flex;align-items:center;gap:8px;padding:12px;justify-content:center; }

.fc-ans-lbl { font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:8px;display:flex;align-items:center;gap:6px; }
.fc-ans { font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7;color:var(--text1);background:var(--bg2);border-radius:4px;padding:12px 16px;white-space:pre-wrap;margin-bottom:14px; }
.fc-user-ans { font-size:12px;line-height:1.7;color:var(--text2);background:var(--bg2);border:1px dashed var(--border);border-radius:4px;padding:12px 16px;white-space:pre-wrap;margin-bottom:14px; }

/* KI Feedback */
.ai-feedback { border-radius:4px;padding:14px 16px;margin-bottom:12px;border:1px solid; }
.ai-feedback.fb-ok { border-color:color-mix(in srgb,var(--ok) 40%,transparent);background:var(--glowok); }
.ai-feedback.fb-err { border-color:color-mix(in srgb,var(--err) 40%,transparent);background:color-mix(in srgb,var(--err) 8%,transparent); }
.fb-header { display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:14px;font-weight:600; }
.fb-ok .fb-header i, .fb-ok .fb-header { color:var(--ok); }
.fb-err .fb-header i, .fb-err .fb-header { color:var(--err); }
.fb-score { font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700; }
.fb-verdict { font-size:13px; }
.fb-text { font-size:12px;color:var(--text1);line-height:1.6; }

/* Aktionen */
.write-actions { display:flex;flex-direction:column;gap:8px;margin-top:10px; }
.rate-row-write { display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px; }
.rate-btn { padding:12px 10px;border-radius:4px;font-size:12px;font-weight:600;border:2px solid;transition:all .15s;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px; }
.rate-btn:disabled { opacity:0.5;cursor:default; }
.rb-ok  { border-color:var(--ok);color:var(--ok);background:transparent; }
.rb-ok:hover:not(:disabled)  { background:var(--ok);color:#fff; }
.rb-err { border-color:var(--err);color:var(--err);background:transparent; }
.rb-err:hover:not(:disabled) { background:var(--err);color:#fff; }
.mat-link { margin-top:10px;font-size:11px; }
.ai-offline-warn { font-size:11px;color:var(--warn);background:color-mix(in srgb,var(--warn) 10%,transparent);border:1px solid color-mix(in srgb,var(--warn) 30%,transparent);border-radius:4px;padding:8px 12px;margin-bottom:10px;display:flex;align-items:center;gap:8px; }
</style>
