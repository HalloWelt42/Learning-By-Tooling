<script>
  import { apiGet } from '../../utils/api.js'
  import { BASE } from '../../utils/api.js'
  import { marked } from 'marked'
  import Paths from './Paths.svelte'
  import LexiconTab from './LexiconTab.svelte'
  import { onMount } from 'svelte'
  marked.setOptions({ breaks: true, gfm: true })

  let { pkg } = $props()

  let section = $state('docs')  // docs | lexicon | paths | media

  let documents = $state([])
  let cards     = $state([])
  let media     = $state([])

  let readingDocId   = $state(null)
  let readingDocText = $state('')

  onMount(() => { loadDocuments(); loadMedia() })

  $effect(() => { if (section === 'paths') loadCards() })

  async function loadDocuments() { documents = await apiGet(`/api/packages/${pkg.id}/documents`).catch(() => []) }
  async function loadCards()     { cards = await apiGet(`/api/cards?package_id=${pkg.id}`).catch(() => []) }
  async function loadMedia()     { try { media = await apiGet(`/api/packages/${pkg.id}/media`) } catch(e) { media = [] } }

  async function toggleReading(doc) {
    if (readingDocId === doc.id) { readingDocId = null; readingDocText = ''; return }
    readingDocId = doc.id
    try {
      const data = await apiGet(`/api/documents/${doc.id}/chunks`)
      readingDocText = data.chunks.map(c => c.text).join('\n\n')
    } catch(e) { readingDocText = 'Fehler beim Laden' }
  }

  const FT = { pdf: 'fa-file-pdf', md: 'fa-file-code', txt: 'fa-file-lines', docx: 'fa-file-word' }
  function fmtSize(b) { return b < 1024 ? `${b}B` : b < 1048576 ? `${(b / 1024).toFixed(1)}KB` : `${(b / 1048576).toFixed(1)}MB` }
</script>

<div class="mt-wrap">
  <div class="mt-nav">
    {#each [
      ['docs',    'fa-file-lines', 'Dokumente', documents.length],
      ['lexicon', 'fa-book-open',  'Lexikon',   0],
      ['paths',   'fa-route',      'Lernpfade', 0],
      ['media',   'fa-images',     'Medien',    media.length],
    ] as [id, fa, lbl, cnt]}
      <button class="mt-nav-btn" class:active={section === id} onclick={() => section = id}>
        <i class="fa-solid {fa}"></i> {lbl}
        {#if cnt > 0}<span class="mt-cnt">{cnt}</span>{/if}
      </button>
    {/each}
  </div>

  <div class="mt-body">

    <!-- DOKUMENTE -->
    {#if section === 'docs'}
      <div class="mt-page">
        {#if documents.length > 0}
          <div class="doc-list">
            {#each documents as doc (doc.id)}
              <div class="doc-card" class:reading={readingDocId === doc.id}>
                <div class="doc-card-hd" onclick={() => toggleReading(doc)} role="button" tabindex="0" onkeydown={e => e.key === 'Enter' && toggleReading(doc)}>
                  <i class="fa-solid {FT[doc.filetype] || 'fa-file'} doc-icon"></i>
                  <div class="doc-card-body">
                    <div class="doc-card-title">{doc.title}</div>
                    <div class="doc-card-meta">{fmtSize(doc.filesize)} -- {doc.chunk_count} Abschnitte</div>
                  </div>
                  <i class="fa-solid {readingDocId === doc.id ? 'fa-chevron-up' : 'fa-chevron-down'} doc-toggle"></i>
                </div>
                {#if readingDocId === doc.id}
                  <article class="doc-content markdown">
                    {#if readingDocText}
                      {@html marked(readingDocText)}
                    {:else}
                      <i class="fa-solid fa-spinner fa-spin"></i> Lade...
                    {/if}
                  </article>
                {/if}
              </div>
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-file-lines"></i>
            <p>Keine Dokumente vorhanden</p>
          </div>
        {/if}
      </div>

    <!-- LEXIKON -->
    {:else if section === 'lexicon'}
      <LexiconTab {pkg} />

    <!-- LERNPFADE -->
    {:else if section === 'paths'}
      <div class="mt-page">
        <Paths packageId={pkg.id} {documents} {cards} />
      </div>

    <!-- MEDIEN -->
    {:else if section === 'media'}
      <div class="mt-page">
        {#if media.length > 0}
          <div class="media-grid">
            {#each media as m (m.name)}
              {#if m.type === 'pdf'}
                <a href="{m.url}" target="_blank" class="media-item media-pdf">
                  <i class="fa-solid fa-file-pdf"></i>
                  <span class="media-name">{m.name}</span>
                  <span class="media-size mono">{(m.size / 1024).toFixed(0)} KB</span>
                </a>
              {:else}
                <div class="media-item media-img">
                  <img src="{m.url}" alt={m.name} loading="lazy" />
                  <span class="media-name">{m.name}</span>
                </div>
              {/if}
            {/each}
          </div>
        {:else}
          <div class="empty-state">
            <i class="fa-solid fa-images"></i>
            <p>Keine Medien vorhanden</p>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
.mt-wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

/* ── Sub-Navigation ───────────────────────────────────────── */
.mt-nav {
  display: flex;
  gap: 2px;
  padding: 8px 16px;
  background: var(--bg1);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.mt-nav-btn {
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
.mt-nav-btn:hover { color: var(--text0); background: var(--bg2); }
.mt-nav-btn.active { color: var(--accent); border-color: var(--accent); background: var(--glow); }
.mt-cnt {
  font-size: 9px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
}

/* ── Body ─────────────────────────────────────────────────── */
.mt-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.mt-page {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  max-width: 1000px;
  width: 100%;
}

/* ── Dokumente ────────────────────────────────────────────── */
.doc-list { display: flex; flex-direction: column; gap: 6px; }
.doc-card {
  background: var(--bg1);
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 1px 3px var(--shadow);
}
.doc-card.reading { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent); }
.doc-card-hd {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background .12s;
}
.doc-card-hd:hover { background: var(--bg2); }
.doc-icon { font-size: 18px; color: var(--accent); flex-shrink: 0; }
.doc-card-body { flex: 1; }
.doc-card-title { font-size: 13px; font-weight: 600; color: var(--text1); }
.doc-card-meta { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
.doc-toggle { font-size: 10px; color: var(--text3); }
.doc-content {
  padding: 14px 16px;
  border-top: 1px solid var(--border);
  font-size: 13px;
  color: var(--text1);
  line-height: 1.7;
  max-height: 500px;
  overflow-y: auto;
}

/* ── Medien ───────────────────────────────────────────────── */
.media-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.media-item { background: var(--bg1); border-radius: 4px; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 1px 3px var(--shadow); }
.media-img img { width: 100%; height: 120px; object-fit: cover; display: block; }
.media-pdf { padding: 20px; align-items: center; text-decoration: none; color: var(--text1); gap: 6px; text-align: center; }
.media-pdf i { font-size: 28px; color: var(--err); }
.media-name { font-size: 10px; color: var(--text2); padding: 6px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.media-size { font-size: 9px; color: var(--text3); }

/* ── Empty ────────────────────────────────────────────────── */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 20px; gap: 8px; }
.empty-state i { font-size: 36px; color: var(--text3); opacity: .3; }
.empty-state p { font-size: 13px; color: var(--text3); }
</style>
