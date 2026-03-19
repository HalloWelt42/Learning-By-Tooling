<!-- Lexicon.svelte -->
<script>
  import { onMount } from 'svelte'
  import { categories, showToast } from '../../stores/index.js'
  import { apiGet, apiPost } from '../../utils/api.js'

  let entries  = $state([])
  let searchQ  = $state('')
  let filterCat= $state('')
  let selected = $state(null)
  let showForm = $state(false)
  let form     = $state({ term:'', definition:'', category_code:'', related_cards:[] })

  onMount(load)

  async function load() {
    const p = new URLSearchParams()
    if (searchQ)   p.set('search', searchQ)
    if (filterCat) p.set('category', filterCat)
    entries = await apiGet(`/api/lexicon?${p}`)
  }

  let st; function onSearch() { clearTimeout(st); st = setTimeout(load, 280) }

  async function save() {
    if (!form.term || !form.definition) { showToast('Begriff und Definition Pflicht','error'); return }
    await apiPost('/api/lexicon', { ...form, related_cards: form.related_cards||[] })
    showToast('Eintrag gespeichert','success')
    showForm = false
    form = { term:'', definition:'', category_code:'', related_cards:[] }
    await load()
  }

  $effect(() => { filterCat; load() })

  let grouped = $derived.by(() => {
    const g = {}
    for (const e of entries) {
      const l = (e.term[0] || '#').toUpperCase()
      if (!g[l]) g[l] = []
      g[l].push(e)
    }
    return Object.entries(g).sort(([a],[b]) => a.localeCompare(b))
  })
</script>

<div class="full-panel" style="grid-template-columns:280px 1fr">
  <div class="list-panel">
    <div class="lp-header">
      <span class="page-title" style="font-size:18px"><i class="fa-solid fa-book-open"></i> Lexikon</span>
      <button class="btn btn-primary btn-sm" onclick={() => showForm = true}><i class="fa-solid fa-plus"></i> Neu</button>
    </div>
    <div class="lp-filters">
      <input type="text" placeholder="Begriff suchen…" bind:value={searchQ} oninput={onSearch} />
      <select bind:value={filterCat}>
        <option value="">Alle Kategorien</option>
        {#each $categories as cat (cat.code)}<option value={cat.code}>{cat.icon} {cat.name}</option>{/each}
      </select>
    </div>
    <div class="card-list">
      {#each grouped as [letter, items]}
        <div class="lex-group">
          <div class="lex-letter">{letter}</div>
          {#each items as entry (entry.id)}
            <button
              class="cl-item" class:selected={selected?.id===entry.id}
              onclick={() => { selected = entry; showForm = false }}
            >
              <div class="cli-q" style="font-weight:600">{entry.term}</div>
              {#if entry.category_code}
                <div class="cli-cat" style="color:var(--accent)">{entry.category_code}</div>
              {/if}
            </button>
          {/each}
        </div>
      {/each}
      {#if entries.length === 0}
        <div style="padding:20px;text-align:center;color:var(--text3);font-size:12px">Keine Einträge</div>
      {/if}
    </div>
  </div>

  <div class="detail-panel" style="overflow-y:auto;background:var(--bg0)">
    {#if showForm}
      <div style="padding:24px;max-width:560px">
        <div class="form-hdr">
          <span style="font-weight:700">Neuer Eintrag</span>
          <button onclick={() => showForm = false} style="color:var(--text3)"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div style="display:flex;flex-direction:column;gap:12px">
          <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
            Begriff *
            <input type="text" bind:value={form.term} placeholder="Fachbegriff…" />
          </label>
          <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
            Definition *
            <textarea bind:value={form.definition} rows="5" placeholder="Erklärung…"></textarea>
          </label>
          <label style="display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:600;color:var(--text2)">
            Kategorie
            <select bind:value={form.category_code}>
              <option value="">Keine</option>
              {#each $categories as cat (cat.code)}<option value={cat.code}>{cat.icon} {cat.name}</option>{/each}
            </select>
          </label>
          <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
            <button class="btn btn-ghost" onclick={() => showForm = false}>Abbrechen</button>
            <button class="btn btn-primary" onclick={save}><i class="fa-solid fa-floppy-disk"></i> Speichern</button>
          </div>
        </div>
      </div>
    {:else if selected}
      <div style="padding:32px;max-width:680px">
        <div style="font-size:30px;font-weight:800;letter-spacing:-.02em;margin-bottom:8px">{selected.term}</div>
        {#if selected.category_code}
          <div style="display:inline-block;font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--accent);background:var(--glow);border:1px solid var(--accent);border-radius: 4px;padding:2px 8px;margin-bottom:18px">{selected.category_code}</div>
        {/if}
        <div style="font-size:14px;line-height:1.75;color:var(--text1);background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:18px 20px;white-space:pre-wrap">{selected.definition}</div>
      </div>
    {:else}
      <div class="empty-state"><i class="fa-solid fa-book-open"></i><p>Begriff auswählen</p></div>
    {/if}
  </div>
</div>

<style>
  .list-panel { border-right:1px solid var(--bdr2);display:flex;flex-direction:column;overflow:hidden;background:var(--bg1); }
  .lp-header { padding:20px 16px 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--bdr2);flex-shrink:0; }
  .lp-filters { padding:10px 14px;display:flex;flex-direction:column;gap:6px;border-bottom:1px solid var(--bdr2);flex-shrink:0; }
  .card-list { flex:1;overflow-y:auto;padding:6px; }
  .cl-item { display:block;width:100%;padding:8px 10px;border-radius: 4px;text-align:left;cursor:pointer;transition:background .12s;border:1px solid transparent;margin-bottom:2px; }
  .cl-item:hover { background:var(--bg2); }
  .cl-item.selected { background:var(--glow);border-color:var(--accent); }
  .cli-q { font-size:12px;color:var(--text1);line-height:1.4;margin-bottom:2px; }
  .cli-cat { font-size:9px;font-weight:700;letter-spacing:.1em; }
  .lex-group { margin-bottom:10px; }
  .lex-letter { font-size:9px;font-weight:700;letter-spacing:.15em;color:var(--accent);padding:3px 8px;font-family:'JetBrains Mono',monospace; }
  .form-hdr { display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid var(--border);font-size:14px; }
  .detail-panel { overflow-y:auto; }
</style>
