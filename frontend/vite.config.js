import { svelte } from '@sveltejs/vite-plugin-svelte'

export default {
  plugins: [svelte()],
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
