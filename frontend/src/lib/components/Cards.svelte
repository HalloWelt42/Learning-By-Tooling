<script>
  import { onMount } from 'svelte'
  import { categories, showToast, loadGlobal, aiOnline } from '../stores/index.js'
  import { apiGet, apiPost, apiPut, apiDelete } from '../utils/api.js'

  let cards    = $state([])
  let loading  = $state(true)
  let searchQ  = $state('')
  let fCat     = $state('')
  let fActive  = $state(true)
  let selected = $state(null)
  let showForm = $state(false)
  let editCard = $state(null)
  let aiState  = $state('idle')  // idle | loading | done | error
  let aiText   = $state('')
  let confirmDelete = $state(null)
  let form     = $state({ card_id:'', category_code:'', question:'', answer:'', hint:'', difficulty:2 })

  const DL = ['','Leicht','Mittel','Schwer']
  const DC = ['','d1','d2','d3']
  const DI = ['','fa-gauge-simple','fa-gauge','fa-gauge-high']

  onMount(load)
  // Filter-Wechsel - nur bei echten Änderungen neu laden
  let prevFCat    = $state(null)
  let prevFActive = $state(true)
  $effect(() => {
    if (fCat === prevFCat && fActive === prevFActive) return
    prevFCat    = fCat
    prevFActive = fActive
    load()
  })

  async function load() {
    loading = true
    const p = new URLSearchParams()
    if (searchQ) p.set('search', searchQ)
    if (fCat)    p.set('category', fCat)
    p.set('active_only', String(fActive))
    cards = await apiGet(`/api/cards?${p}`).catch(()=>[])
    loading = false
  }

  let st; function onSearch() { clearTimeout(st); st = setTimeout(load, 280) }

  function openCreate() {
    editCard = null
    form = { card_id:'', category_code:$categories[0]?.code||'GB', question:'', answer:'', hint:'', difficulty:2 }
    selected = null
    showForm = true
  }
  function openEdit(c) { editCard=c; form={...c, hint:c.hint||''}; showForm=true }

  async function save() {
    if (!form.question||!form.answer||!form.category_code) { showToast('Frage, Antwort und Kategorie sind Pflicht','error'); return }
    try {
      if (editCard) { await apiPut(`/api/cards/${editCard.card_id}`, form); showToast('Gespeichert','success') }
      else          { await apiPost('/api/cards', form); showToast('Karte erstellt','success') }
      showForm=false; selected=null
      await load(); await loadGlobal()
    } catch(e) { showToast(e.message,'error') }
  }

  async function toggle(c) {
    await apiPut(`/api/cards/${c.card_id}`, { active: c.active?0:1 })
    if (selected?.card_id===c.card_id) selected={...selected,active:selected.active?0:1}
    await load()
  }

  async function del(c) {
    if (confirmDelete !== c.card_id) {
      confirmDelete = c.card_id
      setTimeout(() => confirmDelete = null, 3000)
      return
    }
    confirmDelete = null
    await apiDelete(`/api/cards/${c.card_id}`)
    if (selected?.card_id===c.card_id) selected=null
    showToast('Gelöscht','info')
    await load(); await loadGlobal()
  }

  function sel(c) { selected=c; aiText=''; aiState='idle'; showForm=false }

  async function getAI(card) {
    aiState = 'loading'; aiText = ''
    try {
      const d = await apiPost('/api/ai/explain', { card_id: card.card_id })
      aiText = d.explanation; aiState = 'done'
    } catch(e) { aiText='LM Studio nicht erreichbar.'; aiState='error' }
  }
</script>

<div class="full-panel" style="grid-template-columns:340px 1fr">

  <!-- LIST ─────────────────────────────────────────────── -->
  <div class="list-panel">
    <div class="lp-hd">
      <span class="page-title" style="font-size:17px">
        <i class="fa-solid fa-layer-group"></i> Karten
      </span>
      <button class="btn btn-primary btn-sm" onclick={openCreate}>
        <i class="fa-solid fa-plus"></i> Neu
      </button>
    </div>
    <div class="lp-filters">
      <div class="search-wrap">
        <i class="fa-solid fa-magnifying-glass si"></i>
        <input type="search" placeholder="Suchen…" bind:value={searchQ} oninput={onSearch} class="search-inp" />
      </div>
      <select bind:value={fCat}>
        <option value="">Alle Kategorien</option>
        {#each $categories as cat (cat.code)}
          <option value={cat.code}>{cat.icon} {cat.name}</option>
        {/each}
      </select>
      <label class="check-row">
        <input type="checkbox" bind:checked={fActive} />
        <span>Nur aktive</span>
      </label>
    </div>

    {#if loading}
      <div class="load-msg">
        <i class="fa-solid fa-spinner fa-spin" style="color:var(--accent)"></i> Lädt…
      </div>
    {:else}
      <div class="card-list">
        {#each cards as c (c.card_id)}
          <button class="cli" class:selected={selected?.card_id===c.card_id} class:inactive={!c.active}
                  onclick={() => sel(c)}>
            <div class="cli-top">
              <span style="font-size:9px;color:var(--text3);font-family:'JetBrains Mono',monospace">{c.card_id}</span>
              <span class="{DC[c.difficulty]}" style="font-size:9px;font-weight:700;display:flex;align-items:center;gap:3px">
                <i class="fa-solid {DI[c.difficulty]}"></i>{DL[c.difficulty]}
              </span>
            </div>
            <div class="cli-q">{c.question.slice(0,90)}{c.question.length>90?'…':''}</div>
            <div class="cli-cat" style="color:{$categories.find(x=>x.code===c.category_code)?.color||'var(--accent)'}">
              {$categories.find(x=>x.code===c.category_code)?.icon||''} {c.category_code}
            </div>
          </button>
        {/each}
        {#if !loading && cards.length===0}
          <div class="list-empty">
            <i class="fa-solid fa-layer-group" style="opacity:.3;font-size:24px"></i>
            Keine Karten gefunden
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- DETAIL / FORM ─────────────────────────────────────── -->
  <div class="detail-panel">
    {#if showForm}
      <div class="dp-inner">
        <div class="dp-hd">
          <span style="font-weight:700;color:var(--text0);font-size:15px">
            <i class="fa-solid {editCard?'fa-pen':'fa-plus'}" style="color:var(--accent);margin-right:8px"></i>
            {editCard ? 'Karte bearbeiten' : 'Neue Karte'}
          </span>
          <button class="icon-btn" onclick={() => showForm=false}><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="form-fields">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <label><span>Karten-ID</span><input type="text" bind:value={form.card_id} placeholder="K-106 (auto)" /></label>
            <label>
              <span>Kategorie *</span>
              <select bind:value={form.category_code}>
                {#each $categories as cat (cat.code)}<option value={cat.code}>{cat.icon} {cat.name}</option>{/each}
              </select>
            </label>
          </div>
          <label><span>Frage *</span><textarea bind:value={form.question} rows="3" placeholder="Frage eingeben…"></textarea></label>
          <label><span>Antwort *</span><textarea bind:value={form.answer} rows="5" placeholder="Antwort eingeben…"></textarea></label>
          <label><span>Hinweis</span><input type="text" bind:value={form.hint} placeholder="Kleiner Tipp…" /></label>
          <label>
            <span>Schwierigkeit</span>
            <div class="diff-row">
              {#each [1,2,3] as d}
                <button class="diff-btn" class:active={form.difficulty===d}
                  style="--dc:{d===1?'var(--ok)':d===2?'var(--warn)':'var(--err)'}"
                  onclick={() => form.difficulty=d}>
                  <i class="fa-solid {DI[d]}"></i> {DL[d]}
                </button>
              {/each}
            </div>
          </label>
        </div>
        <div class="form-foot">
          <button class="btn btn-ghost" onclick={() => showForm=false}>Abbrechen</button>
          <button class="btn btn-primary" onclick={save}>
            <i class="fa-solid {editCard?'fa-floppy-disk':'fa-plus'}"></i>
            {editCard ? 'Speichern' : 'Erstellen'}
          </button>
        </div>
      </div>

    {:else if selected}
      <div class="dp-inner">
        <div class="dp-hd">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace">{selected.card_id}</span>
            <span class="{DC[selected.difficulty]}" style="font-size:11px;font-weight:600;display:flex;align-items:center;gap:4px">
              <i class="fa-solid {DI[selected.difficulty]}"></i>{DL[selected.difficulty]}
            </span>
            {#if !selected.active}
              <span style="font-size:10px;color:var(--text3);background:var(--bg2);padding:2px 7px;border-radius: 4px"> <i class="fa-solid fa-eye-slash"></i> inaktiv </span>{/if}
          </div>
          <div style="display:flex;gap:6px">
            <button class="icon-btn" onclick={() => openEdit(selected)} title="Bearbeiten">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="icon-btn" onclick={() => toggle(selected)} title="{selected.active?'Deaktivieren':'Aktivieren'}">
              <i class="fa-solid {selected.active?'fa-eye-slash':'fa-eye'}"></i>
            </button>
            <button class="icon-btn err" onclick={() => del(selected)} title="Löschen">
              {#if confirmDelete === selected.card_id}
                Wirklich?
              {:else}
                <i class="fa-solid fa-trash"></i>
              {/if}
            </button>
          </div>
        </div>

        <div class="dp-sec">
          <div class="section-label">Frage</div>
          <div class="dp-q">{selected.question}</div>
        </div>
        {#if selected.hint}
          <div class="dp-sec">
            <div class="section-label">Hinweis</div>
            <div class="dp-hint"><i class="fa-solid fa-lightbulb" style="color:var(--warn)"></i> {selected.hint}</div>
          </div>
        {/if}
        <div class="dp-sec">
          <div class="section-label">Antwort</div>
          <div class="dp-ans">{selected.answer}</div>
        </div>

        <!-- KI Prozess ────────────────────────────────────── -->
        {#if aiState === 'idle' && $aiOnline}
          <button class="btn btn-ghost btn-sm" onclick={() => getAI(selected)}>
            <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Erklärung
          </button>
        {:else if aiState === 'loading'}
          <div class="ai-load">
            <i class="fa-solid fa-spinner fa-spin" style="color:var(--accent)"></i>
            <div style="flex:1">
              <div style="font-size:12px;color:var(--accent);margin-bottom:5px">KI generiert Erklärung…</div>
              <div class="ai-bar"><div class="ai-fill"></div></div>
            </div>
          </div>
        {:else if aiText}
          <div class="dp-sec">
            <div class="section-label" style="color:var(--ac2)">
              <i class="fa-solid fa-wand-magic-sparkles"></i> KI-Erklärung
            </div>
            <div class="dp-ai">{aiText}</div>
          </div>
        {/if}
      </div>

    {:else}
      <div class="empty-state">
        <i class="fa-solid fa-layer-group"></i>
        <p>Karte auswählen</p>
      </div>
    {/if}
  </div>
</div>

<style>
.list-panel  { border-right:1px solid var(--bdr2);display:flex;flex-direction:column;overflow:hidden;background:var(--bg1); }
.lp-hd       { padding:18px 16px 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--bdr2);flex-shrink:0; }
.lp-filters  { padding:10px 14px;display:flex;flex-direction:column;gap:8px;border-bottom:1px solid var(--bdr2);flex-shrink:0; }
.search-wrap { position:relative; }
.si          { position:absolute;left:10px;top:50%;transform:translateY(-50%);font-size:12px;color:var(--text3); }
.search-inp  { padding-left:30px; }
.check-row   { display:flex;align-items:center;gap:7px;font-size:11px;color:var(--text2);cursor:pointer; }
.check-row input { width:auto; }
.card-list   { flex:1;overflow-y:auto;padding:6px; }
.load-msg    { padding:20px;text-align:center;color:var(--text2);font-size:12px;display:flex;align-items:center;justify-content:center;gap:8px; }
.list-empty  { padding:24px;text-align:center;color:var(--text3);font-size:12px;display:flex;flex-direction:column;align-items:center;gap:8px; }
.cli { display:block;width:100%;padding:10px 10px;border-radius: 4px;text-align:left;cursor:pointer;transition:background .12s;border:1px solid transparent;margin-bottom:2px; }
.cli:hover   { background:var(--bg2); }
.cli.selected{ background:var(--glow);border-color:var(--accent); }
.cli.inactive{ opacity:.4; }
.cli-top { display:flex;justify-content:space-between;align-items:center;margin-bottom:3px; }
.cli-q   { font-size:11px;color:var(--text1);line-height:1.4;margin-bottom:4px; }
.cli-cat { font-size:9px;font-weight:700;letter-spacing:.08em; }

.detail-panel { overflow-y:auto;background:var(--bg0); }
.dp-inner { padding:24px; }
.dp-hd    { display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid var(--border); }
.icon-btn { width:28px;height:28px;border-radius: 4px;display:flex;align-items:center;justify-content:center;color:var(--text2);font-size:12px;transition:all .15s; }
.icon-btn:hover { background:var(--bg2);color:var(--text0); }
.icon-btn.err:hover { background:var(--err);color:#fff; }
.form-fields { display:flex;flex-direction:column;gap:12px; }
.form-fields label { display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600;color:var(--text2); }
.diff-row { display:flex;gap:8px; }
.diff-btn { padding:5px 13px;border-radius: 4px;font-size:11px;font-weight:600;border:1px solid var(--border);background:transparent;color:var(--text2);transition:all .15s;cursor:pointer;display:flex;align-items:center;gap:5px; }
.diff-btn.active { border-color:var(--dc);color:var(--dc);background:color-mix(in srgb,var(--dc) 12%,transparent); }
.form-foot { display:flex;justify-content:flex-end;gap:10px;padding-top:14px;border-top:1px solid var(--border);margin-top:14px; }
.dp-sec  { margin-bottom:18px; }
.dp-q    { font-size:15px;font-weight:600;color:var(--text0);background:var(--bg2);border-radius: 4px;padding:12px 16px;line-height:1.5; }
.dp-hint { font-size:12px;color:var(--text2);background:var(--bg2);border-radius: 4px;padding:8px 12px;display:flex;align-items:center;gap:7px; }
.dp-ans  { font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text1);background:var(--bg1);border:1px solid var(--border);border-radius: 4px;padding:12px 14px;white-space:pre-wrap;line-height:1.65; }
.dp-ai   { font-size:13px;color:var(--text1);background:var(--bg2);border:1px solid color-mix(in srgb,var(--ac2) 35%,transparent);border-radius: 4px;padding:12px 14px;line-height:1.6; }
.ai-load { display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--glow);border:1px solid color-mix(in srgb,var(--accent) 30%,transparent);border-radius: 4px;margin-top:4px; }
.ai-bar  { height:2px;background:var(--bg3);border-radius: 1px;overflow:hidden; }
.ai-fill { height:100%;background:var(--accent);animation:scan 1.8s ease-in-out infinite; }
@keyframes scan { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }
</style>
