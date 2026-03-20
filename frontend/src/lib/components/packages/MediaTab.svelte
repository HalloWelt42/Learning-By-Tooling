<script>
  import { apiGet } from '../../utils/api.js'
  import { onMount } from 'svelte'

  let { pkg } = $props()
  let media = $state([])

  onMount(loadMedia)

  async function loadMedia() {
    try { media = await apiGet(`/api/packages/${pkg.id}/media`) } catch(e) { media = [] }
  }
</script>

<div class="tab-page">
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
</div>

<style>
.media-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.media-item { background: var(--bg1); border: 1px solid var(--border); border-radius: 4px; overflow: hidden; display: flex; flex-direction: column; }
.media-img img { width: 100%; height: 120px; object-fit: cover; display: block; }
.media-pdf { padding: 20px; align-items: center; text-decoration: none; color: var(--text1); gap: 6px; text-align: center; }
.media-pdf i { font-size: 28px; color: var(--err); }
.media-name { font-size: 10px; color: var(--text2); padding: 6px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.media-size { font-size: 9px; color: var(--text3); }
</style>
