import { ApiRequestError, fetchPublicTimeline, readJsonDiagnostics } from '../api/client';

const forbiddenMarkers = ['Bearer ', 'runtime_token', 'raw response body', 'http://127.0.0.1:4000/v1'];

describe('frontend API diagnostics', () => {
  const originalFetch = globalThis.fetch;
  let warnings: unknown[][];
  let originalWarn: typeof console.warn;

  beforeEach(() => {
    warnings = [];
    originalWarn = console.warn;
    console.warn = (...args: unknown[]) => {
      warnings.push(args);
    };
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    console.warn = originalWarn;
  });

  it('propagates request IDs on failed reads without logging response bodies', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response('raw response body runtime_token', {
        status: 503,
        headers: { 'X-Request-ID': 'req_public_123' },
      }),
    );

    await expect(fetchPublicTimeline()).rejects.toMatchObject({
      name: 'ApiRequestError',
      status: 503,
      requestId: 'req_public_123',
      routeClass: 'GET /timelines/public',
    });

    expect(warnings).toHaveLength(1);
    const rendered = JSON.stringify(warnings);
    expect(rendered).toContain('frontend_api_read_failed');
    expect(rendered).toContain('req_public_123');
    for (const marker of forbiddenMarkers) {
      expect(rendered).not.toContain(marker);
    }
  });

  it('records safe diagnostics for network errors', async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new TypeError('failed to fetch raw response body from http://127.0.0.1:4000/v1');
    });

    await expect(fetchPublicTimeline()).rejects.toBeInstanceOf(ApiRequestError);

    const diagnostics = readJsonDiagnostics();
    expect(diagnostics.at(-1)).toMatchObject({
      event_class: 'frontend_api_read_failed',
      outcome_class: 'network_error',
      route_class: 'GET /timelines/public',
      request_id: 'none',
      redaction_status: 'redacted',
    });
    const rendered = JSON.stringify(diagnostics);
    for (const marker of forbiddenMarkers) {
      expect(rendered).not.toContain(marker);
    }
  });
});
