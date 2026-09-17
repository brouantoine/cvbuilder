import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // VSCode consomme à lui seul presque tout le quota inotify du système
    // (fs.inotify.max_user_watches), ce qui empêchait Vite de démarrer
    // (ENOSPC). Le polling évite de dépendre de ce quota.
    watch: {
      usePolling: true,
    },
  },
})
