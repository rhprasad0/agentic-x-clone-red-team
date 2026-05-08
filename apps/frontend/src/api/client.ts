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

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

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
  const response = await fetch(`${apiBaseUrl()}${path}`, { method: 'GET' });
  if (!response.ok) {
    throw new ApiRequestError(`Read request failed with ${response.status}`, response.status);
  }

  return response.json() as Promise<T>;
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
