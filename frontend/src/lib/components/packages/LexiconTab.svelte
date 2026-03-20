<script>
  import { categories, showToast } from '../../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete } from '../../utils/api.js'
  import { onMount } from 'svelte'

  let { pkg } = $props()

  const BATCH = 50
  let lexicon = $state([])
  let total = $state(0)
  let searchQ = $state('')
  let searchTimer = null
  let loading = $state(false)
  let showLexForm = $state(false)
  let lexForm = $state({ term: '', definition: '', category_code: '' })
  let editId = $state(null)
  let editForm = $state({ term: '', definition: '', category_code: '' })
  let confirmDelete = $state(null)

  onMount(() => loadLexicon(false))

  function onSearch(val) {
    searchQ = val
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => loadLexicon(false), 200)
  }

  async function loadLexicon(append = false) {
    loading = true
    try {
      const offset = append ? lexicon.length : 0
      const params = new URLSearchParams({ limit: BATCH, offset })
      if (searchQ) params.set('search', searchQ + '*')
      const res = await apiGet(`/api/packages/${pkg.id}/lexicon?${params}`)
      if (append) {
        lexicon = [...lexicon, ...res.items]
      } else {
        lexicon = res.items
      }
      total = res.total
    } catch(e) {
      lexicon = []; total = 0
    }
    loading = false
  }

  let hasMore = $derived(lexicon.length < total)

  async function saveLex() {
    if (!lexForm.term || !lexForm.definition) { showToast('Begriff und Definition sind Pflicht', 'error'); return }
    try {
      await apiPost('/api/lexicon', { ...lexForm, package_id: pkg.id })
      showToast('Eintrag gespeichert', 'success')
      lexForm = { term: '', definition: '', category_code: '' }
      showLexForm = false
      await loadLexicon(false)
    } catch(e) { showToast(e.message, 'error') }
  }

  function startEdit(entry) {
    editId = entry.id
    editForm = { term: entry.term, definition: entry.definition, category_code: entry.category_code || '' }
  }

  async function saveEdit() {
    if (!editForm.term || !editForm.definition) { showToast('Begriff und Definition sind Pflicht', 'error'); return }
    try {
      await apiPut(`/api/lexicon/${editId}`, editForm)
      showToast('Eintrag aktualisiert', 'success')
      editId = null
      await loadLexicon(false)
    } catch(e) { showToast(e.message, 'error') }
  }

  function requestDelete(id) {
    if (confirmDelete === id) { doDelete(id); return }
    confirmDelete = id
    setTimeout(() => { if (confirmDelete === id) confirmDelete = null }, 3000)
  }

  async function doDelete(id) {
    try {
      await apiDelete(`/api/lexicon/${id}`)
      showToast('Eintrag gelöscht', 'info')
      confirmDelete = null
      await loadLexicon(false)
    } catch(e) { showToast(e.message, 'error') }
  }

  let lexGrouped = $derived(
    Object.entries(
      (lexicon || []).reduce((acc, e) => {
        const letter = (e.term || '?')[0].toUpperCase()
        ;(acc[letter] = acc[letter] || []).push(e)
        return acc
      }, {})
    ).sort((a, b) => a[0].localeCompare(b[0]))
  )
</script>

<div class="tab-page">
  <div class="tab-hd">
    <div>
      <div class="tab-hd-title">Lexikon <span class="lex-count">{total}</span></div>
      <div class="tab-hd-sub">Fachbegriffe dieses Pakets</div>
    </div>
    <button class="btn btn-primary" onclick={() => showLexForm = !showLexForm}>
      <i class="fa-solid fa-plus"></i> Eintrag
    </button>
  </div>

  <div class="lex-search">
    <i class="fa-solid fa-magnifying-glass lex-search-icon"></i>
    <input type="text" placeholder="Begriffe suchen..." value={searchQ}
      oninput={(e) => onSearch(e.target.value)} />
    {#if searchQ}
      <button class="lex-search-clear" onclick={() => onSearch('')}>
        <i class="fa-solid fa-xmark"></i>
      </button>
    {/if}
  </div>

  {#if showLexForm}
    <div class="card-box" style="max-width:560px;margin-bottom:16px">
      <div class="form-fields">
        <label class="field-label">Begriff<input type="text" bind:value={lexForm.term} placeholder="Fachbegriff..."></label>
        <label class="field-label">Definition<textarea bind:value={lexForm.definition} rows="4"></textarea></label>
        <label class="field-label">Kategorie
          <select bind:value={lexForm.category_code}>
            <option value="">Keine</option>
            {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
          </select>
        </label>
      </div>
      <div class="form-footer">
        <button class="btn btn-ghost btn-sm" onclick={() => showLexForm = false}>Abbrechen</button>
        <button class="btn btn-primary btn-sm" onclick={saveLex}>
          <i class="fa-solid fa-floppy-disk"></i> Speichern
        </button>
      </div>
    </div>
  {/if}

  {#if lexicon.length === 0 && !loading}
    <div class="empty-state">
      <i class="fa-solid fa-book-open"></i>
      <p>{searchQ ? 'Keine Treffer' : 'Noch keine Einträge'}</p>
    </div>
  {:else}
    {#each lexGrouped as [letter, items]}
      <div class="lex-group">
        <div class="lex-letter">{letter}</div>
        {#each items as entry}
          {#if editId === entry.id}
            <div class="card-box lex-entry">
              <div class="form-fields">
                <label class="field-label">Begriff<input type="text" bind:value={editForm.term}></label>
                <label class="field-label">Definition<textarea bind:value={editForm.definition} rows="4"></textarea></label>
                <label class="field-label">Kategorie
                  <select bind:value={editForm.category_code}>
                    <option value="">Keine</option>
                    {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
                  </select>
                </label>
              </div>
              <div class="form-footer">
                <button class="btn btn-ghost btn-sm" onclick={() => editId = null}>Abbrechen</button>
                <button class="btn btn-primary btn-sm" onclick={saveEdit}>
                  <i class="fa-solid fa-floppy-disk"></i> Speichern
                </button>
              </div>
            </div>
          {:else}
            <div class="card-box lex-entry">
              <div class="lex-row">
                <div style="flex:1">
                  <div class="lex-term">{entry.term}</div>
                  <div class="lex-def">{entry.definition}</div>
                </div>
                <div class="lex-actions">
                  <button class="btn btn-ghost btn-sm lex-btn" onclick={() => startEdit(entry)} title="Bearbeiten">
                    <i class="fa-solid fa-pen"></i>
                  </button>
                  <button class="btn btn-sm lex-btn {confirmDelete === entry.id ? 'btn-danger' : 'btn-ghost'}"
                    onclick={() => requestDelete(entry.id)} title="Löschen">
                    <i class="fa-solid fa-trash"></i>
                    {#if confirmDelete === entry.id}
                      <span style="font-size:10px;margin-left:2px">Sicher?</span>
                    {/if}
                  </button>
                </div>
              </div>
            </div>
          {/if}
        {/each}
      </div>
    {/each}

    {#if hasMore}
      <button class="btn btn-ghost lex-more" onclick={() => loadLexicon(true)} disabled={loading}>
        {#if loading}
          <i class="fa-solid fa-spinner fa-spin"></i>
        {:else}
          <i class="fa-solid fa-angles-down"></i> Weitere laden ({lexicon.length}/{total})
        {/if}
      </button>
    {/if}
  {/if}
</div>

<style>
.lex-count { font-size: 11px; color: var(--text3); font-weight: 400; margin-left: 6px; }
.lex-search { position: relative; max-width: 400px; margin-bottom: 16px; }
.lex-search input {
  width: 100%; padding: 8px 12px 8px 32px;
  background: var(--bg2); border: 1px solid var(--border); border-radius: 3px;
  color: var(--text1); font-size: 13px;
}
.lex-search input:focus { border-color: var(--accent); outline: none; }
.lex-search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text3); font-size: 12px; pointer-events: none; }
.lex-search-clear {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: var(--text3); cursor: pointer; font-size: 12px; padding: 4px;
}
.lex-search-clear:hover { color: var(--text1); }
.lex-group { margin-bottom: 20px; }
.lex-letter { font-size: 11px; font-weight: 700; letter-spacing: .12em; color: var(--accent); font-family: 'JetBrains Mono', monospace; padding-bottom: 8px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
.lex-entry { margin-bottom: 8px; }
.lex-row { display: flex; align-items: flex-start; gap: 12px; }
.lex-term { font-size: 16px; font-weight: 700; color: var(--text0); margin-bottom: 8px; }
.lex-def { font-size: 13px; color: var(--text1); line-height: 1.7; white-space: pre-wrap; }
.lex-actions { display: flex; gap: 4px; flex-shrink: 0; opacity: 0.4; transition: opacity .15s; }
.lex-entry:hover .lex-actions { opacity: 1; }
.lex-btn { padding: 4px 6px; font-size: 11px; }
.lex-more { display: block; margin: 16px auto; font-size: 12px; }
</style>
