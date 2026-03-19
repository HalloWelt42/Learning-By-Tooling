<script>
  import { showToast, loadGlobal } from '../../stores/index.js'
  import { apiPost } from '../../utils/api.js'

  let { pkg } = $props()

  let importFragen = $state('')
  let importAntwt  = $state('')
  let importResult = $state(null)
  let importing    = $state(false)

  async function doImport() {
    if (!importFragen || !importAntwt) { showToast('Beide Texte einfügen', 'error'); return }
    importing = true
    try {
      importResult = await apiPost('/api/import/markdown', { fragen: importFragen, antworten: importAntwt, package_id: pkg.id })
      showToast(`${importResult.created} Karten importiert`, 'success')
      await loadGlobal()
    } catch(e) {
      showToast('Import fehlgeschlagen', 'error')
    }
    importing = false
  }
</script>

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
        {#if importResult.skipped > 0}
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
