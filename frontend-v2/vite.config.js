import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5555'
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // MapLibre GL — ~700KB, only needed for HomePage
          maplibre: ['maplibre-gl'],
          // Export libs — ~400KB, only needed when exporting
          exportlibs: ['jspdf', 'jspdf-autotable', 'xlsx', 'html2pdf.js'],
          // Framer Motion — ~150KB
          motion: ['framer-motion'],
          // React core
          vendor: ['react', 'react-dom'],
        },
      },
    },
  },
})
