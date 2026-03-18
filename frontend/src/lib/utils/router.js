/**
 * router.js -- Hash-basiertes Routing
 * 
 * Routen:
 *   #/                          -> packages (Startseite)
 *   #/packages                  -> packages
 *   #/packages/{id}             -> package (Paket-Detail)
 *   #/packages/{id}/cards/{cat} -> package + Kategorie vorgewählt
 *   #/learn                     -> learn (alle Pakete)
 *   #/learn/{pkg_id}            -> learn (ein Paket)
 *   #/search                    -> search
 *   #/search?q={query}          -> search mit Vorausfüllung
 *   #/search?q={q}&pkg={id}     -> search gefiltert
 *   #/cards/{card_id}           -> Einzelkarte (Deeplink)
 *   #/progress                  -> progress
 *   #/guide                     -> guide
 */

import { writable, get } from 'svelte/store'

export const route = writable({ view: 'packages', params: {}, query: {} })

function parseHash() {
  const hash  = window.location.hash.replace(/^#\/?/, '') || ''
  const [pathPart, queryPart] = hash.split('?')
  const segments = pathPart.split('/').filter(Boolean)
  const query = {}
  if (queryPart) {
    for (const p of queryPart.split('&')) {
      const [k, v] = p.split('=')
      if (k) query[decodeURIComponent(k)] = decodeURIComponent(v || '')
    }
  }

  let view   = 'packages'
  let params = {}

  if (!segments.length || segments[0] === 'packages') {
    if (segments[1]) {
      view = 'package'
      params.pkg_id = parseInt(segments[1])
      if (segments[2] === 'cards' && segments[3]) {
        params.category = segments[3]
      }
    } else {
      view = 'packages'
    }
  } else if (segments[0] === 'learn') {
    view = 'learn'
    if (segments[1]) params.pkg_id = parseInt(segments[1])
  } else if (segments[0] === 'search') {
    view = 'search'
  } else if (segments[0] === 'cards') {
    view = 'card'
    params.card_id = parseInt(segments[1])
  } else if (segments[0] === 'progress') {
    view = 'progress'
  } else if (segments[0] === 'guide') {
    view = 'guide'
  }

  return { view, params, query }
}

export function navigate(path) {
  window.location.hash = path.startsWith('/') ? path : '/' + path
}

export function navToPackage(id) { navigate(`/packages/${id}`) }
export function navToLearn(pkgId) { navigate(pkgId ? `/learn/${pkgId}` : '/learn') }
export function navToSearch(q = '', pkgId = null) {
  let path = '/search'
  const qs = []
  if (q)     qs.push(`q=${encodeURIComponent(q)}`)
  if (pkgId) qs.push(`pkg=${pkgId}`)
  if (qs.length) path += '?' + qs.join('&')
  navigate(path)
}
export function navToCard(cardId) { navigate(`/cards/${cardId}`) }

export function initRouter() {
  const update = () => route.set(parseHash())
  window.addEventListener('hashchange', update)
  update()
  return () => window.removeEventListener('hashchange', update)
}
