<script>
  import { onMount } from 'svelte'
  import { showToast, loadGlobal, activePackageId } from '../stores/index.js'
  import { apiGet, apiPost } from '../utils/api.js'

  let tab          = $state('achievements')
  let achievements = $state([])
  let history      = $state([])
  let importFragen = $state('')
  let importAntwt  = $state('')
  let importResult = $state(null)
  let importing    = $state(false)

  onMount(async () => {
    await Promise.all([loadAch(), loadHist()])
  })

  async function loadAch()  { achievements = await apiGet('/api/achievements') }
  async function loadHist() { history      = await apiGet('/api/history') }

  async function doImport() {
    if (!importFragen || !importAntwt) { showToast('Beide Texte einfügen','error'); return }
    importing = true
    try {
      importResult = await apiPost('/api/import/markdown', { fragen: importFragen, antworten: importAntwt, package_id: $activePackageId || null })
      showToast(`${importResult.created} Karten importiert`, 'success')
      await loadGlobal()
    } catch(e) {
      showToast('Import fehlgeschlagen','error')
    }
    importing = false
  }

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
          <div class="ach-icon-wrap" style="color:{a.color?.hex || '#666'}">
            <i class="fa-solid {a.icon}"></i>
          </div>
          <div class="ach-info">
            <div class="ach-name">{a.name}</div>
            <div class="ach-desc">{a.desc}: <strong class="mono">{a.value}</strong></div>
            <div class="ach-level-row">
              {#if a.level > 0}
                <span class="ach-belt" style="background:{a.color?.hex || '#666'}">
                  {a.color?.name}
                  {#each a.star_colors || [] as sc, s}
                    <i class="fa-solid fa-star" style="font-size:9px;color:{sc}"></i>
                  {/each}
                </span>
                <span class="ach-lvl mono">Stufe {a.level}/30</span>
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

  <!-- Import -->
  {:else}
    <div class="card-box" style="max-width:900px">
      <div style="font-size:15px;font-weight:700;margin-bottom:8px">Karten aus Markdown importieren</div>
      <div style="font-size:12px;color:var(--text2);margin-bottom:20px;line-height:1.6">
        Füge den Inhalt der Fragen- und Antworten-Datei ein.<br>
        Format: <code style="background:var(--bg2);padding:1px 5px;border-radius: 3px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent)">paketname-fragen.md</code> +
        <code style="background:var(--bg2);padding:1px 5px;border-radius: 3px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent)">paketname-antworten.md</code>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
        <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
          Fragen-Datei
          <textarea bind:value={importFragen} rows="12" style="font-family:'JetBrains Mono',monospace;font-size:11px" placeholder="Inhalt hier einfügen…"></textarea>
        </label>
        <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
          Antworten-Datei
          <textarea bind:value={importAntwt} rows="12" style="font-family:'JetBrains Mono',monospace;font-size:11px" placeholder="Inhalt hier einfügen…"></textarea>
        </label>
      </div>
      {#if importResult}
        <div style="display:flex;gap:16px;padding:10px 14px;background:var(--bg2);border-radius: 4px;margin-bottom:14px;font-size:13px;font-weight:700">
          <span style="color:var(--ok)"><i class="fa-solid fa-circle-check"></i> {importResult.created} importiert</span>
          {#if importResult.skipped > 0}<span style="color:var(--warn)"><i class="fa-solid fa-circle-minus"></i> {importResult.skipped} übersprungen</span>{/if}
        </div>
      {/if}
      <button class="btn btn-primary" onclick={doImport} disabled={importing}>
        {importing ? 'Importiere…' : 'Importieren'}
      </button>
    </div>
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
  .ach-icon-wrap { font-size:22px;width:40px;text-align:center;flex-shrink:0; }
  .ach-info { flex:1;min-width:0; }
  .ach-name { font-size:13px;font-weight:700;color:var(--text0); }
  .ach-desc { font-size:11px;color:var(--text2);margin-top:2px; }
  .ach-level-row { display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap; }
  .ach-belt { display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:3px;font-size:10px;font-weight:700;color:#fff; }
  .ach-lvl  { font-size:10px;color:var(--text3); }
  .ach-next { font-size:10px;color:var(--text3); }
  .ach-prog-wrap { width:80px;flex-shrink:0; }
  .ach-prog-bar { height:4px;background:var(--bg3);border-radius:2px; }
  .ach-prog-fill { height:100%;border-radius:2px;transition:width .3s; }

  .hist-item { background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:13px 18px;display:flex;align-items:center;gap:18px; }
</style>
