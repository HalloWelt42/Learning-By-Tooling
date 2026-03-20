<script>
  import { categories, showToast, loadGlobal } from '../../stores/index.js'
  import { apiGet, apiPost, apiDelete, BASE } from '../../utils/api.js'
  import { navigate } from '../../utils/router.js'
  import { onMount } from 'svelte'
  import CardsTab from './CardsTab.svelte'
  import WorkshopTab from './WorkshopTab.svelte'
  import MaterialTab from './MaterialTab.svelte'

  let { pkg } = $props()

  let tab = $state('overview')

  let stats     = $state(null)
  let searchQ   = $state('')

  // Reset
  let confirmReset = $state(false)
  async function resetStats() {
    if (!confirmReset) { confirmReset = true; setTimeout(() => confirmReset = false, 3000); return }
    try {
      await apiPost('/api/reset/my-stats', { package_id: pkg.id })
      showToast('Lernfortschritt zurückgesetzt', 'success')
      confirmReset = false
      await loadStats()
    } catch(e) { showToast(e.message, 'error') }
  }

  // Freigabe
  let showShare     = $state(false)
  let shareUsers    = $state([])
  let shareEmail    = $state('')
  let shareRole     = $state('learner')

  async function loadShareUsers() {
    try { shareUsers = await apiGet(`/api/packages/${pkg.id}/users`) } catch(e) { shareUsers = [] }
  }
  async function doShare() {
    if (!shareEmail.trim()) return
    try {
      await apiPost(`/api/packages/${pkg.id}/share`, { email: shareEmail, role: shareRole })
      showToast(`Paket für ${shareEmail} freigegeben`, 'success')
      shareEmail = ''
      await loadShareUsers()
    } catch(e) {
      showToast(e.message || 'Freigabe fehlgeschlagen', 'error')
    }
  }
  async function removeShare(userId) {
    try {
      await apiDelete(`/api/packages/${pkg.id}/share/${userId}`)
      showToast('Freigabe entfernt', 'success')
      await loadShareUsers()
    } catch(e) {
      showToast('Fehler beim Entfernen', 'error')
    }
  }

  onMount(() => {
    loadStats()
    const hash = window.location.hash
    const qIdx = hash.indexOf('?')
    if (qIdx > -1) {
      const params = new URLSearchParams(hash.substring(qIdx))
      if (params.get('tab')) tab = params.get('tab')
      if (params.get('q')) searchQ = params.get('q')
    }
  })

  async function exportPkg() {
    try {
      const token = localStorage.getItem('lbt-token')
      const res = await fetch(`${BASE}/api/packages/${pkg.id}/export`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (!res.ok) throw new Error('Export fehlgeschlagen')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = res.headers.get('content-disposition')?.match(/filename="(.+)"/)?.[1] || 'paket.zip'
      a.click()
      URL.revokeObjectURL(url)
      showToast('Paket exportiert', 'success')
    } catch(e) {
      showToast(e.message, 'error')
    }
  }

  async function loadStats() { stats = await apiGet(`/api/packages/${pkg.id}/stats`).catch(() => null) }

  function pct(c, t) { return t > 0 ? Math.round(c / t * 100) : 0 }

  let pendingDrafts = $derived(stats?.pending_drafts || 0)
  let catCounts = $derived((stats?.by_category || []).filter(c => c.count > 0))
</script>

<div class="pd-wrap">

  <!-- ── Header ──────────────────────────────────────────────────────────── -->
  <div class="pd-header">
    <div class="pd-hd-left">
      <button class="back-btn" onclick={() => navigate('/packages')}>
        <i class="fa-solid fa-arrow-left"></i> Lernpakete
      </button>
      <div class="pd-title-row">
        <div class="pd-icon" style="background:{pkg.color}">
          <i class="fa-solid {pkg.icon}"></i>
        </div>
        <div style="flex:1">
          <h1 class="pd-name">{pkg.name}</h1>
          {#if pkg.description}<p class="pd-desc">{pkg.description}</p>{/if}
        </div>
        <button class="btn btn-ghost btn-sm" onclick={() => { showShare = !showShare; if (showShare) loadShareUsers() }}>
          <i class="fa-solid fa-user-group"></i> Teilen
        </button>
      </div>

      {#if showShare}
        <div class="share-panel">
          <div class="share-hd">Paket freigeben</div>
          <div class="share-form">
            <input type="email" class="input" placeholder="E-Mail-Adresse" bind:value={shareEmail} style="flex:1" />
            <select class="input" bind:value={shareRole} style="width:120px">
              <option value="learner">Lerner</option>
              <option value="owner">Besitzer</option>
            </select>
            <button class="btn btn-primary btn-sm" onclick={doShare}>Freigeben</button>
          </div>
          {#if shareUsers.length > 0}
            <div class="share-list">
              {#each shareUsers as su (su.id)}
                <div class="share-user">
                  <i class="fa-solid fa-user" style="color:var(--text3)"></i>
                  <span class="share-email">{su.display_name || su.email}</span>
                  <span class="share-role mono">{su.role}</span>
                  <button class="btn-icon btn-icon-danger" title="Freigabe entziehen" onclick={() => removeShare(su.id)}>
                    <i class="fa-solid fa-xmark"></i>
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    {#if stats}
      <div class="pd-stats">
        <div class="pds"><i class="fa-solid fa-layer-group"></i><span class="pds-val">{stats.total_cards}</span><span class="pds-lbl">Karten</span></div>
        <div class="pds"><i class="fa-solid fa-file-lines"></i><span class="pds-val">{stats.total_docs}</span><span class="pds-lbl">Dokumente</span></div>
        <div class="pds ok"><i class="fa-solid fa-bullseye"></i><span class="pds-val">{pct(stats.total_correct,stats.total_reviews)}%</span><span class="pds-lbl">Trefferquote</span></div>
        {#if stats.due_today>0}
          <div class="pds warn"><i class="fa-solid fa-brain"></i><span class="pds-val">{stats.due_today}</span><span class="pds-lbl">Fällig</span></div>
        {/if}
        {#if stats.pending_drafts > 0}
          <button class="pds accent clickable" onclick={() => tab = 'workshop'}>
            <i class="fa-solid fa-pen-to-square"></i>
            <span class="pds-val">{stats.pending_drafts}</span>
            <span class="pds-lbl">Entwürfe</span>
          </button>
        {/if}
        <button class="btn btn-ghost" title="Paket als ZIP exportieren" onclick={exportPkg}>
          <i class="fa-solid fa-file-export"></i>
        </button>
        <button class="btn btn-ghost btn-sm" class:btn-warn={confirmReset} title="Lernfortschritt für dieses Paket zurücksetzen" onclick={resetStats}>
          <i class="fa-solid fa-arrow-rotate-left"></i> {confirmReset ? 'Wirklich?' : ''}
        </button>
        <button class="btn btn-primary" onclick={()=>navigate('/learn')}>
          <i class="fa-solid fa-play"></i> Lernen
        </button>
      </div>
    {/if}
  </div>

  <!-- ── Tabs ─────────────────────────────────────────────────────────────── -->
  <div class="pd-tabs">
    {#each [
      ['overview',  'fa-gauge',              'Übersicht',  0],
      ['workshop',  'fa-screwdriver-wrench', 'Werkstatt',   pendingDrafts],
      ['cards',     'fa-layer-group',        'Karten',      0],
      ['material',  'fa-book-open',          'Material',    0],
    ] as [id, fa, lbl, badge]}
      <button class="pd-tab" class:active={tab === id} onclick={() => tab = id}>
        <i class="fa-solid {fa}"></i> {lbl}
        {#if badge > 0}<span class="tab-badge">{badge}</span>{/if}
      </button>
    {/each}
  </div>

  <!-- ── Tab-Inhalte ───────────────────────────────────────────────────────── -->
  <div class="pd-body">

    <!-- UEBERSICHT -->
    {#if tab === 'overview'}
      <div class="tab-page">
        {#if stats && catCounts.length > 0}
          <div class="overview-cols">
            <div class="card-box">
              <div class="section-label">Karten nach Kategorie</div>
              {#each catCounts as cat}
                <div class="cat-row">
                  <div class="cat-icon-box" style="background:color-mix(in srgb, {cat.color} 15%, transparent)">
                    <i class="fa-solid {cat.icon}" style="color:{cat.color}"></i>
                  </div>
                  <span class="cat-name">{cat.name}</span>
                  <div class="prog-track">
                    <div class="prog-fill" style="width:{cat.shown > 0 ? pct(cat.correct, cat.shown) : 0}%"></div>
                  </div>
                  <span class="cat-n">{cat.count}</span>
                </div>
              {/each}
            </div>

            {#if stats.srs_stacks}
              {@const s = stats.srs_stacks}
              {@const t = s.new + s.due + s.learning + s.solid + s.mastered}
              <div class="card-box">
                <div class="section-label">Lernstand (SRS)</div>
                {#if t > 0}
                  <div class="srs-bar">
                    {#if s.mastered > 0}<div class="srs-seg srs-mastered" style="width:{s.mastered / t * 100}%" title="Gemeistert: {s.mastered}"></div>{/if}
                    {#if s.solid > 0}<div class="srs-seg srs-solid" style="width:{s.solid / t * 100}%" title="Gefestigt: {s.solid}"></div>{/if}
                    {#if s.learning > 0}<div class="srs-seg srs-learning" style="width:{s.learning / t * 100}%" title="Lernphase: {s.learning}"></div>{/if}
                    {#if s.due > 0}<div class="srs-seg srs-due" style="width:{s.due / t * 100}%" title="Fällig: {s.due}"></div>{/if}
                    {#if s.new > 0}<div class="srs-seg srs-new" style="width:{s.new / t * 100}%" title="Neu: {s.new}"></div>{/if}
                  </div>
                {/if}
                <div class="srs-legend">
                  <span class="srs-item"><span class="srs-dot srs-mastered"></span> Gemeistert <strong>{s.mastered}</strong></span>
                  <span class="srs-item"><span class="srs-dot srs-solid"></span> Gefestigt <strong>{s.solid}</strong></span>
                  <span class="srs-item"><span class="srs-dot srs-learning"></span> Lernphase <strong>{s.learning}</strong></span>
                  <span class="srs-item"><span class="srs-dot srs-due"></span> Fällig <strong>{s.due}</strong></span>
                  <span class="srs-item"><span class="srs-dot srs-new"></span> Neu <strong>{s.new}</strong></span>
                </div>
              </div>
            {/if}
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-box-open"></i>
            <p>Paket ist noch leer. Oeffne die Werkstatt um Karten zu erstellen oder zu importieren.</p>
          </div>
        {/if}
      </div>

    <!-- WERKSTATT -->
    {:else if tab === 'workshop'}
      <WorkshopTab {pkg} />

    <!-- KARTEN (nur Browse) -->
    {:else if tab === 'cards'}
      <CardsTab {pkg} {searchQ} />

    <!-- MATERIAL -->
    {:else if tab === 'material'}
      <MaterialTab {pkg} />
    {/if}

  </div>
</div>

<style>
/* ── Wrapper ──────────────────────────────────────────────────────────────── */
.pd-wrap {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--bg0);
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.pd-header {
  background: var(--bg1);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}
.back-btn {
  font-size: 12px;
  color: var(--text2);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  transition: color .15s;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}
.back-btn:hover { color: var(--accent); }
.pd-title-row { display: flex; align-items: center; gap: 12px; }
.pd-icon {
  width: 42px;
  height: 42px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 2px 10px rgba(0,0,0,.2);
}
.pd-name { font-size: 18px; font-weight: 700; color: var(--text0); }
.pd-desc { font-size: 12px; color: var(--text2); margin-top: 2px; }

/* ── Freigabe ────────────────────────────────────────────────────────────── */
.share-panel { background:var(--bg1);border-radius:4px;padding:14px;margin-top:12px;box-shadow:0 1px 3px var(--shadow); }
.share-hd { font-size:12px;font-weight:700;color:var(--text2);margin-bottom:10px;text-transform:uppercase;letter-spacing:.04em; }
.share-form { display:flex;gap:8px;align-items:center;flex-wrap:wrap; }
.share-list { margin-top:12px;display:flex;flex-direction:column;gap:4px; }
.share-user { display:flex;align-items:center;gap:8px;font-size:12px;padding:6px 0; }
.share-email { flex:1;color:var(--text1); }
.share-role { font-size:10px;color:var(--text3);background:var(--bg2);padding:2px 6px;border-radius:2px; }

/* ── Stats ───────────────────────────────────────────────────────────────── */
.pd-stats {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 4px;
}
.pds {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 12px;
  font-size: 10px;
  color: var(--text2);
  border-right: 1px solid var(--border);
}
.pds:last-of-type { border-right: none; margin-right: 10px; }
.pds i { font-size: 12px; color: var(--text3); margin-bottom: 3px; }
.pds-val { font-size: 17px; font-weight: 700; color: var(--text0); font-family: 'JetBrains Mono', monospace; line-height: 1; }
.pds-lbl { font-size: 9px; margin-top: 2px; letter-spacing: .04em; text-transform: uppercase; }
.pds.ok .pds-val, .pds.ok i { color: var(--ok); }
.pds.warn .pds-val, .pds.warn i { color: var(--warn); }
.pds.accent .pds-val, .pds.accent i { color: var(--accent); }
.pds.clickable { cursor: pointer; }

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
.pd-tabs {
  display: flex;
  background: var(--bg1);
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
  flex-shrink: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.pd-tabs::-webkit-scrollbar { display: none; }
.pd-tab {
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
  border: none;
  background: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color .15s;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  white-space: nowrap;
}
.pd-tab i { font-size: 12px; }
.pd-tab:hover { color: var(--text0); }
.pd-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-badge {
  font-size: 10px;
  font-weight: 700;
  background: var(--warn);
  color: #fff;
  border-radius: 4px;
  padding: 1px 5px;
}

/* ── Body ─────────────────────────────────────────────────────────────────── */
.pd-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.tab-page {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

/* ── Übersicht ──────────────────────────────────────────────────────────── */
.overview-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.cat-row { display: grid; grid-template-columns: 28px 1fr minmax(80px,140px) 32px; align-items: center; gap: 10px; padding: 7px 6px; border-radius: 4px; transition: background .12s; }
.cat-row:hover { background: var(--bg2); }
.cat-icon-box { width: 28px; height: 28px; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.cat-icon-box i { font-size: 12px; }
.cat-name { font-size: 12px; font-weight: 600; color: var(--text1); }
.cat-n { font-size: 11px; font-weight: 600; color: var(--text2); min-width: 22px; text-align: right; font-family: 'JetBrains Mono', monospace; }

/* ── SRS-Stapel ──────────────────────────────────────────────────────────── */
.srs-bar { display:flex;height:10px;border-radius:3px;overflow:hidden;margin-bottom:12px;gap:1px; }
.srs-seg { min-width:3px;transition:width .3s; }
.srs-mastered { background:#50a868; }
.srs-solid { background:#4090d0; }
.srs-learning { background:#d0a040; }
.srs-due { background:#d06050; }
.srs-new { background:var(--bg3); }
.srs-legend { display:flex;flex-wrap:wrap;gap:10px;font-size:10px;color:var(--text2); }
.srs-item { display:flex;align-items:center;gap:4px; }
.srs-item strong { color:var(--text0);font-family:'JetBrains Mono',monospace; }
.srs-dot { width:8px;height:8px;border-radius:2px; }
.srs-dot.srs-mastered { background:#50a868; }
.srs-dot.srs-solid { background:#4090d0; }
.srs-dot.srs-learning { background:#d0a040; }
.srs-dot.srs-due { background:#d06050; }
.srs-dot.srs-new { background:var(--bg3); }

/* ── Empty State ─────────────────────────────────────────────────────────── */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 20px; gap: 8px; }
.empty-state i { font-size: 36px; color: var(--text3); opacity: .3; }
.empty-state p { font-size: 13px; color: var(--text3); }
</style>
