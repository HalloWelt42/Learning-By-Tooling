<script>
  /**
   * Packages.svelte -- Paketverwaltung (Desktop-Layout)
   * Zwei-Panel-Ansicht: links Katalog/Grid, rechts Detail-Panel
   */
  import { packages, globalStats, loadGlobal, showToast } from '../../stores/index.js'
  import { onMount } from 'svelte'
  import { apiGet, apiPost, apiDelete, apiUpload } from '../../utils/api.js'
  import { navigate } from '../../utils/router.js'

  let bundles       = $state([])
  let installing    = $state(null)
  let uninstalling  = $state(null)
  let confirmPkg    = $state(null)
  let selectedId    = $state(null)
  let viewMode      = $state('grid') // 'grid' | 'list'
  let showCreate    = $state(false)
  let zipFile       = $state(null)
  let zipInstalling = $state(false)
  let zipResult     = $state(null)
  let showZip       = $state(false)
  let deletingBundle = $state(false)

  const CAT_NAMES = {
    GB:'Grundlagen', TH:'Theorie', PX:'Praxis', VF:'Verfahren',
    PR:'Prüfung', VT:'Vertiefung', AL:'Allgemein',
    AK:'Akteure', GS:'Geschäftsprozesse', AP:'API', HA:'Hash',
    OA:'OAuth2', TC:'Test Cases', MO:'Mock', KA:'Kafka',
    FE:'Fehler', DB:'Datenmodell',
  }
  const CAT_COLORS = {
    GB:'#5b8aff', TH:'#9b7ddf', PX:'#3dd68c', VF:'#ff9f43',
    PR:'#ff6b6b', VT:'#40e0d0', AL:'#6b7280',
    AK:'#9b7ddf', GS:'#3dd68c', AP:'#ff6b6b', HA:'#ffb347',
    OA:'#ff69b4', TC:'#40e0d0', MO:'#c084fc', KA:'#fde68a',
    FE:'#fb7185', DB:'#93c5fd',
  }

  const ICONS = [
    'fa-graduation-cap','fa-book','fa-laptop-code','fa-flask','fa-database',
    'fa-network-wired','fa-code','fa-file-code','fa-cube','fa-layer-group',
    'fa-gear','fa-shield-halved','fa-truck','fa-briefcase','fa-chart-bar',
  ]
  // Katalog-Farben: MD3 400er, OHNE semantische Farben (kein Rot/Grün/Orange/Blau/Blautöne)
  const MD_COLORS = [
    { hex:'#EC407A', name:'Pink' },
    { hex:'#AB47BC', name:'Purple' },
    { hex:'#7E57C2', name:'Deep Purple' },
    { hex:'#5C6BC0', name:'Indigo' },
    { hex:'#26A69A', name:'Teal' },
    { hex:'#D4E157', name:'Lime' },
    { hex:'#FFCA28', name:'Amber' },
    { hex:'#FF7043', name:'Deep Orange' },
    { hex:'#8D6E63', name:'Brown' },
  ]

  let form = $state({ name:'', description:'', color:'#5C6BC0', icon:'fa-graduation-cap' })

  // Alle Einträge vereinheitlicht: installierte Pakete + verfügbare Bundles
  let allItems = $derived((() => {
    const items = []
    // Installierte Pakete
    for (const pkg of ($packages || [])) {
      const bundle = bundles.find(b => b.name === pkg.name)
      items.push({
        type: 'installed',
        id: `pkg-${pkg.id}`,
        pkgId: pkg.id,
        bundleId: bundle?.id || null,
        name: pkg.name,
        description: pkg.description,
        icon: pkg.icon,
        color: pkg.color,
        cardCount: pkg.card_count,
        docCount: pkg.doc_count,
        draftCount: pkg.draft_count || 0,
        categories: bundle?.categories || {},
        version: bundle?.version || null,
      })
    }
    // Nicht-installierte Bundles
    const installedNames = new Set(($packages || []).map(p => p.name))
    for (const b of bundles) {
      if (!installedNames.has(b.name)) {
        items.push({
          type: 'available',
          id: `bundle-${b.id}`,
          bundleId: b.id,
          pkgId: null,
          name: b.name,
          description: b.description,
          icon: b.icon,
          color: b.color,
          cardCount: b.card_count,
          docCount: 0,
          draftCount: 0,
          categories: b.categories || {},
          version: b.version,
        })
      }
    }
    return items
  })())

  let selected = $derived(allItems.find(i => i.id === selectedId) || null)

  onMount(loadBundles)

  async function loadBundles() {
    bundles = await apiGet('/api/bundles').catch(() => [])
  }

  async function installBundle(bundleId) {
    if (installing) return
    installing = bundleId
    try {
      const r = await apiPost(`/api/bundles/${bundleId}/install`, {})
      showToast(`${r.name}: ${r.created} Karten installiert`, 'success')
      await loadGlobal()
      await loadBundles()
      // Auswahl auf das neue installierte Paket setzen
      setTimeout(() => {
        const pkg = ($packages || []).find(p => p.name === r.name)
        if (pkg) selectedId = `pkg-${pkg.id}`
      }, 100)
    } catch(e) { showToast(e.message, 'error') }
    installing = null
  }

  async function uninstallPkg(item) {
    if (uninstalling) return
    confirmPkg = null
    uninstalling = item.pkgId
    try {
      const r = await apiDelete(`/api/packages/${item.pkgId}/uninstall`)
      showToast(`${r.package_name} entfernt -- ${r.cards_deleted} Karten gelöscht`, 'success')
      selectedId = null
      await loadGlobal()
      await loadBundles()
    } catch(e) { showToast(e.message, 'error') }
    uninstalling = null
  }

  async function installZip() {
    if (!zipFile || zipInstalling) return
    zipInstalling = true
    zipResult = null
    try {
      const fd = new FormData()
      fd.append('file', zipFile)
      zipResult = await apiUpload('/api/import/zip', fd)
      showToast(`${zipResult.created} Karten importiert`, 'success')
      await loadGlobal()
      await loadBundles()
      zipFile = null
    } catch(e) { showToast(e.message, 'error') }
    zipInstalling = false
  }

  async function create() {
    if (!form.name.trim()) { showToast('Name ist Pflicht', 'error'); return }
    try {
      await apiPost('/api/packages', form)
      await loadGlobal()
      showToast(`Paket "${form.name}" erstellt`, 'success')
      showCreate = false
      form = { name:'', description:'', color:'#5C6BC0', icon:'fa-graduation-cap' }
    } catch(e) { showToast(e.message, 'error') }
  }

  async function exportPkg(pkgId) {
    try {
      const token = localStorage.getItem('lbt-token')
      const res = await fetch(`/api/packages/${pkgId}/export`, {
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
    } catch (e) { showToast(e.message, 'error') }
  }

  function pct(c,t) { return t > 0 ? Math.round(c/t*100) : 0 }

  function selectItem(item) {
    selectedId = selectedId === item.id ? null : item.id
  }
</script>

<div class="pk-page">

  <!-- Toolbar -->
  <div class="pk-toolbar">
    <div class="pk-toolbar-left">
      <h1 class="pk-title">
        <i class="fa-solid fa-box-archive"></i> Lernpakete
      </h1>
      {#if $globalStats?.total_cards > 0}
        <div class="pk-stats-bar">
          <span class="pk-stat">
            <strong>{$globalStats.total_packages}</strong> Pakete
          </span>
          <span class="pk-stat-sep"></span>
          <span class="pk-stat">
            <strong>{$globalStats.total_cards}</strong> Karten
          </span>
          <span class="pk-stat-sep"></span>
          <span class="pk-stat ok">
            <strong>{pct($globalStats.total_correct, $globalStats.total_reviews)}%</strong> Treffer
          </span>
          {#if $globalStats.due_today > 0}
            <span class="pk-stat-sep"></span>
            <span class="pk-stat warn">
              <strong>{$globalStats.due_today}</strong> fällig
            </span>
          {/if}
        </div>
      {/if}
    </div>
    <div class="pk-toolbar-right">
      <div class="pk-view-toggle">
        <button class="pk-vt" class:active={viewMode==='grid'} title="Raster" onclick={() => viewMode='grid'}>
          <i class="fa-solid fa-table-cells"></i>
        </button>
        <button class="pk-vt" class:active={viewMode==='list'} title="Liste" onclick={() => viewMode='list'}>
          <i class="fa-solid fa-list"></i>
        </button>
      </div>
      <button class="btn btn-ghost btn-sm" onclick={() => { showZip = !showZip; showCreate = false }}>
        <i class="fa-solid fa-file-zipper"></i> ZIP
      </button>
      <button class="btn btn-primary btn-sm" onclick={() => { showCreate = !showCreate; showZip = false }}>
        <i class="fa-solid fa-plus"></i> Neu
      </button>
    </div>
  </div>

  <!-- Eingeklappte Bereiche: ZIP oder Neues Paket -->
  {#if showZip}
    <div class="pk-panel">
      <div class="pk-panel-head">
        <span>Paket aus ZIP installieren</span>
        <button class="ib" title="Schließen" onclick={() => showZip=false}>
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <label class="zip-drop" class:has-file={!!zipFile} class:loading={zipInstalling}>
        <input type="file" accept=".zip"
          onchange={e => { zipFile = e.currentTarget.files[0]||null; zipResult = null }}>
        {#if zipInstalling}
          <i class="fa-solid fa-spinner fa-spin"></i>
          <span>Importiere...</span>
        {:else if zipFile}
          <i class="fa-solid fa-file-zipper"></i>
          <span class="zip-fname">{zipFile.name}</span>
          <span class="zip-fsize">{zipFile.size > 1048576 ? (zipFile.size/1048576).toFixed(1)+'MB' : Math.round(zipFile.size/1024)+'KB'}</span>
        {:else}
          <i class="fa-solid fa-cloud-arrow-up"></i>
          <span>ZIP hier ablegen oder klicken</span>
        {/if}
      </label>
      {#if zipResult}
        <div class="zip-result">
          <i class="fa-solid fa-circle-check"></i>
          <span><strong>{zipResult.created}</strong> Karten importiert</span>
          {#if zipResult.package_id}
            <button class="btn btn-ghost btn-sm" onclick={() => navigate(`/packages/${zipResult.package_id}`)}>
              Paket öffnen <i class="fa-solid fa-arrow-right"></i>
            </button>
          {/if}
        </div>
      {/if}
      {#if zipFile && !zipInstalling}
        <button class="btn btn-primary btn-sm" onclick={installZip}>
          <i class="fa-solid fa-download"></i> Installieren
        </button>
      {/if}
    </div>
  {/if}

  {#if showCreate}
    <div class="pk-panel">
      <div class="pk-panel-head">
        <span>Neues Paket anlegen</span>
        <button class="ib" title="Schließen" onclick={() => showCreate=false}>
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div class="cf-body">
        <div class="cf-left">
          <label>
            <span>Name</span>
            <input type="text" bind:value={form.name} placeholder="z.B. Grundkurs Python" />
          </label>
          <label>
            <span>Beschreibung</span>
            <textarea bind:value={form.description} rows="2" placeholder="Worum geht es?"></textarea>
          </label>
        </div>
        <div class="cf-right">
          <div class="section-label">Icon</div>
          <div class="icon-grid">
            {#each ICONS as ic}
              <button class="icon-opt" class:active={form.icon === ic} style="--c:{form.color}" title={ic}
                onclick={() => form.icon = ic}>
                <i class="fa-solid {ic}"></i>
              </button>
            {/each}
          </div>
          <div class="section-label" style="margin-top:10px">Farbe</div>
          <div class="color-grid">
            {#each MD_COLORS as col}
              <button class="color-opt" class:active={form.color === col.hex} style="background:{col.hex}"
                title={col.name} onclick={() => form.color = col.hex}></button>
            {/each}
          </div>
        </div>
      </div>
      <div class="cf-footer">
        <button class="btn btn-ghost btn-sm" onclick={() => showCreate=false}>Abbrechen</button>
        <button class="btn btn-primary btn-sm" onclick={create}>
          <i class="fa-solid fa-plus"></i> Anlegen
        </button>
      </div>
    </div>
  {/if}

  <!-- Hauptbereich: 2-Panel -->
  <div class="pk-body">

    <!-- Links: Paket-Grid/Liste -->
    <div class="pk-catalog" class:has-detail={!!selected}>

      {#if allItems.length === 0}
        <div class="pk-empty">
          <i class="fa-solid fa-box-open"></i>
          <p>Keine Pakete vorhanden. Lege ein neues an oder installiere ein Bundle.</p>
        </div>
      {:else}
        <div class="pk-items" class:list-mode={viewMode==='list'}>
          {#each allItems as item (item.id)}
            <button
              class="pk-tile"
              class:active={selectedId === item.id}
              class:is-available={item.type === 'available'}
              style="--c:{item.color}"
              onclick={() => selectItem(item)}
            >
              <div class="pk-tile-icon" style="background:{item.color}">
                <i class="fa-solid {item.icon}"></i>
              </div>
              <div class="pk-tile-body">
                <span class="pk-tile-name">{item.name}</span>
                <span class="pk-tile-meta">
                  {item.cardCount} Karten
                  {#if item.type === 'available'}
                    -- verfügbar
                  {/if}
                </span>
              </div>
              {#if item.type === 'available'}
                <span class="pk-tile-badge avail">NEU</span>
              {:else if item.draftCount > 0}
                <span class="pk-tile-badge draft">{item.draftCount}</span>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Rechts: Detail-Panel -->
    {#if selected}
      <div class="pk-detail">
        <div class="pk-detail-head">
          <div class="pk-detail-icon" style="background:{selected.color}">
            <i class="fa-solid {selected.icon}"></i>
          </div>
          <div class="pk-detail-title">
            <h2>{selected.name}</h2>
            {#if selected.version}
              <span class="pk-detail-ver">v{selected.version}</span>
            {/if}
          </div>
          <button class="ib" title="Schließen" onclick={() => selectedId=null}>
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        {#if selected.description}
          <p class="pk-detail-desc">{selected.description}</p>
        {/if}

        <div class="pk-detail-stats">
          <div class="pk-ds">
            <i class="fa-solid fa-layer-group"></i>
            <strong>{selected.cardCount}</strong>
            <span>Karten</span>
          </div>
          {#if selected.type === 'installed'}
            <div class="pk-ds">
              <i class="fa-solid fa-file-lines"></i>
              <strong>{selected.docCount}</strong>
              <span>Dokumente</span>
            </div>
          {/if}
        </div>

        {#if Object.keys(selected.categories).length > 0}
          <div class="pk-detail-cats">
            <div class="section-label">Kategorien</div>
            <div class="pk-cat-list">
              {#each Object.entries(selected.categories) as [code, count]}
                <span class="pk-cat" style="background:{CAT_COLORS[code] || '#6b7280'}20;color:{CAT_COLORS[code] || '#6b7280'}">
                  {CAT_NAMES[code] || code} <span class="pk-cat-n">{count}</span>
                </span>
              {/each}
            </div>
          </div>
        {/if}

        <div class="pk-detail-actions">
          {#if selected.type === 'installed'}
            <button class="btn btn-primary pk-act-btn" onclick={() => navigate(`/packages/${selected.pkgId}`)}>
              <i class="fa-solid fa-arrow-right"></i> Paket öffnen
            </button>
            <button class="btn btn-ghost pk-act-btn" onclick={() => navigate(`/learn/${selected.pkgId}`)}>
              <i class="fa-solid fa-play"></i> Lernen
            </button>
            <button class="btn btn-ghost pk-act-btn" onclick={() => exportPkg(selected.pkgId)}>
              <i class="fa-solid fa-file-export"></i> Export
            </button>
            <button class="btn btn-ghost btn-danger pk-act-btn" disabled={deletingBundle} onclick={() => confirmPkg = selected}>
              <i class="fa-solid fa-trash-can"></i> Löschen
            </button>
          {:else}
            <button
              class="btn btn-primary pk-act-btn"
              disabled={installing === selected.bundleId}
              onclick={() => installBundle(selected.bundleId)}
            >
              {#if installing === selected.bundleId}
                <i class="fa-solid fa-spinner fa-spin"></i> Installiere...
              {:else}
                <i class="fa-solid fa-download"></i> Installieren
              {/if}
            </button>
          {/if}
        </div>
      </div>
    {/if}

  </div>

  <!-- Bestätigungsdialog -->
  {#if confirmPkg}
    <div class="confirm-overlay" role="dialog" aria-modal="true"
      onkeydown={e => e.key==='Escape' && (confirmPkg=null)}
      onclick={() => confirmPkg = null}>
      <div class="confirm-box" onclick={e => e.stopPropagation()} role="document">
        <div class="confirm-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
        <div class="confirm-title">Paket löschen?</div>
        <div class="confirm-msg">
          <strong>{confirmPkg.name}</strong> wird vollständig entfernt:
          alle Karten, Dokumente, Lernfortschritt und Lexikon-Einträge.
          Diese Aktion kann nicht rückgängig gemacht werden.
        </div>
        <div class="confirm-btns">
          <button class="btn btn-ghost" onclick={() => confirmPkg = null}>Abbrechen</button>
          <button
            class="btn btn-err"
            disabled={uninstalling === confirmPkg?.pkgId}
            onclick={() => uninstallPkg(confirmPkg)}
          >
            {#if uninstalling === confirmPkg?.pkgId}
              <i class="fa-solid fa-spinner fa-spin"></i> Wird entfernt...
            {:else}
              <i class="fa-solid fa-trash"></i> Ja, löschen
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
/* ── Layout: volle Höhe, kein Seitenscrolling ─────────────────────────── */
.pk-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ── Toolbar ────────────────────────────────────────────────────────────── */
.pk-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  gap: 16px;
  flex-wrap: wrap;
}
.pk-toolbar-left { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.pk-toolbar-right { display: flex; align-items: center; gap: 8px; }
.pk-title {
  font-size: 18px;
  font-weight: 800;
  color: var(--text0);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.pk-title i { color: var(--accent); font-size: 16px; }
.pk-stats-bar {
  display: flex;
  align-items: center;
  gap: 0;
  font-size: 12px;
  color: var(--text2);
}
.pk-stat { display: flex; align-items: center; gap: 4px; padding: 0 10px; }
.pk-stat strong { font-weight: 700; color: var(--text0); font-family: 'JetBrains Mono', monospace; }
.pk-stat.ok strong { color: var(--ok); }
.pk-stat.warn strong { color: var(--warn); }
.pk-stat-sep { width: 1px; height: 16px; background: var(--border); }

.pk-view-toggle {
  display: flex;
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}
.pk-vt {
  width: 30px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: 11px; transition: all .12s;
}
.pk-vt:hover { color: var(--text1); background: var(--bg2); }
.pk-vt.active { color: var(--accent); background: var(--glow); }

/* ── Einklappbare Panels (ZIP, Neues Paket) ────────────────────────────── */
.pk-panel {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg1);
  max-width: 720px;
}
.pk-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--text0);
}
.ib {
  width: 28px; height: 28px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  color: var(--text2); font-size: 12px; transition: all .15s;
  background: none; border: none; cursor: pointer;
}
.ib:hover { background: var(--bg2); color: var(--text0); }

/* ZIP Upload */
.zip-drop {
  display: flex; align-items: center; gap: 10px;
  border: 1px dashed var(--border); border-radius: 4px;
  padding: 14px 16px; cursor: pointer; transition: all .2s;
  font-size: 13px; color: var(--text2);
}
.zip-drop:hover { border-color: var(--accent); background: var(--glow); }
.zip-drop.has-file { border-color: var(--accent); border-style: solid; }
.zip-drop.loading { cursor: wait; }
.zip-drop input { display: none; }
.zip-drop i { font-size: 18px; color: var(--text3); flex-shrink: 0; }
.zip-drop.has-file i { color: var(--accent); }
.zip-fname { font-weight: 600; color: var(--text0); }
.zip-fsize { font-size: 11px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.zip-result {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 4px; font-size: 13px;
  background: var(--glowok); border: 1px solid color-mix(in srgb, var(--ok) 35%, transparent);
}
.zip-result i { color: var(--ok); }

/* Neues Paket Form */
.cf-body { display: grid; grid-template-columns: 1fr 200px; gap: 16px; }
.cf-left { display: flex; flex-direction: column; gap: 10px; }
.cf-left label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 600; color: var(--text2); }
.cf-right {}
.icon-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 3px; }
.icon-opt {
  width: 30px; height: 30px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  border: none; font-size: 12px;
  color: var(--text2); cursor: pointer; background: var(--bg3); transition: all .15s;
}
.icon-opt:hover { background: var(--bg4); color: var(--c); }
.icon-opt.active { background: color-mix(in srgb, var(--c) 15%, transparent); color: var(--c); }
.color-grid { display: flex; flex-wrap: wrap; gap: 4px; }
.color-opt {
  width: 20px; height: 20px; border-radius: 50%; cursor: pointer;
  border: 2px solid transparent; transition: transform .15s;
}
.color-opt:hover { transform: scale(1.2); }
.color-opt.active { border-color: var(--text0); transform: scale(1.15); }
.cf-footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 10px; border-top: 1px solid var(--border); }

/* ── Hauptbereich: 2-Panel ─────────────────────────────────────────────── */
.pk-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.pk-catalog {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  min-width: 0;
}
.pk-catalog.has-detail {
  max-width: 50%;
}

.pk-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text3);
  font-size: 14px;
}
.pk-empty i { font-size: 40px; }

/* ── Tile Grid / Liste ─────────────────────────────────────────────────── */
.pk-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.pk-items.list-mode {
  grid-template-columns: 1fr;
  gap: 4px;
}

.pk-tile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: var(--bg1);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all .15s;
  text-align: left;
  font-family: inherit;
  width: 100%;
  color: inherit;
  box-shadow: 0 1px 3px var(--shadow);
}
.pk-tile:hover {
  background: var(--bg2);
}
.pk-tile.active {
  background: color-mix(in srgb, var(--c) 8%, var(--bg1));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 40%, transparent);
}
.pk-tile.is-available {
  opacity: .7;
  box-shadow: none;
  border: 1px dashed var(--border);
}
.pk-tile.is-available:hover { opacity: 1; }
.pk-tile.is-available.active { opacity: 1; }

.pk-tile-icon {
  width: 36px; height: 36px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 15px; flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,.2);
}
.pk-tile-body { flex: 1; min-width: 0; }
.pk-tile-name {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--text0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pk-tile-meta {
  display: block;
  font-size: 11px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
}
.pk-tile-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.pk-tile-badge.avail {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
}
.pk-tile-badge.draft {
  background: color-mix(in srgb, var(--warn) 15%, transparent);
  color: var(--warn);
}

/* ── Detail-Panel (rechts) ─────────────────────────────────────────────── */
.pk-detail {
  width: 380px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  background: var(--bg0);
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pk-detail-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.pk-detail-icon {
  width: 48px; height: 48px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 20px; flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
}
.pk-detail-title { flex: 1; min-width: 0; }
.pk-detail-title h2 {
  font-size: 18px;
  font-weight: 800;
  color: var(--text0);
  margin: 0;
  line-height: 1.3;
}
.pk-detail-ver {
  font-size: 11px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
}
.pk-detail-desc {
  font-size: 13px;
  color: var(--text2);
  line-height: 1.6;
  margin: 0;
}
.pk-detail-stats {
  display: flex;
  gap: 20px;
  padding: 12px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.pk-ds {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text2);
}
.pk-ds i { color: var(--text3); font-size: 12px; }
.pk-ds strong {
  font-weight: 700;
  color: var(--text0);
  font-family: 'JetBrains Mono', monospace;
}

.pk-detail-cats { display: flex; flex-direction: column; gap: 6px; }
.pk-cat-list { display: flex; flex-wrap: wrap; gap: 4px; }
.pk-cat {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 3px;
  font-family: 'JetBrains Mono', monospace;
}
.pk-cat-n { font-weight: 400; opacity: .7; }

.pk-detail-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.pk-act-btn { justify-content: center; }
.btn-danger { color: var(--err) !important; }
.btn-danger:hover { background: color-mix(in srgb, var(--err) 12%, transparent) !important; }

/* ── Confirm Dialog ────────────────────────────────────────────────────── */
.confirm-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; backdrop-filter: blur(3px);
}
.confirm-box {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 28px;
  max-width: 420px;
  width: 90%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 20px 60px rgba(0,0,0,.5);
}
.confirm-icon { font-size: 28px; text-align: center; color: var(--warn); }
.confirm-title { font-size: 18px; font-weight: 700; color: var(--text0); text-align: center; }
.confirm-msg { font-size: 13px; color: var(--text1); line-height: 1.6; text-align: center; }
.confirm-btns { display: flex; gap: 10px; justify-content: center; margin-top: 6px; }
.btn-err {
  background: var(--err); color: #fff; border: none;
  padding: 8px 18px; border-radius: 4px; font-size: 13px;
  font-weight: 600; cursor: pointer;
  display: flex; align-items: center; gap: 7px; transition: opacity .15s;
}
.btn-err:hover { opacity: .85; }
.btn-err:disabled { opacity: .5; cursor: wait; }

.section-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--text3);
  margin-bottom: 4px;
}
</style>
