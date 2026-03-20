import { svelte } from '@sveltejs/vite-plugin-svelte'
import fs from 'fs'
import path from 'path'

// Version aus zentraler VERSION-Datei lesen
function readVersion() {
  for (const p of [path.resolve(__dirname, '..', 'VERSION'), '/version']) {
    try { return fs.readFileSync(p, 'utf-8').trim() } catch {}
  }
  return '0.0.0'
}

export default {
  plugins: [svelte()],
  define: {
    __APP_VERSION__: JSON.stringify(readVersion()),
  },
  server: {
    port: 8031,
    host: true,
    strictPort: true,
    // Mac + Docker: inotify funktioniert nicht durch VM-Layer
    // poll: Vite fragt aktiv nach Änderungen statt auf Events zu warten
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
  build: { outDir: 'dist' }
}
