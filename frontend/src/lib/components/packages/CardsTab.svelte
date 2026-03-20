<script>
  import { categories, showToast, aiOnline } from '../../stores/index.js'
  import { apiGet, apiPost } from '../../utils/api.js'
  import { DL, DC, DI } from '../../utils/difficulty.js'
  import { marked } from 'marked'
  marked.setOptions({ breaks: true, gfm: true })

  let { pkg, searchQ = '' } = $props()

  let cards         = $state([])
  let loadingCards   = $state(false)
  let filterCat      = $state('')
  let filterDiff     = $state(0)
  let selectedCard   = $state(null)
  let aiState        = $state('idle')
  let aiText         = $state('')


  $effect(() => { filterCat; filterDiff; searchQ; loadCards() })

  async function loadCards() {
    loadingCards = true
    const p = new URLSearchParams({ package_id: pkg.id })
    if (searchQ) p.set('search', searchQ)
    if (filterCat) p.set('category', filterCat)
    if (filterDiff) p.set('difficulty', filterDiff)
    cards = await apiGet(`/api/cards?${p}`).catch(() => [])
    loadingCards = false
  }

  function onSearch() { loadCards() }

  async function getAI(c) {
    aiState = 'loading'; aiText = ''
    try {
      const data = await apiPost('/api/ai/explain', { card_id: c.card_id })
      aiText = data.explanation || ''
      aiState = 'done'
    } catch(e) {
      aiText = 'KI nicht erreichbar.'
      aiState = 'error'
    }
  }

  let totalCards = $derived(cards.length)
  let correctRate = $derived(() => {
    // Placeholder -- stats könnten später geladen werden
    return null
  })
</script>

<div class="cards-panel-layout">
  <!-- Liste -->
  <div class="cards-list-col">
    <div class="cl-header">
      <span class="cl-title">
        <i class="fa-solid fa-layer-group text-accent"></i>
        Karten <span class="cnt-badge">{totalCards}</span>
      </span>
    </div>
    <div class="cl-filters">
      <div class="search-wrap">
        <i class="fa-solid fa-magnifying-glass search-icon"></i>
        <input type="text" placeholder="Suchen..." bind:value={searchQ} oninput={onSearch} class="search-inp">
      </div>
      <div class="cl-filter-row">
        <select bind:value={filterCat}>
          <option value="">Alle Kategorien</option>
          {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
        </select>
        <select bind:value={filterDiff}>
          <option value={0}>Alle</option>
          <option value={1}>Leicht</option>
          <option value={2}>Mittel</option>
          <option value={3}>Schwer</option>
        </select>
      </div>
    </div>
    {#if loadingCards}
      <div class="list-loading"><i class="fa-solid fa-spinner fa-spin text-accent"></i></div>
    {:else}
      <div class="cl-list">
        {#each cards as c}
          <button class="cl-item"
            class:selected={selectedCard?.card_id === c.card_id}
            class:inactive={!c.active}
            onclick={() => { selectedCard = c; aiText = ''; aiState = 'idle' }}>
            <div class="cli-top">
              <span class="cli-id">{c.card_id}</span>
              {#if c.source === 'ai'}<span class="cli-ai-badge" title="KI-generiert"><i class="fa-solid fa-wand-magic-sparkles"></i></span>{/if}
              <span class="{DC[c.difficulty]}"><i class="fa-solid {DI[c.difficulty]}"></i></span>
            </div>
            <div class="cli-q">{c.question}</div>
            <div class="cli-cat" style="color:{$categories.find(x => x.code === c.category_code)?.color || 'var(--accent)'}">
              {$categories.find(x => x.code === c.category_code)?.name || c.category_code}
            </div>
          </button>
        {/each}
        {#if !loadingCards && cards.length === 0}
          <div class="list-empty">Keine Karten gefunden</div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Detail (nur Lesen) -->
  <div class="cards-detail-col">
    {#if selectedCard}
      <div class="card-detail-wrap">
        <div class="form-hd">
          <span class="cli-id">{selectedCard.card_id}</span>
          {#if selectedCard.source === 'ai'}<span class="source-badge source-ai"><i class="fa-solid fa-wand-magic-sparkles"></i> KI-generiert</span>{:else}<span class="source-badge source-manual"><i class="fa-solid fa-pen-nib"></i> Manuell</span>{/if}
          <span class="{DC[selectedCard.difficulty]} detail-diff"><i class="fa-solid {DI[selectedCard.difficulty]}"></i> {DL[selectedCard.difficulty]}</span>
        </div>
        <div class="detail-section">
          <div class="section-label">Frage</div>
          <div class="detail-q">{selectedCard.question}</div>
        </div>
        {#if selectedCard.hint}
          <div class="detail-section">
            <div class="section-label">Hinweis</div>
            <div class="detail-hint">
              <i class="fa-solid fa-lightbulb text-warn"></i> {selectedCard.hint}
            </div>
          </div>
        {/if}
        <div class="detail-section">
          <div class="section-label">Antwort</div>
          <div class="detail-ans markdown">{@html marked(selectedCard.answer)}</div>
        </div>
        <div class="detail-meta">
          <span class="detail-meta-item">
            <i class="fa-solid {$categories.find(x => x.code === selectedCard.category_code)?.icon || 'fa-tag'}"></i>
            {$categories.find(x => x.code === selectedCard.category_code)?.name || selectedCard.category_code}
          </span>
        </div>
        {#if aiState === 'idle' && $aiOnline}
          <button class="btn btn-ghost btn-sm" onclick={() => getAI(selectedCard)}>
            <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Erklärung
          </button>
        {:else if aiState === 'loading'}
          <div class="ai-load-indicator">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <div>
              <div class="ai-load-text">KI generiert Erklärung...</div>
              <div class="ai-bar"><div class="ai-bar-fill"></div></div>
            </div>
          </div>
        {:else if aiText}
          <div class="detail-section">
            <div class="section-label text-ac2">KI-Erklärung</div>
            <div class="detail-ai markdown">{@html marked(aiText)}</div>
          </div>
        {/if}
      </div>

    {:else}
      <div class="empty-state">
        <i class="fa-solid fa-layer-group"></i>
        <p>Karte auswählen</p>
      </div>
    {/if}
  </div>
</div>

<style>
/* ── Karten Split Layout ──────────────────────────────────── */
.cards-panel-layout { flex: 1; display: grid; grid-template-columns: 320px 1fr; overflow: hidden; }
.cards-list-col { border-right: 1px solid var(--border); display: flex; flex-direction: column; background: var(--bg1); overflow: hidden; }
.cl-header { padding: 14px 14px 10px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.cl-title { font-size: 13px; font-weight: 700; color: var(--text0); display: flex; align-items: center; gap: 6px; }
.cl-title i { font-size: 13px; }
.cnt-badge { font-size: 10px; background: var(--bg3); color: var(--text2); border-radius: 4px; padding: 1px 6px; font-family: 'JetBrains Mono', monospace; }
.cl-filters { padding: 10px 12px; display: flex; flex-direction: column; gap: 7px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.search-wrap { position: relative; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 11px; color: var(--text3); pointer-events: none; }
.search-inp { padding-left: 30px !important; }
.cl-list { flex: 1; overflow-y: auto; padding: 6px; }
.list-loading { padding: 24px; text-align: center; color: var(--accent); font-size: 18px; }
.list-empty { padding: 20px; text-align: center; color: var(--text3); font-size: 12px; }
.cl-item { display: block; width: 100%; padding: 9px 10px; border-radius: 4px; text-align: left; cursor: pointer; transition: all .12s; border: none; margin-bottom: 4px; background: var(--bg1); font-family: inherit; box-shadow: 0 1px 2px var(--shadow); }
.cl-item:hover { background: var(--bg2); }
.cl-item.selected { background: var(--bg2); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent); }
.cl-item.inactive { opacity: .4; }
.cli-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.cli-id { font-size: 9px; color: var(--text3); font-family: 'JetBrains Mono', monospace; letter-spacing: .06em; }
.cli-q { font-size: 11px; color: var(--text1); line-height: 1.4; margin-bottom: 3px; }
.cli-cat { font-size: 9px; font-weight: 600; }

/* KI-Badge in Kartenliste */
.cli-ai-badge { font-size: 8px; color: var(--ac2); opacity: 0.7; }

/* Source-Badge im Detail */
.source-badge {
  font-size: 9px; font-weight: 600; padding: 2px 7px;
  border-radius: 2px; letter-spacing: .03em;
}
.source-badge i { font-size: 8px; margin-right: 2px; }
.source-ai { color: var(--ac2); background: color-mix(in srgb, var(--ac2) 12%, transparent); }
.source-manual { color: var(--text3); background: var(--bg3); }

/* ── Filter-Zeile ─────────────────────────────────────────── */
.cl-filter-row { display: flex; gap: 6px; }
.cl-filter-row select { flex: 1; }

/* ── Detail-Spalte ────────────────────────────────────────── */
.cards-detail-col { overflow-y: auto; background: var(--bg0); }
.card-detail-wrap { padding: 22px; max-width: 700px; }
.detail-diff { margin-left: auto; }
.detail-meta { display: flex; gap: 12px; margin-bottom: 12px; padding: 8px 0; border-top: 1px solid var(--border); }
.detail-meta-item { font-size: 11px; color: var(--text2); display: flex; align-items: center; gap: 5px; }
.detail-section { margin-bottom: 16px; }
.detail-q { font-size: 15px; font-weight: 600; color: var(--text0); background: var(--bg2); border-radius: 4px; padding: 12px 14px; line-height: 1.5; }
.detail-hint { font-size: 12px; color: var(--text2); background: var(--bg2); border-radius: 4px; padding: 8px 12px; display: flex; align-items: center; gap: 6px; }
.detail-hint i { flex-shrink: 0; }
.detail-ans { font-size: 12px; color: var(--text1); background: var(--bg1); border-radius: 4px; padding: 12px 14px; line-height: 1.65; box-shadow: 0 1px 3px var(--shadow); }
.detail-ai { font-size: 13px; color: var(--text1); background: var(--bg2); border: 1px solid color-mix(in srgb, var(--ac2) 35%, transparent); border-radius: 4px; padding: 12px 14px; line-height: 1.6; }
.ai-load-indicator { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--glow); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); border-radius: 4px; margin-top: 4px; }
.ai-load-indicator > i { color: var(--accent); flex-shrink: 0; }
.ai-load-text { font-size: 12px; color: var(--accent); margin-bottom: 4px; }
.ai-bar { height: 2px; background: var(--bg3); border-radius: 1px; overflow: hidden; }
.ai-bar-fill { height: 100%; background: var(--accent); animation: scan 1.8s ease-in-out infinite; }
@keyframes scan { 0% { transform: translateX(-100%); } 100% { transform: translateX(400%); } }

</style>
