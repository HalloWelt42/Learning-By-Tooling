<script>
  import { globalStats, currentView } from '../stores/index.js'
  function pct(c,t){ return t>0?Math.round(c/t*100):0 }
</script>

<div class="page">
  <div class="page-hd">
    <div>
      <h1 class="page-title"><i class="fa-solid fa-gauge"></i> Dashboard</h1>
      <p class="page-sub">Dein Lernfortschritt auf einen Blick</p>
    </div>
    <button class="btn btn-primary btn-lg" onclick={() => currentView.set('learn')}>
      <i class="fa-solid fa-play"></i> Lernen starten
    </button>
  </div>

  {#if $globalStats}
    <!-- Summary -->
    <div class="stats-grid">
      <div class="stat-card stat--accent">
        <i class="fa-solid fa-layer-group stat-icon"></i>
        <div class="stat-body">
          <div class="stat-val">{$globalStats.total_cards}</div>
          <div class="stat-lbl">Aktive Karten</div>
        </div>
      </div>
      <div class="stat-card stat--ok">
        <i class="fa-solid fa-bullseye stat-icon"></i>
        <div class="stat-body">
          <div class="stat-val">{pct($globalStats.total_correct,$globalStats.total_reviews)}%</div>
          <div class="stat-lbl">Trefferquote</div>
        </div>
      </div>
      <div class="stat-card">
        <i class="fa-solid fa-clock-rotate-left stat-icon"></i>
        <div class="stat-body">
          <div class="stat-val">{$globalStats.total_sessions}</div>
          <div class="stat-lbl">Sessions</div>
        </div>
      </div>
      <div class="stat-card stat--warn" style="cursor:{$globalStats.due_today>0?'pointer':'default'}"
           onclick={() => $globalStats.due_today>0 && currentView.set('learn')}>
        <i class="fa-solid fa-brain stat-icon"></i>
        <div class="stat-body">
          <div class="stat-val">{$globalStats.due_today}</div>
          <div class="stat-lbl">Fällig heute</div>
        </div>
      </div>
      {#if ($globalStats.pending_drafts??0) > 0}
        <div class="stat-card stat--draft" style="cursor:pointer"
             onclick={() => currentView.set('documents')}>
          <i class="fa-solid fa-file-circle-exclamation stat-icon"></i>
          <div class="stat-body">
            <div class="stat-val">{$globalStats.pending_drafts}</div>
            <div class="stat-lbl">Entwürfe offen</div>
          </div>
        </div>
      {/if}
    </div>

    <!-- Kategorien -->
    <div class="section-label">Kategorien</div>
    <div class="cat-grid">
      {#each ($globalStats.by_category??[]).filter(c=>c.count>0) as cat (cat.code)}
        <button class="cat-card" style="--c:{cat.color}" onclick={() => currentView.set('cards')}>
          <div class="cc-top">
            <div class="cc-ico-wrap">
              <i class="fa-solid {cat.icon} cc-ico"></i>
            </div>
            <span class="cc-code">{cat.code}</span>
          </div>
          <div class="cc-name">{cat.name}</div>
          <div class="cc-track">
            <div class="cc-fill" style="width:{cat.shown>0?pct(cat.correct,cat.shown):0}%"></div>
          </div>
          <div class="cc-foot">
            <span>{cat.count} Karten</span>
            <span>{cat.shown>0?pct(cat.correct,cat.shown):0}%</span>
          </div>
        </button>
      {/each}
    </div>
  {:else}
    <div class="empty-state">
      <i class="fa-solid fa-satellite-dish"></i>
      <p>Verbinde mit dem Backend…</p>
    </div>
  {/if}
</div>

<style>
.stats-grid{
  display:flex;flex-wrap:wrap;gap:14px;margin-bottom:36px;
}
.stat-card{
  background:var(--bg1);border:1px solid var(--border);
  border-radius: 4px;padding:16px 20px;
  display:flex;align-items:center;gap:14px;
  min-width:140px;flex:1;
}
.stat-icon{font-size:20px;color:var(--text3);flex-shrink:0}
.stat--accent{border-color:var(--accent);background:var(--glow)}
.stat--accent .stat-icon{color:var(--accent)}
.stat--ok    .stat-icon{color:var(--ok)}
.stat--warn  .stat-icon{color:var(--warn)}
.stat--draft .stat-icon{color:var(--ac2)}
.stat-val{
  font-size:32px;font-weight:800;letter-spacing:-.03em;
  line-height:1;font-family:'JetBrains Mono',monospace;
  color:var(--text0);
}
.stat--accent .stat-val{color:var(--accent)}
.stat--ok    .stat-val{color:var(--ok)}
.stat--warn  .stat-val{color:var(--warn)}
.stat--draft .stat-val{color:var(--ac2)}
.stat-lbl{font-size:11px;font-weight:600;color:var(--text2);letter-spacing:.04em;text-transform:uppercase;margin-top:2px}

.cat-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(170px,1fr));
  gap:12px;
}
.cat-card{
  background:var(--bg1);border:1px solid var(--border);
  border-radius: 4px;padding:14px 16px;
  cursor:pointer;transition:all .2s;text-align:left;
}
.cat-card:hover{
  border-color:var(--c);
  box-shadow:0 4px 20px color-mix(in srgb,var(--c) 20%,transparent);
  transform:translateY(-1px);
}
.cc-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.cc-ico-wrap{
  width:30px;height:30px;border-radius: 4px;
  background:color-mix(in srgb,var(--c) 15%,transparent);
  border:1px solid color-mix(in srgb,var(--c) 30%,transparent);
  display:flex;align-items:center;justify-content:center;
}
.cc-ico{font-size:13px;color:var(--c)}
.cc-code{
  font-size:10px;font-weight:700;color:var(--c);
  font-family:'JetBrains Mono',monospace;letter-spacing:.08em;
}
.cc-name{font-size:12px;font-weight:600;color:var(--text1);margin-bottom:10px;line-height:1.3}
.cc-track{height:3px;background:var(--bg3);border-radius: 2px;margin-bottom:7px;overflow:hidden}
.cc-fill{height:100%;background:var(--c);border-radius: 2px;transition:width .5s}
.cc-foot{display:flex;justify-content:space-between;font-size:10px;color:var(--text3)}
</style>
