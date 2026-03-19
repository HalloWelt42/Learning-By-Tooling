<script>
  import { userSettings, saveSetting, showToast, authUser } from '../../stores/index.js'
  import { apiPost, apiPatch } from '../../utils/api.js'

  let { embedded = false } = $props()

  let soundEnabled = $state(true)
  let dailyGoal = $state(100)
  let preferredMode = $state('standard')
  let sessionSize = $state(10)
  let displayName = $state('')
  let nameChanged = $state(false)

  // Passwort-Felder
  let pwOld = $state('')
  let pwNew1 = $state('')
  let pwNew2 = $state('')
  let pwBusy = $state(false)

  // Settings aus Store laden
  $effect(() => {
    const s = $userSettings
    soundEnabled = s.sound_enabled ?? true
    dailyGoal = s.daily_goal ?? 100
    preferredMode = s.preferred_mode ?? 'standard'
    sessionSize = s.session_size ?? 10
  })

  $effect(() => {
    if ($authUser) {
      displayName = $authUser.display_name || $authUser.email || ''
    }
  })

  function toggleSound() {
    soundEnabled = !soundEnabled
    saveSetting('sound_enabled', soundEnabled)
    showToast(soundEnabled ? 'Sound aktiviert' : 'Sound deaktiviert', 'info', 1500)
  }

  function setDailyGoal(val) {
    dailyGoal = val
    saveSetting('daily_goal', val)
  }

  function setPreferredMode(mode) {
    preferredMode = mode
    saveSetting('preferred_mode', mode)
  }

  function setSessionSize(size) {
    sessionSize = size
    saveSetting('session_size', size)
  }

  async function saveDisplayName() {
    if (!displayName.trim()) return
    try {
      await apiPatch('/api/auth/display-name', { display_name: displayName.trim() })
      // Lokalen User aktualisieren
      const stored = localStorage.getItem('lbt-user')
      if (stored) {
        const u = JSON.parse(stored)
        u.display_name = displayName.trim()
        localStorage.setItem('lbt-user', JSON.stringify(u))
      }
      showToast('Name gespeichert', 'success', 2000)
      nameChanged = false
    } catch(e) { showToast(e.message, 'error') }
  }

  async function changePassword() {
    if (pwNew1 !== pwNew2) { showToast('Passwörter stimmen nicht überein', 'error'); return }
    if (pwNew1.length < 4) { showToast('Mindestens 4 Zeichen', 'error'); return }
    pwBusy = true
    try {
      await apiPost('/api/auth/change-password', { old_password: pwOld, new_password: pwNew1 })
      showToast('Passwort geändert', 'success')
      pwOld = ''; pwNew1 = ''; pwNew2 = ''
    } catch(e) { showToast(e.message, 'error') }
    pwBusy = false
  }

  const MODES = [
    { id: 'standard', label: 'Karteikarte', icon: 'fa-clone' },
    { id: 'mc', label: 'Multiple Choice', icon: 'fa-list-check' },
    { id: 'write', label: 'Freitext', icon: 'fa-keyboard' },
    { id: 'srs', label: 'Spaced Repetition', icon: 'fa-brain' },
  ]

  const GOALS = [50, 75, 100, 150, 200, 300]
  const SIZES = [5, 10, 15, 20, 30, 50]
</script>

<div class="page-wrap">
  {#if !embedded}
    <div class="page-hd">
      <h1 class="page-title"><i class="fa-solid fa-gear"></i> Einstellungen</h1>
    </div>
  {/if}

  <div class="settings-grid">

    <!-- Sound -->
    <div class="settings-card">
      <div class="settings-card-hd">
        <i class="fa-solid fa-volume-high"></i>
        <span>Sound</span>
      </div>
      <div class="settings-row">
        <span class="settings-label">Sound-Effekte</span>
        <button class="toggle-switch" class:active={soundEnabled} onclick={toggleSound}>
          <span class="toggle-knob"></span>
        </button>
      </div>
      <p class="settings-hint">Münz-Sound bei richtigen Antworten, Combo-Effekte</p>
    </div>

    <!-- Tagesziel -->
    <div class="settings-card">
      <div class="settings-card-hd">
        <i class="fa-solid fa-bullseye"></i>
        <span>Tagesziel</span>
      </div>
      <div class="settings-row">
        <span class="settings-label">XP pro Tag</span>
        <div class="chip-group">
          {#each GOALS as g}
            <button class="chip" class:active={dailyGoal === g} onclick={() => setDailyGoal(g)}>{g}</button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Lernmodus -->
    <div class="settings-card">
      <div class="settings-card-hd">
        <i class="fa-solid fa-graduation-cap"></i>
        <span>Lernen</span>
      </div>
      <div class="settings-row">
        <span class="settings-label">Bevorzugter Modus</span>
        <div class="chip-group">
          {#each MODES as m}
            <button class="chip" class:active={preferredMode === m.id} onclick={() => setPreferredMode(m.id)} title={m.label}>
              <i class="fa-solid {m.icon}"></i> {m.label}
            </button>
          {/each}
        </div>
      </div>
      <div class="settings-row" style="margin-top:10px">
        <span class="settings-label">Karten pro Session</span>
        <div class="chip-group">
          {#each SIZES as s}
            <button class="chip" class:active={sessionSize === s} onclick={() => setSessionSize(s)}>{s}</button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Profil -->
    <div class="settings-card">
      <div class="settings-card-hd">
        <i class="fa-solid fa-user"></i>
        <span>Profil</span>
      </div>
      <div class="settings-row">
        <span class="settings-label">Anzeigename</span>
        <div class="input-row">
          <input type="text" bind:value={displayName} oninput={() => nameChanged = true} />
          {#if nameChanged}
            <button class="btn btn-primary btn-sm" onclick={saveDisplayName}>Speichern</button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Passwort -->
    <div class="settings-card">
      <div class="settings-card-hd">
        <i class="fa-solid fa-lock"></i>
        <span>Passwort ändern</span>
      </div>
      <div class="pw-form">
        <input type="password" placeholder="Aktuelles Passwort" bind:value={pwOld} />
        <input type="password" placeholder="Neues Passwort" bind:value={pwNew1} />
        <input type="password" placeholder="Neues Passwort wiederholen" bind:value={pwNew2} />
        <button class="btn btn-primary btn-sm" disabled={pwBusy || !pwOld || !pwNew1 || !pwNew2} onclick={changePassword}>
          {pwBusy ? 'Speichern...' : 'Passwort ändern'}
        </button>
      </div>
    </div>

  </div>
</div>

<style>
  .settings-grid {
    display:grid; grid-template-columns:repeat(auto-fill, minmax(340px, 1fr));
    gap:16px; padding:0 20px 40px;
  }
  .settings-card {
    background:var(--bg1); border:1px solid var(--border); border-radius:4px; padding:16px;
  }
  .settings-card-hd {
    display:flex; align-items:center; gap:8px; font-size:13px; font-weight:700;
    color:var(--text0); margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid var(--border);
  }
  .settings-card-hd i { color:var(--accent); font-size:12px; }
  .settings-row {
    display:flex; align-items:center; gap:12px; flex-wrap:wrap;
  }
  .settings-label {
    font-size:12px; color:var(--text2); min-width:120px; flex-shrink:0;
  }
  .settings-hint {
    font-size:11px; color:var(--text3); margin-top:8px;
  }

  /* Toggle Switch */
  .toggle-switch {
    width:40px; height:22px; border-radius:4px; border:1px solid var(--border);
    background:var(--bg2); cursor:pointer; position:relative; transition:all .15s;
    padding:0; flex-shrink:0;
  }
  .toggle-switch.active { background:var(--accent); border-color:var(--accent); }
  .toggle-knob {
    position:absolute; top:2px; left:2px; width:16px; height:16px;
    border-radius:2px; background:#fff; transition:transform .15s;
  }
  .toggle-switch.active .toggle-knob { transform:translateX(18px); }

  /* Chip Group */
  .chip-group { display:flex; gap:4px; flex-wrap:wrap; }
  .chip {
    padding:4px 10px; font-size:11px; border:1px solid var(--border);
    border-radius:3px; background:var(--bg2); color:var(--text2);
    cursor:pointer; transition:all .12s; font-family:inherit;
    white-space:nowrap;
  }
  .chip:hover { border-color:var(--text3); color:var(--text1); }
  .chip.active { border-color:var(--accent); color:var(--accent); background:var(--glow); }
  .chip i { font-size:10px; margin-right:3px; }

  /* Input Row */
  .input-row { display:flex; gap:8px; align-items:center; flex:1; }
  .input-row input {
    background:var(--bg2); border:1px solid var(--border); border-radius:3px;
    padding:6px 10px; font-size:12px; color:var(--text0); font-family:inherit;
    flex:1; min-width:120px;
  }
  .input-row input:focus { border-color:var(--accent); outline:none; }

  /* PW Form */
  .pw-form { display:flex; flex-direction:column; gap:8px; }
  .pw-form input {
    background:var(--bg2); border:1px solid var(--border); border-radius:3px;
    padding:6px 10px; font-size:12px; color:var(--text0); font-family:inherit;
  }
  .pw-form input:focus { border-color:var(--accent); outline:none; }
</style>
