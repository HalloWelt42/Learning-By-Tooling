<script>
  import { onMount } from 'svelte'
  import { showToast, packages, authUser } from '../../stores/index.js'
  import { apiGet, apiPost, apiDelete } from '../../utils/api.js'
  import Settings from './Settings.svelte'

  let tab = $state('settings')  // 'settings' | 'users'
  let users = $state([])
  let showForm = $state(false)
  let form = $state({ email: '', password: '', display_name: '' })
  let creating = $state(false)

  onMount(loadUsers)

  async function loadUsers() {
    try { users = await apiGet('/api/admin/users') } catch(e) { users = [] }
  }

  async function createUser() {
    if (!form.email || !form.password) { showToast('E-Mail und Passwort erforderlich', 'error'); return }
    creating = true
    try {
      await apiPost('/api/admin/users', form)
      showToast(`${form.email} angelegt`, 'success')
      form = { email: '', password: '', display_name: '' }
      showForm = false
      await loadUsers()
    } catch(e) {
      showToast(e.message || 'Fehler beim Anlegen', 'error')
    }
    creating = false
  }

  let resetUser = $state(null)
  let resetPw = $state('')

  async function doResetPassword() {
    if (!resetPw || resetPw.length < 4) { showToast('Mindestens 4 Zeichen', 'error'); return }
    try {
      await apiPost(`/api/admin/users/${resetUser.id}/reset-password`, { new_password: resetPw })
      showToast(`Passwort für ${resetUser.email} zurückgesetzt`, 'success')
      resetUser = null; resetPw = ''
    } catch(e) {
      showToast(e.message || 'Fehler', 'error')
    }
  }

  async function resetUserStats(u) {
    try {
      await apiPost(`/api/admin/reset-user-stats/${u.id}`, {})
      showToast(`Lernfortschritt von ${u.display_name || u.email} zurückgesetzt`, 'success')
      await loadUsers()
    } catch(e) { showToast(e.message || 'Fehler', 'error') }
  }

  async function toggleUser(u) {
    try {
      await apiPost(`/api/admin/users/${u.id}/toggle`, {})
      showToast(`${u.email} ${u.disabled ? 'aktiviert' : 'pausiert'}`, 'success')
      await loadUsers()
    } catch(e) { showToast(e.message || 'Fehler', 'error') }
  }

  async function removeUser(u) {
    try {
      await apiDelete(`/api/admin/users/${u.id}`)
      showToast(`${u.email} entfernt`, 'success')
      await loadUsers()
    } catch(e) {
      showToast(e.message || 'Fehler', 'error')
    }
  }
</script>

<div class="page">
  <div class="page-hd">
    <div>
      <h1 class="page-title"><i class="fa-solid fa-gear"></i> Verwaltung</h1>
    </div>
  </div>

  <div class="admin-tabs">
    <button class="admin-tab" class:active={tab === 'settings'} onclick={() => tab = 'settings'}>
      <i class="fa-solid fa-sliders"></i> Einstellungen
    </button>
    <button class="admin-tab" class:active={tab === 'users'} onclick={() => tab = 'users'}>
      <i class="fa-solid fa-users"></i> Benutzer
    </button>
  </div>

  {#if tab === 'settings'}
    <Settings embedded={true} />
  {:else}
  <!-- User-Liste -->
  <div class="card-box" style="max-width:800px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div class="section-label" style="margin:0">Benutzer</div>
      <button class="btn btn-primary btn-sm" onclick={() => showForm = !showForm}>
        <i class="fa-solid fa-user-plus"></i> Neuer Benutzer
      </button>
    </div>

    {#if showForm}
      <div class="admin-form">
        <input type="email" class="input" placeholder="E-Mail-Adresse" bind:value={form.email} />
        <input type="text" class="input" placeholder="Anzeigename (optional)" bind:value={form.display_name} />
        <input type="password" class="input" placeholder="Passwort" bind:value={form.password} />
        <button class="btn btn-primary btn-sm" onclick={createUser} disabled={creating}>
          {creating ? 'Erstelle...' : 'Anlegen'}
        </button>
      </div>
    {/if}

    <div class="user-list">
      {#each users as u (u.id)}
        <div class="user-item">
          <div class="user-icon">
            <i class="fa-solid fa-user"></i>
          </div>
          <div class="user-info">
            <div class="user-name">
              {u.display_name || u.email}
              {#if u.is_admin}<span class="user-badge-admin">Admin</span>{/if}
            </div>
            <div class="user-meta">{u.email}</div>
            <div class="user-stats">
              <span><i class="fa-solid fa-play"></i> {u.sessions} Sessions</span>
              <span><i class="fa-solid fa-check"></i> {u.reviews} Antworten</span>
              <span><i class="fa-solid fa-box"></i> {u.packages} Pakete</span>
            </div>
          </div>
          <button class="btn-icon" title="Passwort zurücksetzen" onclick={() => { resetUser = u; resetPw = '' }}>
            <i class="fa-solid fa-key"></i>
          </button>
          <button class="btn-icon btn-icon-warn" title="Lernfortschritt zurücksetzen" onclick={() => resetUserStats(u)}>
            <i class="fa-solid fa-arrow-rotate-left"></i>
          </button>
          {#if u.id !== $authUser?.id}
            <button class="btn-icon" title="{u.disabled ? 'Aktivieren' : 'Pausieren'}" onclick={() => toggleUser(u)}>
              <i class="fa-solid {u.disabled ? 'fa-play' : 'fa-pause'}"></i>
            </button>
            <button class="btn-icon btn-icon-danger" title="Benutzer entfernen" onclick={() => removeUser(u)}>
              <i class="fa-solid fa-trash-can"></i>
            </button>
          {/if}
        </div>
      {/each}
    </div>

    {#if resetUser}
      <div class="reset-form">
        <div style="font-size:12px;font-weight:600;color:var(--text1);margin-bottom:6px">
          Neues Passwort für {resetUser.display_name || resetUser.email}
        </div>
        <div style="display:flex;gap:6px;align-items:center">
          <input type="password" placeholder="Neues Passwort (mind. 4 Zeichen)" bind:value={resetPw}
            style="flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:6px 10px;font-size:12px;color:var(--text0);font-family:inherit" />
          <button class="btn btn-primary btn-sm" onclick={doResetPassword}>Setzen</button>
          <button class="btn btn-ghost btn-sm" onclick={() => resetUser = null}>Abbrechen</button>
        </div>
      </div>
    {/if}
  </div>
  {/if}
</div>

<style>
  .admin-tabs {
    display:flex;gap:4px;padding:0 20px 16px;
  }
  .admin-tab {
    padding:8px 16px;font-size:12px;font-weight:600;border:none;
    border-radius:4px;background:var(--bg2);color:var(--text2);cursor:pointer;
    transition:all .12s;font-family:inherit;display:flex;align-items:center;gap:6px;
  }
  .admin-tab:hover { background:var(--bg3);color:var(--text1); }
  .admin-tab.active { background:var(--bg3);color:var(--accent);box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent); }
  .admin-tab i { font-size:11px; }
  .admin-form {
    display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;
    padding:14px;background:var(--bg2);border-radius:4px;box-shadow:0 1px 3px var(--shadow);
  }
  .admin-form .btn { grid-column:span 2; }
  .user-list { display:flex;flex-direction:column;gap:6px; }
  .reset-form { margin-top:12px;padding:12px;background:var(--bg2);border:1px solid var(--accent);border-radius:4px; }
  .user-item {
    display:flex;align-items:center;gap:12px;padding:12px;
    background:var(--bg2);border-radius:4px;box-shadow:0 1px 3px var(--shadow);
  }
  .user-icon { width:32px;height:32px;border-radius:4px;background:var(--bg3);display:flex;align-items:center;justify-content:center;color:var(--text3);flex-shrink:0; }
  .user-info { flex:1;min-width:0; }
  .user-name { font-size:13px;font-weight:700;color:var(--text0);display:flex;align-items:center;gap:6px; }
  .user-meta { font-size:11px;color:var(--text3);margin-top:1px; }
  .user-stats { display:flex;gap:12px;font-size:10px;color:var(--text2);margin-top:4px; }
  .user-stats i { font-size:9px;color:var(--text3); }
  .user-badge-admin { font-size:9px;background:var(--accent);color:#fff;padding:1px 6px;border-radius:2px;font-weight:700; }
</style>
