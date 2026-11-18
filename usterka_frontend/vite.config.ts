import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { src: path.resolve(__dirname, 'src') } },
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks: { pdf: ['jspdf'], docx: ['docx'], pdfjs: ['pdfjs-dist'], msal: ['@azure/msal-browser'] },
      },
    },
  },
});
