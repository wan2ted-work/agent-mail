import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Dev server only. Set VITE_ALLOWED_HOSTS (comma-separated) to restrict;
    // defaults to allowing any host for convenience in local/self-host dev.
    allowedHosts: (process.env.VITE_ALLOWED_HOSTS || '').split(',').filter(Boolean).length
      ? process.env.VITE_ALLOWED_HOSTS.split(',').map((h) => h.trim())
      : true
  }
})
