<script>
  import { categories, showToast } from '../../stores/index.js'
  import { apiGet, apiPost } from '../../utils/api.js'
  import { onMount } from 'svelte'

  let { pkg } = $props()

  let lexicon = $state([])
  let showLexForm = $state(false)
  let lexForm = $state({ term: '', definition: '', category_code: '' })

  onMount(loadLexicon)

  async function loadLexicon() {
    lexicon = await apiGet(`/api/packages/${pkg.id}/lexicon`).catch(() => [])
  }

  async function saveLex() {
    try {
      await apiPost('/api/lexicon', { ...lexForm, package_id: pkg.id })
      showToast('Eintrag gespeichert', 'success')
      lexForm = { term: '', definition: '', category_code: '' }
      showLexForm = false
      await loadLexicon()
    } catch(e) { showToast(e.message, 'error') }
  }

  let lexGrouped = $derived(
    Object.entries(
      (lexicon || []).reduce((acc, e) => {
        const letter = (e.term || '?')[0].toUpperCase()
        ;(acc[letter] = acc[letter] || []).push(e)
        return acc
      }, {})
    ).sort((a, b) => a[0].localeCompare(b[0]))
  )
</script>

<div class="tab-page">
  <div class="tab-hd">
    <div>
      <div class="tab-hd-title">Lexikon</div>
      <div class="tab-hd-sub">Fachbegriffe dieses Pakets</div>
    </div>
    <button class="btn btn-primary" onclick={() => showLexForm = !showLexForm}>
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
        <button class="btn btn-ghost btn-sm" onclick={() => showLexForm = false}>Abbrechen</button>
        <button class="btn btn-primary btn-sm" onclick={saveLex}>
          <i class="fa-solid fa-floppy-disk"></i> Speichern
        </button>
      </div>
    </div>
  {/if}
  {#if lexicon.length === 0}
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

<style>
.lex-group { margin-bottom: 20px; }
.lex-letter { font-size: 11px; font-weight: 700; letter-spacing: .12em; color: var(--accent); font-family: 'JetBrains Mono', monospace; padding-bottom: 8px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
.lex-entry { margin-bottom: 8px; }
.lex-term { font-size: 16px; font-weight: 700; color: var(--text0); margin-bottom: 8px; }
.lex-def { font-size: 13px; color: var(--text1); line-height: 1.7; white-space: pre-wrap; }
</style>
