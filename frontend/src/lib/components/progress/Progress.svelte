<script>
  import { onMount } from 'svelte'
  import { showToast } from '../../stores/index.js'
  import { apiGet } from '../../utils/api.js'
  import ShieldBadge from './ShieldBadge.svelte'

  let tab          = $state('achievements')
  let achievements = $state([])
  let history      = $state([])

  onMount(async () => {
    await Promise.all([loadAch(), loadHist()])
  })

  async function loadAch()  { achievements = await apiGet('/api/achievements') }
  async function loadHist() { history      = await apiGet('/api/history') }

  let totalLevels = $derived(achievements.reduce((s, a) => s + a.level, 0))

  function fmtDate(iso) {
    if (!iso) return '-'
    return new Date(iso).toLocaleString('de-DE', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
  }
  function pct(c, t) { return t > 0 ? Math.round(c/t*100) : 0 }
</script>

<div class="page">
  <div class="page-hd">
    <div>
      <h1 class="page-title"><i class="fa-solid fa-chart-line"></i> Fortschritt</h1>
      <p class="page-sub">Abzeichen und Lernverlauf</p>
    </div>
  </div>

  <div class="tabs">
    {#each [
      ['achievements', 'fa-trophy',           'Abzeichen'],
      ['history',      'fa-clock-rotate-left', 'Verlauf'],
    ] as [id, fa, lbl]}
      <button class="tab" class:active={tab===id} onclick={() => tab=id}>
        <i class="fa-solid {fa}"></i> {lbl}
      </button>
    {/each}
  </div>

  <!-- Achievements mit Levelsystem -->
  {#if tab === 'achievements'}
    <div class="ach-summary">
      <span class="ach-n">{totalLevels}</span>
      <span style="font-size:12px;color:var(--text2)">Gesamtlevel</span>
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
                <span style="font-size:10px;color:var(--text3)">Noch nicht begonnen</span>
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

  <!-- History -->
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

<style>
  .tabs { display:flex;gap:2px;margin-bottom:24px;border-bottom:1px solid var(--border); }
  .tab { padding:9px 18px;font-size:12px;font-weight:700;color:var(--text2);border:none;border-bottom:2px solid transparent;background:none;cursor:pointer;font-family:inherit;transition:all .15s;letter-spacing:.03em; }
  .tab.active { color:var(--accent);border-bottom-color:var(--accent); }
  .tab:hover  { color:var(--text0); }

  .ach-summary { display:flex;align-items:center;gap:14px;margin-bottom:24px;padding:18px;background:var(--bg1);border:1px solid var(--border);border-radius: 4px; }
  .ach-n    { font-size:30px;font-weight:800;color:var(--accent);font-family:'JetBrains Mono',monospace; }
  .ach-list { display:grid;grid-template-columns:repeat(2,1fr);gap:10px; }
  .ach-row  { display:flex;align-items:center;gap:14px;background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:14px 18px; }
  .ach-info { flex:1;min-width:0; }
  .ach-name { font-size:13px;font-weight:700;color:var(--text0); }
  .ach-desc { font-size:11px;color:var(--text2);margin-top:2px; }
  .ach-level-row { display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap; }
  .ach-color-dot { width:8px;height:8px;border-radius:2px;flex-shrink:0; }
  .ach-lvl  { font-size:10px;color:var(--text2); }
  .ach-next { font-size:10px;color:var(--text3); }
  .ach-prog-wrap { width:80px;flex-shrink:0; }
  .ach-prog-wrap .prog-track { height:4px; }

  .hist-table { max-width:760px;display:flex;flex-direction:column;gap:0; }
  .hist-head, .hist-row { display:grid;grid-template-columns:130px 80px 1fr 52px 80px;align-items:center;gap:0;padding:0; }
  .hist-head { font-size:10px;font-weight:700;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border); }
  .hist-row { border-bottom:1px solid var(--bdr2); }
  .hist-row:last-child { border-bottom:none; }
  .hist-head span, .hist-row span { padding:8px 12px; }
  .hist-col-date { font-size:10px;color:var(--text2); }
  .hist-col-mode { font-size:10px; }
  .hist-mode-tag { text-transform:uppercase;letter-spacing:.06em;font-weight:700;color:var(--text3);font-size:9px; }
  .hist-col-pct { font-size:12px;font-weight:700;color:var(--text1);text-align:right; }
  .hist-col-score { font-size:12px;font-weight:600;text-align:right;color:var(--text2); }
  .hist-col-bar .prog-track { display:block; }
  .hist-col-bar .prog-fill { display:block; }
</style>
