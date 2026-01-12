import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'

// https://vite.dev/config/
const base = process.env.VITE_BASE || process.env.BASE_PATH || "/flowtrials-mvp/";

export default defineConfig({
  base: '/flowtrials-mvp/',
  build: {
    outDir: '../docs',
    emptyOutDir: true
  },
  plugins: [svelte()],
  resolve: {
    alias: {
      $lib: path.resolve('./src/lib')
    }
  }
})
