import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const frontendRoot = resolve(__dirname, '..', '..');

it('ships nginx with SPA fallback for documented frontend deep links', () => {
  const config = readFileSync(resolve(frontendRoot, 'nginx.conf'), 'utf8');

  expect(config).toContain('try_files $uri $uri/ /index.html');
  expect(config).toContain('listen 8080');
});

it('copies the SPA fallback nginx config into the runtime image', () => {
  const dockerfile = readFileSync(resolve(frontendRoot, 'Dockerfile'), 'utf8');

  expect(dockerfile).toMatch(/COPY\s+apps\/frontend\/nginx\.conf\s+\/etc\/nginx\/conf\.d\/default\.conf/);
});

it('keeps identity avatar monograms centered despite generic identity span display rules', () => {
  const styles = readFileSync(resolve(frontendRoot, 'src', 'styles.css'), 'utf8');

  expect(styles).toMatch(/\.identity\s+span\s*{[^}]*display:\s*block;/s);
  expect(styles).toMatch(/\.identity\s+\.avatar\s*{[^}]*display:\s*grid;/s);
});
