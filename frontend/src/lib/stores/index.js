import { writable } from 'svelte/store'
import { apiGet, apiPost, apiPatch, BASE } from '../utils/api.js'

// -- Auth ---------------------------------------------------------------------

function createAuth() {
  const stored = typeof localStorage !== 'undefined'
    ? localStorage.getItem('lbt-user') : null
  const token = typeof localStorage !== 'undefined'
    ? localStorage.getItem('lbt-token') : null
  const initial = stored && token ? JSON.parse(stored) : null

  const { subscribe, set } = writable(initial)

  return {
    subscribe,
    async login(email, password) {
      const res = await apiPost('/api/auth/login', { email, password })
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('lbt-token', res.token)
        localStorage.setItem('lbt-user', JSON.stringify(res.user))
      }
      set(res.user)
      return res.user
    },
    logout() {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('lbt-token')
        localStorage.removeItem('lbt-user')
      }
      set(null)
    }
  }
}
export const authUser = createAuth()

// -- Theme --------------------------------------------------------------------

function createTheme() {
  const saved = typeof localStorage !== 'undefined'
    ? (localStorage.getItem('lv-theme') || 'dark') : 'dark'
  const { subscribe, set, update } = writable(saved)
  return {
    subscribe,
    set(v) {
      if (typeof localStorage !== 'undefined') localStorage.setItem('lv-theme', v)
      set(v)
    },
    toggle() {
      const CYCLE = ['dark','light','dracula','contrast','warm']
      update(t => {
        const next = CYCLE[(CYCLE.indexOf(t) + 1) % CYCLE.length]
        if (typeof localStorage !== 'undefined') localStorage.setItem('lv-theme', next)
        return next
      })
    }
  }
}
export const theme = createTheme()

// -- Navigation ---------------------------------------------------------------

export const currentView    = writable('packages')
export const activePackageId = writable(null)

// -- Daten --------------------------------------------------------------------

export const packages    = writable([])
export const categories  = writable([])
export const globalStats = writable(null)
export const aiOnline       = writable(false)
export const activeSession  = writable(null)
export const backendVersion = writable(null)
export const backendOnline  = writable(false)

// -- Streak -------------------------------------------------------------------

export const streakData = writable({ current: 0, longest: 0, today: false })

export async function loadStreak() {
  try {
    const s = await apiGet('/api/stats/streak')
    streakData.set(s)
  } catch(e) {}
}

// -- XP ----------------------------------------------------------------------

export const xpData = writable({ xp_total: 0, xp_today: 0 })

export async function loadXp() {
  try {
    const x = await apiGet('/api/stats/xp')
    xpData.set(x)
  } catch(e) {}
}

// -- Sound -------------------------------------------------------------------

let _audioCtx = null
let _buffers = {}
let _soundReady = false

export async function initSound() {
  try {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    const names = ['correct', 'coin', 'bonus', 'error', 'perfect']
    const responses = await Promise.all(names.map(n => fetch(`/sounds/${n}.mp3`)))
    for (let i = 0; i < names.length; i++) {
      if (responses[i].ok) {
        _buffers[names[i]] = await _audioCtx.decodeAudioData(await responses[i].arrayBuffer())
      }
    }
    _soundReady = Object.keys(_buffers).length > 0
  } catch(e) {
    _soundReady = false
  }
}

function _playBuffer(name, volume = 0.4) {
  if (!_soundReady || !_buffers[name] || !_audioCtx) return
  try {
    if (_audioCtx.state === 'suspended') _audioCtx.resume()
    const src = _audioCtx.createBufferSource()
    src.buffer = _buffers[name]
    const gain = _audioCtx.createGain()
    gain.gain.value = volume
    src.connect(gain).connect(_audioCtx.destination)
    src.start()
  } catch(e) {}
}

export function playCoinSound(settings) {
  if (!settings?.sound_enabled) return
  _playBuffer('correct', 0.4)
}

export function playBonusSound(settings) {
  if (!settings?.sound_enabled) return
  _playBuffer('bonus', 0.5)
}

export function playErrorSound(settings) {
  if (!settings?.sound_enabled) return
  _playBuffer('error', 0.35)
}

export function playCoinRainSound(settings) {
  if (!settings?.sound_enabled) return
  _playBuffer('coin', 0.3)
}

export function playPerfectSound(settings) {
  if (!settings?.sound_enabled) return
  _playBuffer('perfect', 0.5)
}

// -- User Settings ------------------------------------------------------------

export const userSettings = writable({
  sound_enabled: true,
  daily_goal: 100,
  preferred_mode: 'standard',
  session_size: 10,
})

export async function loadSettings() {
  try {
    const s = await apiGet('/api/auth/settings')
    userSettings.set(s)
  } catch(e) {}
}

export async function saveSetting(key, value) {
  try {
    const s = await apiPatch('/api/auth/settings', { [key]: value })
    userSettings.set(s)
  } catch(e) {}
}

// -- Toast --------------------------------------------------------------------

export const toastStore = writable(null)
export function showToast(message, type = 'info', duration = 3500) {
  toastStore.set({ message, type, id: Date.now() })
  setTimeout(() => toastStore.set(null), duration)
}

// -- Daten laden --------------------------------------------------------------

export async function loadGlobal() {
  try {
    const [pkgs, cats, stats, ai, health] = await Promise.all([
      apiGet('/api/packages'),
      apiGet('/api/categories'),
      apiGet('/api/stats'),
      apiGet('/api/ai/status'),
      apiGet('/api/health').catch(() => null),
    ])
    packages.set(pkgs)
    categories.set(cats)
    globalStats.set(stats)
    aiOnline.set(ai.online)
    backendOnline.set(!!health)
    if (health) backendVersion.set(health.version)
  } catch(e) {
    console.error('[LBT] loadGlobal:', e)
    backendOnline.set(false)
  }
}
