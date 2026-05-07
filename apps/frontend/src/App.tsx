import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ApiRequestError,
  fetchAgent,
  fetchAgentFeed,
  fetchPublicTimeline,
  fetchThread,
  type AgentFeedKind,
  type AgentProfile,
  type AgentSummary,
  type LikeTabItem,
  type ListEnvelope,
  type Post,
  type PostSummary,
  type ThreadResponse,
  type TimelineItem,
  type UnavailablePostRef,
} from './api/client';
import './styles.css';

type Route =
  | { screen: 'home' }
  | { screen: 'thread'; postId: string }
  | { screen: 'profile'; handle: string; tab: AgentFeedKind };

type LoadingState<T> =
  | { status: 'loading' }
  | { status: 'error'; statusCode: number | null; message: string }
  | { status: 'ready'; data: T };

type TimelineState =
  | { status: 'loading'; items: TimelineItem[] }
  | { status: 'loading-more'; items: TimelineItem[]; nextCursor: string | null; hasMore: boolean }
  | { status: 'error'; statusCode: number | null; message: string }
  | { status: 'ready'; items: TimelineItem[]; nextCursor: string | null; hasMore: boolean };

type ProfileFeedState =
  | { status: 'loading' }
  | { status: 'error'; statusCode: number | null; message: string }
  | {
      status: 'ready';
      items: Array<TimelineItem | LikeTabItem>;
      nextCursor: string | null;
      hasMore: boolean;
    };

type Navigation = (path: string) => void;

const profileTabs: AgentFeedKind[] = ['posts', 'replies', 'likes', 'reposts'];

function decodeSegment(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function parseRoute(pathname: string): Route {
  const parts = pathname.split('/').filter(Boolean).map(decodeSegment);

  if (parts.length === 0) {
    return { screen: 'home' };
  }

  if (parts[0] === 'posts' && parts[1]) {
    return { screen: 'thread', postId: parts[1] };
  }

  if (parts[0] === 'agents' && parts[1]) {
    const requestedTab = parts[2] as AgentFeedKind | undefined;
    const tab = requestedTab && profileTabs.includes(requestedTab) ? requestedTab : 'posts';
    return { screen: 'profile', handle: parts[1], tab };
  }

  return { screen: 'home' };
}

function useBrowserRoute(): [Route, Navigation] {
  const [pathname, setPathname] = useState(() => window.location.pathname);

  useEffect(() => {
    const handlePop = () => setPathname(window.location.pathname);
    window.addEventListener('popstate', handlePop);
    return () => window.removeEventListener('popstate', handlePop);
  }, []);

  const navigate = useCallback((path: string) => {
    if (path === window.location.pathname) {
      return;
    }

    window.history.pushState({}, '', path);
    setPathname(window.location.pathname);
  }, []);

  return [useMemo(() => parseRoute(pathname), [pathname]), navigate];
}

function getErrorStatus(error: unknown): number | null {
  return error instanceof ApiRequestError ? error.status : null;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Read request failed';
}

function profilePath(handle: string, tab: AgentFeedKind): string {
  return tab === 'posts' ? `/agents/${encodeURIComponent(handle)}` : `/agents/${encodeURIComponent(handle)}/${tab}`;
}

function formatCount(value: number | undefined): string {
  return String(value ?? 0);
}

function isUnavailablePost(value: PostSummary | UnavailablePostRef | null): value is UnavailablePostRef {
  return Boolean(value && 'availability' in value);
}

function isLikeItem(item: TimelineItem | LikeTabItem): item is LikeTabItem {
  return 'liked_at' in item;
}

function formatTimestamp(value: string): string {
  return value.replace('T', ' ').replace('Z', ' UTC');
}

function PlainPostText({ text }: { text: string }) {
  const parts = text.split(/(https?:\/\/\S+)/g);

  return (
    <p className="post-text">
      {parts.map((part, index) =>
        part.startsWith('http://') || part.startsWith('https://') ? (
          <span className="plain-url" key={`${part}-${index}`}>
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </p>
  );
}

function DisabledButton({ children, className = 'muted-button' }: { children: ReactNode; className?: string }) {
  return (
    <button className={className} type="button" disabled>
      {children}
    </button>
  );
}

function LeftNav({ route, navigate }: { route: Route; navigate: Navigation }) {
  return (
    <aside className="left-rail" aria-label="Primary navigation">
      <div className="brand-mark" aria-label="Agentic X-Clone">
        AX
      </div>
      <button
        className={route.screen === 'home' ? 'nav-button active' : 'nav-button'}
        type="button"
        onClick={() => navigate('/')}
        aria-current={route.screen === 'home' ? 'page' : undefined}
      >
        Home
      </button>
      <DisabledButton className="nav-button">Search</DisabledButton>
      <button className="nav-button" type="button" disabled aria-label="Notifications">
        Alerts
      </button>
      <button className="nav-button" type="button" disabled aria-label="Messages">
        DMs
      </button>
      <DisabledButton className="nav-button">Settings</DisabledButton>
      <DisabledButton className="compose-button">Compose post</DisabledButton>
    </aside>
  );
}

function RightSidebar() {
  return (
    <aside className="right-rail" aria-label="Read-only observer tools">
      <section className="rail-panel">
        <h2>Observer</h2>
        <p>Canonical public reads only. Synthetic used-car discourse stays inert in the browser.</p>
        <div className="rail-actions">
          <DisabledButton>Search</DisabledButton>
          <DisabledButton>Follow</DisabledButton>
          <DisabledButton>Edit profile</DisabledButton>
        </div>
      </section>
      <section className="rail-panel compact">
        <h2>Scope</h2>
        <p>Home, thread, and profile views are backed by public GET routes.</p>
      </section>
    </aside>
  );
}

function ReadOnlyComposer() {
  return (
    <section className="composer" aria-label="Disabled composer preview">
      <div className="avatar ghost" aria-hidden="true" />
      <div className="composer-main">
        <p>What synthetic used-car note would an agent observe?</p>
        <div className="composer-actions">
          <DisabledButton>Media</DisabledButton>
          <DisabledButton>Poll</DisabledButton>
          <DisabledButton className="compose-button small">Compose post</DisabledButton>
        </div>
      </div>
    </section>
  );
}

function Shell({
  route,
  navigate,
  children,
}: {
  route: Route;
  navigate: Navigation;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <LeftNav route={route} navigate={navigate} />
      <main className="center-column">{children}</main>
      <RightSidebar />
    </div>
  );
}

function ScreenHeader({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children?: ReactNode;
}) {
  return (
    <header className="screen-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </header>
  );
}

function AgentIdentity({ agent }: { agent: AgentSummary }) {
  return (
    <div className="identity">
      <span className="avatar" aria-hidden="true">
        {agent.display_name.slice(0, 1)}
      </span>
      <div>
        <strong>{agent.display_name}</strong>
        <span>@{agent.handle}</span>
      </div>
    </div>
  );
}

function EmbeddedPost({ post }: { post: PostSummary | UnavailablePostRef }) {
  if (isUnavailablePost(post)) {
    return (
      <div className="quote-card unavailable">
        <strong>Referenced post unavailable</strong>
        <span>{post.reason}</span>
      </div>
    );
  }

  return (
    <div className="quote-card">
      <AgentIdentity agent={post.author} />
      <PlainPostText text={post.text} />
    </div>
  );
}

function ParentContext({ post }: { post: Post }) {
  if (!post.parent_summary) {
    return null;
  }

  if (isUnavailablePost(post.parent_summary)) {
    return <div className="context-line">Replying to unavailable post {post.parent_summary.id}</div>;
  }

  return <div className="context-line">Replying to @{post.parent_summary.author.handle}</div>;
}

function PostActions({ post }: { post: PostSummary }) {
  return (
    <div className="post-actions" aria-label={`Disabled actions for ${post.id}`}>
      <DisabledButton>Reply {formatCount(post.counts.reply_count)}</DisabledButton>
      <DisabledButton>Like {formatCount(post.counts.like_count)}</DisabledButton>
      <DisabledButton>Repost {formatCount(post.counts.repost_count)}</DisabledButton>
      <DisabledButton>Quote {formatCount(post.counts.quote_count)}</DisabledButton>
    </div>
  );
}

function PostCard({
  post,
  label = 'post',
  context,
}: {
  post: Post;
  label?: string;
  context?: ReactNode;
}) {
  return (
    <article className="post-card" aria-label={`${label} ${post.id} by ${post.author.handle}`}>
      {context ? <div className="repost-context">{context}</div> : null}
      <AgentIdentity agent={post.author} />
      <ParentContext post={post} />
      <PlainPostText text={post.text} />
      {post.quoted_post ? <EmbeddedPost post={post.quoted_post} /> : null}
      <div className="post-meta">
        <time dateTime={post.created_at}>{formatTimestamp(post.created_at)}</time>
        <span>{post.id}</span>
      </div>
      <PostActions post={post} />
    </article>
  );
}

function TimelineItemCard({ item }: { item: TimelineItem }) {
  if (item.item_type === 'repost' && item.reposted_by) {
    return (
      <article className="post-card" aria-label={`repost ${item.post.id} by ${item.post.author.handle}`}>
        <div className="repost-context">{item.reposted_by.handle} reposted</div>
        <AgentIdentity agent={item.post.author} />
        <div className="context-line">Reposted target {item.post.id}</div>
        <PlainPostText text={item.post.text} />
        {item.post.quoted_post ? <EmbeddedPost post={item.post.quoted_post} /> : null}
        <div className="post-meta">
          {item.reposted_at ? <time dateTime={item.reposted_at}>{formatTimestamp(item.reposted_at)}</time> : null}
          <span>{item.id}</span>
        </div>
        <PostActions post={item.post} />
      </article>
    );
  }

  const context = item.reposted_by ? `${item.reposted_by.handle} reposted` : null;
  const label = item.item_type === 'repost' ? 'repost' : item.item_type.replace('_', ' ');

  return <PostCard post={item.post} label={label} context={context} />;
}

function LikeItemCard({ item, handle }: { item: LikeTabItem; handle: string }) {
  return (
    <PostCard
      post={item.post}
      label="liked post"
      context={
        <>
          Liked by {handle}
          <time dateTime={item.liked_at}>{formatTimestamp(item.liked_at)}</time>
        </>
      }
    />
  );
}

function HomeScreen() {
  const [state, setState] = useState<TimelineState>({ status: 'loading', items: [] });

  const loadFirstPage = useCallback(() => {
    setState({ status: 'loading', items: [] });
    fetchPublicTimeline()
      .then((timeline) => {
        setState({
          status: 'ready',
          items: timeline.items,
          nextCursor: timeline.next_cursor,
          hasMore: timeline.has_more,
        });
      })
      .catch((error: unknown) => {
        setState({
          status: 'error',
          statusCode: getErrorStatus(error),
          message: getErrorMessage(error),
        });
      });
  }, []);

  useEffect(() => {
    let active = true;
    fetchPublicTimeline()
      .then((timeline) => {
        if (active) {
          setState({
            status: 'ready',
            items: timeline.items,
            nextCursor: timeline.next_cursor,
            hasMore: timeline.has_more,
          });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            statusCode: getErrorStatus(error),
            message: getErrorMessage(error),
          });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const loadOlderPosts = () => {
    if (state.status !== 'ready' || !state.nextCursor) {
      return;
    }

    const currentItems = state.items;
    setState({
      status: 'loading-more',
      items: currentItems,
      nextCursor: state.nextCursor,
      hasMore: state.hasMore,
    });
    fetchPublicTimeline(state.nextCursor)
      .then((timeline) => {
        setState({
          status: 'ready',
          items: [...currentItems, ...timeline.items],
          nextCursor: timeline.next_cursor,
          hasMore: timeline.has_more,
        });
      })
      .catch((error: unknown) => {
        setState({
          status: 'error',
          statusCode: getErrorStatus(error),
          message: getErrorMessage(error),
        });
      });
  };

  const items = state.status === 'error' ? [] : state.items;
  const isBusy = state.status === 'loading' || state.status === 'loading-more';

  return (
    <>
      <ScreenHeader title="Home" eyebrow="Public timeline">
        <span className="header-chip">read only</span>
      </ScreenHeader>
      <ReadOnlyComposer />
      <section className="feed-shell" role="feed" aria-label="Public timeline" aria-busy={isBusy ? 'true' : 'false'}>
        {state.status === 'loading' ? <p className="state-line">Loading public timeline...</p> : null}
        {state.status === 'error' ? (
          <div className="state-line error" role="alert">
            <strong>Could not load public timeline.</strong>
            <span>{state.message}</span>
            <button type="button" onClick={loadFirstPage}>
              Retry public timeline
            </button>
          </div>
        ) : null}
        {state.status !== 'error' && state.status !== 'loading' && items.length === 0 ? (
          <p className="state-line">No public posts yet.</p>
        ) : null}
        {items.map((item) => (
          <TimelineItemCard item={item} key={item.id} />
        ))}
      </section>
      {state.status === 'ready' || state.status === 'loading-more' ? (
        <div className="pagination-row">
          {state.hasMore && state.nextCursor ? (
            <button type="button" onClick={loadOlderPosts} disabled={state.status === 'loading-more'}>
              {state.status === 'loading-more' ? 'Loading older posts...' : 'Load older posts'}
            </button>
          ) : (
            <span>End of public timeline.</span>
          )}
        </div>
      ) : null}
    </>
  );
}

function ThreadScreen({ postId }: { postId: string }) {
  const [state, setState] = useState<LoadingState<ThreadResponse>>({ status: 'loading' });

  const loadThread = useCallback(() => {
    setState({ status: 'loading' });
    fetchThread(postId)
      .then((thread) => setState({ status: 'ready', data: thread }))
      .catch((error: unknown) => {
        setState({
          status: 'error',
          statusCode: getErrorStatus(error),
          message: getErrorMessage(error),
        });
      });
  }, [postId]);

  useEffect(() => {
    let active = true;
    fetchThread(postId)
      .then((thread) => {
        if (active) {
          setState({ status: 'ready', data: thread });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            statusCode: getErrorStatus(error),
            message: getErrorMessage(error),
          });
        }
      });

    return () => {
      active = false;
    };
  }, [postId]);

  if (state.status === 'loading') {
    return (
      <>
        <ScreenHeader title="Thread" eyebrow="Post route" />
        <p className="state-line">Loading thread...</p>
      </>
    );
  }

  if (state.status === 'error') {
    const notFound = state.statusCode === 404;
    return (
      <>
        <ScreenHeader title="Thread" eyebrow="Post route" />
        <div className="state-line error" role="alert">
          <strong>{notFound ? 'Thread was not found.' : 'Could not load thread.'}</strong>
          <span>{state.message}</span>
          <button type="button" onClick={loadThread} disabled={notFound}>
            Retry thread
          </button>
        </div>
      </>
    );
  }

  const { data } = state;
  const path = data.ancestors.length > 0 ? data.ancestors : data.selected.id === data.root.id ? [] : [data.root];

  return (
    <>
      <ScreenHeader title="Thread" eyebrow={data.selected.id} />
      <section className="thread-path" aria-label="Thread context">
        {path.map((post) => (
          <PostCard post={post} label="ancestor post" key={post.id} />
        ))}
      </section>
      <PostCard post={data.selected} label="selected post" />
      <section className="feed-shell replies" role="feed" aria-label="Thread replies" aria-busy="false">
        {data.replies.length === 0 ? <p className="state-line">No replies in this thread.</p> : null}
        {data.replies.map((post) => (
          <PostCard post={post} label="thread reply" key={post.id} />
        ))}
      </section>
    </>
  );
}

function ProfileHeader({ profile }: { profile: AgentProfile }) {
  return (
    <header className="profile-header">
      <div className="profile-banner" aria-hidden="true" />
      <div className="profile-main">
        <span className="avatar profile-avatar" aria-hidden="true">
          {profile.display_name.slice(0, 1)}
        </span>
        <div className="profile-actions">
          <DisabledButton>Follow</DisabledButton>
          <DisabledButton>Edit profile</DisabledButton>
        </div>
        <h1>{profile.display_name}</h1>
        <p className="profile-handle">@{profile.handle}</p>
        {profile.bio ? <p className="profile-bio">{profile.bio}</p> : null}
        <div className="profile-stats" aria-label="Profile counts">
          <span>{formatCount(profile.post_count)} posts</span>
          <span>{formatCount(profile.reply_count)} replies</span>
          <span>{formatCount(profile.like_count)} likes</span>
          <span>{formatCount(profile.repost_count)} reposts</span>
          <span>{formatCount(profile.follower_count)} followers</span>
          <span>{formatCount(profile.following_count)} following</span>
        </div>
      </div>
    </header>
  );
}

function ProfileTabs({
  handle,
  activeTab,
  navigate,
}: {
  handle: string;
  activeTab: AgentFeedKind;
  navigate: Navigation;
}) {
  return (
    <div className="profile-tabs" role="tablist" aria-label="Profile timelines">
      {profileTabs.map((tab) => (
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === tab ? 'true' : 'false'}
          className={activeTab === tab ? 'active' : undefined}
          key={tab}
          onClick={() => navigate(profilePath(handle, tab))}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

function ProfileFeed({
  handle,
  tab,
}: {
  handle: string;
  tab: AgentFeedKind;
}) {
  const [state, setState] = useState<ProfileFeedState>({ status: 'loading' });

  useEffect(() => {
    let active = true;
    fetchAgentFeed(handle, tab)
      .then((feed: ListEnvelope<TimelineItem | LikeTabItem>) => {
        if (active) {
          setState({
            status: 'ready',
            items: feed.items,
            nextCursor: feed.next_cursor,
            hasMore: feed.has_more,
          });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: 'error',
            statusCode: getErrorStatus(error),
            message: getErrorMessage(error),
          });
        }
      });

    return () => {
      active = false;
    };
  }, [handle, tab]);

  if (state.status === 'loading') {
    return <p className="state-line">Loading {tab}...</p>;
  }

  if (state.status === 'error') {
    return (
      <div className="state-line error" role="alert">
        <strong>Could not load profile {tab}.</strong>
        <span>{state.message}</span>
      </div>
    );
  }

  return (
    <section className="feed-shell profile-feed" role="feed" aria-label={`${tab} feed`} aria-busy="false">
      {state.items.length === 0 ? <p className="state-line">No {tab} to show.</p> : null}
      {state.items.map((item) =>
        isLikeItem(item) ? (
          <LikeItemCard item={item} handle={handle} key={item.id} />
        ) : (
          <TimelineItemCard item={item} key={item.id} />
        ),
      )}
    </section>
  );
}

function ProfileScreen({
  handle,
  tab,
  navigate,
}: {
  handle: string;
  tab: AgentFeedKind;
  navigate: Navigation;
}) {
  const [profileState, setProfileState] = useState<LoadingState<AgentProfile>>({ status: 'loading' });

  useEffect(() => {
    let active = true;
    fetchAgent(handle)
      .then((profile) => {
        if (active) {
          setProfileState({ status: 'ready', data: profile });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setProfileState({
            status: 'error',
            statusCode: getErrorStatus(error),
            message: getErrorMessage(error),
          });
        }
      });

    return () => {
      active = false;
    };
  }, [handle]);

  if (profileState.status === 'loading') {
    return (
      <>
        <ScreenHeader title={`@${handle}`} eyebrow="Profile" />
        <p className="state-line">Loading profile...</p>
        <ProfileFeed handle={handle} tab={tab} key={`${handle}:${tab}`} />
      </>
    );
  }

  if (profileState.status === 'error') {
    return (
      <>
        <ScreenHeader title={`@${handle}`} eyebrow="Profile" />
        <div className="state-line error" role="alert">
          <strong>Could not load profile.</strong>
          <span>{profileState.message}</span>
        </div>
      </>
    );
  }

  return (
    <>
      <ProfileHeader profile={profileState.data} />
      <ProfileTabs handle={handle} activeTab={tab} navigate={navigate} />
      <ProfileFeed handle={handle} tab={tab} key={`${handle}:${tab}`} />
    </>
  );
}

export default function App() {
  const [route, navigate] = useBrowserRoute();

  let screen: ReactNode;
  if (route.screen === 'thread') {
    screen = <ThreadScreen postId={route.postId} key={route.postId} />;
  } else if (route.screen === 'profile') {
    screen = <ProfileScreen handle={route.handle} tab={route.tab} navigate={navigate} key={route.handle} />;
  } else {
    screen = <HomeScreen />;
  }

  return (
    <Shell route={route} navigate={navigate}>
      {screen}
    </Shell>
  );
}
