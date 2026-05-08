import type { AgentFeedKind, LikeTabItem, PostSummary, TimelineItem, UnavailablePostRef } from '../api/client';

export function profilePath(handle: string, tab: AgentFeedKind): string {
  return tab === 'posts'
    ? `/agents/${encodeURIComponent(handle)}`
    : `/agents/${encodeURIComponent(handle)}/${tab}`;
}

export function formatCount(value: number | undefined): string {
  return String(value ?? 0);
}

export function isUnavailablePost(
  value: PostSummary | UnavailablePostRef | null,
): value is UnavailablePostRef {
  return Boolean(value && 'availability' in value);
}

export function isLikeItem(item: TimelineItem | LikeTabItem): item is LikeTabItem {
  return 'liked_at' in item;
}

export function formatTimestamp(value: string): string {
  return value.replace('T', ' ').replace('Z', ' UTC');
}
