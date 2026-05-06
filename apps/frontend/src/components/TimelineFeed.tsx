import { useEffect, useState } from 'react';
import { fetchTimeline, type TimelinePost as TimelinePostPayload } from '../api/client';
import { TimelinePost } from './TimelinePost';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; items: TimelinePostPayload[] };

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
        ? state.items.map((post) => <TimelinePost key={post.id} post={post} />)
        : null}

      <div className="feed-foot">end of replay window · backend timeline response · read-only</div>
    </section>
  );
}
