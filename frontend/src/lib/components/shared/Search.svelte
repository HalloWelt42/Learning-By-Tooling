<script>
  /**
   * Search.svelte -- Globale Suche
   * - Echtzeit-Suche mit Debounce
   * - Filter: Paket, Kategorie, Schwierigkeit
   * - Nachladen (50er-Batches)
   * - Deeplinks: #/cards/{id}
   * - Snippet-Hervorhebung
   */
  import { onMount } from 'svelte'
  import { apiGet }  from '../../utils/api.js'
  import { packages, categories, activePackageId, currentView } from '../../stores/index.js'
  import { navigate, navToPackage } from '../../utils/router.js'

  // Props: initiale Query aus URL
  let { initQ = '', initPkg = null } = $props()

  // Suche
  let q          = $state(initQ)
  let filterPkg  = $state(initPkg ? parseInt(initPkg) : null)
  let filterCat  = $state(null)
  let filterDiff = $state(null)

  // Ergebnisse
  let results    = $state([])
  let total      = $state(0)
  let loading    = $state(false)
  let loadingMore= $state(false)
  let offset     = $state(0)
  const LIMIT    = 50

  // Debounce
  let debounceTimer = null

  $effect(() => {
    // Reaktiv auf Filteränderungen
    const _ = [q, filterPkg, filterCat, filterDiff]
    clearTimeout(debounceTimer)
    if (!q || q.length < 2) {
      results = []; total = 0; return
    }
    debounceTimer = setTimeout(runSearch, 280)
  })

  async function runSearch(reset = true) {
    if (!q || q.length < 2) return
    if (reset) { offset = 0; results = [] }
    loading = reset
    loadingMore = !reset
    try {
      const params = new URLSearchParams({ q, limit: LIMIT, offset })
      if (filterPkg)  params.set('pkg_id',     filterPkg)
      if (filterCat)  params.set('category',   filterCat)
      if (filterDiff) params.set('difficulty', filterDiff)
      const r = await apiGet(`/api/search?${params}`)
      total   = r.total || 0
      if (reset) results = r.items || []
      else       results = [...results, ...(r.items || [])]
      offset  = results.length
    } catch(e) {
      if (reset) { results = []; total = 0 }
    }
    loading = false
    loadingMore = false
  }

  function loadMore() {
    if (loadingMore || results.length >= total) return
    runSearch(false)
  }

  function openCard(item) {
    if (item.package_id) {
      activePackageId.set(item.package_id)
      currentView.set('package')
      navigate(`/packages/${item.package_id}?tab=cards&q=${encodeURIComponent(item.card_code || item.card_id || '')}`)
    }
  }

  function diffLabel(d) {
    return d === 1 ? 'Leicht' : d === 2 ? 'Mittel' : 'Schwer'
  }
  function diffColor(d) {
    return d === 1 ? 'var(--ok)' : d === 2 ? 'var(--warn)' : 'var(--err)'
  }

  // URL updaten wenn Query ändert
  $effect(() => {
    const hash = q ? `/search?q=${encodeURIComponent(q)}${filterPkg ? '&pkg='+filterPkg : ''}` : '/search'
    if (window.location.hash.replace(/^#/, '') !== hash) {
      history.replaceState(null, '', '#' + hash)
    }
  })
</script>

<div class="search-page">

  <!-- Such-Header -->
  <div class="search-header">
    <h1 class="page-title">
      <i class="fa-solid fa-magnifying-glass"></i> Suche
    </h1>
    <div class="search-input-wrap">
      <i class="fa-solid fa-magnifying-glass si-icon"></i>
      <input
        class="search-input"
        type="text"
        placeholder="Suchbegriff eingeben (min. 2 Zeichen)…"
        bind:value={q}
        autofocus
      />
      {#if loading}
        <i class="fa-solid fa-spinner fa-spin si-spin"></i>
      {:else if q.length > 0}
        <button class="si-clear" onclick={() => q = ''} aria-label="Löschen">
          <i class="fa-solid fa-xmark"></i>
        </button>
      {/if}
    </div>
  </div>

  <!-- Filter-Leiste -->
  <div class="search-filters">
    <!-- Paket -->
    <div class="sf-group">
      <label class="sf-label">Paket</label>
      <select class="sf-select" bind:value={filterPkg}>
        <option value={null}>Alle Pakete</option>
        {#each $packages || [] as pkg}
          <option value={pkg.id}>{pkg.name}</option>
        {/each}
      </select>
    </div>

    <!-- Kategorie -->
    <div class="sf-group">
      <label class="sf-label">Kategorie</label>
      <select class="sf-select" bind:value={filterCat}>
        <option value={null}>Alle Kategorien</option>
        {#each $categories || [] as cat}
          <option value={cat.code}>{cat.code} -- {cat.name}</option>
        {/each}
      </select>
    </div>

    <!-- Schwierigkeit -->
    <div class="sf-group">
      <label class="sf-label">Schwierigkeit</label>
      <select class="sf-select" bind:value={filterDiff}>
        <option value={null}>Alle</option>
        <option value={1}>Leicht</option>
        <option value={2}>Mittel</option>
        <option value={3}>Schwer</option>
      </select>
    </div>

    {#if filterPkg || filterCat || filterDiff}
      <button class="sf-reset" onclick={() => { filterPkg=null; filterCat=null; filterDiff=null }}>
        <i class="fa-solid fa-filter-circle-xmark"></i> Filter zurücksetzen
      </button>
    {/if}
  </div>

  <!-- Ergebnis-Header -->
  {#if q.length >= 2}
    <div class="search-meta">
      {#if loading}
        <span class="sm-info">Suche…</span>
      {:else}
        <span class="sm-info">
          <strong>{total}</strong> Treffer für
          <span class="sm-q">„{q}"</span>
          {#if results.length < total}
            -- {results.length} geladen
          {/if}
        </span>
      {/if}
    </div>
  {/if}

  <!-- Ergebnis-Liste -->
  <div class="search-results">
    {#if !loading && q.length >= 2 && results.length === 0}
      <div class="search-empty">
        <i class="fa-solid fa-circle-info"></i>
        Keine Treffer für „{q}"
        {#if filterPkg || filterCat}-- Filter anpassen?{/if}
      </div>

    {:else}
      {#each results as item (item.card_id)}
        <div class="sr-item" onclick={() => openCard(item)}>

          <!-- Paket + Kategorie Badge -->
          <div class="sr-meta">
            <span class="sr-pkg" style="--c:{item.package_color}">
              <i class="fa-solid {item.package_icon}"></i>
              {item.package_name}
            </span>
            <span class="sr-sep">·</span>
            <span class="sr-cat">
              {item.category_code}
            </span>
            <span class="sr-sep">·</span>
            <span class="sr-diff" style="color:{diffColor(item.difficulty)}">
              {diffLabel(item.difficulty)}
            </span>
            <span class="sr-id">{item.card_code}</span>
          </div>

          <!-- Frage mit Snippet -->
          <div class="sr-q">
            {#if item.snippet_q}
              {@html item.snippet_q}
            {:else}
              {item.question}
            {/if}
          </div>

          <!-- Antwort-Snippet -->
          {#if item.snippet_a}
            <div class="sr-a">
              {@html item.snippet_a}
            </div>
          {/if}

          <!-- Deeplink -->
          <div class="sr-actions">
            <button class="sr-link" onclick={e => { e.stopPropagation(); navigate(`/packages/${item.package_id}`) }}>
              <i class="fa-solid fa-arrow-up-right-from-square"></i>
              Paket öffnen
            </button>
          </div>
        </div>
      {/each}

      <!-- Nachladen -->
      {#if results.length < total}
        <div class="sr-loadmore">
          <button class="btn btn-ghost" onclick={loadMore} disabled={loadingMore}>
            {#if loadingMore}
              <i class="fa-solid fa-spinner fa-spin"></i> Lädt…
            {:else}
              <i class="fa-solid fa-arrow-down"></i>
              {total - results.length} weitere laden
            {/if}
          </button>
          <span class="sr-progress">{results.length} / {total}</span>
        </div>
      {/if}
    {/if}
  </div>

</div>

<style>
.search-page { padding: 24px 28px; max-width: 860px; }

/* Header */
.search-header { margin-bottom: 16px; }
.search-input-wrap {
  position: relative;
  margin-top: 14px;
}
.search-input {
  width: 100%;
  padding: 11px 40px;
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text0);
  font-size: 15px;
  font-family: inherit;
  outline: none;
  transition: border-color .15s;
}
.search-input:focus { border-color: var(--accent); }
.si-icon, .si-spin {
  position: absolute;
  left: 13px; top: 50%;
  transform: translateY(-50%);
  color: var(--text3);
  font-size: 14px;
  pointer-events: none;
}
.si-spin { left: auto; right: 13px; color: var(--accent); }
.si-clear {
  position: absolute;
  right: 10px; top: 50%;
  transform: translateY(-50%);
  background: none; border: none;
  color: var(--text3); cursor: pointer;
  font-size: 14px; padding: 4px;
}
.si-clear:hover { color: var(--text1); }

/* Filter */
.search-filters {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
}
.sf-group { display: flex; flex-direction: column; gap: 4px; }
.sf-label { font-size: 10px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: .05em; }
.sf-select {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text1);
  font-size: 12px;
  padding: 5px 8px;
  cursor: pointer;
  min-width: 140px;
}
.sf-reset {
  display: flex; align-items: center; gap: 6px;
  background: none; border: 1px solid var(--border);
  border-radius: 4px; color: var(--text2); cursor: pointer;
  font-size: 12px; padding: 5px 10px; align-self: flex-end;
  transition: all .15s;
}
.sf-reset:hover { border-color: var(--err); color: var(--err); }

/* Meta */
.search-meta { font-size: 13px; color: var(--text2); margin-bottom: 12px; }
.sm-q { font-weight: 600; color: var(--text1); }

/* Ergebnisse */
.search-results { display: flex; flex-direction: column; gap: 6px; }
.search-empty {
  display: flex; align-items: center; gap: 10px;
  color: var(--text3); font-size: 14px;
  padding: 32px 0; justify-content: center;
}

.sr-item {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color .12s;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sr-item:hover { border-color: var(--accent); }

.sr-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.sr-pkg {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600;
  color: var(--c, var(--accent));
}
.sr-cat {
  font-size: 11px; font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  background: var(--bg3); padding: 1px 6px;
  border-radius: 3px; color: var(--text2);
}
.sr-diff { font-size: 11px; font-weight: 600; }
.sr-sep  { color: var(--text3); font-size: 11px; }
.sr-id   {
  font-size: 10px; color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
  margin-left: auto;
}

.sr-q {
  font-size: 14px; font-weight: 500; color: var(--text0); line-height: 1.5;
}
.sr-a {
  font-size: 12px; color: var(--text2); line-height: 1.6;
  border-left: 2px solid var(--border); padding-left: 10px;
}

/* FTS5 Snippet highlight */
:global(.sr-q em), :global(.sr-a em) {
  font-style: normal;
  background: color-mix(in srgb, var(--accent) 25%, transparent);
  color: var(--text0);
  border-radius: 2px;
  padding: 0 2px;
}

.sr-actions {
  display: flex; gap: 8px; margin-top: 2px;
}
.sr-link {
  display: flex; align-items: center; gap: 5px;
  background: none; border: none;
  color: var(--text3); cursor: pointer; font-size: 11px;
  padding: 0; transition: color .12s;
}
.sr-link:hover { color: var(--accent); }

/* Nachladen */
.sr-loadmore {
  display: flex; align-items: center; justify-content: center;
  gap: 16px; padding: 16px 0;
}
.sr-progress { font-size: 11px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
</style>
