<script>
  /**
   * MistakeAnalysis.svelte
   * Nach einer Lerneinheit: zeigt falsche Karten + relevante Dokumentpassagen.
   * 2-Tab-Ansicht: Auszüge (KI-kuratiert) ↔ Dokument (Volltext, Passage hervorgehoben)
   */
  import { apiPost, apiGet } from '../../utils/api.js'

  let { wrongCards = [], packageId = null, onClose = () => {} } = $props()

  // State
  let loading      = $state(true)
  let error        = $state('')
  let results      = $state([])         // [{card_id, question, answer, references}]
  let activeCard   = $state(0)          // Index der aktiven Karte
  let activeTab    = $state('excerpts') // 'excerpts' | 'document'
  let activeRef    = $state(null)       // aktive Referenz für Dokumentansicht
  let docData      = $state(null)       // {title, chunks}
  let docLoading   = $state(false)
  let docError     = $state('')

  // Analyse beim Mount starten
  $effect(() => {
    if (wrongCards.length > 0 && packageId) {
      runAnalysis()
    } else {
      loading = false
      error = 'Keine falschen Karten oder kein Paket angegeben.'
    }
  })

  async function runAnalysis() {
    loading = true
    error = ''
    try {
      const r = await apiPost('/api/learn/analyze-mistakes', {
        card_ids:   wrongCards.map(c => c.id),
        package_id: packageId,
      })
      if (r.error) {
        error = r.error
        results = []
      } else {
        results = r.results || []
        if (results.length > 0 && results[0].references?.length > 0) {
          activeRef = results[0].references[0]
        }
      }
    } catch(e) {
      error = e.message || 'Analyse fehlgeschlagen.'
    }
    loading = false
  }

  async function loadDocument(ref) {
    if (!ref?.doc_id) return
    activeRef   = ref
    activeTab   = 'document'
    docLoading  = true
    docError    = ''
    docData     = null
    try {
      docData = await apiGet(`/api/documents/${ref.doc_id}/chunks`)
    } catch(e) {
      docError = 'Dokument konnte nicht geladen werden.'
    }
    docLoading = false
  }

  function highlightPassage(text, passage) {
    if (!passage || !text) return escapeHtml(text)
    // Erste 60 Zeichen der Passage als Suchstring
    const needle = passage.slice(0, 60).trim()
    if (!needle) return escapeHtml(text)
    const idx = text.indexOf(needle)
    if (idx === -1) return escapeHtml(text)
    return (
      escapeHtml(text.slice(0, idx)) +
      '<mark class="hl">' + escapeHtml(text.slice(idx, idx + passage.length)) + '</mark>' +
      escapeHtml(text.slice(idx + passage.length))
    )
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  function selectCard(i) {
    activeCard = i
    activeTab  = 'excerpts'
    activeRef  = results[i]?.references?.[0] || null
    docData    = null
  }
</script>

<div class="ma-overlay">
  <div class="ma-panel">

    <!-- Header -->
    <div class="ma-header">
      <div class="ma-title">
        <i class="fa-solid fa-magnifying-glass-chart" style="color:var(--accent)"></i>
        Fehleranalyse
        {#if results.length > 0}
          <span class="ma-count">{results.length} Karte{results.length !== 1 ? 'n' : ''} analysiert</span>
        {/if}
      </div>
      <button class="ma-close" onclick={onClose} aria-label="Schließen">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    {#if loading}
      <!-- Lade-Ansicht -->
      <div class="ma-loading">
        <div class="ma-loading-icon">
          <i class="fa-solid fa-spinner fa-spin"></i>
        </div>
        <div class="ma-loading-text">LM Studio analysiert deine Fehler...</div>
        <div class="ma-loading-sub">
          Suche relevante Passagen in {wrongCards.length} Karte{wrongCards.length !== 1 ? 'n' : ''}
        </div>
      </div>

    {:else if error}
      <div class="ma-error">
        <i class="fa-solid fa-triangle-exclamation"></i>
        {error}
        <button class="btn btn-ghost btn-sm" onclick={runAnalysis}>
          <i class="fa-solid fa-rotate"></i> Erneut versuchen
        </button>
      </div>

    {:else if results.length === 0}
      <div class="ma-empty">
        <i class="fa-solid fa-face-meh"></i>
        Keine Analyse-Ergebnisse. Sind Dokumente im Paket hochgeladen?
      </div>

    {:else}
      <div class="ma-body">

        <!-- Linke Spalte: Karten-Liste -->
        <div class="ma-cards-col">
          <div class="section-label">Falsche Karten</div>
          <div class="ma-card-list">
            {#each results as r, i}
              <button
                class="ma-card-item"
                class:active={activeCard === i}
                onclick={() => selectCard(i)}
              >
                <div class="ma-card-q">{r.question}</div>
                <div class="ma-card-refs">
                  <i class="fa-solid fa-book-open"></i>
                  {r.references?.length || 0} Fundstelle{(r.references?.length || 0) !== 1 ? 'n' : ''}
                </div>
              </button>
            {/each}
          </div>
        </div>

        <!-- Rechte Spalte: Inhaltsbereich -->
        <div class="ma-content-col">
          {#if results[activeCard]}
            {@const card = results[activeCard]}

            <!-- Karten-Info -->
            <div class="ma-card-info">
              <div class="ma-card-info-q">
                <i class="fa-solid fa-circle-question" style="color:var(--accent)"></i>
                {card.question}
              </div>
              <div class="ma-card-info-a">
                <i class="fa-solid fa-circle-check" style="color:var(--ok)"></i>
                {card.answer}
              </div>
            </div>

            <!-- Tab-Leiste -->
            <div class="ma-tabs">
              <button
                class="ma-tab"
                class:active={activeTab === 'excerpts'}
                onclick={() => activeTab = 'excerpts'}
              >
                <i class="fa-solid fa-scissors"></i>
                Auszüge
                <span class="ma-tab-badge">{card.references?.length || 0}</span>
              </button>
              <button
                class="ma-tab"
                class:active={activeTab === 'document'}
                onclick={() => { if (activeRef) loadDocument(activeRef); else activeTab = 'document' }}
                disabled={!activeRef}
              >
                <i class="fa-solid fa-file-lines"></i>
                Dokument
                {#if activeRef}
                  <span class="ma-tab-source">{activeRef.doc_title}</span>
                {/if}
              </button>
            </div>

            <!-- Tab-Inhalt -->
            <div class="ma-tab-content">

              {#if activeTab === 'excerpts'}
                <!-- Auszüge-Tab -->
                {#if !card.references?.length}
                  <div class="ma-no-refs">
                    Keine Dokumentpassagen gefunden. Lade Lerndokumente in dieses Paket hoch.
                  </div>
                {:else}
                  <div class="ma-excerpts">
                    {#each card.references as ref, ri}
                      <div class="ma-excerpt" class:active-ref={activeRef === ref}>
                        <div class="ma-excerpt-header">
                          <div class="ma-excerpt-source">
                            <i class="fa-solid fa-file-lines"></i>
                            {ref.doc_title}
                            {#if ref.chunk_index !== undefined}
                              <span class="ma-chunk-idx">Abschnitt {ref.chunk_index + 1}</span>
                            {/if}
                          </div>
                          <button
                            class="btn btn-ghost btn-sm"
                            title="Im Dokument anzeigen"
                            onclick={() => loadDocument(ref)}
                          >
                            <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            Im Dokument
                          </button>
                        </div>

                        {#if ref.explanation}
                          <div class="ma-excerpt-why">
                            <i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i>
                            {ref.explanation}
                          </div>
                        {/if}

                        <div class="ma-excerpt-text">
                          {ref.passage}
                        </div>
                      </div>
                    {/each}
                  </div>
                {/if}

              {:else}
                <!-- Dokument-Tab -->
                {#if docLoading}
                  <div class="ma-doc-loading">
                    <i class="fa-solid fa-spinner fa-spin"></i>
                    Dokument wird geladen...
                  </div>
                {:else if docError}
                  <div class="ma-error">{docError}</div>
                {:else if docData}
                  <div class="ma-doc-view">
                    <div class="ma-doc-title">
                      <i class="fa-solid fa-file-lines" style="color:var(--accent)"></i>
                      {docData.title}
                      <span class="ma-chunk-count">{docData.chunks?.length} Abschnitte</span>
                    </div>
                    <div class="ma-doc-chunks">
                      {#each docData.chunks as chunk}
                        <div
                          class="ma-doc-chunk"
                          class:highlighted={activeRef?.chunk_id === chunk.id}
                          id="chunk-{chunk.id}"
                        >
                          <div class="ma-chunk-num">#{chunk.chunk_index + 1}</div>
                          {#if activeRef?.chunk_id === chunk.id}
                            <div class="ma-chunk-text">
                              {@html highlightPassage(chunk.text, activeRef?.passage)}
                            </div>
                          {:else}
                            <div class="ma-chunk-text">{chunk.text}</div>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  </div>
                {:else}
                  <div class="ma-no-refs">
                    Klicke auf "Im Dokument" bei einem Auszug um das Dokument zu öffnen.
                  </div>
                {/if}
              {/if}

            </div>
          {/if}
        </div>

      </div>
    {/if}

  </div>
</div>

<style>
.ma-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.7);
  z-index: 500;
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
  backdrop-filter: blur(4px);
}
.ma-panel {
  width: min(95vw, 1100px);
  height: 100vh;
  background: var(--bg1);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.ma-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg0);
  flex-shrink: 0;
}
.ma-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 700;
  color: var(--text0);
}
.ma-count {
  font-size: 12px;
  font-weight: 400;
  color: var(--text3);
  background: var(--bg2);
  padding: 3px 10px;
  border-radius: 4px;
}
.ma-close {
  width: 32px; height: 32px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text2);
  cursor: pointer;
  font-size: 15px;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.ma-close:hover { color: var(--err); border-color: var(--err); }

/* Loading */
.ma-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: var(--text2);
}
.ma-loading-icon { font-size: 36px; color: var(--accent); }
.ma-loading-text { font-size: 16px; font-weight: 600; color: var(--text1); }
.ma-loading-sub  { font-size: 13px; }

/* Error / Empty */
.ma-error, .ma-empty {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 14px; color: var(--text2); font-size: 14px; text-align: center; padding: 40px;
}
.ma-error i { font-size: 28px; color: var(--warn); }
.ma-empty i { font-size: 32px; }

/* Body: 2-Spalten -->
.ma-body {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr;
  overflow: hidden;
}

/* Linke Spalte: Karten-Liste */
.ma-cards-col {
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 12px;
  gap: 8px;
}
.ma-card-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ma-card-item {
  text-align: left;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all .15s;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ma-card-item:hover    { border-color: var(--accent); }
.ma-card-item.active   { border-color: var(--accent); background: var(--glow); }
.ma-card-q    { font-size: 12px; color: var(--text1); line-height: 1.4; }
.ma-card-refs { font-size: 11px; color: var(--text3); display: flex; align-items: center; gap: 5px; }

/* Rechte Spalte */
.ma-content-col {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Karten-Info */
.ma-card-info {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg0);
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
.ma-card-info-q, .ma-card-info-a {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.5;
}
.ma-card-info-q { color: var(--text1); font-weight: 500; }
.ma-card-info-a { color: var(--text2); }
.ma-card-info-q i, .ma-card-info-a i { flex-shrink: 0; margin-top: 2px; }

/* Tab-Leiste */
.ma-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.ma-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text2);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all .15s;
  margin-bottom: -1px;
}
.ma-tab:hover:not(:disabled) { color: var(--text0); }
.ma-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.ma-tab:disabled { opacity: .4; cursor: default; }
.ma-tab-badge {
  background: var(--accent);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
}
.ma-tab-source {
  font-size: 11px;
  color: var(--text3);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Tab-Inhalt */
.ma-tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.ma-no-refs {
  color: var(--text3);
  font-size: 13px;
  text-align: center;
  padding: 40px 20px;
}

/* Auszüge */
.ma-excerpts { display: flex; flex-direction: column; gap: 16px; }
.ma-excerpt {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  transition: border-color .15s;
}
.ma-excerpt.active-ref { border-color: var(--accent); }
.ma-excerpt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
}
.ma-excerpt-source {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
}
.ma-chunk-idx {
  font-size: 10px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
  background: var(--bg4);
  padding: 1px 6px;
  border-radius: 4px;
}
.ma-excerpt-why {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px 0;
  font-size: 12px;
  color: var(--text2);
  font-style: italic;
  line-height: 1.5;
}
.ma-excerpt-text {
  padding: 10px 14px 14px;
  font-size: 13px;
  color: var(--text1);
  line-height: 1.7;
  font-family: 'JetBrains Mono', monospace;
  white-space: pre-wrap;
}

/* Dokument-Ansicht */
.ma-doc-loading {
  display: flex; align-items: center; gap: 10px;
  color: var(--text2); font-size: 14px; padding: 40px;
  justify-content: center;
}
.ma-doc-view { display: flex; flex-direction: column; gap: 12px; }
.ma-doc-title {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text0);
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.ma-chunk-count {
  font-size: 11px;
  color: var(--text3);
  font-weight: 400;
  font-family: 'JetBrains Mono', monospace;
}
.ma-doc-chunks { display: flex; flex-direction: column; gap: 8px; }
.ma-doc-chunk {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid transparent;
  background: var(--bg2);
  transition: all .2s;
}
.ma-doc-chunk.highlighted {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--bg2));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 30%, transparent);
}
.ma-chunk-num {
  font-size: 10px;
  color: var(--text3);
  font-family: 'JetBrains Mono', monospace;
  padding-top: 2px;
  flex-shrink: 0;
  width: 28px;
}
.ma-chunk-text {
  font-size: 12px;
  color: var(--text1);
  line-height: 1.7;
  white-space: pre-wrap;
}
:global(.hl) {
  background: color-mix(in srgb, var(--warn) 35%, transparent);
  color: var(--text0);
  border-radius: 2px;
  padding: 0 2px;
}
</style>
