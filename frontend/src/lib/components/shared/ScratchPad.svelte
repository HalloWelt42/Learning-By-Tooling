<script>
  import { onMount } from 'svelte'

  let { visible = false, onClose = () => {} } = $props()

  const STORAGE_KEY = 'lv-scratchpad'
  const POS_KEY = 'lv-scratchpad-pos'

  let text = $state('')
  let x = $state(320)
  let y = $state(80)
  let w = $state(320)
  let h = $state(260)
  let dragging = $state(false)
  let resizing = $state(false)
  let dragOff = { dx: 0, dy: 0 }
  let padEl = $state(null)
  let taEl = $state(null)

  onMount(() => {
    // Text laden
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) text = saved

    // Position laden
    const pos = localStorage.getItem(POS_KEY)
    if (pos) {
      try {
        const p = JSON.parse(pos)
        x = p.x ?? 320; y = p.y ?? 80; w = p.w ?? 320; h = p.h ?? 260
      } catch(e) {}
    }
  })

  function saveText() {
    localStorage.setItem(STORAGE_KEY, text)
  }

  function savePos() {
    localStorage.setItem(POS_KEY, JSON.stringify({ x, y, w, h }))
  }

  function clearPad() {
    text = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  function copyAll() {
    if (text) {
      navigator.clipboard.writeText(text).catch(() => {})
    }
  }

  // Drag
  function startDrag(e) {
    if (e.target.closest('.sp-resize') || e.target.closest('textarea') || e.target.closest('button')) return
    dragging = true
    const rect = padEl.getBoundingClientRect()
    dragOff = { dx: e.clientX - rect.left, dy: e.clientY - rect.top }
    e.preventDefault()
  }

  function onMouseMove(e) {
    if (dragging) {
      x = Math.max(0, e.clientX - dragOff.dx)
      y = Math.max(0, e.clientY - dragOff.dy)
    }
    if (resizing) {
      w = Math.max(200, e.clientX - x)
      h = Math.max(120, e.clientY - y)
    }
  }

  function onMouseUp() {
    if (dragging || resizing) {
      dragging = false
      resizing = false
      savePos()
    }
  }

  function startResize(e) {
    resizing = true
    e.preventDefault()
    e.stopPropagation()
  }
</script>

<svelte:window onmousemove={onMouseMove} onmouseup={onMouseUp} />

{#if visible}
  <div
    class="sp-wrap"
    bind:this={padEl}
    style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"
    role="dialog"
    aria-label="Spickzettel"
  >
    <!-- Header / Drag Handle -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="sp-hd" onmousedown={startDrag}>
      <span class="sp-title"><i class="fa-solid fa-note-sticky"></i> Spickzettel</span>
      <div class="sp-actions">
        <button class="sp-btn" title="Alles kopieren" onclick={copyAll}>
          <i class="fa-solid fa-copy"></i>
        </button>
        <button class="sp-btn sp-btn-del" title="Inhalt löschen" onclick={clearPad}>
          <i class="fa-solid fa-trash-can"></i>
        </button>
        <button class="sp-btn" title="Schließen" onclick={onClose}>
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
    </div>

    <!-- Textarea -->
    <textarea
      class="sp-text"
      bind:this={taEl}
      bind:value={text}
      oninput={saveText}
      placeholder="Spickzettel hier schreiben..."
      spellcheck="false"
    ></textarea>

    <!-- Resize Handle -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="sp-resize" onmousedown={startResize}></div>
  </div>
{/if}

<style>
  .sp-wrap {
    position:fixed; z-index:9000;
    background:var(--bg1); border:1px solid var(--border);
    border-radius:4px; display:flex; flex-direction:column;
    box-shadow:0 8px 32px rgba(0,0,0,.5);
    min-width:200px; min-height:120px;
  }
  .sp-hd {
    display:flex; align-items:center; justify-content:space-between;
    padding:6px 10px; border-bottom:1px solid var(--border);
    cursor:grab; user-select:none; flex-shrink:0;
    background:var(--bg2);
  }
  .sp-hd:active { cursor:grabbing; }
  .sp-title {
    font-size:11px; font-weight:700; color:var(--text1);
    display:flex; align-items:center; gap:6px;
  }
  .sp-title i { color:var(--warn); font-size:12px; }
  .sp-actions { display:flex; gap:2px; }
  .sp-btn {
    background:none; border:none; color:var(--text3); cursor:pointer;
    padding:3px 6px; border-radius:3px; font-size:11px;
    transition:all .12s;
  }
  .sp-btn:hover { color:var(--text0); background:var(--bg3); }
  .sp-btn-del:hover { color:var(--err); }
  .sp-text {
    flex:1; background:transparent; border:none; resize:none;
    padding:10px 12px; font-size:12px; line-height:1.6;
    color:var(--text0); font-family:'JetBrains Mono',monospace;
    outline:none;
  }
  .sp-text::placeholder { color:var(--text3); }
  .sp-resize {
    position:absolute; bottom:0; right:0; width:16px; height:16px;
    cursor:nwse-resize;
  }
  .sp-resize::after {
    content:''; position:absolute; bottom:3px; right:3px;
    width:8px; height:8px;
    border-right:2px solid var(--text3); border-bottom:2px solid var(--text3);
  }
</style>
