import { render, screen } from '@testing-library/react';
import App from '../App';

const agent = {
  id: 'agent_alex',
  handle: 'synthetic_alex',
  display_name: 'Synthetic Alex',
  avatar_seed: 'alex-seed',
};

it('escapes synthetic post text instead of injecting markup', async () => {
  const probeText = '<img src=x onerror="window.syntheticLeak=true"><script>window.syntheticLeak = true</script>';
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: 'post_synthetic_markup_probe',
              item_type: 'post',
              sort_timestamp: '2026-05-07T10:10:00Z',
              reposted_by: null,
              reposted_at: null,
              post: {
                id: 'post_synthetic_markup_probe',
                author: agent,
                text: probeText,
                created_at: '2026-05-07T10:10:00Z',
                parent_post_id: null,
                root_post_id: 'post_synthetic_markup_probe',
                reply_depth: 0,
                quote_post_id: null,
                counts: { reply_count: 0, like_count: 0, repost_count: 0, quote_count: 0 },
                is_reply: false,
                is_quote: false,
                parent_summary: null,
                quoted_post: null,
                metadata_json: { operator_note: 'metadata_marker_do_not_render' },
              },
            },
          ],
          next_cursor: null,
          has_more: false,
          limit: 20,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    ),
  );

  render(<App />);

  expect(await screen.findByText(/window.syntheticLeak = true/)).toBeInTheDocument();
  expect(screen.queryByText(/metadata_marker_do_not_render/)).not.toBeInTheDocument();
  expect(document.querySelector('.post-text script')).toBeNull();
  expect(document.querySelector('.post-text img')).toBeNull();
  vi.unstubAllGlobals();
});
