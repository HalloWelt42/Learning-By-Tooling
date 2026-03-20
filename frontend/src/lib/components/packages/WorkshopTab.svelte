<script>
  import { categories, showToast, loadGlobal, aiOnline } from '../../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete, apiUpload } from '../../utils/api.js'
  import { DL, DC, DI } from '../../utils/difficulty.js'
  import { marked } from 'marked'
  import ImportTab from './ImportTab.svelte'
  marked.setOptions({ breaks: true, gfm: true })

  let { pkg } = $props()

  // -- Sub-Navigation --
  let section = $state('drafts')  // drafts | create | documents | mc | import

  // -- Drafts --
  let drafts      = $state([])
  let editDraft   = $state(null)
  let editDForm   = $state({})

  // -- Neue Karte --
  let cardForm = $state({ card_id: '', category_code: 'GB', question: '', answer: '', hint: '', difficulty: 2 })

  // -- Dokument-Upload + KI --
  let documents     = $state([])
  let showUpload    = $state(false)
  let uploadFile    = $state(null)
  let uploadTitle   = $state('')
  let uploadCat     = $state('AL')
  let cardsPerChunk = $state(3)
  let autoGen       = $state(true)
  let uploadState   = $state('idle')
  let uploadMsg     = $state('')
  let genState      = $state('idle')
  let genSteps      = $state([])
  let genSummary    = $state(null)
  let selectedDoc   = $state(null)
  let selectedChunks = $state(new Set())
  let chunks        = $state([])

  // -- MC --
  let mcStatus  = $state(null)
  let mcCards   = $state([])
  let mcLoading = $state(false)
  let mcGenRunning = $state(false)
  let selectedMcCard = $state(null)

  // -- Init --
  import { onMount } from 'svelte'
  onMount(() => { loadDrafts(); loadDocuments() })

  $effect(() => { if (section === 'mc') loadMcStatus() })

  // -- Laden --
  async function loadDrafts()    { drafts    = await apiGet(`/api/packages/${pkg.id}/drafts`).catch(() => []) }
  async function loadDocuments() { documents = await apiGet(`/api/packages/${pkg.id}/documents`).catch(() => []) }

  // -- Entwuerfe --
  let pending = $derived(drafts.filter(d => d.status === 'pending'))

  async function approveDraft(d) {
    await apiPut(`/api/drafts/${d.id}`, { action: 'approve', package_id: pkg.id })
    await loadDrafts(); await loadGlobal()
    showToast('Karte freigegeben', 'success')
  }
  async function rejectDraft(d) {
    await apiPut(`/api/drafts/${d.id}`, { action: 'reject' })
    await loadDrafts()
  }
  function startEditDraft(d) {
    editDraft = d
    editDForm = { question: d.question, answer: d.answer, hint: d.hint || '', difficulty: d.difficulty, category_code: d.category_code }
  }
  async function saveEditDraft() {
    await apiPut(`/api/drafts/${editDraft.id}`, { action: 'edit', ...editDForm, package_id: pkg.id })
    editDraft = null
    await loadDrafts(); await loadGlobal()
    showToast('Bearbeitet und freigegeben', 'success')
  }
  async function approveAll() {
    for (const d of pending) await apiPut(`/api/drafts/${d.id}`, { action: 'approve', package_id: pkg.id }).catch(() => {})
    await loadDrafts(); await loadGlobal()
    showToast(`${pending.length} Karten freigegeben`, 'success')
  }

  // -- Neue Karte erstellen --
  async function createCard() {
    if (!cardForm.question.trim() || !cardForm.answer.trim()) {
      showToast('Frage und Antwort erforderlich', 'error'); return
    }
    try {
      await apiPost('/api/cards', { ...cardForm, package_id: pkg.id })
      showToast('Karte erstellt', 'success')
      cardForm = { card_id: '', category_code: cardForm.category_code, question: '', answer: '', hint: '', difficulty: cardForm.difficulty }
      await loadGlobal()
    } catch(e) { showToast(e.message, 'error') }
  }

  // -- Dokument Upload + KI --
  const FT = { pdf: 'fa-file-pdf', md: 'fa-file-code', txt: 'fa-file-lines', docx: 'fa-file-word' }
  const GSTEP_ICON  = { done: 'fa-check', running: 'fa-spinner fa-spin', pending: 'fa-circle', error: 'fa-xmark' }
  const GSTEP_COLOR = { done: 'var(--ok)', running: 'var(--accent)', pending: 'var(--text3)', error: 'var(--err)' }
  function fmtSize(b) { return b < 1024 ? `${b}B` : b < 1048576 ? `${(b / 1024).toFixed(1)}KB` : `${(b / 1048576).toFixed(1)}MB` }

  async function handleUpload() {
    if (!uploadFile) { showToast('Datei auswaehlen', 'error'); return }
    uploadState = 'uploading'; uploadMsg = 'Datei wird verarbeitet...'
    try {
      const fd = new FormData()
      fd.append('file', uploadFile)
      fd.append('title', uploadTitle || uploadFile.name.replace(/\.[^.]+$/, ''))
      fd.append('category', uploadCat)
      const r = await apiUpload(`/api/packages/${pkg.id}/documents/upload`, fd)
      uploadMsg = `${r.title} -- ${r.chunk_count} Abschnitte`; uploadState = 'done'
      await loadDocuments(); await loadGlobal()
      showUpload = false; uploadFile = null; uploadTitle = ''
      if (autoGen && $aiOnline) {
        await loadDocuments()
        const doc = documents.find(d => d.id === r.document_id)
        if (doc) await openDoc(doc)
      }
    } catch(e) { uploadState = 'error'; uploadMsg = e.message; showToast(e.message, 'error') }
  }

  async function openDoc(doc) {
    selectedDoc = doc
    const data = await apiGet(`/api/documents/${doc.id}/chunks`).catch(() => null)
    if (data) chunks = data.chunks
    selectedChunks = new Set(); genState = 'idle'; genSummary = null
  }

  async function startGen() {
    if (!$aiOnline || !selectedDoc) return
    const cnt = selectedChunks.size > 0 ? selectedChunks.size : chunks.filter(c => !c.processed).length
    genSteps = [
      { label: 'Abschnitte vorbereiten', status: 'running' },
      { label: `${cnt} Abschnitte senden`, status: 'pending' },
      { label: 'KI generiert Fragen und Antworten', status: 'pending' },
      { label: 'Entwuerfe speichern', status: 'pending' },
    ]
    genState = 'running'; genSummary = null
    const tick = ms => new Promise(r => setTimeout(r, ms))
    await tick(400)
    genSteps = genSteps.map((s, i) => i === 0 ? { ...s, status: 'done' } : i === 1 ? { ...s, status: 'running' } : s)
    await tick(300)
    genSteps = genSteps.map((s, i) => i === 1 ? { ...s, status: 'done' } : i === 2 ? { ...s, status: 'running' } : s)
    try {
      const r = await apiPost(`/api/documents/${selectedDoc.id}/generate`, {
        category: uploadCat || 'AL', cards_per_chunk: cardsPerChunk,
        chunk_ids: selectedChunks.size > 0 ? [...selectedChunks] : null,
      })
      genSteps = genSteps.map((s, i) => i === 2 ? { ...s, status: 'done' } : i === 3 ? { ...s, status: 'running' } : s)
      await tick(300)
      genSteps = genSteps.map(s => ({ ...s, status: 'done' }))
      genState = 'done'; genSummary = r
      await loadDrafts(); await loadDocuments(); await loadGlobal()
      selectedChunks = new Set()
      showToast(`${r.created} Entwuerfe erstellt`, 'success')
      section = 'drafts'
    } catch(e) {
      genSteps = genSteps.map(s => s.status === 'running' ? { ...s, status: 'error' } : s)
      genState = 'error'; showToast(e.message, 'error')
    }
  }

  let confirmDeleteDoc = $state(null)
  async function deleteDoc(doc) {
    if (confirmDeleteDoc !== doc.id) {
      confirmDeleteDoc = doc.id; setTimeout(() => confirmDeleteDoc = null, 3000); return
    }
    confirmDeleteDoc = null
    await apiDelete(`/api/documents/${doc.id}`)
    if (selectedDoc?.id === doc.id) { selectedDoc = null; chunks = [] }
    await loadDocuments(); await loadGlobal()
    showToast('Dokument geloescht', 'info')
  }

  function toggleChunk(id) { const s = new Set(selectedChunks); s.has(id) ? s.delete(id) : s.add(id); selectedChunks = s }

  // -- MC --
  async function loadMcStatus() {
    mcStatus = await apiGet(`/api/mc/status/${pkg.id}`).catch(() => null)
    // Lade alle gecachten MC-Optionen
    mcLoading = true
    mcCards = await apiGet(`/api/mc/list/${pkg.id}`).catch(() => [])
    mcLoading = false
  }

  async function generateMcBatch() {
    if (!$aiOnline) { showToast('LM Studio ist offline', 'error'); return }
    mcGenRunning = true
    try {
      const r = await apiPost('/api/mc/generate-batch', { package_id: pkg.id, limit: 20 })
      showToast(`${r.generated} MC-Optionen generiert`, 'success')
      await loadMcStatus()
    } catch(e) { showToast(e.message, 'error') }
    mcGenRunning = false
  }

  async function deleteMcOption(cardId) {
    await apiDelete(`/api/mc/option/${cardId}/${pkg.id}`).catch(() => {})
    await loadMcStatus()
    if (selectedMcCard?.card_id === cardId) selectedMcCard = null
    showToast('MC-Optionen entfernt', 'info')
  }

  async function regenerateMc(cardId) {
    if (!$aiOnline) { showToast('LM Studio ist offline', 'error'); return }
    try {
      await apiPost('/api/mc/regenerate', { card_id: cardId, package_id: pkg.id })
      showToast('MC-Optionen neu generiert', 'success')
      await loadMcStatus()
    } catch(e) { showToast(e.message, 'error') }
  }
</script>

<div class="ws-wrap">
  <!-- Sub-Navigation -->
  <div class="ws-nav">
    {#each [
      ['drafts',    'fa-pen-to-square',       'Entwuerfe',     pending.length],
      ['create',    'fa-plus',                'Neue Karte',    0],
      ['documents', 'fa-wand-magic-sparkles', 'KI-Generierung', 0],
      ['mc',        'fa-list-check',          'MC-Optionen',   0],
      ['import',    'fa-file-import',         'Import',        0],
    ] as [id, fa, lbl, badge]}
      <button class="ws-nav-btn" class:active={section === id} onclick={() => section = id}>
        <i class="fa-solid {fa}"></i> {lbl}
        {#if badge > 0}<span class="ws-badge">{badge}</span>{/if}
      </button>
    {/each}
  </div>

  <div class="ws-body">

    <!-- ENTWUERFE -->
    {#if section === 'drafts'}
      <div class="ws-page">
        {#if pending.length > 0}
          <div class="ws-section-hd">
            <div>
              <div class="ws-section-title">KI-Entwuerfe pruefen</div>
              <div class="ws-section-sub">{pending.length} Entwuerfe warten auf Freigabe</div>
            </div>
            <button class="btn btn-ok btn-sm" onclick={approveAll}>
              <i class="fa-solid fa-check-double"></i> Alle freigeben
            </button>
          </div>
          <div class="drafts-list">
            {#each pending as draft (draft.id)}
              {#if editDraft?.id === draft.id}
                <div class="card-box draft-edit">
                  <div class="draft-edit-title">
                    <i class="fa-solid fa-pen text-accent"></i> Karte bearbeiten
                  </div>
                  <label class="field-label">Frage<textarea bind:value={editDForm.question} rows="2"></textarea></label>
                  <label class="field-label">Antwort<textarea bind:value={editDForm.answer} rows="3"></textarea></label>
                  <div class="draft-edit-row">
                    <label class="field-label">Hinweis<input type="text" bind:value={editDForm.hint}></label>
                    <label class="field-label">Kategorie
                      <select bind:value={editDForm.category_code}>
                        {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
                      </select>
                    </label>
                  </div>
                  <div class="draft-edit-footer">
                    <button class="btn btn-ghost btn-sm" onclick={() => editDraft = null}>Abbrechen</button>
                    <button class="btn btn-ok btn-sm" onclick={saveEditDraft}>
                      <i class="fa-solid fa-check"></i> Speichern
                    </button>
                  </div>
                </div>
              {:else}
                <div class="card-box draft-card">
                  <div class="draft-card-hd">
                    <span class="draft-cat" style="color:{$categories.find(c => c.code === draft.category_code)?.color || 'var(--accent)'}">
                      {draft.category_code}
                      {#if draft.doc_title}<span class="draft-src">aus {draft.doc_title}</span>{/if}
                    </span>
                    <span class="{DC[draft.difficulty]}">{DL[draft.difficulty]}</span>
                  </div>
                  <div class="draft-q">{draft.question}</div>
                  <div class="draft-a">{draft.answer}</div>
                  {#if draft.hint}<div class="draft-hint"><i class="fa-solid fa-lightbulb"></i> {draft.hint}</div>{/if}
                  <div class="draft-btns">
                    <button class="btn btn-err btn-sm" onclick={() => rejectDraft(draft)}>
                      <i class="fa-solid fa-xmark"></i> Ablehnen
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick={() => startEditDraft(draft)}>
                      <i class="fa-solid fa-pen"></i> Bearbeiten
                    </button>
                    <button class="btn btn-ok btn-sm" onclick={() => approveDraft(draft)}>
                      <i class="fa-solid fa-check"></i> Freigeben
                    </button>
                  </div>
                </div>
              {/if}
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-inbox"></i>
            <p>Keine offenen Entwuerfe</p>
            <div class="empty-actions">
              <button class="btn btn-ghost btn-sm" onclick={() => section = 'documents'}>
                <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Karten generieren
              </button>
              <button class="btn btn-ghost btn-sm" onclick={() => section = 'create'}>
                <i class="fa-solid fa-plus"></i> Manuell erstellen
              </button>
            </div>
          </div>
        {/if}
      </div>

    <!-- NEUE KARTE -->
    {:else if section === 'create'}
      <div class="ws-page">
        <div class="ws-section-hd">
          <div>
            <div class="ws-section-title">Neue Karte erstellen</div>
            <div class="ws-section-sub">Karten-ID wird automatisch vergeben</div>
          </div>
        </div>
        <div class="create-form">
          <div class="form-row-2">
            <label class="field-label">Kategorie
              <select bind:value={cardForm.category_code}>
                {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
              </select>
            </label>
            <div>
              <div class="section-label">Schwierigkeit</div>
              <div class="diff-btns">
                {#each [1, 2, 3] as d}
                  <button class="diff-btn" class:diff-active={cardForm.difficulty === d}
                    data-diff={d} onclick={() => cardForm.difficulty = d}>
                    <i class="fa-solid {DI[d]}"></i> {DL[d]}
                  </button>
                {/each}
              </div>
            </div>
          </div>
          <label class="field-label">Frage<textarea bind:value={cardForm.question} rows="3" placeholder="Die Frage..."></textarea></label>
          <label class="field-label">Antwort<textarea bind:value={cardForm.answer} rows="5" placeholder="Die Antwort..."></textarea></label>
          <label class="field-label">Hinweis (optional)<input type="text" bind:value={cardForm.hint} placeholder="Kleiner Tipp..."></label>
          <div class="form-footer">
            <button class="btn btn-primary" onclick={createCard} disabled={!cardForm.question.trim() || !cardForm.answer.trim()}>
              <i class="fa-solid fa-plus"></i> Karte erstellen
            </button>
          </div>
        </div>
      </div>

    <!-- KI-GENERIERUNG (Dokument Upload) -->
    {:else if section === 'documents'}
      <div class="ws-page">
        <div class="ws-section-hd">
          <div>
            <div class="ws-section-title">KI-Kartengenerierung</div>
            <div class="ws-section-sub">Dokument hochladen -- KI generiert Lernkarten-Entwuerfe</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick={() => { showUpload = !showUpload; uploadState = 'idle' }}>
            <i class="fa-solid fa-upload"></i> Hochladen
          </button>
        </div>

        {#if showUpload}
          <div class="card-box upload-box">
            <div class="upload-hd">
              <span class="section-label" style="margin:0">Neues Dokument</span>
              <button class="ib" title="Schliessen" onclick={() => showUpload = false}><i class="fa-solid fa-xmark"></i></button>
            </div>
            {#if uploadState !== 'idle'}
              <div class="proc-banner" class:proc-uploading={uploadState === 'uploading'} class:proc-done={uploadState === 'done'} class:proc-error={uploadState === 'error'}>
                <i class="fa-solid {uploadState === 'uploading' ? 'fa-spinner fa-spin' : uploadState === 'done' ? 'fa-circle-check' : 'fa-circle-xmark'}"></i>
                <span>{uploadMsg}</span>
              </div>
            {:else}
              <div class="upload-body">
                <label class="drop-zone" class:has-file={!!uploadFile}>
                  <input type="file" accept=".txt,.md,.pdf,.docx"
                    onchange={e => { uploadFile = e.currentTarget.files[0] || null; uploadTitle = uploadFile ? uploadFile.name.replace(/\.[^.]+$/, '') : '' }}>
                  {#if uploadFile}
                    <i class="fa-solid {FT[uploadFile.name.split('.').pop()] || 'fa-file'} drop-file-icon"></i>
                    <span class="drop-file-name">{uploadFile.name}</span>
                    <span class="drop-file-size">{fmtSize(uploadFile.size)}</span>
                  {:else}
                    <i class="fa-solid fa-cloud-arrow-up drop-cloud"></i>
                    <span class="drop-hint">TXT, MD, PDF oder DOCX</span>
                    <span class="drop-hint2">Klicken oder hier ablegen</span>
                  {/if}
                </label>
                <div class="upload-fields">
                  <label class="field-label">Titel<input type="text" bind:value={uploadTitle} placeholder="Dokumenttitel..."></label>
                  <label class="field-label">Kategorie fuer Karten
                    <select bind:value={uploadCat}>
                      {#each $categories as cat}<option value={cat.code}>{cat.name}</option>{/each}
                    </select>
                  </label>
                  <label class="field-label">Karten pro Abschnitt: {cardsPerChunk}
                    <input type="range" min="1" max="6" bind:value={cardsPerChunk} class="range-input">
                  </label>
                  <label class="checkbox-label">
                    <input type="checkbox" bind:checked={autoGen}>
                    <span>KI-Generierung direkt starten</span>
                  </label>
                  {#if !$aiOnline && autoGen}
                    <div class="ai-warn-pill">
                      <i class="fa-solid fa-triangle-exclamation"></i>
                      LM Studio ist offline
                    </div>
                  {/if}
                </div>
              </div>
              <div class="upload-footer">
                <button class="btn btn-ghost" onclick={() => showUpload = false}>Abbrechen</button>
                <button class="btn btn-primary" onclick={handleUpload} disabled={!uploadFile}>
                  <i class="fa-solid fa-upload"></i> Hochladen
                </button>
              </div>
            {/if}
          </div>
        {/if}

        {#if documents.length > 0}
          <div class="docs-layout">
            <div class="docs-list-col">
              <div class="section-label">Dokumente</div>
              {#each documents as doc}
                <div class="doc-item" class:selected={selectedDoc?.id === doc.id} onclick={() => openDoc(doc)} role="button" tabindex="0" onkeydown={e => e.key === 'Enter' && openDoc(doc)}>
                  <i class="fa-solid {FT[doc.filetype] || 'fa-file'} di-icon"></i>
                  <div class="di-body">
                    <div class="di-title">{doc.title}</div>
                    <div class="di-meta">{fmtSize(doc.filesize)} -- {doc.chunk_count} Abschnitte</div>
                    {#if doc.card_count > 0}<span class="di-badge">{doc.card_count} Entwuerfe</span>{/if}
                  </div>
                  <button class="ib sm err" title="Dokument loeschen" onclick={e => { e.stopPropagation(); deleteDoc(doc) }}>
                    {#if confirmDeleteDoc === doc.id}Wirklich?{:else}<i class="fa-solid fa-trash"></i>{/if}
                  </button>
                </div>
              {/each}
            </div>

            {#if selectedDoc}
              <div class="doc-detail-col">
                <div class="doc-detail-hd">
                  <div>
                    <div class="doc-detail-title">{selectedDoc.title}</div>
                    <div class="doc-detail-meta">{chunks.length} Abschnitte</div>
                  </div>
                  <button class="btn btn-primary btn-sm" onclick={startGen}
                    disabled={genState === 'running' || !$aiOnline}>
                    {#if genState === 'running'}
                      <i class="fa-solid fa-spinner fa-spin"></i> Generiere...
                    {:else}
                      <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Karten
                    {/if}
                  </button>
                </div>

                {#if genState !== 'idle'}
                  <div class="gen-panel">
                    <div class="gen-panel-hd">
                      <i class="fa-solid fa-wand-magic-sparkles text-accent"></i>
                      <span class="gen-panel-title">KI-Generierung</span>
                      <span class="gen-status gen-{genState}">
                        <i class="fa-solid {genState === 'running' ? 'fa-spinner fa-spin' : genState === 'done' ? 'fa-check' : 'fa-xmark'}"></i>
                        {genState === 'running' ? 'Laeuft' : genState === 'done' ? 'Fertig' : 'Fehler'}
                      </span>
                    </div>
                    <div class="gen-steps">
                      {#each genSteps as step}
                        <div class="gen-step gen-step-{step.status}">
                          <div class="gen-dot">
                            <i class="fa-solid {GSTEP_ICON[step.status]}" style="color:{GSTEP_COLOR[step.status]}"></i>
                          </div>
                          <div class="gen-step-right">
                            <span class="gen-step-label">{step.label}</span>
                            {#if step.status === 'running'}
                              <div class="gen-step-bar"><div class="gen-step-fill"></div></div>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                    {#if genSummary}
                      <div class="gen-result">
                        <span class="text-ok"><i class="fa-solid fa-circle-check"></i> {genSummary.created} Entwuerfe</span>
                        <span class="text-2"><i class="fa-solid fa-layer-group"></i> {genSummary.chunks_processed} Abschnitte</span>
                      </div>
                    {/if}
                  </div>
                {/if}

                <div class="chunks-col">
                  {#each chunks as chunk}
                    <div class="chunk-item"
                      class:selected={selectedChunks.has(chunk.id)}
                      class:done={chunk.processed}
                      onclick={() => toggleChunk(chunk.id)}
                      onkeydown={e => (e.key === 'Enter' || e.key === ' ') && toggleChunk(chunk.id)}
                      role="button" tabindex="0">
                      <input type="checkbox" checked={selectedChunks.has(chunk.id)}
                        onchange={() => toggleChunk(chunk.id)} onclick={e => e.stopPropagation()}>
                      <div class="chunk-body">
                        <div class="chunk-meta">
                          <span class="chunk-idx">#{chunk.chunk_index + 1}</span>
                          {#if chunk.processed}
                            <span class="chunk-done"><i class="fa-solid fa-check"></i> verarbeitet</span>
                          {/if}
                        </div>
                        <div class="chunk-text markdown">{@html marked(chunk.text)}</div>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {:else}
              <div class="doc-detail-col doc-detail-empty">
                <i class="fa-solid fa-file-lines"></i>
                <p>Dokument auswaehlen</p>
              </div>
            {/if}
          </div>
        {:else if !showUpload}
          <div class="empty-state">
            <i class="fa-solid fa-file-circle-plus"></i>
            <p>Noch keine Dokumente -- lade eins hoch fuer die KI-Generierung</p>
          </div>
        {/if}
      </div>

    <!-- MC-OPTIONEN -->
    {:else if section === 'mc'}
      <div class="ws-page">
        <div class="ws-section-hd">
          <div>
            <div class="ws-section-title">Multiple-Choice Optionen</div>
            <div class="ws-section-sub">KI-generierte Antwortoptionen pruefen und verwalten</div>
          </div>
          <div class="ws-section-actions">
            <button class="btn btn-primary btn-sm" onclick={generateMcBatch}
              disabled={mcGenRunning || !$aiOnline}>
              {#if mcGenRunning}
                <i class="fa-solid fa-spinner fa-spin"></i> Generiere...
              {:else}
                <i class="fa-solid fa-wand-magic-sparkles"></i> Batch generieren
              {/if}
            </button>
          </div>
        </div>

        {#if mcStatus}
          <div class="mc-status">
            <span class="mc-stat"><i class="fa-solid fa-layer-group"></i> {mcStatus.total} Karten</span>
            <span class="mc-stat mc-stat-ok"><i class="fa-solid fa-check"></i> {mcStatus.cached} mit MC</span>
            <span class="mc-stat mc-stat-miss"><i class="fa-solid fa-circle-exclamation"></i> {mcStatus.missing} fehlen</span>
          </div>
        {/if}

        {#if mcLoading}
          <div class="list-loading"><i class="fa-solid fa-spinner fa-spin text-accent"></i></div>
        {:else if mcCards.length > 0}
          <div class="mc-grid">
            <div class="mc-list">
              {#each mcCards as mc (mc.card_id)}
                <button class="mc-item" class:selected={selectedMcCard?.card_id === mc.card_id}
                  onclick={() => selectedMcCard = mc}>
                  <div class="mc-item-id mono">{mc.card_id}</div>
                  <div class="mc-item-q">{mc.question}</div>
                  <div class="mc-item-count">{mc.options?.length || 0} Optionen</div>
                </button>
              {/each}
            </div>
            <div class="mc-detail">
              {#if selectedMcCard}
                <div class="mc-detail-hd">
                  <span class="mono">{selectedMcCard.card_id}</span>
                  <div class="mc-detail-actions">
                    <button class="ib" title="Neu generieren" onclick={() => regenerateMc(selectedMcCard.card_id)}>
                      <i class="fa-solid fa-rotate"></i>
                    </button>
                    <button class="ib err" title="Entfernen" onclick={() => deleteMcOption(selectedMcCard.card_id)}>
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </div>
                </div>
                <div class="mc-question">{selectedMcCard.question}</div>
                <div class="mc-correct">
                  <i class="fa-solid fa-check text-ok"></i> {selectedMcCard.answer}
                </div>
                <div class="section-label" style="margin-top:12px">Falsche Optionen</div>
                <div class="mc-options">
                  {#each (selectedMcCard.options || []) as opt, i}
                    <div class="mc-opt">
                      <span class="mc-opt-num">{i + 1}</span>
                      <span>{opt}</span>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="empty-state">
                  <i class="fa-solid fa-list-check"></i>
                  <p>Karte auswaehlen</p>
                </div>
              {/if}
            </div>
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-list-check"></i>
            <p>Keine MC-Optionen vorhanden</p>
            {#if $aiOnline}
              <button class="btn btn-primary btn-sm" onclick={generateMcBatch} style="margin-top:12px">
                <i class="fa-solid fa-wand-magic-sparkles"></i> Jetzt generieren
              </button>
            {/if}
          </div>
        {/if}
      </div>

    <!-- IMPORT -->
    {:else if section === 'import'}
      <ImportTab {pkg} />
    {/if}
  </div>
</div>

<style>
/* ── Wrapper ──────────────────────────────────────────────────── */
.ws-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

/* ── Sub-Navigation ───────────────────────────────────────────── */
.ws-nav {
  display: flex;
  gap: 2px;
  padding: 8px 16px;
  background: var(--bg1);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.ws-nav::-webkit-scrollbar { display: none; }
.ws-nav-btn {
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  border: 1px solid transparent;
  background: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all .15s;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  white-space: nowrap;
}
.ws-nav-btn:hover { color: var(--text0); background: var(--bg2); }
.ws-nav-btn.active { color: var(--accent); border-color: var(--accent); background: var(--glow); }
.ws-badge {
  font-size: 9px;
  font-weight: 700;
  background: var(--warn);
  color: #fff;
  border-radius: 4px;
  padding: 1px 5px;
}

/* ── Body ─────────────────────────────────────────────────────── */
.ws-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.ws-page {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  max-width: 1200px;
  width: 100%;
}

/* ── Section Header ───────────────────────────────────────────── */
.ws-section-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.ws-section-title { font-size: 14px; font-weight: 700; color: var(--text0); }
.ws-section-sub { font-size: 11px; color: var(--text2); margin-top: 2px; }
.ws-section-actions { display: flex; gap: 8px; }

/* ── Entwuerfe ────────────────────────────────────────────────── */
.drafts-list { display: flex; flex-direction: column; gap: 8px; max-width: 700px; }

.draft-card { margin-bottom: 0; }
.draft-card-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.draft-cat { font-size: 11px; font-weight: 700; letter-spacing: .06em; }
.draft-src { font-size: 10px; color: var(--text3); font-weight: 400; margin-left: 6px; }
.draft-q { font-size: 14px; font-weight: 600; color: var(--text0); margin-bottom: 8px; line-height: 1.5; }
.draft-a { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text1); background: var(--bg2); border-radius: 4px; padding: 9px 12px; white-space: pre-wrap; margin-bottom: 8px; line-height: 1.6; }
.draft-hint { font-size: 11px; color: var(--text2); margin-bottom: 8px; display: flex; align-items: center; gap: 5px; }
.draft-hint i { color: var(--warn); }
.draft-btns { display: flex; gap: 8px; justify-content: flex-end; }

.draft-edit { display: flex; flex-direction: column; gap: 10px; max-width: 700px; }
.draft-edit-title { font-size: 13px; font-weight: 600; color: var(--text0); display: flex; align-items: center; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.draft-edit-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.draft-edit-footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border); }

/* ── Neue Karte ───────────────────────────────────────────────── */
.create-form { display: flex; flex-direction: column; gap: 12px; max-width: 700px; }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 14px; border-top: 1px solid var(--border); margin-top: 4px; }
.diff-btns { display: flex; gap: 8px; }
.diff-btn {
  padding: 5px 13px; border-radius: 4px; font-size: 11px; font-weight: 600;
  border: 1px solid var(--border); background: transparent; color: var(--text2);
  cursor: pointer; transition: all .15s; display: flex; align-items: center; gap: 5px; font-family: inherit;
}
.diff-btn[data-diff="1"].diff-active { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 12%, transparent); }
.diff-btn[data-diff="2"].diff-active { border-color: var(--warn); color: var(--warn); background: color-mix(in srgb, var(--warn) 12%, transparent); }
.diff-btn[data-diff="3"].diff-active { border-color: var(--err); color: var(--err); background: color-mix(in srgb, var(--err) 12%, transparent); }

/* ── Upload ───────────────────────────────────────────────────── */
.upload-box { margin-bottom: 20px; }
.upload-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.upload-body { display: grid; grid-template-columns: 180px 1fr; gap: 18px; margin-bottom: 12px; }
.upload-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 12px; border-top: 1px solid var(--border); margin-top: 4px; }
.upload-fields { display: flex; flex-direction: column; gap: 10px; }
.drop-zone {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  border: 2px dashed var(--border); border-radius: 4px; padding: 20px 12px;
  cursor: pointer; transition: all .2s; text-align: center; gap: 6px; min-height: 150px;
}
.drop-zone:hover, .drop-zone.has-file { border-color: var(--accent); background: var(--glow); }
.drop-zone input { display: none; }
.drop-cloud { font-size: 32px; color: var(--accent); opacity: .6; }
.drop-file-icon { font-size: 28px; color: var(--accent); }
.drop-file-name { font-size: 12px; font-weight: 600; color: var(--text0); }
.drop-file-size { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.drop-hint { font-size: 12px; color: var(--text2); }
.drop-hint2 { font-size: 10px; color: var(--text3); }
.proc-banner { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 4px; font-size: 13px; font-weight: 500; }
.proc-uploading { background: var(--glow); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); }
.proc-done { background: var(--glowok); color: var(--ok); border: 1px solid color-mix(in srgb, var(--ok) 35%, transparent); }
.proc-error { background: color-mix(in srgb, var(--err) 10%, transparent); color: var(--err); border: 1px solid color-mix(in srgb, var(--err) 35%, transparent); }
.ai-warn-pill { font-size: 11px; color: var(--warn); background: color-mix(in srgb, var(--warn) 10%, transparent); padding: 7px 12px; border-radius: 4px; border: 1px solid color-mix(in srgb, var(--warn) 35%, transparent); display: flex; align-items: center; gap: 7px; }

/* ── Docs Layout ──────────────────────────────────────────────── */
.docs-layout { display: grid; grid-template-columns: 240px 1fr; gap: 16px; margin-top: 8px; }
.docs-list-col { display: flex; flex-direction: column; gap: 3px; }
.doc-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; transition: all .12s; width: 100%; text-align: left; background: none; font-family: inherit; }
.doc-item:hover { background: var(--bg2); }
.doc-item.selected { background: var(--glow); border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.di-icon { font-size: 18px; color: var(--accent); flex-shrink: 0; }
.di-body { flex: 1; }
.di-title { font-size: 12px; font-weight: 600; color: var(--text1); }
.di-meta { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.di-badge { font-size: 10px; color: var(--ac3); }

.doc-detail-col { background: var(--bg1); border: 1px solid var(--border); border-radius: 4px; padding: 14px; display: flex; flex-direction: column; gap: 10px; min-height: 300px; overflow-y: auto; }
.doc-detail-empty { align-items: center; justify-content: center; }
.doc-detail-empty i { font-size: 32px; opacity: .2; color: var(--text3); }
.doc-detail-empty p { font-size: 13px; color: var(--text3); }
.doc-detail-hd { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.doc-detail-title { font-size: 13px; font-weight: 700; color: var(--text0); }
.doc-detail-meta { font-size: 10px; color: var(--text2); margin-top: 1px; }

/* ── KI Prozess ───────────────────────────────────────────────── */
.gen-panel { background: var(--bg2); border: 1px solid var(--border); border-radius: 4px; padding: 12px; flex-shrink: 0; }
.gen-panel-hd { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.gen-panel-title { font-size: 12px; font-weight: 600; color: var(--text1); flex: 1; }
.gen-status { display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; }
.gen-running { color: var(--accent); background: var(--glow); }
.gen-done { color: var(--ok); background: var(--glowok); }
.gen-error { color: var(--err); background: color-mix(in srgb, var(--err) 10%, transparent); }
.gen-steps { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.gen-step { display: flex; align-items: flex-start; gap: 10px; padding: 3px 0; }
.gen-step-pending { opacity: .3; }
.gen-step-done { opacity: .65; }
.gen-step-running, .gen-step-error { opacity: 1; }
.gen-dot { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid var(--border); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }
.gen-step-running .gen-dot { border-color: var(--accent); }
.gen-step-done .gen-dot { border-color: var(--ok); background: var(--ok); }
.gen-step-done .gen-dot i { color: #fff !important; }
.gen-step-error .gen-dot { border-color: var(--err); background: var(--err); }
.gen-step-error .gen-dot i { color: #fff !important; }
.gen-step-right { flex: 1; display: flex; flex-direction: column; gap: 3px; }
.gen-step-label { font-size: 12px; color: var(--text1); }
.gen-step-bar { height: 2px; background: var(--bg3); border-radius: 1px; overflow: hidden; }
.gen-step-fill { height: 100%; background: var(--accent); animation: scan 1.8s ease-in-out infinite; }
@keyframes scan { 0% { transform: translateX(-100%); } 100% { transform: translateX(400%); } }
.gen-result { display: flex; align-items: center; gap: 12px; font-size: 12px; font-weight: 500; flex-wrap: wrap; padding-top: 8px; border-top: 1px solid var(--border); }

/* ── Chunks ───────────────────────────────────────────────────── */
.chunks-col { display: flex; flex-direction: column; gap: 4px; overflow-y: auto; flex: 1; }
.chunk-item { display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; transition: all .12s; }
.chunk-item:hover { background: var(--bg2); }
.chunk-item.selected { background: var(--glow); border-color: color-mix(in srgb, var(--accent) 35%, transparent); }
.chunk-item.done { opacity: .5; }
.chunk-item input { flex-shrink: 0; margin-top: 2px; }
.chunk-body { flex: 1; }
.chunk-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.chunk-idx { font-size: 9px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.chunk-done { font-size: 9px; color: var(--ok); }
.chunk-text { font-size: 11px; color: var(--text2); line-height: 1.5; }

/* ── MC-Optionen ──────────────────────────────────────────────── */
.mc-status { display: flex; gap: 14px; margin-bottom: 16px; }
.mc-stat { font-size: 12px; font-weight: 600; color: var(--text2); display: flex; align-items: center; gap: 5px; }
.mc-stat-ok { color: var(--ok); }
.mc-stat-miss { color: var(--warn); }

.mc-grid { display: grid; grid-template-columns: 300px 1fr; gap: 16px; }
.mc-list { display: flex; flex-direction: column; gap: 3px; overflow-y: auto; max-height: 600px; }
.mc-item {
  display: block; width: 100%; padding: 9px 10px; border-radius: 4px; text-align: left;
  cursor: pointer; transition: background .12s; border: 1px solid var(--border);
  background: var(--bg1); font-family: inherit;
}
.mc-item:hover { background: var(--bg2); border-color: var(--text3); }
.mc-item.selected { background: var(--bg2); border-color: var(--accent); }
.mc-item-id { font-size: 9px; color: var(--text3); letter-spacing: .06em; margin-bottom: 2px; }
.mc-item-q { font-size: 11px; color: var(--text1); line-height: 1.4; margin-bottom: 3px; }
.mc-item-count { font-size: 9px; color: var(--text3); }

.mc-detail { background: var(--bg1); border: 1px solid var(--border); border-radius: 4px; padding: 16px; }
.mc-detail-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.mc-detail-actions { display: flex; gap: 6px; }
.mc-question { font-size: 14px; font-weight: 600; color: var(--text0); margin-bottom: 10px; line-height: 1.5; }
.mc-correct { font-size: 12px; color: var(--ok); background: var(--glowok); border-radius: 4px; padding: 8px 12px; display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.mc-options { display: flex; flex-direction: column; gap: 4px; }
.mc-opt { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: var(--text1); padding: 6px 10px; background: var(--bg2); border-radius: 4px; }
.mc-opt-num { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; min-width: 16px; }

/* ── Empty State ──────────────────────────────────────────────── */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 20px; gap: 8px; }
.empty-state i { font-size: 36px; color: var(--text3); opacity: .3; }
.empty-state p { font-size: 13px; color: var(--text3); }
.empty-actions { display: flex; gap: 8px; margin-top: 8px; }

/* ── Hilfklassen ──────────────────────────────────────────────── */
.text-accent { color: var(--accent); }
.text-ok { color: var(--ok); }
.text-2 { color: var(--text2); }
.list-loading { padding: 24px; text-align: center; color: var(--accent); font-size: 18px; }

.ib { width: 28px; height: 28px; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--text2); font-size: 12px; transition: all .15s; background: none; border: none; cursor: pointer; }
.ib:hover { background: var(--bg2); color: var(--text0); }
.ib.sm { width: 24px; height: 24px; font-size: 11px; }
.ib.err:hover { background: var(--err); color: #fff; }
</style>
