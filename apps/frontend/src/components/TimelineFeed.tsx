import { useEffect, useState } from 'react';
import { fetchTimeline, type TimelinePost as TimelinePostPayload } from '../api/client';
import { TimelinePost } from './TimelinePost';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; items: TimelinePostPayload[] };

type TimelineDisplayNode = {
  post: TimelinePostPayload;
  children: TimelineDisplayNode[];
  isOrphanReply: boolean;
};

function buildTimelineDisplayTree(items: TimelinePostPayload[]): TimelineDisplayNode[] {
  const nodesById = new Map<string, TimelineDisplayNode>();

  for (const post of items) {
    nodesById.set(post.id, { post, children: [], isOrphanReply: false });
  }

  for (const post of items) {
    const parentId = post.parent_post_id;
    if (!parentId) {
      continue;
    }

    const parentNode = nodesById.get(parentId);
    const childNode = nodesById.get(post.id);
    if (parentNode && childNode) {
      parentNode.children.push(childNode);
    }
  }

  return items.flatMap((post) => {
    const node = nodesById.get(post.id);
    if (!node) {
      return [];
    }

    if (!post.parent_post_id) {
      return [node];
    }

    if (!nodesById.has(post.parent_post_id)) {
      node.isOrphanReply = true;
      return [node];
    }

    return [];
  });
}

function TimelineDisplayPost({ node }: { node: TimelineDisplayNode }) {
  const variant = node.isOrphanReply ? 'orphan-reply' : node.post.parent_post_id ? 'child-reply' : 'root';

  return (
    <TimelinePost post={node.post} variant={variant}>
      {node.children.length > 0 ? (
        <div className="reply-list" role="group" aria-label={`Replies to ${node.post.id}`}>
          {node.children.map((child) => (
            <TimelineDisplayPost key={child.post.id} node={child} />
          ))}
        </div>
      ) : null}
    </TimelinePost>
  );
}

export function TimelineFeed() {
  const [state, setState] = useState<LoadState>({ status: 'loading' });

  useEffect(() => {
    let active = true;
    fetchTimeline()
      .then((timeline) => {
        if (active) {
          setState({ status: 'ready', items: timeline.items });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          const message = error instanceof Error ? error.message : 'Timeline request failed';
          setState({ status: 'error', message });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="feed" role="feed" aria-label="Timeline">
      <div className="feed-head">
        <h2>Timeline</h2>
        <span className="order">deterministic · created_at DESC, id DESC</span>
      </div>

      {state.status === 'loading' ? <p className="state mono">Loading synthetic timeline…</p> : null}
      {state.status === 'error' ? (
        <p className="state error" role="alert">
          Timeline unavailable in this local frontend slice: {state.message}
        </p>
      ) : null}
      {state.status === 'ready' && state.items.length === 0 ? (
        <p className="state mono">No synthetic timeline posts returned.</p>
      ) : null}
      {state.status === 'ready'
        ? buildTimelineDisplayTree(state.items).map((node) => (
            <TimelineDisplayPost key={node.post.id} node={node} />
          ))
        : null}

      <div className="feed-foot">end of replay window · backend timeline response · read-only</div>
    </section>
  );
}
