/**
 * api.js -- HTTP Hilfsfunktionen mit Token-Authentifizierung
 * Erkennt automatisch: Mac (localhost) oder Pi (hostname:8030)
 */
function getBase() {
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
  if (host === 'localhost' || host === '127.0.0.1') return 'http://localhost:8030'
  return `http://${host}:8030`
}
export const BASE = getBase()

function getToken() {
  return typeof localStorage !== 'undefined' ? localStorage.getItem('lbt-token') : null
}

async function req(method, path, body, isForm = false) {
  const opts = { method, headers: {} }
  const token = getToken()
  if (token) {
    opts.headers['Authorization'] = `Bearer ${token}`
  }
  if (body && !isForm) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  } else if (body && isForm) {
    opts.body = body
  }
  const res = await fetch(`${BASE}${path}`, opts)
  if (res.status === 401) {
    // Token ungueltig oder abgelaufen -> ausloggen
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('lbt-token')
      localStorage.removeItem('lbt-user')
    }
    window.dispatchEvent(new CustomEvent('auth-expired'))
    throw new Error('Sitzung abgelaufen')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const apiGet    = (path)        => req('GET',    path)
export const apiPost   = (path, body)  => req('POST',   path, body)
export const apiPut    = (path, body)  => req('PUT',    path, body)
export const apiDelete = (path)        => req('DELETE', path)
export const apiUpload = (path, form)  => req('POST',   path, form, true)
