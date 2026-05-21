import { describe, expect, it } from 'vitest'
import type { LiveRun, LiveStatus } from '@/lib/api'
import { buildLiveProcessSummary } from '@/lib/live'

describe('buildLiveProcessSummary', () => {
  it('summarizes an empty live state', () => {
    expect(buildLiveProcessSummary()).toEqual({
      statusLabel: 'No live runs yet',
      statusTone: 'neutral',
      latestRunLabel: 'Waiting for first collection',
      providerLabel: 'Provider unavailable',
      countersLabel: '0 read / 0 created / 0 skipped',
      errorLabel: 'No recorded live errors',
      openBetsLabel: '0 open',
      settledBetsLabel: '0 settled',
    })
  })

  it('summarizes a successful latest run', () => {
    expect(
      buildLiveProcessSummary(
        status({
          latest_run: run({
            status: 'completed',
            provider: 'misli_public',
            league: 'football',
            items_read: 12,
            items_created: 8,
            items_skipped: 4,
          }),
          open_paper_bets: 3,
          settled_paper_bets: 9,
        }),
      ),
    ).toMatchObject({
      statusLabel: 'Latest run completed',
      statusTone: 'positive',
      providerLabel: 'misli_public / football',
      countersLabel: '12 read / 8 created / 4 skipped',
      errorLabel: 'No errors in latest run',
      openBetsLabel: '3 open',
      settledBetsLabel: '9 settled',
    })
  })

  it('summarizes a failed latest run with the error summary', () => {
    expect(
      buildLiveProcessSummary(
        status({
          latest_run: run({
            status: 'failed',
            errors_count: 2,
            error_summary: 'Missing kickoff datetime',
          }),
          errors_count: 4,
        }),
      ),
    ).toMatchObject({
      statusLabel: 'Latest run failed',
      statusTone: 'negative',
      errorLabel: '2 errors: Missing kickoff datetime',
    })
  })
})

function status(overrides: Partial<LiveStatus> = {}): LiveStatus {
  return {
    latest_run: null,
    latest_success: null,
    latest_failure: null,
    open_paper_bets: 0,
    settled_paper_bets: 0,
    runs_count: 0,
    errors_count: 0,
    ...overrides,
  }
}

function run(overrides: Partial<LiveRun> = {}): LiveRun {
  return {
    id: 1,
    run_id: 'run-001',
    run_type: 'collect_odds',
    provider: 'manual',
    league: null,
    season: null,
    status: 'completed',
    started_at: '2026-05-20T10:00:00+00:00',
    finished_at: '2026-05-20T10:01:00+00:00',
    items_read: 0,
    items_created: 0,
    items_updated: 0,
    items_skipped: 0,
    errors_count: 0,
    error_summary: null,
    model_name: null,
    created_at: '2026-05-20T10:00:00+00:00',
    ...overrides,
  }
}
