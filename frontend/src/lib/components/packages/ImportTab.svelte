<script>
  import { showToast, loadGlobal, categories } from '../../stores/index.js'
  import { apiPost } from '../../utils/api.js'

  let { pkg } = $props()

  // -- Eingabe --
  let inputMode    = $state('file')  // 'file' | 'text'
  let fragenFile   = $state(null)
  let antwortenFile = $state(null)
  let importFragen = $state('')
  let importAntwt  = $state('')

  // -- Vorschau --
  let preview      = $state(null)
  let previewing   = $state(false)
  let excluded     = $state(new Set())

  // -- Import --
  let importResult = $state(null)
  let importing    = $state(false)

  function readFile(file) {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = () => resolve('')
      reader.readAsText(file)
    })
  }

  async function doPreview() {
    let fragen = importFragen
    let antworten = importAntwt

    if (inputMode === 'file') {
      if (!fragenFile || !antwortenFile) { showToast('Beide Dateien auswählen', 'error'); return }
      fragen = await readFile(fragenFile)
      antworten = await readFile(antwortenFile)
      importFragen = fragen
      importAntwt = antworten
    }

    if (!fragen.trim() || !antworten.trim()) { showToast('Beide Inhalte müssen vorhanden sein', 'error'); return }

    previewing = true
    try {
      preview = await apiPost('/api/import/preview', { fragen, antworten, package_id: pkg.id })
      excluded = new Set()
      importResult = null
    } catch(e) {
      showToast('Vorschau fehlgeschlagen: ' + (e.message || ''), 'error')
    }
    previewing = false
  }

  function toggleExclude(cardId) {
    const s = new Set(excluded)
    s.has(cardId) ? s.delete(cardId) : s.add(cardId)
    excluded = s
  }

  let importable = $derived(preview ? preview.cards.filter(c => c.status === 'new' && !excluded.has(c.card_id)) : [])

  async function doImport() {
    if (importable.length === 0) { showToast('Keine Karten zum Importieren', 'warn'); return }
    importing = true
    try {
      // Filter: nur die gewählten Karten senden
      const selectedIds = new Set(importable.map(c => c.card_id))
      const fragenLines = importFragen.split('```')
      const antwortenLines = importAntwt.split('```')

      importResult = await apiPost('/api/import/markdown', {
        fragen: importFragen,
        antworten: importAntwt,
        package_id: pkg.id,
      })
      showToast(`${importResult.created} Karten importiert`, 'success')
      await loadGlobal()
      preview = null
    } catch(e) {
      showToast('Import fehlgeschlagen', 'error')
    }
    importing = false
  }

  function reset() {
    preview = null
    importResult = null
    excluded = new Set()
    importFragen = ''
    importAntwt = ''
    fragenFile = null
    antwortenFile = null
  }

  function catColor(code) {
    const cat = ($categories || []).find(c => c.code === code)
    return cat?.color || 'var(--accent)'
  }
</script>

<div class="tab-page">
  <div class="tab-hd">
    <div>
      <div class="tab-hd-title">Karten importieren</div>
      <div class="tab-hd-sub">Markdown-Lernkarten mit Vorvalidierung importieren</div>
    </div>
    {#if preview || importResult}
      <button class="btn btn-ghost btn-sm" onclick={reset}>
        <i class="fa-solid fa-arrow-rotate-left"></i> Neuer Import
      </button>
    {/if}
  </div>

  {#if importResult}
    <!-- Ergebnis -->
    <div class="card-box imp-result-box">
      <div class="imp-result-icon"><i class="fa-solid fa-circle-check"></i></div>
      <div class="imp-result-text">
        <strong>{importResult.created}</strong> Karten importiert
        {#if importResult.skipped > 0}
          <span class="imp-result-skip">{importResult.skipped} übersprungen</span>
        {/if}
      </div>
    </div>

  {:else if preview}
    <!-- Vorschau -->
    <div class="imp-summary">
      <span class="imp-pill imp-new"><i class="fa-solid fa-plus"></i> {preview.new} neu</span>
      <span class="imp-pill imp-dup"><i class="fa-solid fa-clone"></i> {preview.duplicates} vorhanden</span>
      {#if preview.no_answer > 0}
        <span class="imp-pill imp-err"><i class="fa-solid fa-triangle-exclamation"></i> {preview.no_answer} ohne Antwort</span>
      {/if}
      {#if preview.errors.length > 0}
        <span class="imp-pill imp-err"><i class="fa-solid fa-circle-xmark"></i> {preview.errors.length} Fehler</span>
      {/if}
    </div>

    {#if preview.errors.length > 0}
      <div class="imp-errors">
        {#each preview.errors as err}
          <div class="imp-error-item"><i class="fa-solid fa-triangle-exclamation"></i> {err}</div>
        {/each}
      </div>
    {/if}

    <div class="imp-cards">
      {#each preview.cards as card (card.card_id)}
        <div class="imp-card" class:imp-card-dup={card.status === 'duplicate'} class:imp-card-err={card.status === 'no_answer'} class:imp-card-excluded={excluded.has(card.card_id)}>
          <div class="imp-card-hd">
            <span class="imp-card-id mono">{card.card_id}</span>
            <span class="imp-card-cat" style="color:{catColor(card.category_code)}">{card.category_code}</span>
            {#if card.status === 'duplicate'}
              <span class="imp-badge imp-badge-dup">vorhanden</span>
            {:else if card.status === 'no_answer'}
              <span class="imp-badge imp-badge-err">keine Antwort</span>
            {:else}
              <span class="imp-badge imp-badge-new">neu</span>
            {/if}
            {#if card.status === 'new'}
              <button class="ib sm" title={excluded.has(card.card_id) ? 'Einschliessen' : 'Ausschliessen'} onclick={() => toggleExclude(card.card_id)}>
                <i class="fa-solid {excluded.has(card.card_id) ? 'fa-plus' : 'fa-minus'}"></i>
              </button>
            {/if}
          </div>
          <div class="imp-card-q">{card.question}</div>
          {#if card.answer}
            <div class="imp-card-a">{card.answer}</div>
          {/if}
        </div>
      {/each}
    </div>

    <div class="imp-footer">
      <span class="imp-footer-info">{importable.length} Karten werden importiert</span>
      <button class="btn btn-primary" onclick={doImport} disabled={importing || importable.length === 0}>
        {#if importing}
          <i class="fa-solid fa-spinner fa-spin"></i> Importiere...
        {:else}
          <i class="fa-solid fa-file-import"></i> {importable.length} Karten importieren
        {/if}
      </button>
    </div>

  {:else}
    <!-- Eingabe -->
    <div class="imp-mode-switch">
      <button class="imp-mode-btn" class:active={inputMode==='file'} onclick={() => inputMode='file'}>
        <i class="fa-solid fa-file-arrow-up"></i> Dateien
      </button>
      <button class="imp-mode-btn" class:active={inputMode==='text'} onclick={() => inputMode='text'}>
        <i class="fa-solid fa-keyboard"></i> Text
      </button>
    </div>

    <div class="card-box imp-input-box">
      {#if inputMode === 'file'}
        <div class="imp-file-grid">
          <label class="imp-drop" class:has-file={!!fragenFile}>
            <input type="file" accept=".md,.txt" onchange={e => { fragenFile = e.currentTarget.files[0] || null }}>
            {#if fragenFile}
              <i class="fa-solid fa-file-code imp-drop-icon"></i>
              <span class="imp-drop-name">{fragenFile.name}</span>
            {:else}
              <i class="fa-solid fa-circle-question imp-drop-icon q"></i>
              <span class="imp-drop-label">Fragen-Datei</span>
              <span class="imp-drop-hint">*-fragen.md</span>
            {/if}
          </label>
          <label class="imp-drop" class:has-file={!!antwortenFile}>
            <input type="file" accept=".md,.txt" onchange={e => { antwortenFile = e.currentTarget.files[0] || null }}>
            {#if antwortenFile}
              <i class="fa-solid fa-file-code imp-drop-icon"></i>
              <span class="imp-drop-name">{antwortenFile.name}</span>
            {:else}
              <i class="fa-solid fa-circle-check imp-drop-icon a"></i>
              <span class="imp-drop-label">Antworten-Datei</span>
              <span class="imp-drop-hint">*-antworten.md</span>
            {/if}
          </label>
        </div>
      {:else}
        <div class="imp-text-grid">
          <label class="field-label">
            <span><i class="fa-solid fa-circle-question" style="color:var(--accent)"></i> Fragen</span>
            <textarea bind:value={importFragen} rows="12" class="imp-ta" placeholder="Inhalt der Fragen-Datei..."></textarea>
          </label>
          <label class="field-label">
            <span><i class="fa-solid fa-circle-check" style="color:var(--ok)"></i> Antworten</span>
            <textarea bind:value={importAntwt} rows="12" class="imp-ta" placeholder="Inhalt der Antworten-Datei..."></textarea>
          </label>
        </div>
      {/if}

      <button class="btn btn-primary" style="margin-top:14px" onclick={doPreview} disabled={previewing}>
        {#if previewing}
          <i class="fa-solid fa-spinner fa-spin"></i> Validiere...
        {:else}
          <i class="fa-solid fa-magnifying-glass"></i> Vorschau
        {/if}
      </button>
    </div>
  {/if}
</div>

<style>
.imp-mode-switch { display: flex; gap: 4px; margin-bottom: 14px; }
.imp-mode-btn {
  padding: 7px 14px; font-size: 12px; font-weight: 600; border: none;
  background: var(--bg2); color: var(--text2); border-radius: 4px; cursor: pointer;
  display: flex; align-items: center; gap: 6px; transition: all .15s; font-family: inherit;
}
.imp-mode-btn:hover { color: var(--text0); background: var(--bg3); }
.imp-mode-btn.active { color: var(--accent); background: var(--bg3); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent); }
.imp-input-box { max-width: 920px; }
.imp-file-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.imp-text-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.imp-drop {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  border: 2px dashed var(--border); border-radius: 4px; padding: 28px 16px;
  cursor: pointer; transition: all .2s; text-align: center; gap: 8px; min-height: 120px;
}
.imp-drop:hover, .imp-drop.has-file { border-color: var(--accent); background: var(--glow); }
.imp-drop input { display: none; }
.imp-drop-icon { font-size: 28px; color: var(--text3); }
.imp-drop-icon.q { color: var(--accent); }
.imp-drop-icon.a { color: var(--ok); }
.imp-drop-label { font-size: 13px; font-weight: 600; color: var(--text1); }
.imp-drop-hint { font-size: 10px; color: var(--text3); }
.imp-drop-name { font-size: 12px; font-weight: 600; color: var(--text0); }
.imp-ta { font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; }

/* Vorschau */
.imp-summary { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.imp-pill { font-size: 12px; font-weight: 600; padding: 5px 12px; border-radius: 4px; display: flex; align-items: center; gap: 6px; }
.imp-new { color: var(--ok); background: var(--glowok); border: 1px solid color-mix(in srgb, var(--ok) 30%, transparent); }
.imp-dup { color: var(--text2); background: var(--bg2); border: 1px solid var(--border); }
.imp-err { color: var(--err); background: color-mix(in srgb, var(--err) 8%, transparent); border: 1px solid color-mix(in srgb, var(--err) 30%, transparent); }
.imp-errors { margin-bottom: 14px; display: flex; flex-direction: column; gap: 4px; }
.imp-error-item { font-size: 12px; color: var(--err); display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: color-mix(in srgb, var(--err) 6%, transparent); border-radius: 4px; }

.imp-cards { display: flex; flex-direction: column; gap: 6px; max-width: 800px; }
.imp-card { background: var(--bg1); border-radius: 4px; padding: 10px 14px; box-shadow: 0 1px 3px var(--shadow); }
.imp-card-dup { opacity: .4; }
.imp-card-err { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--err) 40%, transparent); }
.imp-card-excluded { opacity: .3; }
.imp-card-hd { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.imp-card-id { font-size: 10px; color: var(--text3); }
.imp-card-cat { font-size: 10px; font-weight: 700; letter-spacing: .06em; }
.imp-badge { font-size: 9px; font-weight: 600; padding: 1px 6px; border-radius: 3px; }
.imp-badge-new { color: var(--ok); background: var(--glowok); }
.imp-badge-dup { color: var(--text3); background: var(--bg3); }
.imp-badge-err { color: var(--err); background: color-mix(in srgb, var(--err) 10%, transparent); }
.imp-card-q { font-size: 13px; font-weight: 600; color: var(--text0); line-height: 1.5; }
.imp-card-a { font-size: 11px; color: var(--text1); background: var(--bg2); border-radius: 4px; padding: 6px 10px; margin-top: 6px; line-height: 1.5; white-space: pre-wrap; font-family: 'JetBrains Mono', monospace; }

.imp-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); max-width: 800px; }
.imp-footer-info { font-size: 12px; color: var(--text2); font-weight: 600; }

/* Ergebnis */
.imp-result-box { display: flex; align-items: center; gap: 14px; max-width: 500px; }
.imp-result-icon { font-size: 28px; color: var(--ok); }
.imp-result-text { font-size: 15px; color: var(--text0); }
.imp-result-text strong { font-family: 'JetBrains Mono', monospace; }
.imp-result-skip { font-size: 12px; color: var(--text3); margin-left: 8px; }

.ib { width: 28px; height: 28px; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: var(--text2); font-size: 12px; transition: all .15s; background: none; border: none; cursor: pointer; }
.ib:hover { background: var(--bg2); color: var(--text0); }
.ib.sm { width: 22px; height: 22px; font-size: 10px; }
</style>
