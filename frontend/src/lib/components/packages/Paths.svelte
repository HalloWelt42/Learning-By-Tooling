<!--
  Paths.svelte -- Kapitel-basierte Lernpfade
  Geführtes Lernen: Material lesen -> Karten lernen -> Kapitel bestanden
-->
<script>
  import { onMount } from 'svelte'
  import { showToast, categories, activePackageId, currentView } from '../../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete } from '../../utils/api.js'
  import { marked } from 'marked'
  marked.setOptions({ breaks: true, gfm: true })

  let { packageId, documents = [], cards = [] } = $props()

  let paths       = $state([])
  let selectedPath = $state(null)
  let pathDetail  = $state(null)
  let showCreate  = $state(false)
  let showAddChapter = $state(false)
  let form        = $state({ name: '', description: '' })
  let chapterForm = $state({ title: '', description: '', document_ids: [], card_ids: [], pass_threshold: 0.7 })
  let materialView = $state(null)

  onMount(loadPaths)

  async function loadPaths() {
    paths = await apiGet(`/api/packages/${packageId}/paths`).catch(() => [])
  }

  async function loadPathDetail(pathId) {
    pathDetail = await apiGet(`/api/paths/${pathId}`).catch(() => null)
    selectedPath = pathId
  }

  async function createPath() {
    if (!form.name) { showToast('Name ist Pflicht', 'error'); return }
    await apiPost('/api/paths', { package_id: packageId, name: form.name, description: form.description })
    showToast('Lernpfad erstellt', 'success')
    showCreate = false
    form = { name: '', description: '' }
    await loadPaths()
  }

  async function addChapter() {
    if (!chapterForm.title) { showToast('Titel ist Pflicht', 'error'); return }
    await apiPost(`/api/paths/${selectedPath}/chapters`, chapterForm)
    showToast('Kapitel hinzugefügt', 'success')
    showAddChapter = false
    chapterForm = { title: '', description: '', document_ids: [], card_ids: [], pass_threshold: 0.7 }
    await loadPathDetail(selectedPath)
  }

  async function deleteChapter(chId) {
    await apiDelete(`/api/chapters/${chId}`)
    await loadPathDetail(selectedPath)
  }

  async function deletePath(pId) {
    await apiDelete(`/api/paths/${pId}`)
    selectedPath = null
    pathDetail = null
    await loadPaths()
    showToast('Lernpfad gelöscht', 'info')
  }

  function startChapterSession(chapter) {
    // TODO: Session mit nur diesen Karten starten
    showToast(`Session für "${chapter.title}" -- ${chapter.card_ids?.length || 0} Karten`, 'info')
  }

  async function showMaterial(docId) {
    try {
      const data = await apiGet(`/api/documents/${docId}/chunks`)
      materialView = { title: data.title, text: data.chunks.map(c => c.text).join('\n\n') }
    } catch(e) {
      showToast('Dokument konnte nicht geladen werden', 'error')
    }
  }

  function isUnlocked(chapters, index) {
    if (index === 0) return true
    const prev = chapters[index - 1]
    return prev?.passed === true
  }
</script>

{#if materialView}
  <!-- Material-Leseansicht -->
  <div>
    <button class="btn btn-ghost" style="margin-bottom:16px" onclick={() => materialView = null}>
      <i class="fa-solid fa-arrow-left"></i> Zurück zum Lernpfad
    </button>
    <h2 style="font-size:16px;font-weight:700;color:var(--text0);margin-bottom:16px">{materialView.title}</h2>
    <div class="material-content markdown card-box" style="max-width:800px;padding:24px;font-size:14px;line-height:1.8;color:var(--text1)">
      {@html marked(materialView.text)}
    </div>
  </div>

{:else if pathDetail}
  <!-- Pfad-Detail mit Kapiteln -->
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
      <button class="btn btn-ghost btn-sm" onclick={() => { pathDetail = null; selectedPath = null }}>
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <div style="flex:1">
        <h2 style="font-size:16px;font-weight:700;color:var(--text0)">{pathDetail.name}</h2>
        {#if pathDetail.description}
          <p style="font-size:12px;color:var(--text2);margin-top:2px">{pathDetail.description}</p>
        {/if}
      </div>
      <button class="btn btn-ghost btn-sm" onclick={() => showAddChapter = !showAddChapter}>
        <i class="fa-solid fa-plus"></i> Kapitel
      </button>
    </div>

    {#if showAddChapter}
      <div class="card-box" style="margin-bottom:20px;max-width:600px">
        <div class="section-label">Neues Kapitel</div>
        <div style="display:flex;flex-direction:column;gap:10px">
          <input type="text" bind:value={chapterForm.title} placeholder="Kapitel-Titel" />
          <textarea bind:value={chapterForm.description} rows="2" placeholder="Beschreibung (optional)"></textarea>

          <div class="section-label" style="margin-top:8px">Lernmaterial zuweisen</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px">
            {#each documents as doc}
              <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text1);cursor:pointer;padding:4px 8px;background:var(--bg2);border-radius:3px;border:1px solid var(--border)">
                <input type="checkbox" checked={chapterForm.document_ids.includes(doc.id)}
                  onchange={() => {
                    if (chapterForm.document_ids.includes(doc.id))
                      chapterForm.document_ids = chapterForm.document_ids.filter(d => d !== doc.id)
                    else
                      chapterForm.document_ids = [...chapterForm.document_ids, doc.id]
                  }} />
                {doc.title}
              </label>
            {/each}
            {#if documents.length === 0}
              <span style="font-size:11px;color:var(--text3)">Keine Dokumente vorhanden</span>
            {/if}
          </div>

          <div class="section-label" style="margin-top:8px">Karten zuweisen</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;max-height:200px;overflow-y:auto">
            {#each cards as c}
              <label style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text1);cursor:pointer;padding:3px 8px;background:var(--bg2);border-radius:3px;border:1px solid var(--border)">
                <input type="checkbox" checked={chapterForm.card_ids.includes(c.card_id)}
                  onchange={() => {
                    if (chapterForm.card_ids.includes(c.card_id))
                      chapterForm.card_ids = chapterForm.card_ids.filter(d => d !== c.card_id)
                    else
                      chapterForm.card_ids = [...chapterForm.card_ids, c.card_id]
                  }} />
                <span style="color:var(--text3);font-family:'JetBrains Mono',monospace">{c.card_id}</span>
                {c.question.slice(0, 50)}{c.question.length > 50 ? '...' : ''}
              </label>
            {/each}
          </div>

          <div style="display:flex;gap:8px;margin-top:10px">
            <button class="btn btn-ghost" onclick={() => showAddChapter = false}>Abbrechen</button>
            <button class="btn btn-primary" onclick={addChapter}>
              <i class="fa-solid fa-plus"></i> Kapitel hinzufügen
            </button>
          </div>
        </div>
      </div>
    {/if}

    {#if pathDetail.chapters?.length === 0}
      <div class="card-box" style="text-align:center;padding:32px;color:var(--text2)">
        <i class="fa-solid fa-list-ol" style="font-size:24px;color:var(--text3);margin-bottom:10px"></i>
        <p>Noch keine Kapitel. Füge das erste Kapitel hinzu.</p>
      </div>
    {:else}
      <div class="chapters-list">
        {#each pathDetail.chapters as chapter, i}
          {@const unlocked = isUnlocked(pathDetail.chapters, i)}
          <div class="chapter-card" class:locked={!unlocked} class:passed={chapter.passed}>
            <div class="ch-header">
              <div class="ch-number" class:passed={chapter.passed}>
                {#if chapter.passed}
                  <i class="fa-solid fa-check"></i>
                {:else}
                  {i + 1}
                {/if}
              </div>
              <div style="flex:1">
                <div class="ch-title">{chapter.title}</div>
                {#if chapter.description}
                  <div class="ch-desc">{chapter.description}</div>
                {/if}
              </div>
              {#if !unlocked}
                <i class="fa-solid fa-lock" style="color:var(--text3);font-size:14px"></i>
              {/if}
            </div>

            {#if unlocked}
              <div class="ch-progress">
                <div class="ch-prog-bar">
                  <div class="ch-prog-fill" style="width:{Math.round(chapter.progress * 100)}%"></div>
                </div>
                <span class="ch-prog-text">{chapter.mastered}/{chapter.total_cards} Karten gemeistert</span>
              </div>

              <div class="ch-actions">
                {#if chapter.document_ids?.length > 0}
                  {#each chapter.document_ids as docId}
                    <button class="btn btn-ghost btn-sm" onclick={() => showMaterial(docId)}>
                      <i class="fa-solid fa-book-open"></i> Material lesen
                    </button>
                  {/each}
                {/if}
                {#if chapter.card_ids?.length > 0}
                  <button class="btn btn-primary btn-sm" onclick={() => startChapterSession(chapter)}>
                    <i class="fa-solid fa-play"></i> Karten lernen ({chapter.total_cards})
                  </button>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>

{:else}
  <!-- Pfad-Liste -->
  <div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
      <div class="section-label" style="margin:0">Lernpfade</div>
      <button class="btn btn-ghost btn-sm" onclick={() => showCreate = !showCreate}>
        <i class="fa-solid fa-plus"></i> Neuer Pfad
      </button>
    </div>

    {#if showCreate}
      <div class="card-box" style="margin-bottom:16px;max-width:500px">
        <div style="display:flex;flex-direction:column;gap:10px">
          <input type="text" bind:value={form.name} placeholder="Name des Lernpfads" />
          <textarea bind:value={form.description} rows="2" placeholder="Beschreibung (optional)"></textarea>
          <div style="display:flex;gap:8px">
            <button class="btn btn-ghost" onclick={() => showCreate = false}>Abbrechen</button>
            <button class="btn btn-primary" onclick={createPath}>
              <i class="fa-solid fa-plus"></i> Erstellen
            </button>
          </div>
        </div>
      </div>
    {/if}

    {#if paths.length === 0 && !showCreate}
      <div class="card-box" style="text-align:center;padding:32px;color:var(--text2)">
        <i class="fa-solid fa-route" style="font-size:24px;color:var(--text3);margin-bottom:10px"></i>
        <p>Noch keine Lernpfade. Erstelle einen Pfad um dein Lernen zu strukturieren.</p>
      </div>
    {:else}
      {#each paths as p}
        <button class="path-card" onclick={() => loadPathDetail(p.id)}>
          <div style="flex:1">
            <div class="path-name">{p.name}</div>
            {#if p.description}
              <div class="path-desc">{p.description}</div>
            {/if}
          </div>
          <i class="fa-solid fa-chevron-right" style="color:var(--text3)"></i>
        </button>
      {/each}
    {/if}
  </div>
{/if}

<style>
  .chapters-list { display: flex; flex-direction: column; gap: 12px; max-width: 700px; }
  .chapter-card {
    background: var(--bg1); border: 1px solid var(--border); border-radius: 4px;
    padding: 16px; transition: opacity .2s;
  }
  .chapter-card.locked { opacity: .5; }
  .chapter-card.passed { border-color: var(--ok); }
  .ch-header { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px; }
  .ch-number {
    width: 28px; height: 28px; border-radius: 50%; border: 2px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: var(--text2); flex-shrink: 0;
    font-family: 'JetBrains Mono', monospace;
  }
  .ch-number.passed { border-color: var(--ok); color: var(--ok); background: color-mix(in srgb, var(--ok) 10%, transparent); }
  .ch-title { font-size: 14px; font-weight: 700; color: var(--text0); }
  .ch-desc { font-size: 12px; color: var(--text2); margin-top: 2px; }
  .ch-progress { margin-bottom: 10px; }
  .ch-prog-bar { height: 4px; background: var(--bg3); border-radius: 2px; margin-bottom: 4px; }
  .ch-prog-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width .3s; }
  .ch-prog-text { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
  .ch-actions { display: flex; gap: 8px; flex-wrap: wrap; }

  .path-card {
    display: flex; align-items: center; gap: 12px;
    background: var(--bg1); border: 1px solid var(--border); border-radius: 4px;
    padding: 14px 16px; cursor: pointer; transition: background .12s;
    margin-bottom: 8px; width: 100%; text-align: left;
    font-family: inherit; color: inherit;
  }
  .path-card:hover { background: var(--bg2); }
  .path-name { font-size: 14px; font-weight: 600; color: var(--text0); }
  .path-desc { font-size: 12px; color: var(--text2); margin-top: 2px; }
</style>
