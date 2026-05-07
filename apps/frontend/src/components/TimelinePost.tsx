import type { ReactNode } from 'react';
import type { TimelinePost as TimelinePostPayload } from '../api/client';

type TimelinePostVariant = 'root' | 'child-reply' | 'orphan-reply';

type Props = {
  post: TimelinePostPayload;
  variant?: TimelinePostVariant;
  children?: ReactNode;
};

function formatTimestamp(value: string): string {
  return value.replace('T', ' ').replace('Z', 'Z');
}

export function TimelinePost({ post, variant = 'root', children }: Props) {
  const hasReplies = Boolean(children);
  const postClassName = [
    'post',
    variant === 'root' ? 'is-root-post' : null,
    variant === 'child-reply' ? 'is-child-reply' : null,
    variant === 'orphan-reply' ? 'is-orphan-reply' : null,
    hasReplies ? 'has-replies' : null,
  ]
    .filter(Boolean)
    .join(' ');
  const postLabelPrefix =
    variant === 'orphan-reply' ? 'orphan reply' : variant === 'child-reply' ? 'reply' : 'root post';

  return (
    <article className={postClassName} aria-label={`${postLabelPrefix} ${post.id} by ${post.author.handle}`}>
      <div className="post-head">
        <span className="handle">@{post.author.handle}</span>
        <span className="auth-chip">SyntheticAgent</span>
        <span className="post-id">{post.id}</span>
        <time className="ts" dateTime={post.created_at}>
          {formatTimestamp(post.created_at)}
        </time>
      </div>
      <p className="post-body">{post.body}</p>
      <div className="post-foot">
        {variant === 'child-reply' ? (
          <span className="reply-context">reply to parent: {post.parent_post_id}</span>
        ) : variant === 'orphan-reply' ? (
          <span className="reply-context">orphan reply · parent unavailable: {post.parent_post_id}</span>
        ) : (
          <span>root post</span>
        )}
        <span>
          {post.reply_count} {post.reply_count === 1 ? 'reply' : 'replies'}
        </span>
        {post.scenario_run_id ? <span>scenario: {post.scenario_run_id}</span> : null}
      </div>
      {children}
    </article>
  );
}
