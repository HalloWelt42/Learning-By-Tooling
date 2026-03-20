<script>
  /**
   * Progress.svelte -- Gamification-Dashboard
   * Zentrale Anlaufstelle fuer XP, Streak, Abzeichen und Verlauf
   */
  import { onMount } from 'svelte'
  import { showToast, streakData, xpData, loadStreak, loadXp } from '../../stores/index.js'
  import { apiGet } from '../../utils/api.js'
  import ShieldBadge from './ShieldBadge.svelte'

  let tab          = $state('overview')
  let achievements = $state([])
  let history      = $state([])

  onMount(async () => {
    await Promise.all([loadAch(), loadHist(), loadStreak(), loadXp()])
  })

  async function loadAch()  { achievements = await apiGet('/api/achievements').catch(() => []) }
  async function loadHist() { history      = await apiGet('/api/history').catch(() => []) }

  let totalLevels = $derived(achievements.reduce((s, a) => s + a.level, 0))
  let maxLevel    = $derived(achievements.length * 30)
  let topBadges   = $derived(achievements.filter(a => a.level > 0).sort((a, b) => b.level - a.level).slice(0, 6))

  // XP-Aufschluesselung
  let diamonds = $derived(Math.floor(($xpData.xp_total || 0) / 1000000))
  let gold     = $derived(Math.floor((($xpData.xp_total || 0) % 1000000) / 1000))
  let silver   = $derived(($xpData.xp_total || 0) % 1000)

  function fmtDate(iso) {
    if (!iso) return '-'
    return new Date(iso).toLocaleString('de-DE', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
  }
  function pct(c, t) { return t > 0 ? Math.round(c/t*100) : 0 }
</script>

<div class="pg-page">

  <div class="pg-toolbar">
    <h1 class="pg-title"><i class="fa-solid fa-chart-line"></i> Fortschritt</h1>
    <div class="pg-tabs">
      {#each [
        ['overview',     'fa-gauge-high',        'Übersicht'],
        ['achievements', 'fa-trophy',            'Abzeichen'],
        ['history',      'fa-clock-rotate-left',  'Verlauf'],
      ] as [id, fa, lbl]}
        <button class="pg-tab" class:active={tab===id} onclick={() => tab=id}>
          <i class="fa-solid {fa}"></i> {lbl}
        </button>
      {/each}
    </div>
  </div>

  <div class="pg-body">

    <!-- Uebersicht -->
    {#if tab === 'overview'}
      <div class="ov-grid">

        <!-- XP-Karte -->
        <div class="ov-card ov-xp">
          <div class="ov-card-head">
            <i class="fa-solid fa-coins"></i> Erfahrung
          </div>
          <div class="ov-xp-coins">
            {#if diamonds > 0}
              <div class="ov-coin-row">
                <span class="xp-diamond"></span>
                <span class="ov-coin-val diamond">{diamonds}</span>
                <span class="ov-coin-lbl">Diamant</span>
              </div>
            {/if}
            {#if gold > 0}
              <div class="ov-coin-row">
                <span class="xp-gold"></span>
                <span class="ov-coin-val gold">{gold}</span>
                <span class="ov-coin-lbl">Gold</span>
              </div>
            {/if}
            <div class="ov-coin-row">
              <span class="xp-silver"></span>
              <span class="ov-coin-val silver">{silver}</span>
              <span class="ov-coin-lbl">Silber</span>
            </div>
          </div>
          <div class="ov-xp-total">
            <span class="mono">{$xpData.xp_total || 0}</span> XP gesamt
          </div>
          {#if $xpData.xp_today > 0}
            <div class="ov-xp-today">
              +<span class="mono">{$xpData.xp_today}</span> heute
            </div>
          {/if}
        </div>

        <!-- Streak-Karte -->
        <div class="ov-card ov-streak">
          <div class="ov-card-head">
            <i class="fa-solid fa-fire"></i> Tagessträhne
          </div>
          <div class="ov-streak-num">
            <span class="ov-big-num" class:streak-active={$streakData.today}>{$streakData.current || 0}</span>
            <span class="ov-big-unit">Tage</span>
          </div>
          {#if !$streakData.today && $streakData.current > 0}
            <div class="ov-streak-warn">
              <i class="fa-solid fa-triangle-exclamation"></i> Heute noch keine Session
            </div>
          {:else if $streakData.today}
            <div class="ov-streak-ok">
              <i class="fa-solid fa-circle-check"></i> Heute erledigt
            </div>
          {/if}
          {#if $streakData.longest > 0}
            <div class="ov-streak-best">
              Rekord: <span class="mono">{$streakData.longest}</span> Tage
            </div>
          {/if}
        </div>

        <!-- Abzeichen-Karte (Kompaktansicht) -->
        <div class="ov-card ov-badges">
          <div class="ov-card-head">
            <i class="fa-solid fa-trophy"></i> Abzeichen
            <button class="ov-more" onclick={() => tab='achievements'}>
              Alle anzeigen <i class="fa-solid fa-arrow-right"></i>
            </button>
          </div>
          <div class="ov-badge-summary">
            <span class="ov-badge-total">
              <span class="mono">{totalLevels}</span>/<span class="mono">{maxLevel}</span>
            </span>
            <span class="ov-badge-lbl">Gesamtlevel</span>
          </div>
          {#if topBadges.length > 0}
            <div class="ov-badge-row">
              {#each topBadges as b}
                <div class="ov-badge-item" title="{b.name}: {b.desc} ({b.value}) -- {b.color?.name}, Stufe {b.level}/30">
                  <ShieldBadge level={b.level} icon={b.icon} size={40} />
                  <span class="ov-badge-lvl mono">{b.level}</span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="ov-badge-empty">Noch keine Abzeichen freigeschaltet</div>
          {/if}
        </div>

        <!-- Letzte Sessions -->
        <div class="ov-card ov-recent">
          <div class="ov-card-head">
            <i class="fa-solid fa-clock-rotate-left"></i> Letzte Sessions
            {#if history.length > 3}
              <button class="ov-more" onclick={() => tab='history'}>
                Alle anzeigen <i class="fa-solid fa-arrow-right"></i>
              </button>
            {/if}
          </div>
          {#if history.length === 0}
            <div class="ov-badge-empty">Noch keine Sessions</div>
          {:else}
            <div class="ov-session-list">
              {#each history.slice(0, 5) as s (s.id)}
                <div class="ov-session-row">
                  <span class="ov-s-date mono">{fmtDate(s.started_at)}</span>
                  <span class="ov-s-mode">{s.mode}</span>
                  <span class="ov-s-bar">
                    <span class="prog-track"><span class="prog-fill" style="width:{pct(s.correct,s.total_cards)}%"></span></span>
                  </span>
                  <span class="ov-s-pct mono">{pct(s.correct,s.total_cards)}%</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>

      </div>

    <!-- Abzeichen (Detail) -->
    {:else if tab === 'achievements'}
      <div class="ach-summary">
        <span class="ach-n">{totalLevels}</span>
        <span class="ach-n-max">/ {maxLevel}</span>
        <span class="ach-lbl">Gesamtlevel</span>
      </div>
      <div class="ach-list">
        {#each achievements as a (a.id)}
          <div class="ach-row">
            <ShieldBadge level={a.level} icon={a.icon} size={48} />
            <div class="ach-info">
              <div class="ach-name">{a.name}</div>
              <div class="ach-desc">{a.desc}: <strong class="mono">{a.value}</strong></div>
              <div class="ach-level-row">
                {#if a.level > 0}
                  <span class="ach-color-dot" style="background:{a.color?.hex}"></span>
                  <span class="ach-lvl mono">{a.color?.name} -- Stufe {a.level}/30</span>
                {:else}
                  <span class="ach-lvl-inactive">Noch nicht begonnen</span>
                {/if}
                {#if a.next_at}
                  <span class="ach-next mono">Nächste: {a.next_at}</span>
                {/if}
              </div>
            </div>
            <div class="ach-prog-wrap">
              <div class="prog-track">
                <div class="prog-fill" style="width:{Math.min(a.level / 30 * 100, 100)}%;background:{a.color?.hex || 'var(--accent)'}"></div>
              </div>
            </div>
          </div>
        {/each}
      </div>

    <!-- Verlauf -->
    {:else if tab === 'history'}
      {#if history.length === 0}
        <div class="empty-state"><i class="fa-solid fa-clock-rotate-left"></i><p>Noch keine abgeschlossenen Sessions</p></div>
      {:else}
        <div class="hist-table">
          <div class="hist-head">
            <span class="hist-col-date">Datum</span>
            <span class="hist-col-mode">Modus</span>
            <span class="hist-col-bar">Fortschritt</span>
            <span class="hist-col-pct">%</span>
            <span class="hist-col-score">Ergebnis</span>
          </div>
          {#each history as s (s.id)}
            <div class="hist-row">
              <span class="hist-col-date mono">{fmtDate(s.started_at)}</span>
              <span class="hist-col-mode hist-mode-tag">{s.mode}</span>
              <span class="hist-col-bar">
                <span class="prog-track"><span class="prog-fill" style="width:{pct(s.correct,s.total_cards)}%"></span></span>
              </span>
              <span class="hist-col-pct mono">{pct(s.correct,s.total_cards)}%</span>
              <span class="hist-col-score mono">
                <i class="fa-solid fa-check" style="color:var(--ok)"></i> {s.correct||0}<span style="color:var(--text3)">/{s.total_cards}</span>
              </span>
            </div>
          {/each}
        </div>
      {/if}
    {/if}

  </div>
</div>

<style>
/* ── Layout ────────────────────────────────────────────────────────────── */
.pg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.pg-toolbar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 24px 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.pg-title {
  font-size: 18px;
  font-weight: 800;
  color: var(--text0);
  margin: 0;
  white-space: nowrap;
}
.pg-title i { color: var(--accent); font-size: 16px; }
.pg-tabs { display: flex; gap: 2px; }
.pg-tab {
  padding: 10px 16px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text2);
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  cursor: pointer;
  font-family: inherit;
  transition: all .15s;
}
.pg-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.pg-tab:hover { color: var(--text0); }
.pg-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  min-height: 0;
}

/* ── Uebersicht Grid ──────────────────────────────────────────────────── */
.ov-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  max-width: 800px;
}
.ov-card {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ov-card-head {
  font-size: 12px;
  font-weight: 700;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: .06em;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ov-card-head i { font-size: 12px; }
.ov-more {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  text-transform: none;
  letter-spacing: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}
.ov-more:hover { text-decoration: underline; }

/* XP-Karte */
.ov-xp-coins { display: flex; flex-direction: column; gap: 8px; }
.ov-coin-row { display: flex; align-items: center; gap: 10px; }
.ov-coin-val {
  font-size: 28px;
  font-weight: 800;
  font-family: 'Orbitron', 'JetBrains Mono', monospace;
  line-height: 1;
}
.ov-coin-val.silver  { color: #C0C0C0; }
.ov-coin-val.gold    { color: #FFD700; }
.ov-coin-val.diamond { color: #4FC3F7; }
.ov-coin-lbl { font-size: 11px; color: var(--text3); }
.ov-xp-total { font-size: 12px; color: var(--text2); border-top: 1px solid var(--border); padding-top: 10px; }
.ov-xp-total .mono { font-weight: 700; color: var(--text1); }
.ov-xp-today { font-size: 12px; color: var(--ok); font-weight: 600; }
.ov-xp-today .mono { font-weight: 700; }

.xp-silver {
  width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0;
  background: radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
  border: 2px solid #A0A0A0;
}
.xp-gold {
  width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0;
  background: radial-gradient(circle at 35% 35%, #FFD700, #B8860B);
  border: 2px solid #DAA520;
}
.xp-diamond {
  width: 24px; height: 24px; flex-shrink: 0;
  background: radial-gradient(circle at 30% 30%, #81D4FA, #0288D1);
  border: 2px solid #4FC3F7;
  clip-path: polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%);
}

/* Streak-Karte */
.ov-streak-num { display: flex; align-items: baseline; gap: 8px; }
.ov-big-num {
  font-size: 48px;
  font-weight: 800;
  font-family: 'Orbitron', 'JetBrains Mono', monospace;
  color: var(--text0);
  line-height: 1;
}
.ov-big-num.streak-active { color: #ff6b35; }
.ov-big-unit { font-size: 14px; color: var(--text3); font-weight: 600; }
.ov-streak-warn { font-size: 12px; color: var(--warn); display: flex; align-items: center; gap: 6px; }
.ov-streak-ok { font-size: 12px; color: var(--ok); display: flex; align-items: center; gap: 6px; }
.ov-streak-best { font-size: 12px; color: var(--text3); border-top: 1px solid var(--border); padding-top: 10px; }

/* Abzeichen-Kompakt (Uebersicht) */
.ov-badge-summary { display: flex; align-items: baseline; gap: 8px; }
.ov-badge-total { font-size: 20px; font-weight: 800; color: var(--accent); }
.ov-badge-lbl { font-size: 12px; color: var(--text2); }
.ov-badge-row { display: flex; gap: 12px; flex-wrap: wrap; }
.ov-badge-item { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.ov-badge-lvl { font-size: 10px; color: var(--text3); }
.ov-badge-empty { font-size: 12px; color: var(--text3); }

/* Letzte Sessions (Uebersicht) */
.ov-session-list { display: flex; flex-direction: column; gap: 0; }
.ov-session-row {
  display: grid;
  grid-template-columns: 110px 60px 1fr 44px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--bdr2);
}
.ov-session-row:last-child { border-bottom: none; }
.ov-s-date { font-size: 10px; color: var(--text2); }
.ov-s-mode { font-size: 9px; font-weight: 700; color: var(--text3); text-transform: uppercase; letter-spacing: .06em; }
.ov-s-bar .prog-track { display: block; }
.ov-s-bar .prog-fill { display: block; }
.ov-s-pct { font-size: 12px; font-weight: 700; color: var(--text1); text-align: right; }

/* ── Abzeichen (Detail) ───────────────────────────────────────────────── */
.ach-summary {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 20px;
}
.ach-n { font-size: 30px; font-weight: 800; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
.ach-n-max { font-size: 16px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.ach-lbl { font-size: 12px; color: var(--text2); margin-left: 8px; }
.ach-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; max-width: 800px; }
.ach-row {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 14px 18px;
}
.ach-info { flex: 1; min-width: 0; }
.ach-name { font-size: 13px; font-weight: 700; color: var(--text0); }
.ach-desc { font-size: 11px; color: var(--text2); margin-top: 2px; }
.ach-level-row { display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
.ach-color-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
.ach-lvl { font-size: 10px; color: var(--text2); }
.ach-lvl-inactive { font-size: 10px; color: var(--text3); }
.ach-next { font-size: 10px; color: var(--text3); }
.ach-prog-wrap { width: 80px; flex-shrink: 0; }
.ach-prog-wrap .prog-track { height: 4px; }

/* ── Verlauf ──────────────────────────────────────────────────────────── */
.hist-table { max-width: 760px; display: flex; flex-direction: column; }
.hist-head, .hist-row { display: grid; grid-template-columns: 130px 80px 1fr 52px 80px; align-items: center; }
.hist-head {
  font-size: 10px; font-weight: 700; color: var(--text3);
  text-transform: uppercase; letter-spacing: .06em;
  border-bottom: 1px solid var(--border);
}
.hist-row { border-bottom: 1px solid var(--bdr2); }
.hist-row:last-child { border-bottom: none; }
.hist-head span, .hist-row span { padding: 8px 12px; }
.hist-col-date { font-size: 10px; color: var(--text2); }
.hist-col-mode { font-size: 10px; }
.hist-mode-tag { text-transform: uppercase; letter-spacing: .06em; font-weight: 700; color: var(--text3); font-size: 9px; }
.hist-col-pct { font-size: 12px; font-weight: 700; color: var(--text1); text-align: right; }
.hist-col-score { font-size: 12px; font-weight: 600; text-align: right; color: var(--text2); }
.hist-col-bar .prog-track { display: block; }
.hist-col-bar .prog-fill { display: block; }
</style>
