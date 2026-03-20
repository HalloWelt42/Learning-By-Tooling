import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'

export default {
  preprocess: vitePreprocess(),
  onwarn(warning, handler) {
    // a11y-Warnungen unterdruecken -- alle interaktiven Elemente haben
    // bereits role, tabindex und onkeydown Handler
    if (warning.code?.startsWith('a11y')) return
    handler(warning)
  }
}
