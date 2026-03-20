<script>
  import { showToast } from '../../stores/index.js'
  import { apiGet, apiPost, apiPatch } from '../../utils/api.js'

  // Provider-State
  let providers = $state([])
  let activeProvider = $state('')
  let providerUrl = $state('')
  let testBusy = $state(false)
  let providerStatus = $state(null) // { online, model }

  // Templates
  let templates = $state([])
  let openSlug = $state('')
  let saveBusy = $state({})
  let resetBusy = $state({})

  // Editierbare Kopien der Templates
  let edits = $state({})

  $effect(() => { loadData() })

  async function loadData() {
    try {
      const [tpl, prov] = await Promise.all([
        apiGet('/api/ai/templates'),
        apiGet('/api/ai/providers'),
      ])
      templates = tpl
      providers = prov.providers || prov
      if (prov.active) {
        activeProvider = prov.active.name || ''
        providerUrl = prov.active.url || ''
        providerStatus = prov.active.status || null
      } else if (Array.isArray(providers) && providers.length > 0) {
        activeProvider = providers[0].name || providers[0]
        providerUrl = providers[0].url || ''
      }
      // Editierbare Kopien anlegen
      const e = {}
      for (const t of tpl) {
        e[t.slug] = {
          system_prompt: t.system_prompt || '',
          user_prompt: t.user_prompt || '',
          temperature: t.temperature ?? 0.3,
          max_tokens: t.max_tokens ?? 500,
          timeout: t.timeout ?? 30,
        }
      }
      edits = e
    } catch(err) {
      showToast('KI-Konfiguration konnte nicht geladen werden: ' + err.message, 'error')
    }
  }

  async function testProvider() {
    testBusy = true
    try {
      const result = await apiPost('/api/ai/providers/test', {
        provider: activeProvider,
        url: providerUrl,
      })
      providerStatus = result
      showToast(result.online ? 'Verbindung erfolgreich' : 'Verbindung fehlgeschlagen', result.online ? 'success' : 'error', 2500)
    } catch(err) {
      providerStatus = { online: false }
      showToast('Verbindungstest fehlgeschlagen: ' + err.message, 'error')
    }
    testBusy = false
  }

  function toggleTemplate(slug) {
    openSlug = openSlug === slug ? '' : slug
  }

  async function saveTemplate(slug) {
    saveBusy = { ...saveBusy, [slug]: true }
    try {
      const data = edits[slug]
      const updated = await apiPatch(`/api/ai/templates/${slug}`, {
        system_prompt: data.system_prompt,
        user_prompt: data.user_prompt,
        temperature: data.temperature,
        max_tokens: data.max_tokens,
        timeout: data.timeout,
      })
      // Template in Liste aktualisieren
      templates = templates.map(t => t.slug === slug ? { ...t, ...updated } : t)
      showToast('Template gespeichert', 'success', 2000)
    } catch(err) {
      showToast('Fehler beim Speichern: ' + err.message, 'error')
    }
    saveBusy = { ...saveBusy, [slug]: false }
  }

  async function resetTemplate(slug) {
    resetBusy = { ...resetBusy, [slug]: true }
    try {
      const updated = await apiPost(`/api/ai/templates/${slug}/reset`)
      templates = templates.map(t => t.slug === slug ? { ...t, ...updated } : t)
      // Edit-Kopie aktualisieren
      edits = {
        ...edits,
        [slug]: {
          system_prompt: updated.system_prompt || '',
          user_prompt: updated.user_prompt || '',
          temperature: updated.temperature ?? 0.3,
          max_tokens: updated.max_tokens ?? 500,
          timeout: updated.timeout ?? 30,
        },
      }
      showToast('Template zurückgesetzt', 'success', 2000)
    } catch(err) {
      showToast('Fehler beim Zurücksetzen: ' + err.message, 'error')
    }
    resetBusy = { ...resetBusy, [slug]: false }
  }
</script>

<div class="ai-config">

  <!-- Provider-Bereich -->
  <div class="provider-box">
    <div class="provider-row">
      <select class="provider-select" bind:value={activeProvider}>
        {#each providers as p}
          <option value={typeof p === 'string' ? p : p.name}>{typeof p === 'string' ? p : p.name}</option>
        {/each}
        {#if providers.length === 0}
          <option value="lmstudio">lmstudio</option>
          <option value="ollama">ollama</option>
        {/if}
      </select>
      <input type="text" class="provider-url" bind:value={providerUrl} placeholder="http://localhost:1234" />
      <button class="btn btn-primary btn-sm" onclick={testProvider} disabled={testBusy}>
        {testBusy ? 'Teste...' : 'Testen'}
      </button>
      {#if providerStatus}
        <span class="provider-badge" class:online={providerStatus.online} class:offline={!providerStatus.online}>
          {providerStatus.online ? 'Online' : 'Offline'}
          {#if providerStatus.model}
            <span class="provider-model">({providerStatus.model})</span>
          {/if}
        </span>
      {/if}
    </div>
  </div>

  <!-- Template-Liste -->
  <div class="tpl-list">
    {#each templates as tpl (tpl.slug)}
      {@const ed = edits[tpl.slug]}
      {#if ed}
        <div class="tpl-item" class:open={openSlug === tpl.slug}>
          <button class="tpl-header" onclick={() => toggleTemplate(tpl.slug)}>
            <i class="fa-solid fa-chevron-right tpl-chevron" class:rotated={openSlug === tpl.slug}></i>
            <span class="tpl-name">{tpl.display_name || tpl.slug}</span>
            <span class="tpl-desc">{tpl.description || ''}</span>
          </button>

          {#if openSlug === tpl.slug}
            <div class="tpl-body">
              <!-- System-Prompt -->
              <div class="tpl-field">
                <label class="tpl-label">System-Prompt</label>
                <textarea class="tpl-textarea" rows="6"
                  bind:value={ed.system_prompt}></textarea>
              </div>

              <!-- User-Prompt -->
              <div class="tpl-field">
                <label class="tpl-label">User-Prompt</label>
                <textarea class="tpl-textarea" rows="6"
                  bind:value={ed.user_prompt}></textarea>
              </div>

              <!-- Platzhalter -->
              {#if tpl.placeholders && tpl.placeholders.length > 0}
                <div class="tpl-field">
                  <label class="tpl-label">Platzhalter</label>
                  <div class="placeholder-tags">
                    {#each tpl.placeholders as ph}
                      <span class="placeholder-tag">{ph}</span>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Parameter -->
              <div class="tpl-params">
                <div class="tpl-param">
                  <label class="tpl-param-label">
                    Temperature <span class="mono">{ed.temperature}</span>
                  </label>
                  <input type="range" class="range-input" min="0" max="1" step="0.05"
                    bind:value={ed.temperature} />
                </div>
                <div class="tpl-param">
                  <label class="tpl-param-label">
                    Max Tokens <span class="mono">{ed.max_tokens}</span>
                  </label>
                  <input type="range" class="range-input" min="50" max="4000" step="50"
                    bind:value={ed.max_tokens} />
                </div>
                <div class="tpl-param">
                  <label class="tpl-param-label">
                    Timeout <span class="mono">{ed.timeout}s</span>
                  </label>
                  <input type="range" class="range-input" min="5" max="120" step="5"
                    bind:value={ed.timeout} />
                </div>
              </div>

              <!-- Aktionen -->
              <div class="tpl-actions">
                <button class="btn btn-primary btn-sm" onclick={() => saveTemplate(tpl.slug)}
                  disabled={saveBusy[tpl.slug]}>
                  <i class="fa-solid fa-floppy-disk"></i>
                  {saveBusy[tpl.slug] ? 'Speichern...' : 'Speichern'}
                </button>
                <button class="btn btn-ghost btn-sm" onclick={() => resetTemplate(tpl.slug)}
                  disabled={resetBusy[tpl.slug]}>
                  <i class="fa-solid fa-arrow-rotate-left"></i>
                  {resetBusy[tpl.slug] ? 'Zurücksetzen...' : 'Zurücksetzen'}
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    {/each}

    {#if templates.length === 0}
      <div class="tpl-empty">
        <i class="fa-solid fa-circle-info"></i> Keine Templates gefunden. Ist das Backend erreichbar?
      </div>
    {/if}
  </div>
</div>

<style>
  .ai-config {
    padding: 0 20px 40px;
  }

  /* Provider */
  .provider-box {
    background: var(--bg1); border-radius: 4px; padding: 14px;
    margin-bottom: 16px; box-shadow: 0 1px 3px var(--shadow);
  }
  .provider-row {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }
  .provider-select {
    background: var(--bg2); border: 1px solid var(--border); border-radius: 3px;
    padding: 6px 10px; font-size: 12px; color: var(--text0); font-family: inherit;
    cursor: pointer;
  }
  .provider-select:focus { border-color: var(--accent); outline: none; }
  .provider-url {
    background: var(--bg2); border: 1px solid var(--border); border-radius: 3px;
    padding: 6px 10px; font-size: 12px; color: var(--text0); font-family: inherit;
    flex: 1; min-width: 180px;
  }
  .provider-url:focus { border-color: var(--accent); outline: none; }
  .provider-badge {
    font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 3px;
    display: inline-flex; align-items: center; gap: 4px;
  }
  .provider-badge.online {
    color: #4caf50; background: color-mix(in srgb, #4caf50 12%, transparent);
  }
  .provider-badge.offline {
    color: #f44336; background: color-mix(in srgb, #f44336 12%, transparent);
  }
  .provider-model { font-weight: 400; font-size: 10px; color: var(--text3); }

  /* Template-Liste */
  .tpl-list {
    display: flex; flex-direction: column; gap: 6px;
  }
  .tpl-item {
    background: var(--bg1); border-radius: 4px;
    box-shadow: 0 1px 3px var(--shadow); overflow: hidden;
  }
  .tpl-header {
    display: flex; align-items: center; gap: 8px; width: 100%;
    padding: 12px 14px; border: none; background: transparent;
    cursor: pointer; font-family: inherit; text-align: left;
    color: var(--text0); font-size: 13px;
  }
  .tpl-header:hover { background: var(--bg2); }
  .tpl-chevron {
    font-size: 10px; color: var(--text3); transition: transform .15s;
    flex-shrink: 0;
  }
  .tpl-chevron.rotated { transform: rotate(90deg); }
  .tpl-name { font-weight: 700; flex-shrink: 0; }
  .tpl-desc {
    font-size: 11px; color: var(--text3); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }

  /* Template-Body */
  .tpl-body {
    padding: 0 14px 14px; display: flex; flex-direction: column; gap: 12px;
    border-top: 1px solid var(--border);
  }
  .tpl-field { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
  .tpl-field:first-child { margin-top: 12px; }
  .tpl-label {
    font-size: 10px; font-weight: 700; color: var(--text3);
    text-transform: uppercase; letter-spacing: .06em;
  }
  .tpl-textarea {
    background: var(--bg2); border: 1px solid var(--border); border-radius: 3px;
    padding: 8px 10px; font-size: 12px; color: var(--text0);
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    line-height: 1.5; resize: vertical; min-height: 80px;
  }
  .tpl-textarea:focus { border-color: var(--accent); outline: none; }

  /* Platzhalter-Tags */
  .placeholder-tags { display: flex; flex-wrap: wrap; gap: 4px; }
  .placeholder-tag {
    font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 3px;
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    color: var(--accent); font-family: 'JetBrains Mono', 'Fira Code', monospace;
  }

  /* Parameter */
  .tpl-params {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px;
  }
  .tpl-param { display: flex; flex-direction: column; gap: 4px; }
  .tpl-param-label {
    font-size: 11px; color: var(--text2);
    display: flex; justify-content: space-between; align-items: center;
  }

  /* Range-Slider (gleich wie Settings) */
  .range-input {
    -webkit-appearance: none; appearance: none; width: 100%; height: 4px;
    background: var(--bg3); border-radius: 2px; outline: none; cursor: pointer;
  }
  .range-input::-webkit-slider-thumb {
    -webkit-appearance: none; width: 14px; height: 14px; border-radius: 2px;
    background: var(--accent); border: none; cursor: pointer;
  }
  .range-input::-moz-range-thumb {
    width: 14px; height: 14px; border-radius: 2px;
    background: var(--accent); border: none; cursor: pointer;
  }

  /* Aktionen */
  .tpl-actions {
    display: flex; gap: 8px; padding-top: 4px;
  }

  /* Leer-Zustand */
  .tpl-empty {
    font-size: 12px; color: var(--text3); padding: 20px;
    text-align: center; background: var(--bg1); border-radius: 4px;
  }
  .tpl-empty i { margin-right: 4px; }

  .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
</style>
