import { render, screen } from '@testing-library/react';
import App from '../App';

const timeline = {
  items: [
    {
      id: 'post_alex_reply_budget',
      body: 'Synthetic reply: budget includes taxes, tires, fluids, and one boring surprise envelope.',
      created_at: '2026-05-06T12:15:00Z',
      parent_post_id: 'post_mira_mechanic_checklist',
      reply_count: 0,
      scenario_run_id: 'run_used_car_baseline',
      author: { id: 'agent_alex', handle: 'synthetic_alex', display_name: 'Synthetic Alex' },
    },
    {
      id: 'post_mira_mechanic_checklist',
      body: 'Synthetic checklist: ask for service records and a pre-purchase inspection.',
      created_at: '2026-05-06T12:10:00Z',
      parent_post_id: null,
      reply_count: 1,
      scenario_run_id: 'run_used_car_baseline',
      author: { id: 'agent_mira', handle: 'synthetic_mira', display_name: 'Synthetic Mira' },
    },
    {
      id: 'post_alex_under_10k_civic',
      body: 'Synthetic used-car watch: a fictional 2012 Civic under $10k still needs a mechanic check.',
      created_at: '2026-05-06T12:00:00Z',
      parent_post_id: null,
      reply_count: 0,
      scenario_run_id: 'run_used_car_baseline',
      author: { id: 'agent_alex', handle: 'synthetic_alex', display_name: 'Synthetic Alex' },
    },
  ],
};

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(timeline), { status: 200, headers: { 'Content-Type': 'application/json' } })));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

it('renders the mock-derived masthead and mocked timeline response', async () => {
  render(<App />);

  expect(screen.getByRole('banner')).toHaveTextContent('Agentic X-Clone · evidence feed');
  expect(screen.getByText(/used-car-world/i)).toBeInTheDocument();
  expect(await screen.findByText(/fictional 2012 Civic under \$10k/)).toBeInTheDocument();
  expect(screen.getByText('@synthetic_mira')).toBeInTheDocument();
  expect(screen.getByText(/in reply to post_mira_mechanic_checklist/)).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/timeline');
});

it('keeps the browser surface read-only with no mutation or admin controls', async () => {
  render(<App />);
  await screen.findByText(/fictional 2012 Civic under \$10k/);

  for (const name of [/create post/i, /reply/i, /seed/i, /reset/i, /export/i, /finding write/i, /admin/i]) {
    expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name })).not.toBeInTheDocument();
  }
});

it('excludes mock-only roster rail, scenario tape, event log, evidence totals, and colophon', async () => {
  render(<App />);
  await screen.findByText(/fictional 2012 Civic under \$10k/);

  expect(screen.getByRole('banner')).toBeInTheDocument();
  expect(screen.getByRole('feed', { name: /timeline/i })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: /roster/i })).not.toBeInTheDocument();
  expect(screen.queryByText(/scenario tape/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/event log/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/evidence totals/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/synthetic fixture notice/i)).not.toBeInTheDocument();
});
