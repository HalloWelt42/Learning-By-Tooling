<script>
  import { categories, showToast, aiOnline } from '../../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete } from '../../utils/api.js'
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

  const DL = ['','Leicht','Mittel','Schwer']
  const DC = ['','d1','d2','d3']
  const DI = ['','fa-gauge-simple','fa-gauge','fa-gauge-high']

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
