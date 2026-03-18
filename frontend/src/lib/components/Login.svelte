<script>
  import { authUser, showToast } from '../stores/index.js'

  let email = $state('admin@example.com')
  let password = $state('admin')
  let loading = $state(false)
  let error = $state('')

  async function handleLogin() {
    error = ''
    loading = true
    try {
      await authUser.login(email, password)
    } catch (e) {
      error = e.message || 'Login fehlgeschlagen'
    } finally {
      loading = false
    }
  }
</script>

<div class="login-wrap">
  <div class="login-card">
    <div class="login-header">
      <div class="login-icon"><i class="fa-solid fa-graduation-cap"></i></div>
      <h1>Learning-By-Tooling</h1>
      <p>Lernplattform anmelden</p>
    </div>

    <form onsubmit={e => { e.preventDefault(); handleLogin() }}>
      <label>
        <span>E-Mail</span>
        <input type="email" bind:value={email} required autocomplete="email" />
      </label>

      <label>
        <span>Passwort</span>
        <input type="password" bind:value={password} required autocomplete="current-password" />
      </label>

      {#if error}
        <div class="login-error">{error}</div>
      {/if}

      <button type="submit" class="login-btn" disabled={loading}>
        {#if loading}
          <i class="fa-solid fa-spinner fa-spin"></i> Anmelden...
        {:else}
          Anmelden
        {/if}
      </button>
    </form>
  </div>
</div>

<style>
  .login-wrap {
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; background: var(--bg0);
  }
  .login-card {
    background: var(--bg1); border: 1px solid var(--border);
    border-radius: 6px; padding: 32px; width: 340px;
    box-shadow: 0 4px 24px rgba(0,0,0,.2);
  }
  .login-header { text-align: center; margin-bottom: 24px; }
  .login-icon {
    width: 40px; height: 40px; background: var(--accent);
    border-radius: 4px; display: inline-flex; align-items: center;
    justify-content: center; color: #fff; font-size: 18px; margin-bottom: 12px;
  }
  h1 { font-size: 18px; font-weight: 800; color: var(--text0); margin: 0 0 4px; letter-spacing: -.03em; }
  p { font-size: 12px; color: var(--text3); margin: 0; }

  form { display: flex; flex-direction: column; gap: 14px; }
  label { display: flex; flex-direction: column; gap: 4px; }
  label span { font-size: 11px; font-weight: 600; color: var(--text2); text-transform: uppercase; letter-spacing: .05em; }
  input {
    background: var(--bg0); border: 1px solid var(--border); border-radius: 3px;
    padding: 8px 10px; color: var(--text0); font-size: 13px;
    font-family: inherit; outline: none; transition: border-color .15s;
  }
  input:focus { border-color: var(--accent); }

  .login-error {
    background: rgba(255,80,80,.1); border: 1px solid rgba(255,80,80,.3);
    border-radius: 3px; padding: 8px 10px; font-size: 12px; color: var(--err);
  }
  .login-btn {
    background: var(--accent); color: #fff; border: none; border-radius: 3px;
    padding: 10px; font-size: 13px; font-weight: 700; cursor: pointer;
    font-family: inherit; transition: opacity .15s;
  }
  .login-btn:hover { opacity: .9; }
  .login-btn:disabled { opacity: .5; cursor: default; }
</style>
