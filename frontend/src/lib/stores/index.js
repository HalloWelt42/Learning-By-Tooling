import { writable } from 'svelte/store'
import { apiGet, apiPost, BASE } from '../utils/api.js'

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
      const CYCLE = ['dark','light','soft','contrast','warm']
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
export const aiOnline    = writable(false)
export const activeSession = writable(null)

// -- Toast --------------------------------------------------------------------

export const toastStore = writable(null)
export function showToast(message, type = 'info', duration = 3500) {
  toastStore.set({ message, type, id: Date.now() })
  setTimeout(() => toastStore.set(null), duration)
}

// -- Daten laden --------------------------------------------------------------

export async function loadGlobal() {
  try {
    const [pkgs, cats, stats, ai] = await Promise.all([
      apiGet('/api/packages'),
      apiGet('/api/categories'),
      apiGet('/api/stats'),
      apiGet('/api/ai/status'),
    ])
    packages.set(pkgs)
    categories.set(cats)
    globalStats.set(stats)
    aiOnline.set(ai.online)
  } catch(e) {
    console.error('[LBT] loadGlobal:', e)
  }
}
