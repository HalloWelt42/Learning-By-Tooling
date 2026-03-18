<script>
  import { onMount } from 'svelte'
  import {
    theme, currentView, activePackageId,
    loadGlobal, packages, globalStats, aiOnline,
    toastStore, activeSession, authUser,
  } from './lib/stores/index.js'
  import { VERSION } from './lib/utils/version.js'

  import Login         from './lib/components/Login.svelte'
  import Packages      from './lib/components/Packages.svelte'
  import PackageDetail from './lib/components/PackageDetail.svelte'
  import Learn         from './lib/components/Learn.svelte'
  import Progress      from './lib/components/Progress.svelte'
  import Guide         from './lib/components/Guide.svelte'
  import Search        from './lib/components/Search.svelte'
  import { route, initRouter } from './lib/utils/router.js'

  let interval = $state(null)

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
      interval = setInterval(loadGlobal, 30_000)

      const cleanupRouter = initRouter()
      const unsubRoute = route.subscribe(r => {
        if (!r) return
        if (r.view === 'package' && r.params?.pkg_id) {
          activePackageId.set(r.params.pkg_id)
          currentView.set('package')
        } else if (['packages','learn','progress','guide','search'].includes(r.view)) {
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
          <div class="brand-ver">v{VERSION}</div>
        </div>
      </div>

      <nav class="nav">
        <button class="nav-item" class:active={$currentView==='packages'}
          onclick={() => { currentView.set('packages'); activePackageId.set(null) }}>
          <i class="fa-solid fa-box-archive"></i>
          <span>Alle Pakete</span>
          {#if ($globalStats?.total_packages ?? 0) > 0}
            <span class="nc">{$globalStats.total_packages}</span>
          {/if}
        </button>

        <button class="nav-item" class:active={$currentView==='learn'}
          onclick={() => currentView.set('learn')}>
          <i class="fa-solid fa-play"></i>
          <span>Lernen</span>
          {#if $activeSession}
            <span class="nbadge live"><i class="fa-solid fa-circle"></i></span>
          {/if}
          {#if ($globalStats?.due_today ?? 0) > 0}
            <span class="nbadge due">{$globalStats.due_today}</span>
          {/if}
        </button>

        <button class="nav-item" class:active={$currentView==='progress'}
          onclick={() => currentView.set('progress')}>
          <i class="fa-solid fa-chart-line"></i>
          <span>Fortschritt</span>
        </button>

        <button class="nav-item" class:active={$currentView==='search'}
          onclick={() => currentView.set('search')}>
          <i class="fa-solid fa-magnifying-glass"></i>
          <span>Suche</span>
        </button>

        <button class="nav-item" class:active={$currentView==='guide'}
          onclick={() => currentView.set('guide')}>
          <i class="fa-solid fa-map"></i>
          <span>Anleitung</span>
        </button>
      </nav>

      {#if ($packages || []).length > 0}
        <div class="pkg-section">
          <div class="pkg-section-label">Pakete</div>
          {#each ($packages || []) as pkg (pkg.id)}
            <button
              class="pkg-item"
              class:active={$activePackageId === pkg.id && $currentView === 'package'}
              style="--c:{pkg.color}"
              onclick={() => { activePackageId.set(pkg.id); currentView.set('package') }}
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
      {/if}

      <div class="sf">
        <div class="user-row">
          <i class="fa-solid fa-user"></i>
          <span>{$authUser.display_name || $authUser.email}</span>
          <button class="logout-btn" title="Abmelden" onclick={() => authUser.logout()}>
            <i class="fa-solid fa-right-from-bracket"></i>
          </button>
        </div>
        <div class="ai-status" class:online={$aiOnline}>
          <div class="ai-dot" class:online={$aiOnline} class:offline={!$aiOnline}></div>
          <span>LM Studio</span>
        </div>
        <div class="theme-row">
          {#each [
            {id:'dark',     icon:'fa-moon'},
            {id:'light',    icon:'fa-sun'},
            {id:'soft',     icon:'fa-leaf'},
            {id:'contrast', icon:'fa-circle-half-stroke'},
            {id:'warm',     icon:'fa-fire'},
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
      </div>
    </aside>

    <main class="main">
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
      {:else}
        <Packages />
      {/if}
    </main>

    {#if $toastStore}
      {#key $toastStore.id}
        <div class="toast toast--{$toastStore.type}" role="alert">
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
  </div>
{/if}

<style>
  .app { display:flex; height:100vh; overflow:hidden; }

  .sidebar {
    width:200px; flex-shrink:0; background:var(--bg1);
    border-right:1px solid var(--border); display:flex;
    flex-direction:column; overflow-y:auto;
  }
  .main {
    flex:1; overflow-y:auto; background:var(--bg0); min-width:0;
  }

  .brand { padding:14px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:9px; }
  .brand-icon { width:26px;height:26px;background:var(--accent);border-radius: 3px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;flex-shrink:0; }
  .brand-name { font-size:13px;font-weight:800;color:var(--text0);letter-spacing:-.03em; }
  .brand-ver  { font-size:9px;color:var(--text3);font-family:'JetBrains Mono',monospace;margin-left:auto; }

  .pkg-section { padding:8px 0; border-top:1px solid var(--border); }
  .pkg-section-label { padding:8px 14px 4px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--text3); }
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
  .nbadge.live { background:var(--err);color:#fff; }
  .nbadge.due  { background:var(--accent);color:#fff; }

  .sf { padding:10px 14px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:8px;margin-top:auto; }
  .user-row { display:flex;align-items:center;gap:7px;font-size:11px;color:var(--text2); }
  .user-row span { flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
  .logout-btn {
    background:none;border:none;color:var(--text3);cursor:pointer;padding:2px 4px;
    font-size:11px;transition:color .12s;
  }
  .logout-btn:hover { color:var(--err); }
  .ai-status { display:flex;align-items:center;gap:7px;font-size:11px;color:var(--text3); }
  .ai-dot    { width:6px;height:6px;border-radius:50%;background:var(--text3);flex-shrink:0; }
  .ai-dot.online  { background:var(--ok);box-shadow:0 0 5px var(--ok); }
  .ai-dot.offline { background:var(--text3); }
  .theme-row { display:flex;gap:4px; }
  .theme-dot {
    width:22px;height:22px;border-radius: 2px;border:1px solid var(--border);
    background:none;cursor:pointer;font-size:10px;color:var(--text3);
    display:flex;align-items:center;justify-content:center;transition:all .12s;
  }
  .theme-dot:hover  { border-color:var(--text2);color:var(--text1); }
  .theme-dot.active { border-color:var(--accent);color:var(--accent);background:var(--glow); }
</style>
