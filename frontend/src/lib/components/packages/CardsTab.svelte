<script>
  import { categories, showToast, aiOnline } from '../../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete } from '../../utils/api.js'
  import { DL, DC, DI } from '../../utils/difficulty.js'
  import { marked } from 'marked'
  marked.setOptions({ breaks: true, gfm: true })

  let { pkg, searchQ = '' } = $props()

  let cards         = $state([])
  let loadingCards   = $state(false)
  let filterCat      = $state('')
  let selectedCard   = $state(null)
  let showCardForm   = $state(false)
  let editCard       = $state(null)
  let cardForm       = $state({})
  let confirmDeleteCard = $state(null)
  let aiState        = $state('idle')
  let aiText         = $state('')


  $effect(() => { filterCat; searchQ; loadCards() })

  async function loadCards() {
    loadingCards = true
    const p = new URLSearchParams({ package_id: pkg.id })
    if (searchQ) p.set('search', searchQ)
    if (filterCat) p.set('category', filterCat)
    cards = await apiGet(`/api/cards?${p}`).catch(() => [])
    loadingCards = false
  }

  function onSearch() { loadCards() }
  function openCreate() { editCard = null; cardForm = { card_id:'', category_code:'GB', question:'', answer:'', hint:'', difficulty:2 }; showCardForm = true }
  function openEdit(c) { editCard = c; cardForm = {...c, hint:c.hint||''}; showCardForm = true }

  async function saveCard() {
    try {
      if (editCard) {
        await apiPut(`/api/cards/${editCard.card_id}`, cardForm)
        showToast('Gespeichert', 'success')
      } else {
        await apiPost('/api/cards', {...cardForm, package_id: pkg.id})
        showToast('Erstellt', 'success')
      }
      showCardForm = false
      await loadCards()
    } catch(e) { showToast(e.message, 'error') }
  }

  async function deleteCard(c) {
    if (confirmDeleteCard !== c.card_id) { confirmDeleteCard = c.card_id; setTimeout(() => confirmDeleteCard = null, 3000); return }
    try {
      await apiDelete(`/api/cards/${c.card_id}`)
      showToast('Gelöscht', 'success')
      selectedCard = null; confirmDeleteCard = null
      await loadCards()
    } catch(e) { showToast(e.message, 'error') }
  }

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
</script>

<div class="cards-panel-layout">
  <!-- Liste -->
  <div class="cards-list-col">
    <div class="cl-header">
      <span class="cl-title">
        <i class="fa-solid fa-layer-group text-accent"></i>
        Karten <span class="cnt-badge">{cards.length}</span>
      </span>
      <button class="btn btn-primary btn-sm" onclick={openCreate}>
        <i class="fa-solid fa-plus"></i>
      </button>
    </div>
    <div class="cl-filters">
      <div class="search-wrap">
        <i class="fa-solid fa-magnifying-glass search-icon"></i>
        <input type="text" placeholder="Suchen..." bind:value={searchQ} oninput={onSearch} class="search-inp">
      </div>
      <select bind:value={filterCat}>
        <option value="">Alle Kategorien</option>
        {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
      </select>
    </div>
    {#if loadingCards}
      <div class="list-loading"><i class="fa-solid fa-spinner fa-spin text-accent"></i></div>
    {:else}
      <div class="cl-list">
        {#each cards as c}
          <button class="cl-item"
            class:selected={selectedCard?.card_id===c.card_id}
            class:inactive={!c.active}
            onclick={()=>{selectedCard=c;aiText='';aiState='idle';showCardForm=false}}>
            <div class="cli-top">
              <span class="cli-id">{c.card_id}</span>
              {#if c.source === 'ai'}<span class="cli-ai-badge" title="KI-generiert"><i class="fa-solid fa-wand-magic-sparkles"></i></span>{/if}
              <span class="{DC[c.difficulty]}"><i class="fa-solid {DI[c.difficulty]}"></i></span>
            </div>
            <div class="cli-q">{c.question}</div>
            <div class="cli-cat" style="color:{$categories.find(x=>x.code===c.category_code)?.color||'var(--accent)'}">
              {$categories.find(x=>x.code===c.category_code)?.name || c.category_code}
            </div>
          </button>
        {/each}
        {#if !loadingCards && cards.length===0}
          <div class="list-empty">Keine Karten gefunden</div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Detail -->
  <div class="cards-detail-col">
    {#if showCardForm}
      <div class="card-form-wrap">
        <div class="form-hd">
          <span class="form-title">
            <i class="fa-solid {editCard?'fa-pen':'fa-plus'} text-accent"></i>
            {editCard?'Karte bearbeiten':'Neue Karte'}
          </span>
          <button class="ib" onclick={()=>showCardForm=false}><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="form-fields">
          <div class="form-row-2">
            <label class="field-label">Karten-ID<input type="text" bind:value={cardForm.card_id} placeholder="K-106 (auto)"></label>
            <label class="field-label">Kategorie
              <select bind:value={cardForm.category_code}>
                {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
              </select>
            </label>
          </div>
          <label class="field-label">Frage<textarea bind:value={cardForm.question} rows="3"></textarea></label>
          <label class="field-label">Antwort<textarea bind:value={cardForm.answer} rows="5"></textarea></label>
          <label class="field-label">Hinweis<input type="text" bind:value={cardForm.hint} placeholder="Kleiner Tipp..."></label>
          <div>
            <div class="section-label">Schwierigkeit</div>
            <div class="diff-btns">
              {#each [1,2,3] as d}
                <button class="diff-btn" class:diff-active={cardForm.difficulty===d}
                  data-diff={d} onclick={()=>cardForm.difficulty=d}>
                  <i class="fa-solid {DI[d]}"></i> {DL[d]}
                </button>
              {/each}
            </div>
          </div>
        </div>
        <div class="form-footer">
          <button class="btn btn-ghost" onclick={()=>showCardForm=false}>Abbrechen</button>
          <button class="btn btn-primary" onclick={saveCard}>
            <i class="fa-solid {editCard?'fa-floppy-disk':'fa-plus'}"></i>
            {editCard?'Speichern':'Erstellen'}
          </button>
        </div>
      </div>

    {:else if selectedCard}
      <div class="card-detail-wrap">
        <div class="form-hd">
          <span class="cli-id">{selectedCard.card_id}</span>
          {#if selectedCard.source === 'ai'}<span class="source-badge source-ai"><i class="fa-solid fa-wand-magic-sparkles"></i> KI-generiert</span>{:else}<span class="source-badge source-manual"><i class="fa-solid fa-pen-nib"></i> Manuell</span>{/if}
          <div class="card-detail-actions">
            <button class="ib" onclick={()=>openEdit(selectedCard)} title="Bearbeiten">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="ib err" onclick={()=>deleteCard(selectedCard)}>
              {#if confirmDeleteCard === selectedCard.card_id}
                Wirklich?
              {:else}
                <i class="fa-solid fa-trash"></i>
              {/if}
            </button>
          </div>
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
        {#if aiState==='idle' && $aiOnline}
          <button class="btn btn-ghost btn-sm" onclick={()=>getAI(selectedCard)}>
            <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Erklärung
          </button>
        {:else if aiState==='loading'}
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
.cl-item { display: block; width: 100%; padding: 9px 10px; border-radius: 4px; text-align: left; cursor: pointer; transition: background .12s; border: 1px solid var(--border); margin-bottom: 4px; background: var(--bg1); font-family: inherit; }
.cl-item:hover { background: var(--bg2); border-color: var(--text3); }
.cl-item.selected { background: var(--bg2); border-color: var(--accent); }
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

/* ── Detail-Spalte ────────────────────────────────────────── */
.cards-detail-col { overflow-y: auto; background: var(--bg0); }
.card-form-wrap, .card-detail-wrap { padding: 22px; max-width: 700px; }
.card-detail-actions { display: flex; gap: 6px; }
.detail-section { margin-bottom: 16px; }
.detail-q { font-size: 15px; font-weight: 600; color: var(--text0); background: var(--bg2); border-radius: 4px; padding: 12px 14px; line-height: 1.5; }
.detail-hint { font-size: 12px; color: var(--text2); background: var(--bg2); border-radius: 4px; padding: 8px 12px; display: flex; align-items: center; gap: 6px; }
.detail-hint i { flex-shrink: 0; }
.detail-ans { font-size: 12px; color: var(--text1); background: var(--bg1); border: 1px solid var(--border); border-radius: 4px; padding: 12px 14px; line-height: 1.65; }
.detail-ai { font-size: 13px; color: var(--text1); background: var(--bg2); border: 1px solid color-mix(in srgb, var(--ac2) 35%, transparent); border-radius: 4px; padding: 12px 14px; line-height: 1.6; }
.ai-load-indicator { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--glow); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); border-radius: 4px; margin-top: 4px; }
.ai-load-indicator > i { color: var(--accent); flex-shrink: 0; }
.ai-load-text { font-size: 12px; color: var(--accent); margin-bottom: 4px; }
.ai-bar { height: 2px; background: var(--bg3); border-radius: 1px; overflow: hidden; }
.ai-bar-fill { height: 100%; background: var(--accent); animation: scan 1.8s ease-in-out infinite; }
@keyframes scan { 0% { transform: translateX(-100%); } 100% { transform: translateX(400%); } }

/* ── Schwierigkeit ────────────────────────────────────────── */
.diff-btns { display: flex; gap: 8px; }
.diff-btn {
  padding: 5px 13px; border-radius: 4px; font-size: 11px; font-weight: 600;
  border: 1px solid var(--border); background: transparent; color: var(--text2);
  cursor: pointer; transition: all .15s; display: flex; align-items: center; gap: 5px; font-family: inherit;
}
.diff-btn[data-diff="1"].diff-active { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 12%, transparent); }
.diff-btn[data-diff="2"].diff-active { border-color: var(--warn); color: var(--warn); background: color-mix(in srgb, var(--warn) 12%, transparent); }
.diff-btn[data-diff="3"].diff-active { border-color: var(--err); color: var(--err); background: color-mix(in srgb, var(--err) 12%, transparent); }
</style>
