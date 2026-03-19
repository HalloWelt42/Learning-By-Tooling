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
