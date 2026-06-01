import { describe, expect, it } from 'vitest'
import type { LiveRun, LiveStatus } from '@/lib/api'
import { buildLiveProcessSummary, buildResultPipelineSummary } from '@/lib/live'

describe('buildLiveProcessSummary', () => {
  it('summarizes an empty live state', () => {
    expect(buildLiveProcessSummary()).toEqual({
      statusLabel: 'No live runs yet',
      statusTone: 'neutral',
      latestRunLabel: 'Waiting for first collection',
      providerLabel: 'Provider unavailable',
      countersLabel: '0 read / 0 created / 0 skipped',
      totalErrorsLabel: '0 historical',
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
      latestRunLabel: 'collect odds',
      providerLabel: 'misli_public / football',
      countersLabel: '12 read / 8 created / 4 skipped',
      totalErrorsLabel: '0 historical',
      errorLabel: 'No recorded live errors',
      openBetsLabel: '3 open',
      settledBetsLabel: '9 settled',
    })
  })

  it('separates historical error count from latest-run error health', () => {
    expect(
      buildLiveProcessSummary(
        status({
          latest_run: run({
            status: 'completed',
            errors_count: 0,
          }),
          errors_count: 24,
        }),
      ),
    ).toMatchObject({
      totalErrorsLabel: '24 historical',
      errorLabel: 'Latest run clean',
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
      totalErrorsLabel: '4 historical',
      errorLabel: '2 errors: Missing kickoff datetime',
    })
  })

  it('keeps scheduled worker labels short enough for dashboard tiles', () => {
    expect(
      buildLiveProcessSummary(
        status({
          latest_run: run({
            run_type: 'scheduled_paper_worker',
            provider: 'misli_public',
            model_name: 'baseline_heuristic',
            run_id:
              'scheduled_paper_worker:misli-public:baseline_heuristic:url:ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public:2026-05-28T14:02:25.604604+00:00',
          }),
        }),
      ),
    ).toMatchObject({
      latestRunLabel: 'scheduled paper worker',
      providerLabel: 'misli_public / baseline_heuristic',
    })
  })
})

describe('buildResultPipelineSummary', () => {
  it('summarizes an empty result queue', () => {
    expect(buildResultPipelineSummary()).toMatchObject({
      statusLabel: 'No result jobs',
      statusTone: 'neutral',
      dueLabel: '0 due',
      latestJobLabel: 'Waiting for tracked matches',
    })
  })

  it('surfaces due and failed Misli result jobs', () => {
    expect(
      buildResultPipelineSummary({
        summary: {
          total: 3,
          due: 2,
          completed: 1,
          postponed: 1,
          failed: 1,
          pending: 0,
        },
        jobs: [
          {
            id: 1,
            match_id: 10,
            source_match_id: 'misli:football:2816300',
            misli_event_id: '2816300',
            detail_url: null,
            status: 'failed',
            next_attempt_at: '2026-05-20T01:00:00+04:00',
            attempt_count: 3,
            last_error: 'parser drift',
            is_due: true,
            match_label: 'Forest City vs Eastport Athletic',
            kickoff_time: '2026-05-19T20:30:00+04:00',
          },
        ],
      }),
    ).toMatchObject({
      statusLabel: 'Result fetch needs review',
      statusTone: 'negative',
      dueLabel: '2 due',
      completedLabel: '1 completed',
      pendingLabel: '1 waiting',
      failureLabel: '1 failed',
      latestJobLabel: 'Forest City vs Eastport Athletic',
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
