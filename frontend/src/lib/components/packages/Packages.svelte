<script>
  /**
   * Packages.svelte -- Uebersicht aller Pakete (Themenwelten)
   * Startseite der App
   */
  import { packages, globalStats, currentView, activePackageId, loadGlobal, showToast } from '../../stores/index.js'
  import { onMount } from 'svelte'
  import { apiGet, apiPost, apiDelete, apiUpload } from '../../utils/api.js'
  import { navigate } from '../../utils/router.js'

  let showCreate = $state(false)
  let bundles      = $state([])
  let installing   = $state(null)
  let zipFile      = $state(null)
  let uninstalling = $state(null)  // pkg_id gerade in Deinstallation
  let confirmPkg   = $state(null)  // pkg_id für Bestätigungsdialog
  let zipInstalling= $state(false)
  let zipResult    = $state(null)

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

  onMount(loadBundles)

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
    } catch(e) {
      showToast(e.message, 'error')
    }
    zipInstalling = false
  }

  async function uninstallPkg(pkg) {
    if (uninstalling) return
    confirmPkg = null
    uninstalling = pkg.id
    try {
      const r = await apiDelete(`/api/packages/${pkg.id}/uninstall`)
      showToast(`${r.package_name} entfernt -- ${r.cards_deleted} Karten gelöscht`, 'success')
      await loadGlobal()
      await loadBundles()
    } catch(e) { showToast(e.message, 'error') }
    uninstalling = null
  }

  async function loadBundles() {
    bundles = await apiGet('/api/bundles').catch(() => [])
  }

  async function installBundle(b) {
    if (installing) return
    installing = b.id
    try {
      const r = await apiPost(`/api/bundles/${b.id}/install`, {})
      showToast(`${r.name}: ${r.created} Karten installiert`, 'success')
      await loadGlobal()
      await loadBundles()
    } catch(e) {
      showToast(e.message, 'error')
    }
    installing = null
  }

  async function uninstallBundle(b) {
    if (installing) return
    // Paket-ID finden
    const pkg = ($packages || []).find(p => p.name === b.name)
    if (!pkg) { showToast('Paket nicht gefunden', 'error'); return }
    installing = b.id
    try {
      await apiDelete(`/api/packages/${pkg.id}/uninstall`)
      showToast(`${b.name} deinstalliert`, 'success')
      await loadGlobal()
      await loadBundles()
    } catch(e) {
      showToast(e.message, 'error')
    }
    installing = null
  }
  let form = $state({ name:'', description:'', color:'#5b8aff', icon:'fa-graduation-cap' })

  const ICONS = [
    'fa-graduation-cap','fa-book','fa-laptop-code','fa-flask','fa-database',
    'fa-network-wired','fa-code','fa-file-code','fa-cube','fa-layer-group',
    'fa-gear','fa-shield-halved','fa-truck','fa-briefcase','fa-chart-bar',
  ]
  const MD_COLORS = [
    { hex:'#F44336', name:'Red'         },
    { hex:'#E91E63', name:'Pink'        },
    { hex:'#9C27B0', name:'Purple'      },
    { hex:'#673AB7', name:'Deep Purple' },
    { hex:'#3F51B5', name:'Indigo'      },
    { hex:'#2196F3', name:'Blue'        },
    { hex:'#03A9F4', name:'Light Blue'  },
    { hex:'#00BCD4', name:'Cyan'        },
    { hex:'#009688', name:'Teal'        },
    { hex:'#4CAF50', name:'Green'       },
    { hex:'#8BC34A', name:'Light Green' },
    { hex:'#CDDC39', name:'Lime'        },
    { hex:'#FFC107', name:'Amber'       },
    { hex:'#FF9800', name:'Orange'      },
    { hex:'#FF5722', name:'Deep Orange' },
    { hex:'#795548', name:'Brown'       },
    { hex:'#607D8B', name:'Blue Grey'   },
    { hex:'#9E9E9E', name:'Grey'        },
  ]

  async function create() {
    if (!form.name.trim()) { showToast('Name ist Pflicht', 'error'); return }
    try {
      await apiPost('/api/packages', form)
      await loadGlobal()
      showToast(`Paket "${form.name}" erstellt`, 'success')
      showCreate = false
      form = { name:'', description:'', color:'#2196F3', icon:'fa-graduation-cap' }
    } catch(e) {
      showToast(e.message, 'error')
    }
  }


  function open(pkg) {
    navigate(`/packages/${pkg.id}`)
  }

  async function exportPkg(pkgId) {
    try {
      const token = localStorage.getItem('lbt-token')
      const res = await fetch(`${BASE}/api/packages/${pkgId}/export`, {
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
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  function pct(c,t){ return t>0 ? Math.round(c/t*100) : 0 }
</script>

<div class="page">
  <div class="page-hd">
    <div>
      <h1 class="page-title">
        <i class="fa-solid fa-box-archive"></i> Lernpakete
      </h1>
      <p class="page-sub">
        Jedes Paket ist eine abgeschlossene Themenwelt mit eigenen Dokumenten und Karten
      </p>
    </div>
    <button class="btn btn-primary" onclick={() => showCreate = !showCreate}>
      <i class="fa-solid fa-plus"></i> Neues Paket
    </button>
  </div>

  <!-- Neues Paket Form -->
  {#if showCreate}
    <div class="create-form card-box">
      <div class="cf-header">
        <span style="font-size:14px;font-weight:700;color:var(--text0)">
          Neues Paket anlegen
        </span>
        <button class="ib" title="Schließen" onclick={() => showCreate=false}>
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <div class="cf-body">
        <div class="cf-left">
          <label>
            <span>Name</span>
            <input type="text" bind:value={form.name} placeholder="z.B. Grundkurs Python, API Dokumentation..." />
          </label>
          <label>
            <span>Beschreibung</span>
            <textarea bind:value={form.description} rows="2"
              placeholder="Worum geht es in diesem Paket?"></textarea>
          </label>
        </div>

        <div class="cf-right">
          <div class="section-label">Icon</div>
          <div class="icon-grid">
            {#each ICONS as ic}
              <button
                class="icon-opt"
                class:active={form.icon === ic}
                style="--c:{form.color}"
                title={ic}
                onclick={() => form.icon = ic}
              >
                <i class="fa-solid {ic}"></i>
              </button>
            {/each}
          </div>

          <div class="section-label" style="margin-top:14px">Farbe</div>
          <div class="color-grid">
            {#each MD_COLORS as col}
              <button
                class="color-opt"
                class:active={form.color === col.hex}
                style="background:{col.hex}"
                title="{col.name}"
                onclick={() => form.color = col.hex}
              ></button>
            {/each}
          </div>
        </div>
      </div>

      <!-- Vorschau -->
      <div class="pkg-preview" style="--c:{form.color}">
        <div class="pkg-preview-icon" style="background:{form.color}">
          <i class="fa-solid {form.icon}"></i>
        </div>
        <div>
          <div style="font-weight:700;color:var(--text0)">{form.name || 'Paketname'}</div>
          <div style="font-size:12px;color:var(--text2)">{form.description || 'Keine Beschreibung'}</div>
        </div>
      </div>

      <div class="cf-footer">
        <button class="btn btn-ghost" onclick={() => showCreate=false}>Abbrechen</button>
        <button class="btn btn-primary" onclick={create}>
          <i class="fa-solid fa-plus"></i> Paket anlegen
        </button>
      </div>
    </div>
  {/if}

  <!-- Globale Übersicht (Kopfbereich) -->
  {#if $globalStats && $globalStats.total_cards > 0}
    <div class="global-stats">
      <div class="gs-item">
        <i class="fa-solid fa-box-archive"></i>
        <strong>{$globalStats.total_packages}</strong>
        <span>Lernpakete</span>
      </div>
      <div class="gs-sep"></div>
      <div class="gs-item">
        <i class="fa-solid fa-layer-group"></i>
        <strong>{$globalStats.total_cards}</strong>
        <span>Karten gesamt</span>
      </div>
      <div class="gs-sep"></div>
      <div class="gs-item ok">
        <i class="fa-solid fa-bullseye"></i>
        <strong>{pct($globalStats.total_correct, $globalStats.total_reviews)}%</strong>
        <span>Trefferquote</span>
      </div>
      {#if $globalStats.due_today > 0}
        <div class="gs-sep"></div>
        <div class="gs-item warn">
          <i class="fa-solid fa-brain"></i>
          <strong>{$globalStats.due_today}</strong>
          <span>Fällig heute</span>
        </div>
      {/if}
      {#if $globalStats.pending_drafts > 0}
        <div class="gs-sep"></div>
        <div class="gs-item accent">
          <i class="fa-solid fa-file-circle-exclamation"></i>
          <strong>{$globalStats.pending_drafts}</strong>
          <span>Entwürfe offen</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- ── ZIP-Paket hochladen ──────────────────────────────────────────────── -->
  <div class="zip-section">
    <div class="section-label">
      <i class="fa-solid fa-file-zipper" style="color:var(--accent);margin-right:6px"></i>
      Paket aus ZIP installieren
    </div>
    <label class="zip-drop" class:has-file={!!zipFile} class:loading={zipInstalling}>
      <input type="file" accept=".zip"
        onchange={e => { zipFile = e.currentTarget.files[0]||null; zipResult = null }}>
      {#if zipInstalling}
        <i class="fa-solid fa-spinner fa-spin" style="font-size:28px;color:var(--accent)"></i>
        <span class="zip-hint">Importiere Karten...</span>
      {:else if zipFile}
        <i class="fa-solid fa-file-zipper" style="font-size:28px;color:var(--accent)"></i>
        <span class="zip-fname">{zipFile.name}</span>
        <span class="zip-fsize">{zipFile.size > 1048576 ? (zipFile.size/1048576).toFixed(1)+'MB' : Math.round(zipFile.size/1024)+'KB'}</span>
      {:else}
        <i class="fa-solid fa-cloud-arrow-up" style="font-size:32px;color:var(--text3)"></i>
        <span class="zip-hint">Lernpaket-ZIP hier ablegen</span>
        <span class="zip-hint2">oder klicken zum Auswählen</span>
      {/if}
    </label>

    {#if zipResult}
      <div class="zip-result">
        <i class="fa-solid fa-circle-check" style="color:var(--ok)"></i>
        <span><strong>{zipResult.created}</strong> Karten importiert</span>
        {#if zipResult.skipped > 0}
          <span style="color:var(--text2)">{zipResult.skipped} übersprungen</span>
        {/if}
        {#if zipResult.package_id}
          <button class="btn btn-ghost btn-sm" onclick={() => navigate(`/packages/${zipResult.package_id}`)}>
            <i class="fa-solid fa-arrow-right"></i> Paket öffnen
          </button>
        {/if}
      </div>
    {/if}

    {#if zipFile && !zipInstalling}
      <button class="btn btn-primary" onclick={installZip}>
        <i class="fa-solid fa-download"></i> Installieren
      </button>
    {/if}
  </div>

  <!-- ── Verfügbare Lernpakete ────────────────────────────────────────────── -->
  {#if bundles.length > 0}
    <div class="bundles-section">
      <div class="section-label">
        <i class="fa-solid fa-box-open" style="color:var(--accent);margin-right:6px"></i>
        Lernpakete installieren
      </div>
      <div class="bundles-grid">
        {#each bundles as b (b.id)}
          <div class="bundle-card" style="--c:{b.color}">
            <div class="bc-head">
              <div class="bc-icon" style="background:{b.color}">
                <i class="fa-solid {b.icon}"></i>
              </div>
              <div class="bc-badge-wrap">
                {#if b.installed}
                  <span class="bc-badge installed">
                    <i class="fa-solid fa-circle-check"></i> Installiert
                  </span>
                {:else}
                  <span class="bc-badge available">Verfügbar</span>
                {/if}
              </div>
            </div>
            <div class="bc-name">{b.name}</div>
            <div class="bc-desc">{b.description}</div>
            <div class="bc-meta">
              <span><i class="fa-solid fa-layer-group"></i> {b.card_count} Karten</span>
              <span><i class="fa-solid fa-tag"></i> v{b.version}</span>
            </div>
            <div class="bc-cats">
              {#each Object.entries(b.categories || {}) as [code, count]}
                <span class="bc-cat" style="background:{CAT_COLORS[code] || '#6b7280'}20;color:{CAT_COLORS[code] || '#6b7280'}" title="{CAT_NAMES[code] || code}: {count} Karten">{code} <span class="bc-cat-n">{count}</span></span>
              {/each}
            </div>
            {#if b.installed}
              <button
                class="btn btn-ghost bc-btn"
                onclick={() => uninstallBundle(b)}
                disabled={installing === b.id}
              >
                {#if installing === b.id}
                  <i class="fa-solid fa-spinner fa-spin"></i> Entferne...
                {:else}
                  <i class="fa-solid fa-trash-can"></i> Deinstallieren
                {/if}
              </button>
            {:else}
              <button
                class="btn btn-primary bc-btn"
                onclick={() => installBundle(b)}
                disabled={installing === b.id}
              >
                {#if installing === b.id}
                  <i class="fa-solid fa-spinner fa-spin"></i> Installiere...
                {:else}
                  <i class="fa-solid fa-download"></i> Installieren
                {/if}
              </button>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  {/if}


  <!-- Pakete Grid -->
  {#if ($packages || []).length === 0}
    <div class="empty-state">
      <i class="fa-solid fa-box-open"></i>
      <p>Noch keine Pakete. Lege dein erstes Themenpaket an.</p>
    </div>
  {:else}
    <div class="pkg-grid">
      {#each ($packages || []) as pkg (pkg.id)}
        <div
          class="pkg-card"
          style="--c:{pkg.color}"
          onclick={() => open(pkg)}
          role="button"
          tabindex="0"
          onkeydown={e => e.key==='Enter' && open(pkg)}
        >
          <div class="pk-icon" style="background:{pkg.color}">
            <i class="fa-solid {pkg.icon}"></i>
          </div>
          <div class="pk-name">{pkg.name}</div>
          {#if pkg.description}
            <div class="pk-desc">{pkg.description}</div>
          {/if}

          <div class="pk-bottom">
            <div class="pk-stats">
              <span><i class="fa-solid fa-layer-group"></i> {pkg.card_count} Karten</span>
              <span><i class="fa-solid fa-file-lines"></i> {pkg.doc_count} Dokumente</span>
            </div>
            <div class="pk-footer">
              <button class="btn btn-ghost btn-sm" onclick={e => { e.stopPropagation(); open(pkg) }}>
                <i class="fa-solid fa-arrow-right"></i> Öffnen
              </button>
              <button class="btn btn-ghost btn-sm" onclick={e => { e.stopPropagation(); exportPkg(pkg.id) }}>
                <i class="fa-solid fa-file-export"></i> Export
              </button>
              <button class="btn-icon" style="margin-left:auto" onclick={e => { e.stopPropagation(); confirmPkg = pkg }}>
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Bestätigungsdialog Uninstall -->
  {#if confirmPkg}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="confirm-overlay" onclick={() => confirmPkg = null}>
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div class="confirm-box" onclick={e => e.stopPropagation()}>
        <div class="confirm-icon"><i class="fa-solid fa-triangle-exclamation" style="color:var(--warn)"></i></div>
        <div class="confirm-title">Paket zurückziehen?</div>
        <div class="confirm-msg">
          <strong>{confirmPkg.name}</strong> wird vollständig entfernt:
          alle Karten, Dokumente, Lernfortschritt und Lexikon-Einträge.
          Diese Aktion kann nicht rückgängig gemacht werden.
        </div>
        <div class="confirm-btns">
          <button class="btn btn-ghost" onclick={() => confirmPkg = null}>Abbrechen</button>
          <button
            class="btn btn-err"
            disabled={uninstalling === confirmPkg?.id}
            onclick={() => uninstallPkg(confirmPkg)}
          >
            {#if uninstalling === confirmPkg?.id}
              <i class="fa-solid fa-spinner fa-spin"></i> Wird entfernt...
            {:else}
              <i class="fa-solid fa-trash"></i> Ja, zurückziehen
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}

</div>

<style>
.global-stats{
  display:flex;align-items:center;gap:0;
  background:var(--bg1);border:1px solid var(--border);
  border-radius: 4px;padding:14px 20px;margin-bottom:28px;
  flex-wrap:wrap;gap:0;
}
.gs-item{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text2);padding:4px 16px}
.gs-item :global(strong){font-size:18px;font-weight:700;color:var(--text0);font-family:'JetBrains Mono',monospace}
.gs-item :global(i){font-size:14px;color:var(--text3)}
.gs-item.ok :global(strong),.gs-item.ok :global(i){color:var(--ok)}
.gs-item.warn :global(strong),.gs-item.warn :global(i){color:var(--warn)}
.gs-item.accent :global(strong),.gs-item.accent :global(i){color:var(--accent)}
.gs-sep{width:1px;height:32px;background:var(--border);flex-shrink:0}

.create-form{max-width:720px;margin-bottom:28px}
.cf-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid var(--border)}
.ib{width:28px;height:28px;border-radius: 4px;display:flex;align-items:center;justify-content:center;color:var(--text2);font-size:12px;transition:all .15s}
.ib:hover{background:var(--bg2);color:var(--text0)}
.ib.sm{width:24px;height:24px;font-size:11px}
.ib.err:hover{background:var(--err);color:#fff}
.cf-body{display:grid;grid-template-columns:1fr 200px;gap:20px;margin-bottom:16px}
.cf-left{display:flex;flex-direction:column;gap:12px}
.cf-left label{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;color:var(--text2)}
.cf-right{}
.icon-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}
.icon-opt{width:32px;height:32px;border-radius: 4px;display:flex;align-items:center;justify-content:center;border:1px solid var(--border);font-size:13px;color:var(--text2);transition:all .15s;cursor:pointer;background:transparent}
.icon-opt:hover{border-color:var(--c);color:var(--c)}
.icon-opt.active{border-color:var(--c);background:color-mix(in srgb,var(--c) 15%,transparent);color:var(--c)}
.color-grid{display:flex;flex-wrap:wrap;gap:6px}
.color-opt{width:22px;height:22px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:transform .15s}
.color-opt:hover{transform:scale(1.2)}
.color-opt.active{border-color:var(--text0);transform:scale(1.15)}
.pkg-preview{
  display:flex;align-items:center;gap:14px;
  padding:12px 16px;background:var(--bg2);border-radius: 4px;
  border:1px solid color-mix(in srgb,var(--c) 35%,transparent);
  margin-bottom:16px;
}
.pkg-preview-icon{width:40px;height:40px;border-radius: 4px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;flex-shrink:0}
.cf-footer{display:flex;justify-content:flex-end;gap:10px;padding-top:14px;border-top:1px solid var(--border)}

/* Paket Grid */
.pkg-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
  gap:16px;
}
.pkg-card{
  background:var(--bg1);
  border:1px solid var(--border);
  border-radius: 4px;padding:20px;
  cursor:pointer;transition:all .2s;
  display:flex;flex-direction:column;gap:8px;
}
.pkg-card:hover{
  border-color:var(--c);
  box-shadow:0 6px 24px color-mix(in srgb,var(--c) 15%,transparent);
  transform:translateY(-1px);
}
.pk-bottom{margin-top:auto;display:flex;flex-direction:column;gap:8px;padding-top:10px;border-top:1px solid var(--border)}
.pk-icon{
  width:44px;height:44px;border-radius: 4px;
  display:flex;align-items:center;justify-content:center;
  color:#fff;font-size:18px;flex-shrink:0;
  box-shadow:0 2px 8px rgba(0,0,0,.2);
}
.pk-actions{display:flex;align-items:center;gap:6px}
.pk-badge{
  font-size:11px;font-weight:600;padding:3px 8px;border-radius: 4px;
  display:flex;align-items:center;gap:4px;
}
.pk-badge.warn{background:color-mix(in srgb,var(--warn) 15%,transparent);color:var(--warn);border:1px solid color-mix(in srgb,var(--warn) 35%,transparent)}
.pk-name{font-size:16px;font-weight:700;color:var(--text0);line-height:1.3}
.pk-desc{font-size:12px;color:var(--text2);line-height:1.5;flex:1}
.pk-stats{display:flex;gap:14px;font-size:11px;color:var(--text3);font-family:'JetBrains Mono',monospace}
.pk-stats i{margin-right:4px}
.pk-footer{margin-top:auto;padding-top:10px;display:flex;align-items:center;gap:6px}

/* ── Bundle Install ───────────────────────────────────────────────────────── */
.bundles-section {
  margin-bottom: 28px;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--border);
}
.bundles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.bundle-card {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.bc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.bc-icon {
  width: 42px;
  height: 42px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
}
.bc-badge-wrap {}
.bc-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.bc-badge.installed {
  background: color-mix(in srgb, var(--ok) 12%, transparent);
  color: var(--ok);
  border: 1px solid color-mix(in srgb, var(--ok) 35%, transparent);
}
.bc-badge.available {
  background: var(--glow);
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
}
.bc-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text0);
}
.bc-desc {
  font-size: 12px;
  color: var(--text2);
  line-height: 1.5;
}
.bc-meta {
  display: flex;
  gap: 14px;
  font-size: 11px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
  margin-top: auto;
}
.bc-meta i { margin-right: 4px; }
.bc-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.bc-cat {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
  letter-spacing: .04em;
  font-family: 'JetBrains Mono', monospace;
}
.bc-cat-n { color: var(--text2); font-weight: 500; }
.bc-btn {
  width: 100%;
  justify-content: center;
}


/* ── ZIP Upload ───────────────────────────────────────────────────────────── */
.zip-section {
  margin-bottom: 28px;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 520px;
}
.zip-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 2px dashed var(--border);
  border-radius: 4px;
  padding: 28px 20px;
  cursor: pointer;
  transition: all .2s;
  text-align: center;
  background: transparent;
}
.zip-drop:hover { border-color: var(--accent); background: var(--glow); }
.zip-drop.has-file { border-color: var(--accent); background: var(--glow); }
.zip-drop.loading  { border-color: var(--accent); background: var(--glow); cursor: wait; }
.zip-drop input    { display: none; }
.zip-fname  { font-size: 14px; font-weight: 600; color: var(--text0); }
.zip-fsize  { font-size: 11px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.zip-hint   { font-size: 13px; color: var(--text2); }
.zip-hint2  { font-size: 11px; color: var(--text3); }
.zip-result {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  background: var(--glowok);
  border: 1px solid color-mix(in srgb, var(--ok) 35%, transparent);
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text0);
  flex-wrap: wrap;
}


/* ── Confirm Dialog ───────────────────────────────────────────────────────── */
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
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
.confirm-icon { font-size: 28px; text-align: center; }
.confirm-title { font-size: 18px; font-weight: 700; color: var(--text0); text-align: center; }
.confirm-msg { font-size: 13px; color: var(--text1); line-height: 1.6; text-align: center; }
.confirm-btns { display: flex; gap: 10px; justify-content: center; margin-top: 6px; }
.btn-err {
  background: var(--err);
  color: #fff;
  border: none;
  padding: 8px 18px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  transition: opacity .15s;
}
.btn-err:hover { opacity: .85; }
.btn-err:disabled { opacity: .5; cursor: wait; }
/* pk-footer: siehe oben */

</style>
