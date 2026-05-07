import type { TimelinePost as TimelinePostPayload } from '../api/client';

type Props = {
  post: TimelinePostPayload;
};

function formatTimestamp(value: string): string {
  return value.replace('T', ' ').replace('Z', 'Z');
}

export function TimelinePost({ post }: Props) {
  const isReply = Boolean(post.parent_post_id);

  return (
    <article className={isReply ? 'post is-reply' : 'post'} aria-label={`${post.id} by ${post.author.handle}`}>
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
        {isReply ? (
          <span className="reply-arrow">↳ in reply to {post.parent_post_id}</span>
        ) : (
          <span>root post</span>
        )}
        <span>
          {post.reply_count} {post.reply_count === 1 ? 'reply' : 'replies'}
        </span>
        {post.scenario_run_id ? <span>scenario: {post.scenario_run_id}</span> : null}
      </div>
    </article>
  );
}
