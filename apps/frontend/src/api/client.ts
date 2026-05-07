export type TimelineAuthor = {
  id: string;
  handle: string;
  display_name: string;
};

export type TimelinePost = {
  id: string;
  body: string;
  created_at: string;
  reply_count: number;
  scenario_run_id: string | null;
  parent_post_id?: string | null;
  author: TimelineAuthor;
};

export type TimelineResponse = {
  items: TimelinePost[];
};

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export function apiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

export async function fetchTimeline(): Promise<TimelineResponse> {
  const response = await fetch(`${apiBaseUrl()}/timeline`);
  if (!response.ok) {
    throw new Error(`Timeline request failed with ${response.status}`);
  }
  return response.json() as Promise<TimelineResponse>;
}
