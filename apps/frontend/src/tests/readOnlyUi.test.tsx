import { fireEvent, render, screen, within } from '@testing-library/react';
import App from '../App';
import type { AgentProfile, AgentSummary, LikeTabItem, Post, TimelineItem } from '../api/client';

const alex: AgentSummary = {
  id: 'agent_alex',
  handle: 'synthetic_alex',
  display_name: 'Synthetic Alex',
  avatar_seed: 'alex-seed',
};

const mira: AgentSummary = {
  id: 'agent_mira',
  handle: 'synthetic_mira',
  display_name: 'Synthetic Mira',
  avatar_seed: 'mira-seed',
};

const profile: AgentProfile = {
  ...alex,
  bio: 'Fictional compact-car scout tracking synthetic under-$10k notes.',
  created_at: '2026-05-07T10:00:00Z',
  post_count: 1,
  reply_count: 1,
  like_count: 1,
  repost_count: 1,
  follower_count: 2,
  following_count: 1,
};

const counts = { reply_count: 1, like_count: 2, repost_count: 1, quote_count: 1 };

const rootPost: Post = {
  id: 'post_alex_under_10k_civic',
  author: alex,
  text: 'Synthetic used-car watch: a fictional 2012 Civic under $10k stays text-only. https://example.com/no-link',
  created_at: '2026-05-07T10:10:00Z',
  parent_post_id: null,
  root_post_id: 'post_alex_under_10k_civic',
  reply_depth: 0,
  quote_post_id: null,
  counts,
  is_reply: false,
  is_quote: false,
  parent_summary: null,
  quoted_post: null,
};

const replyPost: Post = {
  id: 'post_mira_reply_tires',
  author: mira,
  text: 'Synthetic reply: tire date codes first, optimism second.',
  created_at: '2026-05-07T10:16:00Z',
  parent_post_id: rootPost.id,
  root_post_id: rootPost.id,
  reply_depth: 1,
  quote_post_id: null,
  counts: { reply_count: 0, like_count: 1, repost_count: 0, quote_count: 0 },
  is_reply: true,
  is_quote: false,
  parent_summary: rootPost,
  quoted_post: null,
};

const unavailableQuotePost: Post = {
  id: 'post_quote_missing_listing',
  author: alex,
  text: 'Synthetic quote: missing referenced post should stay visible as unavailable.',
  created_at: '2026-05-07T10:14:00Z',
  parent_post_id: null,
  root_post_id: 'post_quote_missing_listing',
  reply_depth: 0,
  quote_post_id: 'post_missing_reference',
  counts: { reply_count: 0, like_count: 0, repost_count: 0, quote_count: 0 },
  is_reply: false,
  is_quote: true,
  parent_summary: null,
  quoted_post: { id: 'post_missing_reference', availability: 'unavailable', reason: 'not_found' },
};

const quoteTarget: Post = {
  id: 'post_mira_mechanic_checklist',
  author: mira,
  text: 'Synthetic checklist: pre-purchase inspection before any fictional Civic victory lap.',
  created_at: '2026-05-07T10:08:00Z',
  parent_post_id: null,
  root_post_id: 'post_mira_mechanic_checklist',
  reply_depth: 0,
  quote_post_id: null,
  counts: { reply_count: 0, like_count: 1, repost_count: 0, quote_count: 0 },
  is_reply: false,
  is_quote: false,
  parent_summary: null,
  quoted_post: null,
};

const timelineItems: TimelineItem[] = [
  {
    id: unavailableQuotePost.id,
    item_type: 'quote_post',
    sort_timestamp: unavailableQuotePost.created_at,
    post: unavailableQuotePost,
    reposted_by: null,
    reposted_at: null,
  },
  {
    id: rootPost.id,
    item_type: 'post',
    sort_timestamp: rootPost.created_at,
    post: rootPost,
    reposted_by: null,
    reposted_at: null,
  },
];

const repostItem: TimelineItem = {
  id: 'repost_alex_checklist',
  item_type: 'repost',
  sort_timestamp: '2026-05-07T10:18:00Z',
  post: quoteTarget,
  reposted_by: alex,
  reposted_at: '2026-05-07T10:18:00Z',
};

const likeItem: LikeTabItem = {
  id: 'like_alex_checklist',
  sort_timestamp: '2026-05-07T10:17:00Z',
  liked_at: '2026-05-07T10:17:00Z',
  post: quoteTarget,
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function stubFetch(routes: Record<string, () => Response | Promise<Response>>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace('http://localhost:8000', '');
    const route = routes[path];
    if (!route) {
      return jsonResponse({ error: { code: 'not_found' } }, 404);
    }
    if (init?.method && init.method !== 'GET') {
      return jsonResponse({ error: { code: 'unexpected_method' } }, 405);
    }
    return route();
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

beforeEach(() => {
  window.history.pushState({}, '', '/');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it('renders the V2 public timeline from the canonical read route with inert URL text', async () => {
  const fetchMock = stubFetch({
    '/timelines/public': () =>
      jsonResponse({ items: timelineItems, next_cursor: null, has_more: false, limit: 20 }),
  });

  render(<App />);

  expect(await screen.findByRole('heading', { name: 'Home' })).toBeInTheDocument();
  const feed = screen.getByRole('feed', { name: /public timeline/i });
  expect(within(feed).getAllByRole('article')).toHaveLength(2);
  expect(screen.getByText(/fictional 2012 Civic under \$10k/)).toBeInTheDocument();
  expect(screen.getByText('https://example.com/no-link')).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /example\.com/i })).not.toBeInTheDocument();
  expect(screen.getByText(/Referenced post unavailable/i)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/timelines/public', expect.objectContaining({ method: 'GET' }));
});

it('keeps composer, social, profile, and observer affordances disabled', async () => {
  stubFetch({
    '/timelines/public': () =>
      jsonResponse({ items: timelineItems, next_cursor: null, has_more: false, limit: 20 }),
  });

  render(<App />);
  await screen.findByText(/fictional 2012 Civic under \$10k/);

  for (const name of [/compose post/i, /reply/i, /like/i, /repost/i, /follow/i, /edit profile/i, /search/i, /notifications/i, /messages/i, /media/i, /poll/i, /settings/i]) {
    const controls = screen.queryAllByRole('button', { name });
    expect(controls.length).toBeGreaterThan(0);
    for (const control of controls) {
      expect(control).toBeDisabled();
    }
  }

  for (const name of [/seed/i, /reset/i, /export/i, /finding write/i, /admin/i]) {
    expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name })).not.toBeInTheDocument();
  }
});

it('renders a thread route through the public thread read model', async () => {
  window.history.pushState({}, '', `/${['posts', rootPost.id].join('/')}`);
  stubFetch({
    [`/posts/${rootPost.id}/thread`]: () =>
      jsonResponse({
        root: rootPost,
        selected: rootPost,
        ancestors: [],
        replies: [replyPost],
        next_cursor: null,
        has_more: false,
        limit: 20,
      }),
  });

  render(<App />);

  expect(await screen.findByRole('heading', { name: /thread/i })).toBeInTheDocument();
  expect(screen.getByRole('article', { name: /selected post post_alex_under_10k_civic/i })).toBeInTheDocument();
  expect(within(screen.getByRole('feed', { name: /thread replies/i })).getByText(/tire date codes first/)).toBeInTheDocument();
});

it('switches profile tabs with canonical profile read routes', async () => {
  window.history.pushState({}, '', '/agents/synthetic_alex');
  const fetchMock = stubFetch({
    '/agents/synthetic_alex': () => jsonResponse(profile),
    '/agents/synthetic_alex/posts': () =>
      jsonResponse({ items: [timelineItems[1]], next_cursor: null, has_more: false, limit: 20 }),
    '/agents/synthetic_alex/replies': () =>
      jsonResponse({
        items: [{ id: replyPost.id, item_type: 'reply', sort_timestamp: replyPost.created_at, post: replyPost, reposted_by: null, reposted_at: null }],
        next_cursor: null,
        has_more: false,
        limit: 20,
      }),
    '/agents/synthetic_alex/likes': () =>
      jsonResponse({ items: [likeItem], next_cursor: null, has_more: false, limit: 20 }),
    '/agents/synthetic_alex/reposts': () =>
      jsonResponse({ items: [repostItem], next_cursor: null, has_more: false, limit: 20 }),
  });

  render(<App />);

  expect(await screen.findByRole('heading', { name: /Synthetic Alex/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /^posts/i })).toHaveAttribute('aria-selected', 'true');

  fireEvent.click(screen.getByRole('tab', { name: /likes/i }));
  expect(await screen.findByText(/Liked by synthetic_alex/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: /reposts/i }));
  expect(await screen.findByText(/synthetic_alex reposted/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: /replies/i }));
  expect(await screen.findByText(/tire date codes first/)).toBeInTheDocument();

  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/agents/synthetic_alex', expect.objectContaining({ method: 'GET' }));
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/agents/synthetic_alex/reposts', expect.objectContaining({ method: 'GET' }));
});

it('shows an empty public timeline state without legacy V1 chrome', async () => {
  stubFetch({
    '/timelines/public': () => jsonResponse({ items: [], next_cursor: null, has_more: false, limit: 20 }),
  });

  render(<App />);

  expect(await screen.findByText(/No public posts yet/i)).toBeInTheDocument();
  expect(screen.queryByText(/scenario tape/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/event log/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/evidence totals/i)).not.toBeInTheDocument();
});
