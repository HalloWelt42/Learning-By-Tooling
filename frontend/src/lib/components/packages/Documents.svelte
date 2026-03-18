<script>
  /**
   * Documents.svelte -- Dokument-Upload -> Chunking -> KI -> Draft-Review
   * Alle KI-Prozesse vollständig visualisiert
   */
  import { onMount }  from 'svelte'
  import { marked } from 'marked'
  marked.setOptions({ breaks: true, gfm: true })
  import { categories, aiOnline, showToast, loadGlobal } from '../../stores/index.js'
  import { API, apiGet, apiDelete, apiPost, apiPut, apiUpload } from '../../utils/api.js'

  // ── State ─────────────────────────────────────────────────
  let documents    = $state([])
  let selectedDoc  = $state(null)
  let chunks       = $state([])
  let drafts       = $state([])
  let view         = $state('list')  // list | detail | review

  // Upload
  let uploadFile     = $state(null)
  let uploadTitle    = $state('')
  let uploadCategory = $state('GB')
  let cardsPerChunk  = $state(3)
  let autoGenerate   = $state(true)
  let showUpload     = $state(false)

  // Process states -- jeder hat eigenen Status für Visualisierung
  let uploadState  = $state('idle')  // idle | uploading | done | error
  let uploadMsg    = $state('')
  let genState     = $state('idle')  // idle | running | done | error
  let genSteps     = $state([])      // [{label, status: pending|running|done|error}]
  let genSummary   = $state(null)    // {created, errors, chunks_processed}

  let confirmDeleteDoc = $state(null)

  // Draft editing
  let editDraft    = $state(null)
  let editForm     = $state({})
  let selectedChunks = $state(new Set())

  // Derived
  let pending  = $derived(drafts.filter(d => d.status === 'pending'))
  let approved = $derived(drafts.filter(d => d.status === 'approved'))
  let allSel   = $derived(chunks.length > 0 && selectedChunks.size === chunks.length)

  onMount(loadDocs)

  async function loadDocs() {
    documents = await apiGet('/api/documents').catch(() => [])
  }

  async function openDocument(doc) {
    selectedDoc = doc
    view = 'detail'
    genState = 'idle'
    genSummary = null
    selectedChunks = new Set()
    const data = await apiGet(`/api/documents/${doc.id}/chunks`).catch(() => null)
    if (data) {
      chunks = data.chunks
      await loadDrafts()
    }
  }

  async function loadDrafts() {
    if (!selectedDoc) return
    const [p, a, r] = await Promise.all([
      apiGet(`/api/documents/${selectedDoc.id}/drafts?status=pending`).catch(()=>[]),
      apiGet(`/api/documents/${selectedDoc.id}/drafts?status=approved`).catch(()=>[]),
      apiGet(`/api/documents/${selectedDoc.id}/drafts?status=rejected`).catch(()=>[]),
    ])
    drafts = [...p, ...a, ...r]
  }

  // ── Upload ────────────────────────────────────────────────
  async function handleUpload() {
    if (!uploadFile) { showToast('Bitte eine Datei auswählen', 'error'); return }

    uploadState = 'uploading'
    uploadMsg   = 'Datei wird hochgeladen…'

    try {
      const fd = new FormData()
      fd.append('file',     uploadFile)
      fd.append('title',    uploadTitle || uploadFile.name.replace(/\.[^.]+$/, ''))
      fd.append('category', uploadCategory)

      const result = await apiUpload('/api/documents/upload', fd)

      uploadMsg   = `"${result.title}" -- ${result.chunk_count} Abschnitte erkannt`
      uploadState = 'done'

      await loadDocs()
      showUpload = false
      uploadFile = null
      uploadTitle = ''

      // Dokument öffnen
      const docs = await apiGet('/api/documents').catch(()=>[])
      const doc  = docs.find(d => d.id === result.document_id) || docs[0]
      if (doc) {
        await openDocument(doc)
        if (autoGenerate && $aiOnline) {
          await startGeneration(doc.id)
        }
      }
    } catch(e) {
      uploadState = 'error'
      uploadMsg   = e.message
      showToast(`Upload fehlgeschlagen: ${e.message}`, 'error')
    }
  }

  // ── KI-Generierung mit vollständiger Step-Visualisierung ──
  async function startGeneration(docId) {
    if (!$aiOnline) { showToast('LM Studio ist offline', 'error'); return }

    const targetId = docId || selectedDoc?.id
    if (!targetId) return

    const chunkCount = selectedChunks.size > 0
      ? selectedChunks.size
      : chunks.filter(c => !c.processed).length

    // Schritte definieren
    genSteps = [
      { label: 'Abschnitte vorbereiten',        status: 'running' },
      { label: `${chunkCount} Abschnitte senden`, status: 'pending' },
      { label: 'KI generiert Fragen + Antworten', status: 'pending' },
      { label: 'Entwürfe speichern',             status: 'pending' },
    ]
    genState   = 'running'
    genSummary = null

    // Schritt 1 done
    await tick(400)
    genSteps = genSteps.map((s,i) => i===0 ? {...s, status:'done'} : i===1 ? {...s, status:'running'} : s)
    await tick(300)
    genSteps = genSteps.map((s,i) => i===1 ? {...s, status:'done'} : i===2 ? {...s, status:'running'} : s)

    try {
      const body = {
        category:        uploadCategory || 'GB',
        cards_per_chunk: cardsPerChunk,
        chunk_ids:       selectedChunks.size > 0 ? [...selectedChunks] : null,
      }
      const result = await apiPost(`/api/documents/${targetId}/generate`, body)

      genSteps = genSteps.map((s,i) => i===2 ? {...s, status:'done'} : i===3 ? {...s, status:'running'} : s)
      await tick(300)
      genSteps = genSteps.map(s => ({...s, status:'done'}))

      genSummary = result
      genState   = 'done'

      await loadDrafts()
      await loadDocs()
      await loadGlobal()
      selectedChunks = new Set()

      if (result.created > 0) {
        showToast(`${result.created} Karten-Entwürfe erstellt`, 'success')
      } else {
        showToast('Keine Karten generiert -- KI-Antwort prüfen', 'warn')
      }
    } catch(e) {
      genSteps = genSteps.map(s => s.status === 'running' ? {...s, status:'error'} : s)
      genState = 'error'
      showToast(`Generierung fehlgeschlagen: ${e.message}`, 'error')
    }
  }

  function tick(ms) { return new Promise(r => setTimeout(r, ms)) }

  // ── Draft Actions ─────────────────────────────────────────
  async function approveDraft(d) {
    await apiPut(`/api/drafts/${d.id}`, { action: 'approve' }).catch(()=>{})
    await loadDrafts(); await loadGlobal()
    showToast('Karte freigegeben', 'success')
  }

  async function rejectDraft(d) {
    await apiPut(`/api/drafts/${d.id}`, { action: 'reject' }).catch(()=>{})
    await loadDrafts()
  }

  function startEdit(d) {
    editDraft = d
    editForm  = { question: d.question, answer: d.answer, hint: d.hint||'', difficulty: d.difficulty, category_code: d.category_code }
  }

  async function saveEdit() {
    await apiPut(`/api/drafts/${editDraft.id}`, { action:'edit', ...editForm, difficulty: Number(editForm.difficulty) }).catch(()=>{})
    editDraft = null
    await loadDrafts(); await loadGlobal()
    showToast('Karte bearbeitet und freigegeben', 'success')
  }

  async function approveAll() {
    const list = [...pending]
    for (const d of list) await apiPut(`/api/drafts/${d.id}`, { action:'approve' }).catch(()=>{})
    await loadDrafts(); await loadGlobal()
    showToast(`${list.length} Karten freigegeben`, 'success')
  }

  async function deleteDoc(doc) {
    if (confirmDeleteDoc !== doc.id) {
      confirmDeleteDoc = doc.id
      setTimeout(() => confirmDeleteDoc = null, 3000)
      return
    }
    confirmDeleteDoc = null
    await apiDelete(`/api/documents/${doc.id}`).catch(()=>{})
    await loadDocs()
    if (selectedDoc?.id === doc.id) { selectedDoc=null; view='list' }
    showToast('Dokument gelöscht', 'info')
  }

  function toggleChunk(id) {
    const s = new Set(selectedChunks)
    s.has(id) ? s.delete(id) : s.add(id)
    selectedChunks = s
  }
  function toggleAll() {
    selectedChunks = allSel ? new Set() : new Set(chunks.map(c=>c.id))
  }

  function ftIcon(t) { return {pdf:'fa-file-pdf',md:'fa-file-code',txt:'fa-file-lines',docx:'fa-file-word'}[t]||'fa-file' }
  function fmtSize(b) { return b<1024?`${b}B`:b<1048576?`${(b/1024).toFixed(1)}KB`:`${(b/1048576).toFixed(1)}MB` }
  function diffLbl(d) { return ['','Leicht','Mittel','Schwer'][d]||'Mittel' }
  function diffCls(d) { return ['','d1','d2','d3'][d]||'d2' }

  const statusIcon = { done:'fa-check', running:'fa-spinner fa-spin', pending:'fa-circle', error:'fa-xmark' }
  const statusColor= { done:'var(--ok)', running:'var(--accent)', pending:'var(--text3)', error:'var(--err)' }
</script>

<!-- ─── LIST VIEW ──────────────────────────────────────────── -->
{#if view === 'list'}
<div class="page">
  <div class="page-hd">
    <div>
      <h1 class="page-title">
        <i class="fa-solid fa-file-lines"></i> Dokumente
      </h1>
      <p class="page-sub">Dokument hochladen -> KI generiert Lernkarten-Entwürfe</p>
    </div>
    <button class="btn btn-primary" onclick={() => { showUpload = !showUpload; uploadState='idle' }}>
      <i class="fa-solid fa-upload"></i> Hochladen
    </button>
  </div>

  <!-- ── Upload Panel ─────────────────────────────────────── -->
  {#if showUpload}
    <div class="upload-panel card-box">
      <div class="up-header">
        <span class="section-label" style="margin:0">Neues Dokument</span>
        <button class="icon-btn" onclick={() => showUpload=false}>
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Process indicator wenn aktiv -->
      {#if uploadState !== 'idle'}
        <div class="proc-banner proc-{uploadState}">
          <i class="fa-solid {uploadState==='uploading'?'fa-spinner fa-spin':uploadState==='done'?'fa-circle-check':'fa-circle-xmark'}"></i>
          <span>{uploadMsg}</span>
        </div>
      {:else}
        <div class="up-body">
          <label class="drop-zone" class:has-file={!!uploadFile}>
            <input type="file" accept=".txt,.md,.pdf,.docx"
              onchange={e => { uploadFile=e.currentTarget.files[0]||null; uploadTitle=uploadFile?uploadFile.name.replace(/\.[^.]+$/,''):'' }} />
            {#if uploadFile}
              <i class="fa-solid {ftIcon(uploadFile.name.split('.').pop())} drop-icon-file"></i>
              <span class="drop-fname">{uploadFile.name}</span>
              <span class="drop-fsize">{fmtSize(uploadFile.size)}</span>
            {:else}
              <i class="fa-solid fa-cloud-arrow-up drop-icon"></i>
              <span class="drop-hint">TXT, MD, PDF oder DOCX hier ablegen</span>
              <span class="drop-hint2">oder klicken zum Auswählen</span>
            {/if}
          </label>

          <div class="up-fields">
            <label>
              <span>Titel</span>
              <input type="text" bind:value={uploadTitle} placeholder="Dokumenttitel (optional)…" />
            </label>
            <label>
              <span>Kategorie für Karten</span>
              <select bind:value={uploadCategory}>
                {#each $categories as cat (cat.code)}
                  <option value={cat.code}>{cat.icon} {cat.name}</option>
                {/each}
              </select>
            </label>
            <label>
              <span>Karten pro Abschnitt: <strong>{cardsPerChunk}</strong></span>
              <input type="range" min="1" max="6" bind:value={cardsPerChunk}
                     style="width:100%;accent-color:var(--accent)" />
            </label>
            <label class="check-row">
              <input type="checkbox" bind:checked={autoGenerate} />
              <span>KI-Generierung direkt nach Upload starten</span>
            </label>
            {#if !$aiOnline && autoGenerate}
              <div class="ai-warn">
                <i class="fa-solid fa-triangle-exclamation"></i>
                LM Studio ist offline -- Generierung nicht möglich
              </div>
            {/if}
          </div>
        </div>

        <div class="up-footer">
          <button class="btn btn-ghost" onclick={() => showUpload=false}>Abbrechen</button>
          <button class="btn btn-primary" onclick={handleUpload} disabled={!uploadFile}>
            <i class="fa-solid fa-upload"></i> Hochladen
          </button>
        </div>
      {/if}
    </div>
  {/if}

  <!-- ── Document Grid ─────────────────────────────────────── -->
  {#if documents.length === 0}
    <div class="empty-state">
      <i class="fa-solid fa-file-circle-plus"></i>
      <p>Noch keine Dokumente. Lade dein erstes hoch.</p>
    </div>
  {:else}
    <div class="doc-grid">
      {#each documents as doc (doc.id)}
        <div class="doc-card">
          <div class="dc-left">
            <i class="fa-solid {ftIcon(doc.filetype)} dc-ficon"></i>
          </div>
          <div class="dc-body">
            <div class="dc-title">{doc.title}</div>
            <div class="dc-meta">
              <span class="dc-badge">{doc.filetype.toUpperCase()}</span>
              <span>{fmtSize(doc.filesize)}</span>
              <span><i class="fa-solid fa-layer-group"></i> {doc.chunk_count}</span>
              {#if doc.card_count > 0}
                <span class="dc-badge ok">
                  <i class="fa-solid fa-cards-blank"></i> {doc.card_count} Entwürfe
                </span>
              {/if}
            </div>
          </div>
          <div class="dc-actions">
            <button class="btn btn-ghost btn-sm" onclick={() => openDocument(doc)}>
              <i class="fa-solid fa-folder-open"></i> Öffnen
            </button>
            <button class="icon-btn err" onclick={() => deleteDoc(doc)}>
              {#if confirmDeleteDoc === doc.id}
                Wirklich?
              {:else}
                <i class="fa-solid fa-trash"></i>
              {/if}
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- ─── DETAIL VIEW ────────────────────────────────────────── -->
{:else if view === 'detail' && selectedDoc}
<div class="page">
  <div class="page-hd">
    <div>
      <button class="back-btn" onclick={() => { view='list'; selectedDoc=null }}>
        <i class="fa-solid fa-arrow-left"></i> Zurück
      </button>
      <h1 class="page-title" style="font-size:19px;margin-top:8px">
        <i class="fa-solid {ftIcon(selectedDoc.filetype)}"></i> {selectedDoc.title}
      </h1>
      <p class="page-sub">
        {selectedDoc.chunk_count} Abschnitte ·
        {selectedDoc.card_count} Entwürfe generiert
      </p>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-shrink:0">
      <button class="btn btn-ghost" onclick={() => view='read'}>
        <i class="fa-solid fa-book-open"></i> Lesen
      </button>
      {#if pending.length > 0}
        <button class="btn btn-ghost" onclick={() => view='review'}>
          <i class="fa-solid fa-list-check"></i> Prüfen ({pending.length})
        </button>
      {/if}
      <button class="btn btn-primary"
        onclick={() => startGeneration(selectedDoc.id)}
        disabled={genState==='running' || !$aiOnline}
      >
        {#if genState === 'running'}
          <i class="fa-solid fa-spinner fa-spin"></i> Generiere…
        {:else}
          <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Karten generieren
        {/if}
      </button>
    </div>
  </div>

  <!-- ── KI-Prozess Visualisierung ──────────────────────────── -->
  {#if genState !== 'idle'}
    <div class="gen-process card-box">
      <div class="gp-header">
        <i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent)"></i>
        <span class="section-label" style="margin:0">KI-Generierung</span>
        {#if genState === 'done'}
          <span class="gp-status ok">
            <i class="fa-solid fa-circle-check"></i> Abgeschlossen
          </span>
        {:else if genState === 'error'}
          <span class="gp-status err">
            <i class="fa-solid fa-circle-xmark"></i> Fehler
          </span>
        {:else}
          <span class="gp-status running">
            <i class="fa-solid fa-spinner fa-spin"></i> Läuft…
          </span>
        {/if}
      </div>

      <div class="gp-steps">
        {#each genSteps as step, i}
          <div class="gp-step gp-step--{step.status}">
            <div class="gp-dot">
              <i class="fa-solid {statusIcon[step.status]}"
                 style="color:{statusColor[step.status]};font-size:{step.status==='running'?'11px':'10px'}"></i>
            </div>
            <div class="gp-line-wrap">
              <div class="gp-step-label">{step.label}</div>
              {#if step.status === 'running'}
                <div class="gp-step-bar"><div class="gp-step-fill"></div></div>
              {/if}
            </div>
          </div>
        {/each}
      </div>

      {#if genSummary}
        <div class="gen-result">
          <div class="gr-item ok">
            <i class="fa-solid fa-circle-check"></i>
            <strong>{genSummary.created}</strong> Entwürfe erstellt
          </div>
          <div class="gr-item muted">
            <i class="fa-solid fa-layer-group"></i>
            {genSummary.chunks_processed} Abschnitte verarbeitet
          </div>
          {#if genSummary.errors > 0}
            <div class="gr-item warn">
              <i class="fa-solid fa-triangle-exclamation"></i>
              {genSummary.errors} Fehler
            </div>
          {/if}
          {#if genSummary.created > 0}
            <button class="btn btn-ok btn-sm" onclick={() => view='review'} style="margin-left:auto">
              <i class="fa-solid fa-list-check"></i> Jetzt prüfen
            </button>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <!-- ── Gen Options ────────────────────────────────────────── -->
  <div class="gen-opts card-box">
    <div class="go-row">
      <label class="go-field">
        <span>Kategorie</span>
        <select bind:value={uploadCategory} style="width:auto">
          {#each $categories as cat (cat.code)}
            <option value={cat.code}>{cat.icon} {cat.name}</option>
          {/each}
        </select>
      </label>
      <label class="go-field">
        <span>Karten pro Abschnitt: <strong>{cardsPerChunk}</strong></span>
        <input type="range" min="1" max="6" bind:value={cardsPerChunk}
               style="width:130px;accent-color:var(--accent)" />
      </label>
      <label class="check-row" style="margin:0;align-self:flex-end">
        <input type="checkbox" checked={allSel} onchange={toggleAll} />
        <span>{allSel ? 'Alle abwählen' : 'Alle auswählen'}</span>
      </label>
      {#if selectedChunks.size > 0}
        <span style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace;align-self:flex-end">
          {selectedChunks.size} ausgewählt
        </span>
      {/if}
    </div>
  </div>

  <!-- ── Chunks ─────────────────────────────────────────────── -->
  <div class="chunks-list">
    {#each chunks as chunk (chunk.id)}
      <div class="chunk-item"
           class:selected={selectedChunks.has(chunk.id)}
           class:processed={chunk.processed}>
        <label class="chunk-check">
          <input type="checkbox" checked={selectedChunks.has(chunk.id)}
                 onchange={() => toggleChunk(chunk.id)} />
        </label>
        <div class="chunk-body">
          <div class="chunk-hd">
            <span style="font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace">
              #{chunk.chunk_index + 1}
            </span>
            {#if chunk.processed}
              <span class="micro-badge ok">
                <i class="fa-solid fa-check"></i> verarbeitet
              </span>
            {/if}
          </div>
          <div class="chunk-text markdown">{@html marked(chunk.text)}</div>
        </div>
      </div>
    {/each}
  </div>
</div>

<!-- ─── REVIEW VIEW ────────────────────────────────────────── -->
{:else if view === 'review' && selectedDoc}
<div class="page">
  <div class="page-hd">
    <div>
      <button class="back-btn" onclick={() => view='detail'}>
        <i class="fa-solid fa-arrow-left"></i> Abschnitte
      </button>
      <h1 class="page-title" style="font-size:19px;margin-top:8px">
        <i class="fa-solid fa-list-check"></i> Entwürfe prüfen
      </h1>
      <p class="page-sub">
        <span style="color:var(--warn)">{pending.length} ausstehend</span> ·
        <span style="color:var(--ok)">{approved.length} freigegeben</span>
      </p>
    </div>
    {#if pending.length > 0}
      <button class="btn btn-ok" onclick={approveAll}>
        <i class="fa-solid fa-check-double"></i> Alle freigeben ({pending.length})
      </button>
    {/if}
  </div>

  {#if pending.length === 0}
    <div class="empty-state">
      <i class="fa-solid fa-circle-check" style="color:var(--ok)"></i>
      <p>Alle Entwürfe wurden bearbeitet.</p>
      <button class="btn btn-ghost" onclick={() => view='detail'}>
        <i class="fa-solid fa-arrow-left"></i> Zurück
      </button>
    </div>
  {:else}
    <div class="drafts-list">
      {#each pending as draft (draft.id)}
        {#if editDraft?.id === draft.id}
          <!-- Edit-Modus -->
          <div class="draft-edit card-box">
            <div class="de-header">
              <span style="font-size:13px;font-weight:600;color:var(--text0)">
                <i class="fa-solid fa-pen" style="color:var(--accent);margin-right:6px"></i>
                Karte bearbeiten
              </span>
            </div>
            <label>
              <span>Frage</span>
              <textarea bind:value={editForm.question} rows="2"></textarea>
            </label>
            <label>
              <span>Antwort</span>
              <textarea bind:value={editForm.answer} rows="4"></textarea>
            </label>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <label>
                <span>Hinweis</span>
                <input type="text" bind:value={editForm.hint} />
              </label>
              <label>
                <span>Kategorie</span>
                <select bind:value={editForm.category_code}>
                  {#each $categories as cat (cat.code)}
                    <option value={cat.code}>{cat.icon} {cat.name}</option>
                  {/each}
                </select>
              </label>
            </div>
            <div class="de-footer">
              <button class="btn btn-ghost btn-sm" onclick={() => editDraft=null}>Abbrechen</button>
              <button class="btn btn-ok btn-sm" onclick={saveEdit}>
                <i class="fa-solid fa-check"></i> Speichern & freigeben
              </button>
            </div>
          </div>

        {:else}
          <!-- Review-Karte -->
          <div class="draft-card">
            <div class="dr-top">
              <span class="dr-cat"
                style="color:{$categories.find(c=>c.code===draft.category_code)?.color||'var(--accent)'}">
                {$categories.find(c=>c.code===draft.category_code)?.icon||''}
                {draft.category_code}
              </span>
              <span class="{diffCls(draft.difficulty)}" style="font-size:11px;font-weight:600">
                <i class="fa-solid {draft.difficulty===1?'fa-signal-weak':draft.difficulty===2?'fa-signal-fair':'fa-signal'}"></i>
                {diffLbl(draft.difficulty)}
              </span>
            </div>
            <div class="dr-q">{draft.question}</div>
            <div class="dr-a">{draft.answer}</div>
            {#if draft.hint}
              <div class="dr-hint">
                <i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i> {draft.hint}
              </div>
            {/if}
            <div class="dr-btns">
              <button class="btn btn-err btn-sm" onclick={() => rejectDraft(draft)}>
                <i class="fa-solid fa-xmark"></i> Ablehnen
              </button>
              <button class="btn btn-ghost btn-sm" onclick={() => startEdit(draft)}>
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
  {/if}
</div>

<!-- ─── READ VIEW (Volltext als Markdown) ─────────────────── -->
{:else if view === 'read' && selectedDoc}
<div class="page">
  <div class="page-hd">
    <div>
      <button class="back-btn" onclick={() => view='detail'}>
        <i class="fa-solid fa-arrow-left"></i> Abschnitte
      </button>
      <h1 class="page-title" style="font-size:19px;margin-top:8px">
        <i class="fa-solid fa-book-open"></i> {selectedDoc.title}
      </h1>
      <p class="page-sub">Lernmaterial -- Volltext</p>
    </div>
  </div>
  <div class="read-doc card-box markdown">
    {@html marked(chunks.map(c => c.text).join('\n\n'))}
  </div>
</div>
{/if}

<style>
/* ── Upload Panel ────────────────────────────────────── */
.upload-panel { max-width:700px; margin-bottom:24px; }
.up-header    { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.icon-btn     { width:28px;height:28px;border-radius: 4px;display:flex;align-items:center;justify-content:center;color:var(--text2);font-size:13px;transition:all .15s; }
.icon-btn:hover { background:var(--bg2);color:var(--text0); }
.icon-btn.err:hover { background:var(--err);color:#fff; }
.proc-banner { display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius: 4px;font-size:13px;font-weight:500; }
.proc-uploading { background:var(--glow);color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 40%,transparent); }
.proc-done      { background:var(--glowok);color:var(--ok);border:1px solid color-mix(in srgb,var(--ok) 40%,transparent); }
.proc-error     { background:color-mix(in srgb,var(--err) 10%,transparent);color:var(--err);border:1px solid color-mix(in srgb,var(--err) 40%,transparent); }
.up-body  { display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:16px; }
.drop-zone {
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  border:2px dashed var(--border);border-radius: 4px;padding:24px 16px;
  cursor:pointer;transition:all .2s;text-align:center;min-height:170px;gap:6px;
}
.drop-zone:hover,.drop-zone.has-file { border-color:var(--accent);background:var(--glow); }
.drop-zone input[type=file] { display:none; }
.drop-icon { font-size:36px;color:var(--accent);opacity:.6; }
.drop-icon-file { font-size:32px;color:var(--accent); }
.drop-fname { font-size:13px;font-weight:600;color:var(--text0); }
.drop-fsize { font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace; }
.drop-hint  { font-size:12px;color:var(--text2); }
.drop-hint2 { font-size:10px;color:var(--text3); }
.up-fields  { display:flex;flex-direction:column;gap:12px; }
.up-fields label { display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;color:var(--text2); }
.check-row  { flex-direction:row !important;align-items:center;gap:8px;cursor:pointer;font-size:12px !important; }
.check-row input { width:auto; }
.ai-warn    { font-size:11px;color:var(--warn);background:color-mix(in srgb,var(--warn) 10%,transparent);padding:7px 12px;border-radius: 4px;border:1px solid color-mix(in srgb,var(--warn) 40%,transparent);display:flex;align-items:center;gap:7px; }
.up-footer  { display:flex;justify-content:flex-end;gap:10px;padding-top:12px;border-top:1px solid var(--border); }

/* ── Document Grid ─────────────────────────────────── */
.doc-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px; }
.doc-card { background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:16px;display:grid;grid-template-columns:40px 1fr auto;gap:14px;align-items:center;transition:border-color .2s; }
.doc-card:hover { border-color:var(--accent); }
.dc-ficon { font-size:28px;color:var(--accent);text-align:center; }
.dc-title { font-size:14px;font-weight:600;color:var(--text0);margin-bottom:6px; }
.dc-meta  { display:flex;align-items:center;gap:8px;font-size:11px;color:var(--text2);flex-wrap:wrap; }
.dc-badge { padding:2px 7px;border-radius: 4px;background:var(--bg2);font-weight:600;letter-spacing:.04em; }
.dc-badge.ok { color:var(--ok);background:var(--glowok);border:1px solid color-mix(in srgb,var(--ok) 30%,transparent); }
.dc-actions { display:flex;flex-direction:column;gap:6px; }

/* ── KI Prozess Visualisierung ─────────────────────── */
.gen-process { margin-bottom:16px; }
.gp-header { display:flex;align-items:center;gap:10px;margin-bottom:16px; }
.gp-status { display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;margin-left:auto;padding:4px 10px;border-radius: 4px; }
.gp-status.ok      { color:var(--ok);background:var(--glowok); }
.gp-status.err     { color:var(--err);background:color-mix(in srgb,var(--err) 10%,transparent); }
.gp-status.running { color:var(--accent);background:var(--glow); }
.gp-steps  { display:flex;flex-direction:column;gap:0; }
.gp-step   { display:flex;gap:14px;padding:8px 0;position:relative;opacity:.35;transition:opacity .3s; }
.gp-step--running { opacity:1; }
.gp-step--done    { opacity:.75; }
.gp-step--error   { opacity:1; }
.gp-step:not(:last-child)::before {
  content:'';position:absolute;left:9px;top:28px;bottom:0;width:1px;background:var(--border);
}
.gp-dot { width:20px;height:20px;border-radius:50%;border:1.5px solid var(--border);display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px; }
.gp-step--running .gp-dot { border-color:var(--accent); }
.gp-step--done    .gp-dot { border-color:var(--ok);background:var(--ok); }
.gp-step--error   .gp-dot { border-color:var(--err);background:var(--err); }
.gp-step--done    .gp-dot i,.gp-step--error .gp-dot i { color:#fff !important; }
.gp-line-wrap { flex:1;display:flex;flex-direction:column;gap:4px; }
.gp-step-label { font-size:12px;font-weight:500;color:var(--text1); }
.gp-step-bar  { height:2px;background:var(--bg3);border-radius: 1px;overflow:hidden; }
.gp-step-fill { height:100%;background:var(--accent);border-radius: 1px;animation:progress-fill 2s ease-in-out infinite; }
@keyframes progress-fill { 0%{width:15%} 50%{width:75%} 100%{width:15%} }
.gen-result { display:flex;align-items:center;gap:16px;padding:12px 16px;background:var(--bg2);border-radius: 4px;margin-top:12px;flex-wrap:wrap; }
.gr-item    { display:flex;align-items:center;gap:6px;font-size:12px;font-weight:500; }
.gr-item.ok   { color:var(--ok); }
.gr-item.warn { color:var(--warn); }
.gr-item.muted{ color:var(--text2); }

/* ── Gen Options ───────────────────────────────────── */
.gen-opts  { margin-bottom:16px; }
.go-row    { display:flex;align-items:flex-end;gap:20px;flex-wrap:wrap; }
.go-field  { display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;color:var(--text2); }

/* ── Chunks ────────────────────────────────────────── */
.chunks-list { display:flex;flex-direction:column;gap:8px; }
.chunk-item  { background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:12px 16px;display:grid;grid-template-columns:24px 1fr;gap:12px;transition:border-color .15s; }
.chunk-item.selected   { border-color:var(--accent);background:var(--glow); }
.chunk-item.processed  { opacity:.55; }
.chunk-check input { width:auto; }
.chunk-hd   { display:flex;align-items:center;gap:8px;margin-bottom:5px; }
.chunk-text { font-size:12px;color:var(--text2);line-height:1.6;white-space:pre-wrap; }
.micro-badge { font-size:10px;font-weight:600;padding:1px 7px;border-radius: 3px;display:flex;align-items:center;gap:4px; }
.micro-badge.ok { color:var(--ok);background:var(--glowok); }

/* ── Drafts ────────────────────────────────────────── */
.drafts-list { display:flex;flex-direction:column;gap:12px;max-width:740px; }
.draft-card  { background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:20px; }
.dr-top      { display:flex;justify-content:space-between;align-items:center;margin-bottom:12px; }
.dr-cat      { font-size:11px;font-weight:700;letter-spacing:.06em; }
.dr-q        { font-size:15px;font-weight:600;color:var(--text0);margin-bottom:10px;line-height:1.5; }
.dr-a        { font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text1);background:var(--bg2);border-radius: 4px;padding:10px 14px;white-space:pre-wrap;margin-bottom:10px;line-height:1.6; }
.dr-hint     { font-size:11px;color:var(--text2);margin-bottom:10px;display:flex;align-items:center;gap:6px; }
.dr-btns     { display:flex;gap:8px;justify-content:flex-end; }
.draft-edit  { display:flex;flex-direction:column;gap:12px;max-width:740px; }
.draft-edit label { display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;color:var(--text2); }
.de-header   { padding-bottom:12px;border-bottom:1px solid var(--border); }
.de-footer   { display:flex;justify-content:flex-end;gap:10px;padding-top:12px;border-top:1px solid var(--border); }

/* ── Misc ──────────────────────────────────────────── */
.back-btn    { font-size:12px;color:var(--text2);display:inline-flex;align-items:center;gap:6px;transition:color .15s;padding:0; }
.back-btn:hover { color:var(--accent); }
/* ── Read View ─────────────────────────────────────── */
.read-doc { max-width:800px; font-size:14px; color:var(--text1); line-height:1.8; padding:24px 28px; }
</style>
