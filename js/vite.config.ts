import { resolve } from 'path';
import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';

export default defineConfig({
  build: {
    lib: {
      name: 'BBQr',
      entry: resolve(__dirname, 'src/main.ts'),
      formats: ['es', 'iife'],
    },
  },
  esbuild: {
    // removes console.log from production builds (but useful in dev)
    pure: ['console.log'],
  },
  plugins: [dts()],
});
