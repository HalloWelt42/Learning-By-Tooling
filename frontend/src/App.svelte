<script>
  import { onMount } from 'svelte'
  import { tweened } from 'svelte/motion'
  import { cubicOut } from 'svelte/easing'
  import {
    theme, currentView, activePackageId,
    loadGlobal, packages, globalStats, aiOnline,
    toastStore, activeSession, authUser, showToast,
    backendOnline, backendVersion, loadSettings,
    streakData, loadStreak, xpData, loadXp, initSound,
  } from './lib/stores/index.js'
  import { VERSION } from './lib/utils/version.js'

  import Login         from './lib/components/shared/Login.svelte'
  import Packages      from './lib/components/packages/Packages.svelte'
  import PackageDetail from './lib/components/packages/PackageDetail.svelte'
  import Learn         from './lib/components/learn/Learn.svelte'
  import Progress      from './lib/components/progress/Progress.svelte'
  import Guide         from './lib/components/shared/Guide.svelte'
  import Search        from './lib/components/shared/Search.svelte'
  import Admin         from './lib/components/shared/Admin.svelte'
  import Settings      from './lib/components/shared/Settings.svelte'
  import ScratchPad    from './lib/components/shared/ScratchPad.svelte'
  import { route, initRouter, navigate } from './lib/utils/router.js'
  import { apiGet, apiPost } from './lib/utils/api.js'

  let interval = $state(null)
  let showPwWarn = $state(false)
  let showScratchPad = $state(false)
  let sessionTimer = $state(null)
  let sessionElapsed = $state(0)

  // Animiertes Hochzählen der Sidebar-XP
  let sidebarXp = tweened(0, { duration: 2800, easing: cubicOut })
  let sidebarStreak = tweened(0, { duration: 1200, easing: cubicOut })

  $effect(() => {
    if ($xpData.xp_total > 0) sidebarXp.set($xpData.xp_total)
  })
  $effect(() => {
    if ($streakData.current >= 0) sidebarStreak.set($streakData.current)
  })

  $effect(() => {
    if ($activeSession) {
      sessionElapsed = 0
      sessionTimer = setInterval(() => sessionElapsed++, 1000)
    } else {
      clearInterval(sessionTimer)
      sessionElapsed = 0
    }
    return () => clearInterval(sessionTimer)
  })

  function fmtTime(s) {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }
  let pwForm = $state({ old: '', new1: '', new2: '' })
  let pwChanging = $state(false)

  onMount(() => {
    // Auth-Expired Event abfangen
    const onExpired = () => authUser.logout()
    window.addEventListener('auth-expired', onExpired)

    return () => {
      window.removeEventListener('auth-expired', onExpired)
      if (interval) clearInterval(interval)
    }
  })

  // Daten laden wenn eingeloggt
  $effect(() => {
    if ($authUser) {
      loadGlobal()
      loadSettings()
      loadStreak()
      loadXp()
      initSound()
      apiGet('/api/auth/me').then(me => { if (me?.default_password) showPwWarn = true }).catch(() => {})
      interval = setInterval(() => {
        loadGlobal()
        loadStreak()
        loadXp()
        }, 30_000)

      const cleanupRouter = initRouter()
      const unsubRoute = route.subscribe(r => {
        if (!r) return
        if (r.view === 'package' && r.params?.pkg_id) {
          activePackageId.set(r.params.pkg_id)
          currentView.set('package')
        } else if (['packages','learn','progress','guide','search','admin','settings'].includes(r.view)) {
          currentView.set(r.view)
        }
      })

      return () => {
        if (interval) clearInterval(interval)
        cleanupRouter()
        unsubRoute()
      }
    }
  })

  let activePkg = $state(null)
  $effect(() => {
    activePkg = ($packages || []).find(p => p.id === $activePackageId) || null
  })

  $effect(() => {
    document.documentElement.setAttribute('data-theme', $theme)
  })
</script>

{#if !$authUser}
  <div data-theme={$theme}>
    <Login />
  </div>
{:else}
  <div class="app" data-theme={$theme}>

    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon"><i class="fa-solid fa-graduation-cap"></i></div>
        <div>
          <div class="brand-name">Learning-By-Tooling</div>
        </div>
      </div>

      <div class="gamify-bar" role="button" tabindex="0" onclick={() => navigate('/progress')} title="Fortschritt öffnen">
        {#if $streakData.current > 0 || $streakData.today}
          <div class="gamify-item" title="Tagessträhne: {$streakData.current} Tage">
            <i class="fa-solid fa-fire" class:streak-active={$streakData.today}></i>
            <span class="gamify-num">{Math.round($sidebarStreak)}</span>
            {#if !$streakData.today}
              <i class="fa-solid fa-triangle-exclamation streak-warn-icon"></i>
            {/if}
          </div>
        {/if}
        {#if $xpData.xp_total > 0}
          {@const xpAnimated = Math.round($sidebarXp)}
          {@const diamonds = Math.floor(xpAnimated / 1000000)}
          {@const gold = Math.floor((xpAnimated % 1000000) / 1000)}
          {@const silver = xpAnimated % 1000}
          <div class="gamify-item" title="Silber: {silver} / Gold: {gold} / Diamant: {diamonds} -- Gesamt: {$xpData.xp_total} XP">
            {#if diamonds > 0}
              <span class="xp-diamond-mini"></span>
              <span class="gamify-num gn-diamond">{diamonds}</span>
            {/if}
            {#if gold > 0}
              <span class="xp-gold-mini"></span>
              <span class="gamify-num gn-gold">{gold}</span>
            {/if}
            <span class="xp-silver-mini"></span>
            <span class="gamify-num gn-silver">{silver}</span>
          </div>
        {/if}
      </div>

      <nav class="nav">
        <button class="nav-item" class:active={$currentView==='packages'}
          onclick={() => navigate('/packages')}>
          <i class="fa-solid fa-box-archive"></i>
          <span>Lernpakete</span>
          {#if ($globalStats?.total_packages ?? 0) > 0}
            <span class="nc">{$globalStats.total_packages}</span>
          {/if}
        </button>

        <button class="nav-item" class:active={$currentView==='learn'}
          onclick={() => navigate('/learn')}>
          <i class="fa-solid fa-play"></i>
          <span>Lernen</span>
          {#if $activeSession}
            <span class="session-info">
              <span class="session-dot"></span>
              <span class="session-time mono">{fmtTime(sessionElapsed)}</span>
            </span>
          {/if}
          {#if ($globalStats?.due_today ?? 0) > 0}
            <span class="nbadge due">{$globalStats.due_today}</span>
          {/if}
        </button>

        <button class="nav-item" class:active={$currentView==='progress'}
          onclick={() => navigate('/progress')}>
          <i class="fa-solid fa-chart-line"></i>
          <span>Fortschritt</span>
        </button>

        <button class="nav-item" class:active={$currentView==='search'}
          onclick={() => navigate('/search')}>
          <i class="fa-solid fa-magnifying-glass"></i>
          <span>Suche</span>
        </button>

        <button class="nav-item" class:active={$currentView==='guide'}
          onclick={() => navigate('/guide')}>
          <i class="fa-solid fa-map"></i>
          <span>Anleitung</span>
        </button>

        <button class="nav-item" class:active={$currentView==='admin' || $currentView==='settings'}
          onclick={() => navigate('/admin')}>
          <i class="fa-solid fa-gear"></i>
          <span>Verwaltung</span>
        </button>

        <button class="nav-item" class:active={showScratchPad}
          onclick={() => showScratchPad = !showScratchPad}>
          <i class="fa-solid fa-clipboard-list"></i>
          <span>Notizen</span>
        </button>
      </nav>

      {#if ($packages || []).length > 0}
        <div class="pkg-section">
          <div class="pkg-section-label">Lernpakete</div>
          <div class="pkg-scroll">
            {#each ($packages || []) as pkg (pkg.id)}
              <button
                class="pkg-item"
                class:active={$activePackageId === pkg.id && $currentView === 'package'}
                style="--c:{pkg.color}"
                onclick={() => navigate(`/packages/${pkg.id}`)}
              >
                <div class="pkg-dot" style="background:{pkg.color}">
                  <i class="fa-solid {pkg.icon}"></i>
                </div>
                <div class="pkg-item-body">
                  <span class="pkg-item-name">{pkg.name}</span>
                  <span class="pkg-item-meta">{pkg.card_count} Karten</span>
                </div>
                {#if pkg.draft_count > 0}
                  <span class="pkg-badge">{pkg.draft_count}</span>
                {/if}
              </button>
            {/each}
          </div>
        </div>
      {/if}

      <div class="sf">
        <div class="theme-row">
          {#each [
            {id:'dark',     icon:'fa-moon'},
            {id:'light',    icon:'fa-sun'},
            {id:'dracula',  icon:'fa-ghost'},
            {id:'contrast', icon:'fa-water'},
            {id:'warm',     icon:'fa-tree'},
          ] as t}
            <button
              class="theme-dot"
              class:active={$theme === t.id}
              title={t.id}
              aria-label="Theme: {t.id}"
              onclick={() => theme.set(t.id)}
              data-t={t.id}
            >
              <i class="fa-solid {t.icon}"></i>
            </button>
          {/each}
        </div>
        <div class="user-row">
          <i class="fa-solid fa-user"></i>
          <span>{$authUser.display_name || $authUser.email}</span>
          <button class="logout-btn" title="Abmelden" onclick={() => authUser.logout()}>
            <i class="fa-solid fa-right-from-bracket"></i>
          </button>
        </div>
        <div class="sf-line">
          <div class="status-dot" class:online={$backendOnline}></div>
          <span>API</span>
          <div class="status-dot" class:online={$aiOnline}></div>
          <span>LM</span>
          <span class="sf-sep">|</span>
          <span class="mono">v{VERSION}</span>
        </div>
      </div>
    </aside>

    <main class="main">
      {#if showPwWarn}
        <div class="pw-warn">
          <div class="pw-warn-text">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>Du nutzt noch das Standard-Passwort. Bitte ändere es.</span>
          </div>
          <div class="pw-warn-form">
            <input type="password" placeholder="Altes Passwort" bind:value={pwForm.old} />
            <input type="password" placeholder="Neues Passwort" bind:value={pwForm.new1} />
            <input type="password" placeholder="Wiederholen" bind:value={pwForm.new2} />
            <button class="btn btn-primary btn-sm" disabled={pwChanging} onclick={async () => {
              if (pwForm.new1 !== pwForm.new2) { showToast('Passwörter stimmen nicht überein', 'error'); return }
              pwChanging = true
              try {
                await apiPost('/api/auth/change-password', { old_password: pwForm.old, new_password: pwForm.new1 })
                showToast('Passwort geändert', 'success')
                showPwWarn = false
              } catch(e) { showToast(e.message, 'error') }
              pwChanging = false
            }}>{pwChanging ? 'Speichern...' : 'Ändern'}</button>
            <button class="btn btn-ghost btn-sm" onclick={() => showPwWarn = false}>Später</button>
          </div>
        </div>
      {/if}
      {#if $currentView === 'packages'}
        <Packages />
      {:else if $currentView === 'package' && activePkg}
        <PackageDetail pkg={activePkg} />
      {:else if $currentView === 'learn'}
        <Learn />
      {:else if $currentView === 'progress'}
        <Progress />
      {:else if $currentView === 'guide'}
        <Guide />
      {:else if $currentView === 'search'}
        <Search initQ={$route?.query?.q || ''} initPkg={$route?.query?.pkg || null} />
      {:else if $currentView === 'admin' || $currentView === 'settings'}
        <Admin />
      {:else}
        <Packages />
      {/if}
    </main>

  </div>

  <ScratchPad visible={showScratchPad} onClose={() => showScratchPad = false} />

  {#if $toastStore}
    {#key $toastStore.id}
      <div class="toast-float {$toastStore.type}" role="alert">
        <i class="fa-solid {
          $toastStore.type==='success' ? 'fa-circle-check' :
          $toastStore.type==='error'   ? 'fa-circle-xmark' :
          $toastStore.type==='warn'    ? 'fa-triangle-exclamation' :
          'fa-circle-info'
        }"></i>
        <span>{$toastStore.message}</span>
      </div>
    {/key}
  {/if}
{/if}

<style>
  .app { display:flex; height:100vh; overflow:hidden; }

  .sidebar {
    width:220px; flex-shrink:0; background:var(--bg1);
    border-right:1px solid var(--border); display:flex;
    flex-direction:column; overflow:hidden;
  }
  .main {
    flex:1; overflow-y:auto; background:var(--bg0); min-width:0;
  }

  .brand { padding:14px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:9px; }
  .brand-icon { width:26px;height:26px;background:var(--accent);border-radius: 3px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;flex-shrink:0; }
  .brand-name { font-size:13px;font-weight:800;color:var(--text0);letter-spacing:-.03em; }
  .brand-ver  { font-size:9px;color:var(--text3);font-family:'JetBrains Mono',monospace;margin-left:auto; }

  .pkg-section { padding:8px 0; border-top:1px solid var(--border); display:flex; flex-direction:column; min-height:0; overflow:hidden; }
  .pkg-section-label { padding:8px 14px 4px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text3);flex-shrink:0; }
  .pkg-scroll { overflow-y:auto; max-height:200px; }
  .pkg-item {
    display:flex;align-items:center;gap:8px;width:100%;
    padding:6px 14px;background:none;border:none;
    color:var(--text2);font-size:12px;cursor:pointer;text-align:left;
    transition:all .1s;font-family:inherit;
  }
  .pkg-item:hover  { background:var(--bg2);color:var(--text0); }
  .pkg-item.active { background:var(--bg2);color:var(--text0); }
  .pkg-dot { width:18px;height:18px;border-radius: 2px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:9px; }
  .pkg-dot i { color:#fff; }
  .pkg-item-body { flex:1;min-width:0; }
  .pkg-item-name { display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
  .pkg-item-meta { font-size:10px;color:var(--text3);font-family:'JetBrains Mono',monospace; }
  .pkg-badge { font-size:9px;background:var(--warn);color:#000;padding:1px 5px;border-radius: 2px;font-weight:700;flex-shrink:0; }

  .nc    { margin-left:auto;font-size:9px;color:var(--text3);font-family:'JetBrains Mono',monospace; }
  .nbadge { margin-left:auto;font-size:9px;font-weight:700;padding:1px 5px;border-radius: 2px; }
  .session-info { display:flex;align-items:center;gap:4px;margin-left:auto; }
  .session-dot { width:6px;height:6px;border-radius:50%;background:var(--ok);flex-shrink:0; }
  .session-time { font-size:9px;color:var(--text2); }
  .nbadge.due  { background:var(--accent);color:#fff; }

  .sf { padding:8px 14px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:6px;margin-top:auto; }
  .sf-line { display:flex;align-items:center;gap:5px;font-size:10px;color:var(--text3); }

  .pw-warn { background:color-mix(in srgb, var(--warn) 10%, var(--bg1));border-bottom:1px solid var(--warn);padding:12px 20px;display:flex;flex-direction:column;gap:8px; }
  .pw-warn-text { display:flex;align-items:center;gap:8px;font-size:12px;font-weight:600;color:var(--warn); }
  .pw-warn-form { display:flex;align-items:center;gap:6px;flex-wrap:wrap; }
  .pw-warn-form input {
    background:var(--bg2);border:1px solid var(--border);border-radius:4px;
    padding:6px 10px;font-size:12px;color:var(--text0);font-family:inherit;
    width:140px;
  }
  .pw-warn-form input:focus { border-color:var(--accent);outline:none; }
  .sf-sep { color:var(--border); }
  .user-row { display:flex;align-items:center;gap:7px;font-size:11px;color:var(--text2); }
  .user-row > span:first-of-type { flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
  .gamify-bar {
    cursor:pointer;border-radius:4px;transition:background .15s;
    display:flex;align-items:center;justify-content:center;gap:12px;
    padding:4px 10px;
  }
  .gamify-item {
    display:flex;align-items:center;gap:4px;cursor:pointer;
    padding:2px 6px;border-radius:3px;transition:background .12s;
  }
  .gamify-item:hover { background:var(--bg2); }
  .gamify-item i { font-size:12px;color:var(--text3); }
  .gamify-item i.streak-active { color:#ff6b35; }
  .streak-warn-icon { color:var(--warn) !important;font-size:10px !important; }
  .gamify-num { font-size:13px;font-weight:800;color:var(--text0);font-family:'Orbitron',sans-serif; }
  .gn-silver { color:#C0C0C0; }
  .gn-gold { color:#FFD700; }
  .gn-diamond { color:#4FC3F7; }
  .xp-silver-mini {
    width:14px;height:14px;border-radius:50%;flex-shrink:0;
    background:radial-gradient(circle at 35% 35%, #E8E8E8, #909090);
    border:1px solid #A0A0A0;
  }
  .xp-gold-mini {
    width:14px;height:14px;border-radius:50%;flex-shrink:0;
    background:radial-gradient(circle at 35% 35%, #FFD700, #B8860B);
    border:1px solid #DAA520;
  }
  .xp-diamond-mini {
    width:14px;height:14px;flex-shrink:0;
    background:radial-gradient(circle at 30% 30%, #81D4FA, #0288D1);
    border:1px solid #4FC3F7;
    clip-path:polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%);
  }
  .util-row { display:flex;gap:4px;justify-content:center;padding:2px 0; }
  .util-btn {
    background:none;border:1px solid var(--border);color:var(--text3);cursor:pointer;
    padding:4px 8px;border-radius:3px;font-size:11px;transition:all .12s;
  }
  .util-btn:hover { color:var(--warn);border-color:var(--warn); }
  .util-btn.active { color:var(--warn);border-color:var(--warn);background:rgba(232,168,48,.08); }
  .logout-btn {
    background:none;border:none;color:var(--text3);cursor:pointer;padding:2px 4px;
    font-size:11px;transition:color .12s;
  }
  .logout-btn:hover { color:var(--err); }

  .status-dot { width:6px;height:6px;border-radius:50%;background:var(--text3);flex-shrink:0; }
  .status-dot.online { background:var(--ok);box-shadow:0 0 5px var(--ok); }
  .theme-row { display:flex;gap:4px; }
  .theme-dot {
    width:22px;height:22px;border-radius: 2px;border:1px solid var(--border);
    background:none;cursor:pointer;font-size:10px;color:var(--text3);
    display:flex;align-items:center;justify-content:center;transition:all .12s;
  }
  .theme-dot:hover  { border-color:var(--text2);color:var(--text1); }
  .theme-dot.active { border-color:var(--accent);color:var(--accent);background:var(--glow); }

  .toast-float {
    position:fixed; bottom:20px; right:20px; z-index:9999;
    display:flex; align-items:center; gap:9px;
    padding:10px 16px; background:var(--bg2); border:1px solid var(--border);
    border-radius:3px; font-size:13px; color:var(--text0);
    box-shadow:0 4px 20px var(--shadow);
    max-width:360px; animation:toast-in .15s ease;
  }
  .toast-float.success { border-color:var(--ok); }
  .toast-float.success i { color:var(--ok); }
  .toast-float.error { border-color:var(--err); }
  .toast-float.error i { color:var(--err); }
  .toast-float.warn { border-color:var(--warn); }
  .toast-float.warn i { color:var(--warn); }
  .toast-float.info i { color:var(--accent); }
  @keyframes toast-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
</style>
