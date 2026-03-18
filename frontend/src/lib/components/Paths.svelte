<!-- Paths.svelte -->
<script>
  import { onMount } from 'svelte'
  import { categories, currentView, showToast } from '../stores/index.js'
  import { apiGet, apiPost } from '../utils/api.js'

  let paths    = $state([])
  let showForm = $state(false)
  let form     = $state({ name:'', description:'', category_codes:[], card_ids:[] })

  onMount(async () => { paths = await apiGet('/api/paths') })

  async function save() {
    if (!form.name) { showToast('Name ist Pflicht','error'); return }
    await apiPost('/api/paths', form)
    showToast('Lernpfad erstellt','success')
    showForm = false
    form = { name:'', description:'', category_codes:[], card_ids:[] }
    paths = await apiGet('/api/paths')
  }
</script>

<div class="page">
  <div class="page-hd">
    <div>
      <h1 class="page-title"><i class="fa-solid fa-route"></i> Lernpfade</h1>
      <p class="page-sub">Strukturierte Lernreihenfolgen definieren</p>
    </div>
    <button class="btn btn-primary" onclick={() => showForm = !showForm}><i class="fa-solid fa-plus"></i> Neuer Pfad</button>
  </div>

  {#if showForm}
    <div class="card-box" style="max-width:580px;margin-bottom:24px">
      <div style="font-size:14px;font-weight:700;margin-bottom:16px">Neuer Lernpfad</div>
      <div style="display:flex;flex-direction:column;gap:12px">
        <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
          Name *<input type="text" bind:value={form.name} placeholder="z.B. Grundlagen Modul 1" />
        </label>
        <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
          Beschreibung<textarea bind:value={form.description} rows="2"></textarea>
        </label>
        <div>
          <div class="section-label">Kategorien einschließen</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;padding:10px;background:var(--bg2);border-radius: 4px;border:1px solid var(--border)">
            {#each $categories as cat (cat.code)}
              <label style="display:flex;align-items:center;gap:5px;font-size:11px;cursor:pointer">
                <input type="checkbox" bind:group={form.category_codes} value={cat.code}
                       style="accent-color:{cat.color}" />
                {cat.icon} {cat.code}
              </label>
            {/each}
          </div>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button class="btn btn-ghost" onclick={() => showForm = false}><i class="fa-solid fa-xmark"></i> Abbrechen</button>
          <button class="btn btn-primary" onclick={save}><i class="fa-solid fa-floppy-disk"></i> Erstellen</button>
        </div>
      </div>
    </div>
  {/if}

  {#if paths.length === 0}
    <div class="empty-state"><i class="fa-solid fa-route"></i><p>Noch keine Lernpfade</p></div>
  {:else}
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px">
      {#each paths as path (path.id)}
        <div class="card-box" style="display:flex;flex-direction:column;gap:10px;transition:border-color .2s">
          <div style="font-size:15px;font-weight:700">{path.name}</div>
          {#if path.description}
            <div style="font-size:12px;color:var(--text2);line-height:1.5">{path.description}</div>
          {/if}
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            {#each (path.category_codes||[]) as code}
              {@const cat = $categories.find(c=>c.code===code)}
              {#if cat}
                <span class="tag" style="background:var(--bg2);color:{cat.color};border:1px solid {cat.color}">
                  {cat.icon} {code}
                </span>
              {/if}
            {/each}
          </div>
          <button class="btn btn-primary btn-sm" style="align-self:flex-start;margin-top:4px"
                  onclick={() => currentView.set('learn')}><i class="fa-solid fa-play"></i> Starten</button>
        </div>
      {/each}
    </div>
  {/if}
</div>
