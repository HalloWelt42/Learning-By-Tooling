<script>
  import { categories, packages, activePackageId } from '../../stores/index.js'

  let { card, progress, totalCards, sessionMode, combo = 0, comboFlash = false, xpEarned = 0, xpFlash = false } = $props()

  const MODE_LABELS = { standard: 'Karteikarte', mc: 'Multiple Choice', write: 'Freitext', srs: 'SRS' }
  let pctDone = $derived(totalCards > 0 ? progress.current_index / totalCards : 0)
  let catObj  = $derived($categories?.find(c => c.code === card?.category_code))
  let pkgObj  = $derived($packages?.find(p => p.id === $activePackageId))
</script>

<!-- Breadcrumb -->
<div class="ctx-bar">
  <div class="ctx-breadcrumb">
    {#if pkgObj}
      <span class="ctx-pkg" style="--c:{pkgObj.color}">
        <i class="fa-solid {pkgObj.icon}"></i>
        {pkgObj.name}
      </span>
      <span class="ctx-sep">/</span>
    {/if}
    {#if catObj}
      <span class="ctx-cat" style="color:{catObj.color}">{catObj.name}</span>
    {/if}
    <span class="ctx-mode">{MODE_LABELS[sessionMode] || sessionMode}</span>
  </div>
  <div class="ctx-pos">
    <span class="ctx-num">{progress.current_index + 1}</span>
    <span class="ctx-of">/ {totalCards}</span>
    {#if card}
      <span class="ctx-id">{card.card_id}</span>
    {/if}
  </div>
</div>

<!-- Progress + Score -->
<div class="learn-bar">
  <div class="lb-info">
    <span class="lb-cat" style="color:{catObj?.color || 'var(--accent)'}">
      <i class="fa-solid {catObj?.icon || 'fa-tag'}"></i>
      {catObj?.name || card?.category_code}
    </span>
  </div>
  <div class="lb-track">
    <div class="lb-fill" style="width:{pctDone * 100}%"></div>
  </div>
  <div class="lb-score">
    {#if combo >= 3}
      <span class="ls combo" class:combo-flash={comboFlash}>
        <i class="fa-solid fa-bolt"></i>{combo}x
      </span>
    {/if}
    <span class="ls ok"><i class="fa-solid fa-check"></i>{progress.correct}</span>
    <span class="ls err"><i class="fa-solid fa-xmark"></i>{progress.wrong}</span>
    <span class="ls skip"><i class="fa-solid fa-forward"></i>{progress.skipped}</span>
    {#if xpEarned > 0}
      <span class="ls xp" class:xp-flash={xpFlash}>
        <span class="xp-coin-sm"></span>{xpEarned}
      </span>
    {/if}
  </div>
</div>

<style>
.ctx-bar {
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 0 6px;margin-bottom:4px;border-bottom:1px solid var(--border);
}
.ctx-breadcrumb { display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2);flex-wrap:wrap; }
.ctx-pkg { display:flex;align-items:center;gap:5px;font-weight:600;color:var(--c, var(--accent)); }
.ctx-cat { display:flex;align-items:center;gap:5px;font-weight:500; }
.ctx-sep { font-size:9px;color:var(--text3); }
.ctx-mode { color:var(--text3);font-size:11px; }
.ctx-pos { display:flex;align-items:baseline;gap:3px; }
.ctx-num { font-size:16px;font-weight:800;color:var(--text0);font-family:'Orbitron',sans-serif; }
.ctx-of  { font-size:11px;color:var(--text3); }
.ctx-id  { font-size:10px;color:var(--text3);background:var(--bg3);padding:1px 6px;border-radius:3px;margin-left:6px; }

.learn-bar { padding:14px 32px;display:flex;align-items:center;gap:16px;border-bottom:1px solid var(--border);background:var(--bg1);position:sticky;top:0;z-index:10; }
.lb-info   { display:flex;align-items:center;gap:10px;min-width:130px; }
.lb-cat    { font-size:11px;font-weight:600;letter-spacing:.06em; }
.lb-track  { flex:1;height:4px;background:var(--bg3);border-radius:2px;overflow:hidden; }
.lb-fill   { height:100%;background:var(--text3);opacity:0.7;border-radius:2px;transition:width .4s ease; }
.lb-score  { display:flex;gap:10px; }
.ls        { font-size:11px;font-weight:700;font-family:'Orbitron',sans-serif;display:flex;align-items:center;gap:4px; }
.ls.ok  { color:var(--ok); }
.ls.err  { color:var(--err); }
.ls.skip { color:var(--text3); }
.ls.combo { color:#ffa500;font-weight:800; }
.ls.xp { color:#C0C0C0; }
.ls.xp-flash { animation:xp-pop .6s ease; }
@keyframes xp-pop {
  0%   { transform:scale(1); }
  30%  { transform:scale(1.4); }
  100% { transform:scale(1); }
}
.xp-coin-sm {
  display:inline-block;width:12px;height:12px;border-radius:50%;
  background:radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
  border:1px solid #A0A0A0;margin-right:3px;vertical-align:middle;
}
.ls.combo-flash { animation:combo-pulse .5s ease; }
@keyframes combo-pulse {
  0%   { transform:scale(1); }
  30%  { transform:scale(1.3); }
  100% { transform:scale(1); }
}
</style>
