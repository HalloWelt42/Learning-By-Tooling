<!--
  AiProcess.svelte -- Universelle KI-Prozess-Visualisierung
  Zeigt dem Benutzer klar was die KI gerade macht.

  Props:
    title     -- Überschrift (z.B. "KI bewertet deine Antwort")
    steps     -- Array<{ label: string, sublabel?: string }>
    active    -- Index des aktiven Schritts (0-based)
    done      -- Bool: Alle Schritte fertig
    error     -- Bool: Fehler aufgetreten
    progress  -- Optional: 0-100 für übergeordneten Fortschrittsbalken
    compact   -- Bool: Kompakte Darstellung ohne Box
-->
<script>
  let {
    title    = 'KI arbeitet…',
    steps    = [],
    active   = 0,
    done     = false,
    error    = false,
    progress = null,
    compact  = false,
  } = $props()

  // Elapsed timer
  let elapsed = $state(0)
  let timer   = null

  $effect(() => {
    if (!done && !error) {
      elapsed = 0
      timer = setInterval(() => elapsed++, 1000)
    } else {
      clearInterval(timer)
    }
    return () => clearInterval(timer)
  })

  function stepState(i) {
    if (done)    return i < steps.length ? 'done' : 'pending'
    if (error)   return i < active ? 'done' : i === active ? 'error' : 'pending'
    if (i < active)  return 'done'
    if (i === active) return 'running'
    return 'pending'
  }

  const ICONS = {
    done:    'fa-check',
    running: 'fa-spinner fa-spin',
    error:   'fa-xmark',
    pending: '',
  }
  const COLORS = {
    done:    'var(--ok)',
    running: 'var(--accent)',
    error:   'var(--err)',
    pending: 'var(--text3)',
  }
</script>

<div class="aip" class:compact class:aip--done={done} class:aip--error={error}>

  <!-- Header -->
  <div class="aip-header">
    <div class="aip-icon">
      {#if done}
        <i class="fa-solid fa-circle-check" style="color:var(--ok)"></i>
      {:else if error}
        <i class="fa-solid fa-circle-xmark" style="color:var(--err)"></i>
      {:else}
        <i class="fa-solid fa-brain aip-pulse" style="color:var(--accent)"></i>
      {/if}
    </div>
    <div class="aip-title-wrap">
      <span class="aip-title">{title}</span>
      {#if !done && !error}
        <span class="aip-timer">{elapsed}s</span>
      {:else if done}
        <span class="aip-fin ok">Fertig in {elapsed}s</span>
      {:else}
        <span class="aip-fin err">Fehlgeschlagen</span>
      {/if}
    </div>
  </div>

  <!-- Optional progress bar -->
  {#if progress !== null}
    <div class="aip-bar">
      <div class="aip-bar-fill" style="width:{progress}%"></div>
    </div>
    <div class="aip-pct">{Math.round(progress)}%</div>
  {:else if !done && !error}
    <div class="aip-bar">
      <div class="aip-bar-scan"></div>
    </div>
  {/if}

  <!-- Steps -->
  {#if steps.length > 0}
    <div class="aip-steps">
      {#each steps as step, i}
        {@const st = stepState(i)}
        <div class="aip-step aip-step--{st}">
          <!-- Connector line -->
          {#if i < steps.length - 1}
            <div class="aip-connector" class:filled={st === 'done'}></div>
          {/if}

          <!-- Dot -->
          <div class="aip-dot">
            {#if st === 'done'}
              <i class="fa-solid fa-check"></i>
            {:else if st === 'running'}
              <div class="aip-spin"></div>
            {:else if st === 'error'}
              <i class="fa-solid fa-xmark"></i>
            {:else}
              <span class="aip-num">{i + 1}</span>
            {/if}
          </div>

          <!-- Label -->
          <div class="aip-step-body">
            <span class="aip-step-label">{step.label}</span>
            {#if step.sublabel && st === 'running'}
              <span class="aip-step-sub">{step.sublabel}</span>
            {/if}
          </div>

          <!-- Status badge -->
          <div class="aip-step-status">
            {#if st === 'done'}
              <span class="sst ok"><i class="fa-solid fa-check"></i></span>
            {:else if st === 'running'}
              <span class="sst run">läuft</span>
            {:else if st === 'error'}
              <span class="sst err"><i class="fa-solid fa-xmark"></i></span>
            {:else}
              <span class="sst wait">wartet</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .aip {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 16px;
    transition: border-color .3s;
  }
  .aip.compact { background: transparent; border: none; padding: 0; }
  .aip--done   { border-color: color-mix(in srgb, var(--ok) 40%, transparent); }
  .aip--error  { border-color: color-mix(in srgb, var(--err) 40%, transparent); }

  /* Header */
  .aip-header {
    display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
  }
  .aip-icon { font-size: 16px; flex-shrink: 0; }
  .aip-pulse { animation: glow-pulse 1.6s ease-in-out infinite; }
  @keyframes glow-pulse {
    0%,100% { opacity: 1; }
    50%      { opacity: .5; }
  }
  .aip-title-wrap { display: flex; flex-direction: column; gap: 1px; }
  .aip-title { font-size: 13px; font-weight: 600; color: var(--text0); }
  .aip-timer { font-size: 10px; color: var(--text3); font-family: 'JetBrains Mono', monospace; }
  .aip-fin   { font-size: 10px; font-family: 'JetBrains Mono', monospace; font-weight: 700; }
  .aip-fin.ok  { color: var(--ok); }
  .aip-fin.err { color: var(--err); }

  /* Progress bar */
  .aip-bar {
    height: 3px; background: var(--bg3); border-radius: 2px;
    overflow: hidden; margin-bottom: 4px; position: relative;
  }
  .aip-bar-fill {
    height: 100%; background: var(--accent); border-radius: 2px;
    transition: width .4s ease;
  }
  .aip-bar-scan {
    position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent 0%, var(--accent) 50%, transparent 100%);
    animation: scan-anim 1.6s ease-in-out infinite;
    width: 60%;
  }
  @keyframes scan-anim {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(280%); }
  }
  .aip-pct { font-size: 10px; color: var(--accent); font-family: 'JetBrains Mono', monospace; text-align: right; margin-bottom: 8px; }

  /* Steps */
  .aip-steps {
    display: flex; flex-direction: column; gap: 0;
    margin-top: 6px;
  }
  .aip-step {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 7px 0; position: relative;
    opacity: .35; transition: opacity .25s;
  }
  .aip-step--running { opacity: 1; }
  .aip-step--done    { opacity: .7; }
  .aip-step--error   { opacity: 1; }

  /* Vertical connector */
  .aip-connector {
    position: absolute; left: 9px; top: 24px; bottom: -7px;
    width: 1px; background: var(--border); z-index: 0;
  }
  .aip-connector.filled { background: var(--ok); }

  /* Dot */
  .aip-dot {
    width: 20px; height: 20px; border-radius: 50%;
    border: 1.5px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; z-index: 1; background: var(--bg2);
    transition: all .25s;
  }
  .aip-step--running .aip-dot { border-color: var(--accent); }
  .aip-step--done    .aip-dot { border-color: var(--ok); background: var(--ok); }
  .aip-step--done    .aip-dot i { color: #fff; font-size: 9px; }
  .aip-step--error   .aip-dot { border-color: var(--err); background: var(--err); }
  .aip-step--error   .aip-dot i { color: #fff; font-size: 9px; }

  .aip-spin {
    width: 10px; height: 10px; border-radius: 50%;
    border: 2px solid color-mix(in srgb, var(--accent) 30%, transparent);
    border-top-color: var(--accent);
    animation: dot-spin .7s linear infinite;
  }
  @keyframes dot-spin { to { transform: rotate(360deg); } }

  .aip-num { font-size: 9px; font-weight: 700; color: var(--text3); }

  /* Step body */
  .aip-step-body { flex: 1; display: flex; flex-direction: column; gap: 2px; padding-top: 1px; }
  .aip-step-label { font-size: 12px; font-weight: 500; color: var(--text1); line-height: 1.3; }
  .aip-step-sub   { font-size: 10px; color: var(--accent); font-family: 'JetBrains Mono', monospace; }

  /* Status badges */
  .aip-step-status { padding-top: 2px; }
  .sst {
    font-size: 9px; font-weight: 700; letter-spacing: .06em;
    padding: 1px 6px; border-radius: 4px; text-transform: uppercase;
  }
  .sst.ok   { color: var(--ok);     background: var(--glowok); }
  .sst.run  { color: var(--accent); background: var(--glow); animation: badge-pulse 1.2s infinite; }
  .sst.err  { color: var(--err);    background: color-mix(in srgb, var(--err) 12%, transparent); }
  .sst.wait { color: var(--text3);  background: var(--bg3); }
  @keyframes badge-pulse { 0%,100%{opacity:1} 50%{opacity:.6} }
</style>
