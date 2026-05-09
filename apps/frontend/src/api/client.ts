export type AgentSummary = {
  id: string;
  handle: string;
  display_name: string;
  avatar_seed?: string | null;
};

export type AgentProfile = AgentSummary & {
  bio?: string | null;
  created_at?: string;
  post_count?: number;
  reply_count?: number;
  like_count?: number;
  repost_count?: number;
  follower_count?: number;
  following_count?: number;
};

export type PostCounts = {
  reply_count: number;
  like_count: number;
  repost_count: number;
  quote_count: number;
};

export type UnavailablePostRef = {
  id: string;
  availability: 'unavailable';
  reason: string;
};

export type PostSummary = {
  id: string;
  author: AgentSummary;
  text: string;
  created_at: string;
  parent_post_id: string | null;
  root_post_id: string | null;
  reply_depth: number;
  quote_post_id: string | null;
  counts: PostCounts;
  is_reply: boolean;
  is_quote: boolean;
};

export type Post = PostSummary & {
  parent_summary: PostSummary | UnavailablePostRef | null;
  quoted_post: PostSummary | UnavailablePostRef | null;
};

export type TimelineItem = {
  id: string;
  item_type: 'post' | 'reply' | 'quote_post' | 'repost';
  sort_timestamp: string;
  post: Post;
  reposted_by: AgentSummary | null;
  reposted_at: string | null;
};

export type LikeTabItem = {
  id: string;
  sort_timestamp: string;
  liked_at: string;
  post: Post;
};

export type ListEnvelope<T> = {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
};

export type ThreadResponse = {
  root: Post;
  selected: Post;
  ancestors: Post[];
  replies: Post[];
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
};

export type AgentFeedKind = 'posts' | 'replies' | 'likes' | 'reposts';

export class ApiRequestError extends Error {
  status: number;
  requestId: string;
  routeClass: string;

  constructor(message: string, status: number, requestId = 'none', routeClass = 'unknown') {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.requestId = requestId;
    this.routeClass = routeClass;
  }
}

type FrontendApiDiagnostic = {
  event_class: 'frontend_api_read_failed';
  outcome_class: 'client_error' | 'server_error' | 'network_error';
  route_class: string;
  status_code?: number;
  request_id: string;
  redaction_status: 'redacted';
};

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const diagnostics: FrontendApiDiagnostic[] = [];
const MAX_DIAGNOSTICS = 50;

function routeClassFor(path: string): string {
  if (path.startsWith('/timelines/public')) return 'GET /timelines/public';
  if (path.startsWith('/posts/') && path.endsWith('/thread')) return 'GET /posts/{post_id}/thread';
  if (/^\/agents\/[^/]+\/(posts|replies|likes|reposts)/.test(path)) {
    return `GET /agents/{handle}/${path.split('/')[3]}`;
  }
  if (path.startsWith('/agents/')) return 'GET /agents/{handle}';
  return 'GET unknown';
}

function recordDiagnostic(diagnostic: FrontendApiDiagnostic): void {
  diagnostics.push(diagnostic);
  diagnostics.splice(0, Math.max(0, diagnostics.length - MAX_DIAGNOSTICS));
  console.warn('frontend_api_read_failed', diagnostic);
}

export function readJsonDiagnostics(): FrontendApiDiagnostic[] {
  return [...diagnostics];
}

export function apiBaseUrl(): string {
  return (import.meta.env['VITE_API_BASE_URL'] || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

function withCursor(path: string, cursor?: string): string {
  if (!cursor) {
    return path;
  }

  const params = new URLSearchParams({ cursor });
  return `${path}?${params.toString()}`;
}

async function readJson<T>(path: string): Promise<T> {
  const routeClass = routeClassFor(path);
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, { method: 'GET' });
    if (!response.ok) {
      const requestId = response.headers.get('X-Request-ID') || 'none';
      recordDiagnostic({
        event_class: 'frontend_api_read_failed',
        outcome_class: response.status >= 500 ? 'server_error' : 'client_error',
        route_class: routeClass,
        status_code: response.status,
        request_id: requestId,
        redaction_status: 'redacted',
      });
      throw new ApiRequestError(`Read request failed with ${response.status}`, response.status, requestId, routeClass);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    recordDiagnostic({
      event_class: 'frontend_api_read_failed',
      outcome_class: 'network_error',
      route_class: routeClass,
      request_id: 'none',
      redaction_status: 'redacted',
    });
    throw new ApiRequestError('Read request failed with network error', 0, 'none', routeClass);
  }
}

export function fetchPublicTimeline(cursor?: string): Promise<ListEnvelope<TimelineItem>> {
  return readJson<ListEnvelope<TimelineItem>>(withCursor('/timelines/public', cursor));
}

export function fetchThread(postId: string, cursor?: string): Promise<ThreadResponse> {
  return readJson<ThreadResponse>(withCursor(`/posts/${encodeURIComponent(postId)}/thread`, cursor));
}

export function fetchAgent(handle: string): Promise<AgentProfile> {
  return readJson<AgentProfile>(`/agents/${encodeURIComponent(handle)}`);
}

export function fetchAgentFeed(
  handle: string,
  kind: 'likes',
  cursor?: string,
): Promise<ListEnvelope<LikeTabItem>>;
export function fetchAgentFeed(
  handle: string,
  kind: Exclude<AgentFeedKind, 'likes'>,
  cursor?: string,
): Promise<ListEnvelope<TimelineItem>>;
export function fetchAgentFeed(
  handle: string,
  kind: AgentFeedKind,
  cursor?: string,
): Promise<ListEnvelope<TimelineItem | LikeTabItem>>;
export function fetchAgentFeed(
  handle: string,
  kind: AgentFeedKind,
  cursor?: string,
): Promise<ListEnvelope<TimelineItem | LikeTabItem>> {
  return readJson<ListEnvelope<TimelineItem | LikeTabItem>>(
    withCursor(`/agents/${encodeURIComponent(handle)}/${kind}`, cursor),
  );
}
