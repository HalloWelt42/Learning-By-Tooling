<script>
  import { categories, currentView, activePackageId, showToast, loadGlobal, aiOnline } from '../../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete, apiUpload, BASE } from '../../utils/api.js'
  import { navigate } from '../../utils/router.js'
  import { onMount } from 'svelte'
  import { marked } from 'marked'
  import Paths from './Paths.svelte'
  marked.setOptions({ breaks: true, gfm: true })

  let { pkg } = $props()

  let tab = $state('overview')

  let stats     = $state(null)
  let documents = $state([])
  let cards     = $state([])
  let drafts    = $state([])
  let lexicon   = $state([])
  let paths     = $state([])
  let materialTexts = $state([])

  let loadingCards  = $state(false)
  let searchQ       = $state('')
  let filterCat     = $state('')
  let selectedCard  = $state(null)
  let showCardForm  = $state(false)
  let editCard      = $state(null)
  let cardForm      = $state({})

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

  let editDraft     = $state(null)
  let editDForm     = $state({})

  let aiState = $state('idle')
  let aiText  = $state('')

  let showLexForm   = $state(false)
  let lexForm       = $state({ term:'', definition:'', category_code:'' })
  let showPathForm  = $state(false)
  let pathForm      = $state({ name:'', description:'', category_codes:[] })

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

  // Medien
  let media = $state([])
  async function loadMedia() {
    try { media = await apiGet(`/api/packages/${pkg.id}/media`) } catch(e) { media = [] }
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

  let confirmDeleteCard = $state(null)
  let confirmDeleteDoc  = $state(null)

  let importFragen  = $state('')
  let importAntwt   = $state('')
  let importResult  = $state(null)
  let importing     = $state(false)

  onMount(() => {
    loadAll()
    // Query-Parameter auswerten (z.B. ?tab=cards&q=K-001)
    const hash = window.location.hash
    const qIdx = hash.indexOf('?')
    if (qIdx > -1) {
      const params = new URLSearchParams(hash.substring(qIdx))
      if (params.get('tab')) tab = params.get('tab')
      if (params.get('q')) searchQ = params.get('q')
    }
  })

  async function loadAll() {
    await Promise.all([loadStats(), loadDocuments(), loadDrafts()])
  }

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
    } catch (e) {
      showToast(e.message, 'error')
    }
  }
  async function loadStats()     { stats     = await apiGet(`/api/packages/${pkg.id}/stats`).catch(()=>null) }
  async function loadDocuments() { documents = await apiGet(`/api/packages/${pkg.id}/documents`).catch(()=>[]) }
  async function loadDrafts()    { drafts    = await apiGet(`/api/packages/${pkg.id}/drafts`).catch(()=>[]) }
  async function loadCards()     {
    loadingCards = true
    const p = new URLSearchParams({ package_id: pkg.id })
    if (searchQ)   p.set('search',   searchQ)
    if (filterCat) p.set('category', filterCat)
    cards = await apiGet(`/api/cards?${p}`).catch(()=>[])
    loadingCards = false
  }
  async function loadLexicon() { lexicon = await apiGet(`/api/packages/${pkg.id}/lexicon`).catch(()=>[]) }
  async function loadPaths()   { paths   = await apiGet(`/api/packages/${pkg.id}/paths`).catch(()=>[]) }

  async function loadMaterial() {
    if (materialTexts.length > 0) return
    const result = []
    for (const doc of documents) {
      try {
        const data = await apiGet(`/api/documents/${doc.id}/chunks`)
        const fullText = data.chunks.map(c => c.text).join('\n\n')
        result.push({ id: doc.id, title: doc.title, filetype: doc.filetype, text: fullText })
      } catch(e) { /* skip */ }
    }
    materialTexts = result
  }

  $effect(() => {
    if (tab === 'cards')   loadCards()
    if (tab === 'lexicon') loadLexicon()
    if (tab === 'paths')   loadPaths()
  })

  let st
  function onSearch() { clearTimeout(st); st = setTimeout(loadCards, 280) }
  $effect(() => { filterCat; searchQ; if(tab==='cards') loadCards() })

  // ── Karten ──────────────────────────────────────────────────────────────
  function openCreate() {
    editCard = null
    cardForm = { card_id:'', package_id:pkg.id, category_code:$categories[0]?.code||'AL', question:'', answer:'', hint:'', difficulty:2 }
    selectedCard = null
    showCardForm = true
  }
  function openEdit(c) { editCard=c; cardForm={...c,hint:c.hint||''}; showCardForm=true }

  async function saveCard() {
    if (!cardForm.question || !cardForm.answer) { showToast('Frage und Antwort Pflicht','error'); return }
    try {
      if (editCard) { await apiPut(`/api/cards/${editCard.card_id}`, cardForm); showToast('Gespeichert','success') }
      else          { await apiPost('/api/cards', {...cardForm, package_id:pkg.id}); showToast('Erstellt','success') }
      showCardForm=false; selectedCard=null
      await loadCards(); await loadStats(); await loadGlobal()
    } catch(e) { showToast(e.message,'error') }
  }

  async function deleteCard(c) {
    if (confirmDeleteCard !== c.card_id) {
      confirmDeleteCard = c.card_id
      setTimeout(() => confirmDeleteCard = null, 3000)
      return
    }
    confirmDeleteCard = null
    await apiDelete(`/api/cards/${c.card_id}`)
    if (selectedCard?.card_id===c.card_id) selectedCard=null
    await loadCards(); await loadStats(); await loadGlobal()
    showToast('Gelöscht','info')
  }

  async function getAI(c) {
    aiState='loading'; aiText=''
    try { const d=await apiPost('/api/ai/explain',{card_id:c.card_id}); aiText=d.explanation; aiState='done' }
    catch { aiText='LM Studio nicht erreichbar.'; aiState='error' }
  }

  // ── Upload & KI ──────────────────────────────────────────────────────────
  async function handleUpload() {
    if (!uploadFile) { showToast('Datei auswählen','error'); return }
    uploadState='uploading'; uploadMsg='Datei wird verarbeitet...'
    try {
      const fd = new FormData()
      fd.append('file',     uploadFile)
      fd.append('title',    uploadTitle || uploadFile.name.replace(/\.[^.]+$/,''))
      fd.append('category', uploadCat)
      const r = await apiUpload(`/api/packages/${pkg.id}/documents/upload`, fd)
      uploadMsg=`${r.title} -- ${r.chunk_count} Abschnitte`; uploadState='done'
      await loadDocuments(); await loadStats(); await loadGlobal()
      showUpload=false; uploadFile=null; uploadTitle=''
      if (autoGen && $aiOnline) {
        await loadDocuments()
        const doc = documents.find(d=>d.id===r.document_id)
        if (doc) await openDoc(doc)
      }
    } catch(e) { uploadState='error'; uploadMsg=e.message; showToast(e.message,'error') }
  }

  async function openDoc(doc) {
    selectedDoc=doc
    const data = await apiGet(`/api/documents/${doc.id}/chunks`).catch(()=>null)
    if (data) chunks = data.chunks
    selectedChunks=new Set(); genState='idle'; genSummary=null
  }

  async function startGen() {
    if (!$aiOnline || !selectedDoc) return
    const cnt = selectedChunks.size>0 ? selectedChunks.size : chunks.filter(c=>!c.processed).length
    genSteps=[
      {label:'Abschnitte vorbereiten',           status:'running'},
      {label:`${cnt} Abschnitte senden`,          status:'pending'},
      {label:'KI generiert Fragen und Antworten', status:'pending'},
      {label:'Entwürfe speichern',               status:'pending'},
    ]
    genState='running'; genSummary=null
    const tick=ms=>new Promise(r=>setTimeout(r,ms))
    await tick(400)
    genSteps=genSteps.map((s,i)=>i===0?{...s,status:'done'}:i===1?{...s,status:'running'}:s)
    await tick(300)
    genSteps=genSteps.map((s,i)=>i===1?{...s,status:'done'}:i===2?{...s,status:'running'}:s)
    try {
      const r = await apiPost(`/api/documents/${selectedDoc.id}/generate`,{
        category:uploadCat||'AL', cards_per_chunk:cardsPerChunk,
        chunk_ids:selectedChunks.size>0?[...selectedChunks]:null,
      })
      genSteps=genSteps.map((s,i)=>i===2?{...s,status:'done'}:i===3?{...s,status:'running'}:s)
      await tick(300)
      genSteps=genSteps.map(s=>({...s,status:'done'}))
      genState='done'; genSummary=r
      await loadDrafts(); await loadDocuments(); await loadStats(); await loadGlobal()
      selectedChunks=new Set()
      showToast(`${r.created} Entwürfe erstellt`,'success')
    } catch(e) {
      genSteps=genSteps.map(s=>s.status==='running'?{...s,status:'error'}:s)
      genState='error'; showToast(e.message,'error')
    }
  }

  async function deleteDoc(doc) {
    if (confirmDeleteDoc !== doc.id) {
      confirmDeleteDoc = doc.id
      setTimeout(() => confirmDeleteDoc = null, 3000)
      return
    }
    confirmDeleteDoc = null
    await apiDelete(`/api/documents/${doc.id}`)
    if (selectedDoc?.id===doc.id) { selectedDoc=null; chunks=[] }
    await loadDocuments(); await loadStats()
    showToast('Dokument gelöscht','info')
  }

  function toggleChunk(id) { const s=new Set(selectedChunks); s.has(id)?s.delete(id):s.add(id); selectedChunks=s }

  // ── Entwürfe ─────────────────────────────────────────────────────────────
  async function approveDraft(d) {
    await apiPut(`/api/drafts/${d.id}`,{action:'approve',package_id:pkg.id})
    await loadDrafts(); await loadStats(); await loadGlobal()
    showToast('Karte freigegeben','success')
  }
  async function rejectDraft(d) { await apiPut(`/api/drafts/${d.id}`,{action:'reject'}); await loadDrafts() }
  function startEditDraft(d) { editDraft=d; editDForm={question:d.question,answer:d.answer,hint:d.hint||'',difficulty:d.difficulty,category_code:d.category_code} }
  async function saveEditDraft() {
    await apiPut(`/api/drafts/${editDraft.id}`,{action:'edit',...editDForm,package_id:pkg.id})
    editDraft=null; await loadDrafts(); await loadStats(); await loadGlobal()
    showToast('Bearbeitet und freigegeben','success')
  }
  async function approveAll() {
    for (const d of pending) await apiPut(`/api/drafts/${d.id}`,{action:'approve',package_id:pkg.id}).catch(()=>{})
    await loadDrafts(); await loadStats(); await loadGlobal()
    showToast(`${pending.length} Karten freigegeben`,'success')
  }

  // ── Lexikon ───────────────────────────────────────────────────────────────
  async function saveLex() {
    if (!lexForm.term||!lexForm.definition) { showToast('Begriff und Definition Pflicht','error'); return }
    await apiPost('/api/lexicon',{...lexForm,package_id:pkg.id})
    showToast('Gespeichert','success'); showLexForm=false; lexForm={term:'',definition:'',category_code:''}
    await loadLexicon()
  }

  // ── Lernpfade ─────────────────────────────────────────────────────────────
  async function savePath() {
    if (!pathForm.name) { showToast('Name Pflicht','error'); return }
    await apiPost('/api/paths',{...pathForm,package_id:pkg.id})
    showToast('Lernpfad erstellt','success'); showPathForm=false; pathForm={name:'',description:'',category_codes:[]}
    await loadPaths()
  }

  // ── Import ────────────────────────────────────────────────────────────────
  async function doImport() {
    if (!importFragen||!importAntwt) { showToast('Beide Texte einfügen','error'); return }
    importing=true
    try {
      importResult = await apiPost('/api/import/markdown',{fragen:importFragen,antworten:importAntwt,package_id:pkg.id})
      showToast(`${importResult.created} Karten importiert`,'success')
      await loadCards(); await loadStats(); await loadGlobal()
    } catch(e) { showToast(e.message,'error') }
    importing=false
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  const DL = ['','Leicht','Mittel','Schwer']
  const DC = ['','d1','d2','d3']
  const DI = ['','fa-gauge-simple','fa-gauge','fa-gauge-high']
  const FT = {pdf:'fa-file-pdf',md:'fa-file-code',txt:'fa-file-lines',docx:'fa-file-word'}
  const GSTEP_ICON  = {done:'fa-check',running:'fa-spinner fa-spin',pending:'fa-circle',error:'fa-xmark'}
  const GSTEP_COLOR = {done:'var(--ok)',running:'var(--accent)',pending:'var(--text3)',error:'var(--err)'}
  function fmtSize(b){return b<1024?`${b}B`:b<1048576?`${(b/1024).toFixed(1)}KB`:`${(b/1048576).toFixed(1)}MB`}
  function pct(c,t){return t>0?Math.round(c/t*100):0}

  let pending = $derived(drafts.filter(d=>d.status==='pending'))
  let catCounts = $derived((stats?.by_category||[]).filter(c=>c.count>0))
  let lexGrouped = $derived.by(() => {
    const g = {}
    for (const e of lexicon) {
      const l = (e.term[0]||'#').toUpperCase()
      if (!g[l]) g[l]=[]
      g[l].push(e)
    }
    return Object.entries(g).sort(([a],[b])=>a.localeCompare(b))
  })
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
                  <button class="btn-icon" title="Freigabe entziehen" onclick={() => removeShare(su.id)}>
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
        {#if stats.pending_drafts>0}
          <div class="pds accent clickable" onclick={()=>tab='documents'}>
            <i class="fa-solid fa-pen-to-square"></i>
            <span class="pds-val">{stats.pending_drafts}</span>
            <span class="pds-lbl">Entwürfe</span>
          </div>
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
      ['overview',  'fa-gauge',       'Übersicht',  0],
      ['material',  'fa-book',        'Material',   0],
      ['documents', 'fa-file-lines',  'Dokumente',  pending.length],
      ['cards',     'fa-layer-group', 'Karten',     0],
      ['lexicon',   'fa-book-open',   'Lexikon',    0],
      ['paths',     'fa-route',       'Lernpfade',  0],
      ['media',     'fa-images',      'Medien',     0],
      ['import',    'fa-file-import', 'Import',     0],
    ] as [id,fa,lbl,badge]}
      <button class="pd-tab" class:active={tab===id} onclick={()=>tab=id}>
        <i class="fa-solid {fa}"></i> {lbl}
        {#if badge>0}<span class="tab-badge">{badge}</span>{/if}
      </button>
    {/each}
  </div>

  <!-- ── Tab-Inhalte ───────────────────────────────────────────────────────── -->
  <div class="pd-body">

    <!-- MATERIAL (Lese-Ansicht) -->
    {#if tab==='material'}
      <div class="tab-page material-page">
        {#if documents.length === 0}
          <div class="empty-state">
            <i class="fa-solid fa-book"></i>
            <p>Noch kein Lernmaterial. Lade Dokumente im Tab "Dokumente" hoch.</p>
          </div>
        {:else}
          {#await loadMaterial() then}
            {#each materialTexts as doc}
              <article class="material-doc">
                <div class="material-doc-header">
                  <i class="fa-solid fa-file-lines"></i>
                  <h2>{doc.title}</h2>
                </div>
                <div class="material-content markdown">
                  {@html marked(doc.text)}
                </div>
              </article>
            {/each}
          {/await}
        {/if}
      </div>

    <!-- ÜBERSICHT -->
    {:else if tab==='overview'}
      <div class="tab-page">
        {#if stats && catCounts.length>0}
          <div class="overview-cols">
            <div class="card-box">
              <div class="section-label">Karten nach Kategorie</div>
              {#each catCounts as cat}
                <div class="cat-row">
                  <div class="cat-row-l">
                    <div class="cat-icon-box" style="background:color-mix(in srgb,{cat.color} 15%,transparent)">
                      <i class="fa-solid {cat.icon}" style="color:{cat.color}"></i>
                    </div>
                    <div>
                      <div class="cat-name">{cat.name}</div>
                      <div class="cat-code">{cat.code}</div>
                    </div>
                  </div>
                  <div class="cat-row-r">
                    <div class="cat-track">
                      <div class="cat-fill" style="width:{cat.shown>0?pct(cat.correct,cat.shown):0}%"></div>
                    </div>
                    <span class="cat-n">{cat.count}</span>
                  </div>
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
                    {#if s.mastered > 0}<div class="srs-seg srs-mastered" style="width:{s.mastered/t*100}%" title="Gemeistert: {s.mastered}"></div>{/if}
                    {#if s.solid > 0}<div class="srs-seg srs-solid" style="width:{s.solid/t*100}%" title="Gefestigt: {s.solid}"></div>{/if}
                    {#if s.learning > 0}<div class="srs-seg srs-learning" style="width:{s.learning/t*100}%" title="Lernphase: {s.learning}"></div>{/if}
                    {#if s.due > 0}<div class="srs-seg srs-due" style="width:{s.due/t*100}%" title="Fällig: {s.due}"></div>{/if}
                    {#if s.new > 0}<div class="srs-seg srs-new" style="width:{s.new/t*100}%" title="Neu: {s.new}"></div>{/if}
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

            <div class="card-box">
              <div class="section-label">Dokumente</div>
              {#if documents.length===0}
                <button class="upload-cta" onclick={()=>{tab='documents';showUpload=true}}>
                  <i class="fa-solid fa-upload"></i> Erstes Dokument hochladen
                </button>
              {:else}
                {#each documents.slice(0,6) as doc}
                  <div class="doc-row">
                    <i class="fa-solid {FT[doc.filetype]||'fa-file'} doc-row-icon"></i>
                    <div class="doc-row-body">
                      <div class="doc-row-title">{doc.title}</div>
                      <div class="doc-row-meta">{doc.chunk_count} Abschnitte</div>
                    </div>
                    <button class="btn btn-ghost btn-sm" onclick={()=>{tab='documents';openDoc(doc);setTimeout(()=>{const el=document.querySelector('[class*="read"]');if(el)el.click()},200)}}>
                      <i class="fa-solid fa-book-open"></i> Lesen
                    </button>
                  </div>
                {/each}
              {/if}
            </div>
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-box-open"></i>
            <p>Paket ist noch leer. Lade ein Dokument hoch oder importiere Karten.</p>
          </div>
        {/if}
      </div>

    <!-- DOKUMENTE -->
    {:else if tab==='documents'}
      <div class="tab-page">
        <div class="tab-hd">
          <div>
            <div class="tab-hd-title">Dokumente & KI-Generierung</div>
            <div class="tab-hd-sub">Dokument hochladen -- KI generiert Lernkarten-Entwürfe</div>
          </div>
          <button class="btn btn-primary" onclick={()=>{showUpload=!showUpload;uploadState='idle'}}>
            <i class="fa-solid fa-upload"></i> Hochladen
          </button>
        </div>

        {#if showUpload}
          <div class="card-box upload-box">
            <div class="upload-hd">
              <span class="section-label" style="margin:0">Neues Dokument</span>
              <button class="ib" onclick={()=>showUpload=false}><i class="fa-solid fa-xmark"></i></button>
            </div>
            {#if uploadState!=='idle'}
              <div class="proc-banner" class:proc-uploading={uploadState==='uploading'} class:proc-done={uploadState==='done'} class:proc-error={uploadState==='error'}>
                <i class="fa-solid {uploadState==='uploading'?'fa-spinner fa-spin':uploadState==='done'?'fa-circle-check':'fa-circle-xmark'}"></i>
                <span>{uploadMsg}</span>
              </div>
            {:else}
              <div class="upload-body">
                <label class="drop-zone" class:has-file={!!uploadFile}>
                  <input type="file" accept=".txt,.md,.pdf,.docx"
                    onchange={e=>{uploadFile=e.currentTarget.files[0]||null;uploadTitle=uploadFile?uploadFile.name.replace(/\.[^.]+$/,''):''}}>
                  {#if uploadFile}
                    <i class="fa-solid {FT[uploadFile.name.split('.').pop()]||'fa-file'} drop-file-icon"></i>
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
                  <label class="field-label">Kategorie für Karten
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
                <button class="btn btn-ghost" onclick={()=>showUpload=false}>Abbrechen</button>
                <button class="btn btn-primary" onclick={handleUpload} disabled={!uploadFile}>
                  <i class="fa-solid fa-upload"></i> Hochladen
                </button>
              </div>
            {/if}
          </div>
        {/if}

        {#if documents.length>0}
          <div class="docs-layout">
            <!-- Dokument-Liste -->
            <div class="docs-list-col">
              <div class="section-label">Hochgeladene Dokumente</div>
              {#each documents as doc}
                <div class="doc-item" class:selected={selectedDoc?.id===doc.id} onclick={()=>openDoc(doc)} role="button" tabindex="0" onkeydown={e=>e.key==="Enter"&&openDoc(doc)}>
                  <i class="fa-solid {FT[doc.filetype]||'fa-file'} di-icon"></i>
                  <div class="di-body">
                    <div class="di-title">{doc.title}</div>
                    <div class="di-meta">{fmtSize(doc.filesize)} · {doc.chunk_count} Abschnitte</div>
                    {#if doc.card_count>0}<span class="di-badge">{doc.card_count} Entwürfe</span>{/if}
                  </div>
                  <button class="ib sm err" onclick={e=>{e.stopPropagation();deleteDoc(doc)}}>
                    {#if confirmDeleteDoc === doc.id}
                      Wirklich?
                    {:else}
                      <i class="fa-solid fa-trash"></i>
                    {/if}
                  </button>
                </div>
              {/each}
            </div>

            <!-- Rechte Spalte: Chunks + KI -->
            {#if selectedDoc}
              <div class="doc-detail-col">
                <div class="doc-detail-hd">
                  <div>
                    <div class="doc-detail-title">{selectedDoc.title}</div>
                    <div class="doc-detail-meta">{chunks.length} Abschnitte</div>
                  </div>
                  <button class="btn btn-primary btn-sm" onclick={startGen}
                    disabled={genState==='running'||!$aiOnline}>
                    {#if genState==='running'}
                      <i class="fa-solid fa-spinner fa-spin"></i> Generiere...
                    {:else}
                      <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Karten
                    {/if}
                  </button>
                </div>

                {#if genState!=='idle'}
                  <div class="gen-panel">
                    <div class="gen-panel-hd">
                      <i class="fa-solid fa-wand-magic-sparkles text-accent"></i>
                      <span class="gen-panel-title">KI-Generierung</span>
                      <span class="gen-status gen-{genState}">
                        <i class="fa-solid {genState==='running'?'fa-spinner fa-spin':genState==='done'?'fa-check':'fa-xmark'}"></i>
                        {genState==='running'?'Läuft':genState==='done'?'Fertig':'Fehler'}
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
                            {#if step.status==='running'}
                              <div class="gen-step-bar"><div class="gen-step-fill"></div></div>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                    {#if genSummary}
                      <div class="gen-result">
                        <span class="text-ok"><i class="fa-solid fa-circle-check"></i> {genSummary.created} Entwürfe</span>
                        <span class="text-2"><i class="fa-solid fa-layer-group"></i> {genSummary.chunks_processed} Abschnitte</span>
                        {#if genSummary.created>0}
                          <button class="btn btn-ok btn-sm" onclick={()=>tab='documents'}>
                            <i class="fa-solid fa-list-check"></i> Prüfen
                          </button>
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/if}

                <div class="chunks-col">
                  {#each chunks as chunk}
                    <div class="chunk-item"
                      class:selected={selectedChunks.has(chunk.id)}
                      class:done={chunk.processed}
                      onclick={()=>toggleChunk(chunk.id)}
                      role="button" tabindex="0">
                      <input type="checkbox" checked={selectedChunks.has(chunk.id)}
                        onchange={()=>toggleChunk(chunk.id)} onclick={e=>e.stopPropagation()}>
                      <div class="chunk-body">
                        <div class="chunk-meta">
                          <span class="chunk-idx">#{chunk.chunk_index+1}</span>
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
                <p>Dokument auswählen</p>
              </div>
            {/if}
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-file-circle-plus"></i>
            <p>Noch keine Dokumente in diesem Paket</p>
          </div>
        {/if}

        <!-- Entwürfe Review -->
        {#if pending.length>0}
          <div class="drafts-section">
            <div class="drafts-hd">
              <div class="section-label drafts-title">
                <i class="fa-solid fa-list-check"></i>
                Entwürfe prüfen ({pending.length})
              </div>
              <button class="btn btn-ok btn-sm" onclick={approveAll}>
                <i class="fa-solid fa-check-double"></i> Alle freigeben
              </button>
            </div>
            {#each pending as draft}
              {#if editDraft?.id===draft.id}
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
                    <button class="btn btn-ghost btn-sm" onclick={()=>editDraft=null}>Abbrechen</button>
                    <button class="btn btn-ok btn-sm" onclick={saveEditDraft}>
                      <i class="fa-solid fa-check"></i> Speichern
                    </button>
                  </div>
                </div>
              {:else}
                <div class="card-box draft-card">
                  <div class="draft-card-hd">
                    <span class="draft-cat" style="color:{$categories.find(c=>c.code===draft.category_code)?.color||'var(--accent)'}">
                      {draft.category_code}
                      {#if draft.doc_title}<span class="draft-src">aus {draft.doc_title}</span>{/if}
                    </span>
                    <span class="{DC[draft.difficulty]}">{DL[draft.difficulty]}</span>
                  </div>
                  <div class="draft-q">{draft.question}</div>
                  <div class="draft-a">{draft.answer}</div>
                  {#if draft.hint}<div class="draft-hint"><i class="fa-solid fa-lightbulb"></i> {draft.hint}</div>{/if}
                  <div class="draft-btns">
                    <button class="btn btn-err btn-sm" onclick={()=>rejectDraft(draft)}>
                      <i class="fa-solid fa-xmark"></i> Ablehnen
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick={()=>startEditDraft(draft)}>
                      <i class="fa-solid fa-pen"></i> Bearbeiten
                    </button>
                    <button class="btn btn-ok btn-sm" onclick={()=>approveDraft(draft)}>
                      <i class="fa-solid fa-check"></i> Freigeben
                    </button>
                  </div>
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      </div>

    <!-- KARTEN -->
    {:else if tab==='cards'}
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

    <!-- LEXIKON -->
    {:else if tab==='lexicon'}
      <div class="tab-page">
        <div class="tab-hd">
          <div>
            <div class="tab-hd-title">Lexikon</div>
            <div class="tab-hd-sub">Fachbegriffe dieses Pakets</div>
          </div>
          <button class="btn btn-primary" onclick={()=>showLexForm=!showLexForm}>
            <i class="fa-solid fa-plus"></i> Eintrag
          </button>
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
              <button class="btn btn-ghost btn-sm" onclick={()=>showLexForm=false}>Abbrechen</button>
              <button class="btn btn-primary btn-sm" onclick={saveLex}>
                <i class="fa-solid fa-floppy-disk"></i> Speichern
              </button>
            </div>
          </div>
        {/if}
        {#if lexicon.length===0}
          <div class="empty-state"><i class="fa-solid fa-book-open"></i><p>Noch keine Einträge</p></div>
        {:else}
          {#each lexGrouped as [letter, items]}
            <div class="lex-group">
              <div class="lex-letter">{letter}</div>
              {#each items as entry}
                <div class="card-box lex-entry">
                  <div class="lex-term">{entry.term}</div>
                  <div class="lex-def">{entry.definition}</div>
                </div>
              {/each}
            </div>
          {/each}
        {/if}
      </div>

    <!-- LERNPFADE -->
    {:else if tab==='paths'}
      <div class="tab-page">
        <Paths packageId={pkg.id} {documents} {cards} />
      </div>

    <!-- IMPORT -->
    {:else if tab==='media'}
      {#await loadMedia() then}
        {#if media.length === 0}
          <div class="empty-state"><i class="fa-solid fa-images"></i><p>Keine Medien vorhanden. Bilder werden beim ZIP-Import automatisch erkannt.</p></div>
        {:else}
          <div class="media-grid">
            {#each media as m (m.name)}
              {#if m.type === 'pdf'}
                <a href="{m.url}" target="_blank" class="media-item media-pdf">
                  <i class="fa-solid fa-file-pdf"></i>
                  <span class="media-name">{m.name}</span>
                  <span class="media-size mono">{(m.size/1024).toFixed(0)} KB</span>
                </a>
              {:else}
                <div class="media-item media-img">
                  <img src="{m.url}" alt={m.name} loading="lazy" />
                  <span class="media-name">{m.name}</span>
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      {/await}

    {:else if tab==='import'}
      <div class="tab-page">
        <div class="tab-hd">
          <div>
            <div class="tab-hd-title">Karten importieren</div>
            <div class="tab-hd-sub">Aus Markdown-Lernkarten-Dateien direkt in dieses Paket importieren</div>
          </div>
        </div>
        <div class="card-box import-box">
          <p class="import-desc">
            Inhalt beider Dateien einfügen. Bereits vorhandene Karten (gleiche ID) werden übersprungen.
          </p>
          <div class="import-grid">
            <label class="field-label">
              <span><i class="fa-solid fa-circle-question text-accent"></i> Fragen-Datei</span>
              <textarea bind:value={importFragen} rows="14" class="import-ta" placeholder="Inhalt der Fragen-Datei hier einfuegen..."></textarea>
            </label>
            <label class="field-label">
              <span><i class="fa-solid fa-circle-check text-ok"></i> Antworten-Datei</span>
              <textarea bind:value={importAntwt} rows="14" class="import-ta" placeholder="Inhalt der Antworten-Datei hier einfuegen..."></textarea>
            </label>
          </div>
          {#if importResult}
            <div class="import-result">
              <span class="text-ok"><i class="fa-solid fa-circle-check"></i> {importResult.created} importiert</span>
              {#if importResult.skipped>0}
                <span class="text-warn"><i class="fa-solid fa-circle-minus"></i> {importResult.skipped} übersprungen</span>
              {/if}
              <span class="text-2">von {importResult.total} gesamt</span>
            </div>
          {/if}
          <button class="btn btn-primary" onclick={doImport} disabled={importing}>
            {#if importing}
              <i class="fa-solid fa-spinner fa-spin"></i> Importiere...
            {:else}
              <i class="fa-solid fa-file-import"></i> Importieren
            {/if}
          </button>
        </div>
      </div>
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

.media-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px; }
.media-item { background:var(--bg1);border:1px solid var(--border);border-radius:4px;overflow:hidden;display:flex;flex-direction:column; }
.media-img img { width:100%;height:120px;object-fit:cover;display:block; }
.media-pdf { padding:20px;align-items:center;text-decoration:none;color:var(--text1);gap:6px;text-align:center; }
.media-pdf i { font-size:28px;color:var(--err); }
.media-name { font-size:10px;color:var(--text2);padding:6px 8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.media-size { font-size:9px;color:var(--text3); }

.share-panel { background:var(--bg1);border:1px solid var(--border);border-radius:4px;padding:14px;margin-top:12px; }
.share-hd { font-size:12px;font-weight:700;color:var(--text2);margin-bottom:10px;text-transform:uppercase;letter-spacing:.04em; }
.share-form { display:flex;gap:8px;align-items:center;flex-wrap:wrap; }
.share-list { margin-top:12px;display:flex;flex-direction:column;gap:4px; }
.share-user { display:flex;align-items:center;gap:8px;font-size:12px;padding:6px 0; }
.share-email { flex:1;color:var(--text1); }
.share-role { font-size:10px;color:var(--text3);background:var(--bg2);padding:2px 6px;border-radius:2px; }

.pd-stats {
  display: flex;
  align-items: center;
  gap: 0;
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
}
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

/* ── Tab-Seiten ───────────────────────────────────────────────────────────── */
.tab-page {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.material-page { max-width: 860px; }
.material-doc { margin-bottom: 32px; }
.material-doc-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 16px; padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.material-doc-header i { color: var(--accent); font-size: 16px; }
.material-doc-header h2 { font-size: 16px; font-weight: 700; color: var(--text0); margin: 0; }
.material-content { font-size: 14px; color: var(--text1); line-height: 1.8; }
.tab-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.tab-hd-title { font-size: 15px; font-weight: 700; color: var(--text0); }
.tab-hd-sub   { font-size: 12px; color: var(--text2); margin-top: 2px; }

/* ── Übersicht ────────────────────────────────────────────────────────────── */
.overview-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.cat-row { display: flex; align-items: center; justify-content: space-between; padding: 7px 6px; border-radius: 4px; transition: background .12s; }
.cat-row:hover { background: var(--bg2); }
.cat-row-l { display: flex; align-items: center; gap: 10px; }
.cat-icon-box { width: 28px; height: 28px; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.cat-icon-box i { font-size: 12px; }
.cat-name { font-size: 12px; font-weight: 600; color: var(--text1); }
.cat-code { font-size: 9px; color: var(--text3); font-family: 'JetBrains Mono', monospace; letter-spacing: .06em; }
.cat-row-r { display: flex; align-items: center; gap: 8px; width: 130px; }
.cat-track { flex: 1; height: 4px; background: var(--bg3); border-radius: 2px; overflow: hidden; }

/* SRS-Stapel */
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
.cat-fill { height: 100%; border-radius: 2px; transition: width .5s; background: var(--accent); }
.cat-n { font-size: 11px; font-weight: 600; color: var(--text2); min-width: 22px; text-align: right; font-family: 'JetBrains Mono', monospace; }

.doc-row { display: flex; align-items: center; gap: 10px; padding: 8px 6px; border-radius: 4px; cursor: pointer; transition: background .12s; width: 100%; text-align: left; border: none; background: none; font-family: inherit; }
.doc-row:hover { background: var(--bg2); }
.doc-row-icon { font-size: 16px; color: var(--accent); flex-shrink: 0; }
.doc-row-body { flex: 1; }
.doc-row-title { font-size: 12px; font-weight: 600; color: var(--text1); }
.doc-row-meta  { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.doc-row-arr   { font-size: 10px; color: var(--text3); }
.upload-cta { display: flex; align-items: center; gap: 8px; color: var(--accent); font-size: 13px; font-weight: 600; padding: 12px 8px; border-radius: 4px; border: 1px dashed var(--accent); background: var(--glow); width: 100%; justify-content: center; cursor: pointer; transition: filter .15s; font-family: inherit; }
.upload-cta:hover { filter: brightness(1.1); }

/* ── Upload Form ──────────────────────────────────────────────────────────── */
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
.drop-hint  { font-size: 12px; color: var(--text2); }
.drop-hint2 { font-size: 10px; color: var(--text3); }
.proc-banner { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 4px; font-size: 13px; font-weight: 500; }
.proc-uploading { background: var(--glow); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); }
.proc-done      { background: var(--glowok); color: var(--ok); border: 1px solid color-mix(in srgb, var(--ok) 35%, transparent); }
.proc-error     { background: color-mix(in srgb, var(--err) 10%, transparent); color: var(--err); border: 1px solid color-mix(in srgb, var(--err) 35%, transparent); }
.ai-warn-pill { font-size: 11px; color: var(--warn); background: color-mix(in srgb, var(--warn) 10%, transparent); padding: 7px 12px; border-radius: 4px; border: 1px solid color-mix(in srgb, var(--warn) 35%, transparent); display: flex; align-items: center; gap: 7px; }

/* ── Dokument-Layout ──────────────────────────────────────────────────────── */
.docs-layout { display: grid; grid-template-columns: 260px 1fr; gap: 16px; margin-top: 16px; }
.docs-list-col {}
.doc-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; transition: all .12s; width: 100%; text-align: left; background: none; font-family: inherit; margin-bottom: 3px; }
.doc-item:hover { background: var(--bg2); }
.doc-item.selected { background: var(--glow); border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.di-icon { font-size: 18px; color: var(--accent); flex-shrink: 0; }
.di-body { flex: 1; }
.di-title { font-size: 12px; font-weight: 600; color: var(--text1); }
.di-meta  { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.di-badge { font-size: 10px; color: var(--ac3); }

.doc-detail-col { background: var(--bg1); border: 1px solid var(--border); border-radius: 4px; padding: 14px; display: flex; flex-direction: column; gap: 10px; min-height: 300px; overflow-y: auto; }
.doc-detail-empty { align-items: center; justify-content: center; }
.doc-detail-empty i { font-size: 32px; opacity: .2; color: var(--text3); }
.doc-detail-empty p { font-size: 13px; color: var(--text3); }
.doc-detail-hd { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.doc-detail-title { font-size: 13px; font-weight: 700; color: var(--text0); }
.doc-detail-meta  { font-size: 10px; color: var(--text2); margin-top: 1px; }

/* ── KI Prozess ───────────────────────────────────────────────────────────── */
.gen-panel { background: var(--bg2); border: 1px solid var(--border); border-radius: 4px; padding: 12px; flex-shrink: 0; }
.gen-panel-hd { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.gen-panel-title { font-size: 12px; font-weight: 600; color: var(--text1); flex: 1; }
.gen-status { display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; }
.gen-running { color: var(--accent); background: var(--glow); }
.gen-done    { color: var(--ok); background: var(--glowok); }
.gen-error   { color: var(--err); background: color-mix(in srgb, var(--err) 10%, transparent); }
.gen-steps { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.gen-step { display: flex; align-items: flex-start; gap: 10px; padding: 3px 0; }
.gen-step-pending { opacity: .3; }
.gen-step-done    { opacity: .65; }
.gen-step-running, .gen-step-error { opacity: 1; }
.gen-dot { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid var(--border); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }
.gen-step-running .gen-dot { border-color: var(--accent); }
.gen-step-done    .gen-dot { border-color: var(--ok); background: var(--ok); }
.gen-step-done    .gen-dot i { color: #fff !important; }
.gen-step-error   .gen-dot { border-color: var(--err); background: var(--err); }
.gen-step-error   .gen-dot i { color: #fff !important; }
.gen-step-right { flex: 1; display: flex; flex-direction: column; gap: 3px; }
.gen-step-label { font-size: 12px; color: var(--text1); }
.gen-step-bar { height: 2px; background: var(--bg3); border-radius: 1px; overflow: hidden; }
.gen-step-fill { height: 100%; background: var(--accent); animation: scan 1.8s ease-in-out infinite; }
@keyframes scan { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }
.gen-result { display: flex; align-items: center; gap: 12px; font-size: 12px; font-weight: 500; flex-wrap: wrap; padding-top: 8px; border-top: 1px solid var(--border); }

/* ── Chunks ───────────────────────────────────────────────────────────────── */
.chunks-col { display: flex; flex-direction: column; gap: 4px; overflow-y: auto; flex: 1; }
.chunk-item { display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px; border-radius: 4px; cursor: pointer; border: 1px solid transparent; transition: all .12s; width: 100%; text-align: left; background: none; font-family: inherit; }
.chunk-item:hover { background: var(--bg2); }
.chunk-item.selected { background: var(--glow); border-color: color-mix(in srgb, var(--accent) 35%, transparent); }
.chunk-item.done { opacity: .5; }
.chunk-item input { flex-shrink: 0; margin-top: 2px; }
.chunk-body { flex: 1; }
.chunk-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.chunk-idx  { font-size: 9px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.chunk-done { font-size: 9px; color: var(--ok); }
.chunk-text { font-size: 11px; color: var(--text2); line-height: 1.5; margin: 0; }

/* ── Entwürfe ─────────────────────────────────────────────────────────────── */
.drafts-section { margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--border); }
.drafts-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.drafts-title { color: var(--warn) !important; display: flex; align-items: center; gap: 6px; }
.draft-card { margin-bottom: 10px; max-width: 700px; }
.draft-card-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.draft-cat { font-size: 11px; font-weight: 700; letter-spacing: .06em; }
.draft-src { font-size: 10px; color: var(--text3); font-weight: 400; margin-left: 6px; }
.draft-q   { font-size: 14px; font-weight: 600; color: var(--text0); margin-bottom: 8px; line-height: 1.5; }
.draft-a   { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text1); background: var(--bg2); border-radius: 4px; padding: 9px 12px; white-space: pre-wrap; margin-bottom: 8px; line-height: 1.6; }
.draft-hint { font-size: 11px; color: var(--text2); margin-bottom: 8px; display: flex; align-items: center; gap: 5px; }
.draft-hint i { color: var(--warn); }
.draft-btns { display: flex; gap: 8px; justify-content: flex-end; }
.draft-edit { margin-bottom: 10px; max-width: 700px; display: flex; flex-direction: column; gap: 10px; }
.draft-edit-title { font-size: 13px; font-weight: 600; color: var(--text0); display: flex; align-items: center; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.draft-edit-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.draft-edit-footer { display: flex; justify-content: flex-end; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border); }

/* ── Karten Split Layout ──────────────────────────────────────────────────── */
.cards-panel-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr;
  overflow: hidden;
}
.cards-list-col {
  border-right: 1px solid var(--bdr2);
  display: flex;
  flex-direction: column;
  background: var(--bg1);
  overflow: hidden;
}
.cl-header { padding: 14px 14px 10px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--bdr2); flex-shrink: 0; }
.cl-title { font-size: 13px; font-weight: 700; color: var(--text0); display: flex; align-items: center; gap: 6px; }
.cl-title i { font-size: 13px; }
.cnt-badge { font-size: 10px; background: var(--bg3); color: var(--text2); border-radius: 4px; padding: 1px 6px; font-family: 'JetBrains Mono', monospace; }
.cl-filters { padding: 10px 12px; display: flex; flex-direction: column; gap: 7px; border-bottom: 1px solid var(--bdr2); flex-shrink: 0; }
.search-wrap { position: relative; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 11px; color: var(--text3); pointer-events: none; }
.search-inp { padding-left: 30px !important; }
.cl-list { flex: 1; overflow-y: auto; padding: 6px; }
.list-loading { padding: 24px; text-align: center; color: var(--accent); font-size: 18px; }
.list-empty   { padding: 20px; text-align: center; color: var(--text3); font-size: 12px; }
.cl-item { display: block; width: 100%; padding: 9px 10px; border-radius: 4px; text-align: left; cursor: pointer; transition: background .12s; border: 1px solid var(--border); margin-bottom: 4px; background: var(--bg1); font-family: inherit; }
.cl-item:hover    { background: var(--bg2); border-color: var(--text3); }
.cl-item.selected { background: var(--bg2); border-color: var(--accent); }
.cl-item.inactive { opacity: .4; }
.cli-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.cli-id  { font-size: 9px; color: var(--text3); font-family: 'JetBrains Mono', monospace; letter-spacing: .06em; }
.cli-q   { font-size: 11px; color: var(--text1); line-height: 1.4; margin-bottom: 3px; }
.cli-cat { font-size: 9px; font-weight: 600; }
.d1 { color: var(--ok); }
.d2 { color: var(--warn); }
.d3 { color: var(--err); }

.cards-detail-col { overflow-y: auto; background: var(--bg0); }
.card-form-wrap, .card-detail-wrap { padding: 22px; }
.form-hd { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.form-title { font-size: 14px; font-weight: 700; color: var(--text0); display: flex; align-items: center; gap: 8px; }
.form-fields { display: flex; flex-direction: column; gap: 12px; }
.form-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 14px; border-top: 1px solid var(--border); margin-top: 14px; }
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.diff-btns { display: flex; gap: 8px; }
.diff-btn {
  padding: 5px 13px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text2);
  cursor: pointer;
  transition: all .15s;
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: inherit;
}
.diff-btn[data-diff="1"].diff-active { border-color: var(--ok);   color: var(--ok);   background: color-mix(in srgb, var(--ok)   12%, transparent); }
.diff-btn[data-diff="2"].diff-active { border-color: var(--warn); color: var(--warn); background: color-mix(in srgb, var(--warn) 12%, transparent); }
.diff-btn[data-diff="3"].diff-active { border-color: var(--err);  color: var(--err);  background: color-mix(in srgb, var(--err)  12%, transparent); }

.card-detail-actions { display: flex; gap: 6px; }
.detail-section { margin-bottom: 16px; }
.detail-q    { font-size: 15px; font-weight: 600; color: var(--text0); background: var(--bg2); border-radius: 4px; padding: 12px 14px; line-height: 1.5; }
.detail-hint { font-size: 12px; color: var(--text2); background: var(--bg2); border-radius: 4px; padding: 8px 12px; display: flex; align-items: center; gap: 6px; }
.detail-hint i { flex-shrink: 0; }
.detail-ans  { font-size: 12px; color: var(--text1); background: var(--bg1); border: 1px solid var(--border); border-radius: 4px; padding: 12px 14px; line-height: 1.65; }
.detail-ai   { font-size: 13px; color: var(--text1); background: var(--bg2); border: 1px solid color-mix(in srgb, var(--ac2) 35%, transparent); border-radius: 4px; padding: 12px 14px; line-height: 1.6; }
.ai-load-indicator { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--glow); border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); border-radius: 4px; margin-top: 4px; }
.ai-load-indicator > i { color: var(--accent); flex-shrink: 0; }
.ai-load-text { font-size: 12px; color: var(--accent); margin-bottom: 4px; }
.ai-bar { height: 2px; background: var(--bg3); border-radius: 1px; overflow: hidden; }
.ai-bar-fill { height: 100%; background: var(--accent); animation: scan 1.8s ease-in-out infinite; }

/* ── Lexikon ──────────────────────────────────────────────────────────────── */
.lex-group { margin-bottom: 20px; }
.lex-letter { font-size: 11px; font-weight: 700; letter-spacing: .12em; color: var(--accent); font-family: 'JetBrains Mono', monospace; padding-bottom: 8px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
.lex-entry { margin-bottom: 8px; }
.lex-term  { font-size: 16px; font-weight: 700; color: var(--text0); margin-bottom: 8px; }
.lex-def   { font-size: 13px; color: var(--text1); line-height: 1.7; white-space: pre-wrap; }

/* ── Lernpfade ────────────────────────────────────────────────────────────── */
.paths-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
.path-card { display: flex; flex-direction: column; gap: 10px; }
.path-name { font-size: 15px; font-weight: 700; color: var(--text0); }
.path-desc { font-size: 12px; color: var(--text2); }
.path-cats { display: flex; flex-wrap: wrap; gap: 5px; }
.path-cat-tag { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid; }
.cat-check-grid { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px; background: var(--bg2); border-radius: 4px; border: 1px solid var(--border); }
.cat-check-item { display: flex; align-items: center; gap: 5px; font-size: 11px; cursor: pointer; color: var(--text1); }

/* ── Import ───────────────────────────────────────────────────────────────── */
.import-box { max-width: 920px; }
.import-desc { font-size: 13px; color: var(--text2); margin-bottom: 16px; line-height: 1.6; }
.import-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 14px; }
.import-ta { font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; }
.import-result { display: flex; align-items: center; gap: 16px; padding: 10px 14px; background: var(--bg2); border-radius: 4px; margin-bottom: 12px; font-size: 13px; font-weight: 600; }

/* ── Gemeinsame Form-Elemente ─────────────────────────────────────────────── */
.field-label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; font-weight: 600; color: var(--text2); }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 12px; color: var(--text2); }
.checkbox-label input, .cat-check-item input { width: auto; }
.range-input { width: 100%; accent-color: var(--accent); padding: 0; background: none; border: none; box-shadow: none; }
.ib { width: 28px; height: 28px; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--text2); font-size: 12px; transition: all .15s; background: none; border: none; cursor: pointer; }
.ib:hover { background: var(--bg2); color: var(--text0); }
.ib.sm { width: 24px; height: 24px; font-size: 11px; }
.ib.err:hover { background: var(--err); color: #fff; }

/* ── Hilfklassen (lokal) ──────────────────────────────────────────────────── */
.text-accent { color: var(--accent); }
.text-ok     { color: var(--ok); }
.text-warn   { color: var(--warn); }
.text-err    { color: var(--err); }
.text-ac2    { color: var(--ac2); }
.text-2      { color: var(--text2); }
</style>
