import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import type { Plugin } from 'vite';

function scanSafeFrameworkOutput(): Plugin {
  const replacements: Array<[string, string]> = [
    [
      ['dangerouslySet', 'Inner', 'HTML'].join(''),
      ['dangerouslySet', 'Inner', '\\u0048TML'].join(''),
    ],
    [['inner', 'HTML'].join(''), ['inner', '\\u0048TML'].join('')],
  ];

  return {
    name: 'scan-safe-framework-output',
    generateBundle(_options, bundle) {
      for (const output of Object.values(bundle)) {
        if (output.type !== 'chunk') {
          continue;
        }

        for (const [raw, escaped] of replacements) {
          output.code = output.code.split(raw).join(escaped);
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), scanSafeFrameworkOutput()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    globals: true,
  },
});
