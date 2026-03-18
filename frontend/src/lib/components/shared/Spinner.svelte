<!--
  Spinner.svelte -- Universelle Lade-Komponente
  Props:
    size:    'sm' | 'md' | 'lg'
    label:   Text unter dem Spinner (optional)
    overlay: Bool -- zeigt halbtransparentes Overlay über Parent
    steps:   Array<{label, done, active}> -- Prozess-Schritte
-->
<script>
  let {
    size    = 'md',
    label   = '',
    overlay = false,
    steps   = [],
  } = $props()
</script>

{#if overlay}
  <div class="overlay">
    <div class="overlay-box">
      <div class="spinner spinner--{size}"></div>
      {#if label}
        <div class="overlay-label">{label}</div>
      {/if}
      {#if steps.length > 0}
        <div class="steps">
          {#each steps as step, i}
            <div class="step" class:done={step.done} class:active={step.active}>
              <div class="step-dot">
                {#if step.done}
                  <i class="fa-solid fa-check"></i>
                {:else if step.active}
                  <div class="step-spin"></div>
                {:else}
                  <span>{i + 1}</span>
                {/if}
              </div>
              <div class="step-label">{step.label}</div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{:else}
  <div class="inline-spinner">
    <div class="spinner spinner--{size}"></div>
    {#if label}
      <span class="inline-label">{label}</span>
    {/if}
  </div>
{/if}

<style>
  .spinner {
    border-radius: 50%;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    animation: spin .7s linear infinite;
    flex-shrink: 0;
  }
  .spinner--sm { width: 16px; height: 16px; border-width: 2px; }
  .spinner--md { width: 28px; height: 28px; }
  .spinner--lg { width: 44px; height: 44px; border-width: 4px; }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* Overlay */
  .overlay {
    position: absolute;
    inset: 0;
    background: color-mix(in srgb, var(--bg0) 85%, transparent);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    border-radius: inherit;
  }
  .overlay-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 28px 32px;
    background: var(--bg1);
    border: 1px solid var(--border);
    border-radius: 4px;
    box-shadow: 0 16px 48px var(--shadow);
    min-width: 220px;
  }
  .overlay-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text1);
    text-align: center;
  }

  /* Steps */
  .steps {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
    margin-top: 4px;
  }
  .step {
    display: flex;
    align-items: center;
    gap: 10px;
    opacity: .35;
    transition: opacity .3s;
  }
  .step.active { opacity: 1; }
  .step.done   { opacity: .7; }

  .step-dot {
    width: 24px; height: 24px;
    border-radius: 50%;
    border: 2px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; color: var(--text2);
    flex-shrink: 0; transition: all .3s;
  }
  .step.active .step-dot { border-color: var(--accent); color: var(--accent); }
  .step.done   .step-dot { border-color: var(--ok); background: var(--ok); color: #fff; }
  .step.done   .step-dot i { font-size: 10px; }

  .step-spin {
    width: 10px; height: 10px;
    border-radius: 50%;
    border: 2px solid color-mix(in srgb, var(--accent) 30%, transparent);
    border-top-color: var(--accent);
    animation: spin .6s linear infinite;
  }
  .step-label { font-size: 12px; font-weight: 500; color: var(--text1); }

  /* Inline */
  .inline-spinner { display: inline-flex; align-items: center; gap: 8px; }
  .inline-label   { font-size: 12px; color: var(--text2); }
</style>
