import { render, screen } from '@testing-library/react';
import App from '../App';

it('escapes synthetic post text instead of injecting HTML', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
    items: [{
      id: 'post_synthetic_html_probe',
      body: '<img src=x onerror="window.syntheticLeak=true"><script>window.syntheticLeak = true</script>',
      created_at: '2026-05-06T12:00:00Z',
      metadata_json: { operator_note: 'metadata_marker_do_not_render' },
      parent_post_id: null,
      reply_count: 0,
      scenario_run_id: 'run_used_car_baseline',
      author: { id: 'agent_alex', handle: 'synthetic_alex', display_name: 'Synthetic Alex' },
    }],
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })));

  render(<App />);

  expect(await screen.findByText(/window.syntheticLeak = true/)).toBeInTheDocument();
  expect(screen.queryByText(/metadata_marker_do_not_render/)).not.toBeInTheDocument();
  expect(document.querySelector('.post-body script')).toBeNull();
  expect(document.querySelector('.post-body img')).toBeNull();
  vi.unstubAllGlobals();
});
