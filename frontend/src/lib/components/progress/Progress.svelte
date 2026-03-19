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
                <span class="ach-lvl mono" style="color:{a.color?.hex}">{a.color?.name} -- Stufe {a.level}/30</span>
              {:else}
                <span style="font-size:10px;color:var(--text3)">Noch nicht begonnen</span>
              {/if}
              {#if a.next_at}
                <span class="ach-next mono">Nächste: {a.next_at}</span>
              {/if}
            </div>
          </div>
          <div class="ach-prog-wrap">
            <div class="ach-prog-bar">
              <div class="ach-prog-fill" style="width:{Math.min(a.level / 30 * 100, 100)}%;background:{a.color?.hex || 'var(--accent)'}"></div>
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
      <div style="display:flex;flex-direction:column;gap:8px;max-width:760px">
        {#each history as s (s.id)}
          <div class="hist-item">
            <div>
              <div class="mono" style="font-size:10px;color:var(--text2)">{fmtDate(s.started_at)}</div>
              <div style="font-size:9px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-top:1px">{s.mode}</div>
            </div>
            <div style="flex:1;display:flex;align-items:center;gap:10px">
              <div style="flex:1;height:5px;background:var(--bg3);border-radius: 3px;overflow:hidden">
                <div style="height:100%;background:var(--ok);border-radius: 3px;width:{pct(s.correct,s.total_cards)}%"></div>
              </div>
              <span class="mono" style="font-size:11px;font-weight:700;color:var(--ok);min-width:34px;text-align:right">{pct(s.correct,s.total_cards)}%</span>
            </div>
            <div style="display:flex;gap:8px;font-size:12px;font-weight:700;font-family:'JetBrains Mono',monospace">
              <span style="color:var(--ok)"><i class="fa-solid fa-check"></i> {s.correct||0}</span>
              <span style="color:var(--text3)">/{s.total_cards}</span>
            </div>
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
  .ach-list { display:flex;flex-direction:column;gap:10px;max-width:700px; }
  .ach-row  { display:flex;align-items:center;gap:14px;background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:14px 18px; }
  .ach-info { flex:1;min-width:0; }
  .ach-name { font-size:13px;font-weight:700;color:var(--text0); }
  .ach-desc { font-size:11px;color:var(--text2);margin-top:2px; }
  .ach-level-row { display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap; }
  .ach-lvl  { font-size:10px; }
  .ach-next { font-size:10px;color:var(--text3); }
  .ach-prog-wrap { width:80px;flex-shrink:0; }
  .ach-prog-bar { height:4px;background:var(--bg3);border-radius:2px; }
  .ach-prog-fill { height:100%;border-radius:2px;transition:width .3s; }

  .hist-item { background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:13px 18px;display:flex;align-items:center;gap:18px; }
</style>
