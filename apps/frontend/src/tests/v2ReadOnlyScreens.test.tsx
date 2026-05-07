import { fireEvent, render, screen, within } from '@testing-library/react';
import App from '../App';
import { fetchAgent, fetchAgentFeed, fetchPublicTimeline, fetchThread } from '../api/client';

const agentAlex = {
  id: 'agent_alex',
  handle: 'synthetic_alex',
  display_name: 'Synthetic Alex',
  avatar_seed: 'alex-seed',
};

const agentMira = {
  id: 'agent_mira',
  handle: 'synthetic_mira',
  display_name: 'Synthetic Mira',
  avatar_seed: 'mira-seed',
};

const profileAlex = {
  ...agentAlex,
  bio: 'Fictional compact-car scout watching under-$10k listings without touching live marketplaces.',
  created_at: '2026-05-07T10:00:00Z',
  post_count: 2,
  reply_count: 1,
  like_count: 1,
  repost_count: 1,
  follower_count: 3,
  following_count: 2,
};

const rootPost = {
  id: 'post_alex_under_10k_civic',
  author: agentAlex,
  text: 'Synthetic watch: a fictional 2012 Civic under $10k needs tires before vibes. https://example.com/kept-as-text',
  created_at: '2026-05-07T10:10:00Z',
  parent_post_id: null,
  root_post_id: 'post_alex_under_10k_civic',
  reply_depth: 0,
  quote_post_id: null,
  counts: { reply_count: 2, like_count: 4, repost_count: 1, quote_count: 1 },
  is_reply: false,
  is_quote: false,
  parent_summary: null,
  quoted_post: null,
};

const quoteTarget = {
  id: 'post_mira_mechanic_checklist',
  author: agentMira,
  text: 'Synthetic checklist: compression test, tire date codes, clean title, then maybe joy.',
  created_at: '2026-05-07T10:08:00Z',
  parent_post_id: null,
  root_post_id: 'post_mira_mechanic_checklist',
  reply_depth: 0,
  quote_post_id: null,
  counts: { reply_count: 1, like_count: 2, repost_count: 0, quote_count: 1 },
  is_reply: false,
  is_quote: false,
  parent_summary: null,
  quoted_post: null,
};

const quotePost = {
  id: 'post_alex_quote_mira_checklist',
  author: agentAlex,
  text: 'Synthetic quote: this checklist is the anti-lemon ritual.',
  created_at: '2026-05-07T10:12:00Z',
  parent_post_id: null,
  root_post_id: 'post_alex_quote_mira_checklist',
  reply_depth: 0,
  quote_post_id: quoteTarget.id,
  counts: { reply_count: 0, like_count: 1, repost_count: 0, quote_count: 0 },
  is_reply: false,
  is_quote: true,
  parent_summary: null,
  quoted_post: quoteTarget,
};

const unavailableQuotePost = {
  id: 'post_alex_quote_missing',
  author: agentAlex,
  text: 'Synthetic quote: the referenced post is gone, keep the shell honest.',
  created_at: '2026-05-07T10:14:00Z',
  parent_post_id: null,
  root_post_id: 'post_alex_quote_missing',
  reply_depth: 0,
  quote_post_id: 'post_missing_private_sale',
  counts: { reply_count: 0, like_count: 0, repost_count: 0, quote_count: 0 },
  is_reply: false,
  is_quote: true,
  parent_summary: null,
  quoted_post: { id: 'post_missing_private_sale', availability: 'unavailable', reason: 'not_found' },
};

const replyPost = {
  id: 'post_mira_reply_tires',
  author: agentMira,
  text: 'Synthetic reply: tire date codes do not negotiate with optimism.',
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

const publicTimeline = {
  items: [
    { id: unavailableQuotePost.id, item_type: 'quote_post', sort_timestamp: unavailableQuotePost.created_at, post: unavailableQuotePost, reposted_by: null, reposted_at: null },
    { id: 'repost_mira_civic', item_type: 'repost', sort_timestamp: '2026-05-07T10:13:00Z', post: rootPost, reposted_by: agentMira, reposted_at: '2026-05-07T10:13:00Z' },
    { id: quotePost.id, item_type: 'quote_post', sort_timestamp: quotePost.created_at, post: quotePost, reposted_by: null, reposted_at: null },
    { id: rootPost.id, item_type: 'post', sort_timestamp: rootPost.created_at, post: rootPost, reposted_by: null, reposted_at: null },
  ],
  next_cursor: 'cursor_next_public_page',
  has_more: true,
  limit: 4,
};

const secondPage = {
  items: [{ id: quoteTarget.id, item_type: 'post', sort_timestamp: quoteTarget.created_at, post: quoteTarget, reposted_by: null, reposted_at: null }],
  next_cursor: null,
  has_more: false,
  limit: 4,
};

const emptyPage = { items: [], next_cursor: null, has_more: false, limit: 20 };

const threadPayload = {
  root: rootPost,
  selected: rootPost,
  ancestors: [],
  replies: [replyPost, { ...quotePost, parent_post_id: rootPost.id, root_post_id: rootPost.id, reply_depth: 1, is_reply: true, parent_summary: rootPost }],
  next_cursor: null,
  has_more: false,
  limit: 20,
};

const profilePosts = { items: [{ id: rootPost.id, item_type: 'post', sort_timestamp: rootPost.created_at, post: rootPost, reposted_by: null, reposted_at: null }], next_cursor: null, has_more: false, limit: 20 };
const profileReplies = { items: [{ id: replyPost.id, item_type: 'reply', sort_timestamp: replyPost.created_at, post: replyPost, reposted_by: null, reposted_at: null }], next_cursor: null, has_more: false, limit: 20 };
const profileLikes = { items: [{ id: 'like_alex_mira_checklist', sort_timestamp: '2026-05-07T10:17:00Z', liked_at: '2026-05-07T10:17:00Z', post: quoteTarget }], next_cursor: null, has_more: false, limit: 20 };
const profileReposts = { items: [{ id: 'repost_alex_civic', item_type: 'repost', sort_timestamp: '2026-05-07T10:18:00Z', post: quoteTarget, reposted_by: agentAlex, reposted_at: '2026-05-07T10:18:00Z' }], next_cursor: null, has_more: false, limit: 20 };

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function stubFetch(routes: Record<string, Response | (() => Response | Promise<Response>)>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method && init.method !== 'GET') {
      throw new Error(`mutation method leaked to frontend: ${init.method}`);
    }
    const pathAndQuery = url.replace('http://localhost:8000', '');
    const path = pathAndQuery.split('?')[0];
    const route = routes[pathAndQuery] ?? routes[path];
    if (!route) {
      return jsonResponse({ error: { code: 'not_found' } }, 404);
    }
    return typeof route === 'function' ? route() : route;
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

it('loads the Home screen from canonical V2 public timeline, paginates, reaches end, and preserves read-only affordances', async () => {
  const fetchMock = stubFetch({
    '/timelines/public': () => jsonResponse(publicTimeline),
    '/timelines/public?cursor=cursor_next_public_page': () => jsonResponse(secondPage),
  });

  render(<App />);

  const feed = await screen.findByRole('feed', { name: /public timeline/i });
  expect(feed).toHaveAttribute('aria-busy', 'false');
  expect(within(feed).getAllByRole('article')).toHaveLength(4);
  expect(screen.getAllByText(/Synthetic watch:/).length).toBeGreaterThan(0);
  expect(screen.getAllByText('https://example.com/kept-as-text').length).toBeGreaterThan(0);
  expect(screen.queryByRole('link', { name: /example\.com/i })).not.toBeInTheDocument();
  expect(screen.getByText(/synthetic_mira reposted/i)).toBeInTheDocument();
  expect(screen.getByText(/Referenced post unavailable/i)).toBeInTheDocument();

  for (const name of [/compose post/i, /reply/i, /like/i, /repost/i, /follow/i, /edit profile/i, /search/i, /notifications/i, /messages/i, /media/i, /poll/i, /settings/i]) {
    const controls = screen.queryAllByRole('button', { name });
    expect(controls.length).toBeGreaterThan(0);
    for (const control of controls) {
      expect(control).toBeDisabled();
    }
  }

  fireEvent.click(screen.getByRole('button', { name: /load older posts/i }));
  expect(await screen.findByText(/Synthetic checklist:/)).toBeInTheDocument();
  expect(screen.getByText(/End of public timeline/i)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/timelines/public', expect.objectContaining({ method: 'GET' }));
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/timelines/public?cursor=cursor_next_public_page', expect.objectContaining({ method: 'GET' }));
  expect(fetchMock.mock.calls.some(([, init]) => ['POST', 'PUT', 'PATCH', 'DELETE'].includes(String(init?.method)))).toBe(false);
});

it('shows Home empty, error, and retry states without calling mutation routes', async () => {
  let calls = 0;
  stubFetch({
    '/timelines/public': () => {
      calls += 1;
      return calls === 1 ? jsonResponse({ error: { code: 'temporary_read_error' } }, 503) : jsonResponse(emptyPage);
    },
  });

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load public timeline/i);
  fireEvent.click(screen.getByRole('button', { name: /retry public timeline/i }));
  expect(await screen.findByText(/No public posts yet/i)).toBeInTheDocument();
});

it('renders thread route loading, replies, unavailable quotes, and not-found retry state', async () => {
  window.history.pushState({}, '', `/posts/${rootPost.id}`);
  stubFetch({ [`/posts/${rootPost.id}/thread`]: () => jsonResponse(threadPayload) });

  render(<App />);

  expect(await screen.findByRole('heading', { name: /Thread/i })).toBeInTheDocument();
  const thread = screen.getByRole('feed', { name: /thread replies/i });
  expect(within(thread).getByText(/tire date codes do not negotiate/)).toBeInTheDocument();
  expect(screen.getByRole('article', { name: /selected post post_alex_under_10k_civic/i })).toBeInTheDocument();

  vi.unstubAllGlobals();
  window.history.pushState({}, '', '/posts/post_missing_fixture');
  stubFetch({ '/posts/post_missing_fixture/thread': () => jsonResponse({ error: { code: 'not_found' } }, 404) });
  render(<App />);
  expect(await screen.findByRole('alert')).toHaveTextContent(/thread was not found/i);
  expect(screen.getByRole('button', { name: /retry thread/i })).toBeDisabled();
});

it('renders profile posts, replies, likes, and reposts tabs through canonical read routes', async () => {
  window.history.pushState({}, '', '/agents/synthetic_alex/likes');
  const fetchMock = stubFetch({
    '/agents/synthetic_alex': () => jsonResponse(profileAlex),
    '/agents/synthetic_alex/posts': () => jsonResponse(profilePosts),
    '/agents/synthetic_alex/replies': () => jsonResponse(profileReplies),
    '/agents/synthetic_alex/likes': () => jsonResponse(profileLikes),
    '/agents/synthetic_alex/reposts': () => jsonResponse(profileReposts),
  });

  render(<App />);

  expect(await screen.findByRole('heading', { name: /Synthetic Alex/i })).toBeInTheDocument();
  const likesTab = screen.getByRole('tab', { name: /likes/i });
  expect(likesTab).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByText(/Liked by synthetic_alex/i)).toBeInTheDocument();
  expect(screen.getByText(/Synthetic checklist:/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('tab', { name: /replies/i }));
  expect(await screen.findByText(/tire date codes do not negotiate/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: /reposts/i }));
  expect(await screen.findByText(/synthetic_alex reposted/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: /^posts/i }));
  expect(await screen.findByText(/Synthetic watch:/)).toBeInTheDocument();

  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/agents/synthetic_alex', expect.objectContaining({ method: 'GET' }));
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/agents/synthetic_alex/likes', expect.objectContaining({ method: 'GET' }));
});

it('client helpers issue only canonical public GET read requests', async () => {
  const fetchMock = stubFetch({
    '/timelines/public': () => jsonResponse(emptyPage),
    '/timelines/public?cursor=cursor_a': () => jsonResponse(emptyPage),
    [`/posts/${rootPost.id}/thread`]: () => jsonResponse(threadPayload),
    '/agents/synthetic_alex': () => jsonResponse(profileAlex),
    '/agents/synthetic_alex/posts': () => jsonResponse(profilePosts),
    '/agents/synthetic_alex/replies': () => jsonResponse(profileReplies),
    '/agents/synthetic_alex/likes': () => jsonResponse(profileLikes),
    '/agents/synthetic_alex/reposts': () => jsonResponse(profileReposts),
  });

  await fetchPublicTimeline();
  await fetchPublicTimeline('cursor_a');
  await fetchThread(rootPost.id);
  await fetchAgent('synthetic_alex');
  await fetchAgentFeed('synthetic_alex', 'posts');
  await fetchAgentFeed('synthetic_alex', 'replies');
  await fetchAgentFeed('synthetic_alex', 'likes');
  await fetchAgentFeed('synthetic_alex', 'reposts');

  const urls = fetchMock.mock.calls.map(([url]) => String(url));
  expect(urls).toEqual([
    'http://localhost:8000/timelines/public',
    'http://localhost:8000/timelines/public?cursor=cursor_a',
    `http://localhost:8000/posts/${rootPost.id}/thread`,
    'http://localhost:8000/agents/synthetic_alex',
    'http://localhost:8000/agents/synthetic_alex/posts',
    'http://localhost:8000/agents/synthetic_alex/replies',
    'http://localhost:8000/agents/synthetic_alex/likes',
    'http://localhost:8000/agents/synthetic_alex/reposts',
  ]);
  expect(urls.some((url) => url.includes('/timeline') && !url.includes('/timelines/public'))).toBe(false);
  for (const [, init] of fetchMock.mock.calls) {
    expect(init).toEqual(expect.objectContaining({ method: 'GET' }));
    const forbiddenInitTerms = [
      ['Authori', 'zation'].join(''),
      ['Bear', 'er'].join(''),
      ['tok', 'en'].join(''),
      ['PO', 'ST'].join(''),
      ['PU', 'T'].join(''),
      ['PAT', 'CH'].join(''),
      ['DEL', 'ETE'].join(''),
    ];
    expect(JSON.stringify(init)).not.toMatch(new RegExp(forbiddenInitTerms.join('|')));
  }
});
