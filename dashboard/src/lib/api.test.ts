import { describe, expect, it, vi } from 'vitest'
import {
  buildApiUrl,
  fetchBetLedger,
  fetchRecommendationQuality,
  fetchOperationalGuardrails,
  fetchLatestRecommendationReview,
  fetchOddsMovement,
  fetchPaperBets,
  fetchPaperRecommendations,
} from '@/lib/api'

describe('buildApiUrl', () => {
  it('keeps relative API paths when no deployed API base is configured', () => {
    expect(buildApiUrl('/api/health', '')).toBe('/api/health')
  })

  it('prefixes API paths with the deployed API base URL', () => {
    expect(buildApiUrl('/api/health', 'https://paper-odds-api.up.railway.app/')).toBe(
      'https://paper-odds-api.up.railway.app/api/health',
    )
  })
})

describe('fetchOddsMovement', () => {
  it('reads live odds movement summaries from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/live/odds-movement')
      return new Response(
        JSON.stringify([
          {
            match_id: 1,
            source: 'misli_public',
            source_match_id: 'misli:football:1',
            league: 'Sample Premier',
            home_team: 'Home',
            away_team: 'Away',
            kickoff_time: '2026-05-19T20:30:00+04:00',
            bookmaker: 'Misli.az',
            market: '1X2',
            selection: 'HOME',
            opening_odds: 2.1,
            previous_odds: 2.1,
            current_odds: 2.3,
            latest_snapshot_time: '2026-05-19T12:00:00+00:00',
            market_latest_snapshot_time: '2026-05-19T12:00:00+00:00',
            movement_direction: 'up',
            status: 'active',
            is_stale: false,
            snapshots_count: 2,
          },
        ]),
        { status: 200 },
      )
    }) as typeof fetch

    try {
      const summaries = await fetchOddsMovement()

      expect(summaries[0].movement_direction).toBe('up')
      expect(summaries[0].current_odds).toBe(2.3)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

describe('recommendation API helpers', () => {
  it('requests the full recommendation window from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/live/recommendations?limit=500')
      return new Response(JSON.stringify([]), { status: 200 })
    }) as typeof fetch

    try {
      await expect(fetchPaperRecommendations()).resolves.toEqual([])
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('reads paper recommendations from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/live/recommendations?limit=500')
      return new Response(
        JSON.stringify([
          {
            id: 1,
            match_id: 1,
            source_match_id: 'misli:football:1',
            bookmaker: 'Misli.az',
            market: '1X2',
            selection: 'HOME',
            latest_snapshot_time: '2026-05-19T12:00:00+00:00',
            model_name: 'baseline_heuristic',
            model_version: 'v0',
            grade: 'recommended',
            status: 'active',
            model_probability: 0.62,
            implied_probability: 0.5,
            edge: 0.12,
            confidence_score: 0.72,
            current_odds: 2,
            expected_value: 0.24,
            risk_flags: ['no_current_risk_flags'],
            rationale: 'Seed recommendation',
            created_at: '2026-05-19T12:00:00+00:00',
          },
        ]),
        { status: 200 },
      )
    }) as typeof fetch

    try {
      const recommendations = await fetchPaperRecommendations()

      expect(recommendations[0].grade).toBe('recommended')
      expect(recommendations[0].risk_flags).toEqual(['no_current_risk_flags'])
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('reads paper bets from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/live/paper-bets?limit=500')
      return new Response(
        JSON.stringify([
          {
            id: 1,
            prediction_id: 2,
            match_id: 3,
            source_match_id: 'misli:football:1',
            league: 'Sample Premier',
            home_team: 'Home',
            away_team: 'Away',
            match_label: 'Home vs Away',
            kickoff_time: '2026-05-29T20:30:00+04:00',
            market: '1X2',
            selection: 'HOME',
            odds_taken: 2,
            stake_units: 1,
            expected_value: 0.1,
            status: 'open',
            profit_loss_units: null,
            closing_odds: null,
            clv: null,
            settled_at: null,
            created_at: '2026-05-28T12:00:00+00:00',
            model_name: 'baseline_heuristic',
            model_version: 'v0',
            model_probability: 0.55,
            edge: 0.05,
            confidence_score: 0.6,
            risk_flags: ['no_current_risk_flags'],
            is_valid_open: true,
          },
        ]),
        { status: 200 },
      )
    }) as typeof fetch

    try {
      const bets = await fetchPaperBets()

      expect(bets[0].status).toBe('open')
      expect(bets[0].match_label).toBe('Home vs Away')
      expect(bets[0].is_valid_open).toBe(true)
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  it('returns null when no recommendation review exists yet', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/ai/recommendation-review/latest')
      return new Response(JSON.stringify({ detail: 'missing' }), { status: 404 })
    }) as typeof fetch

    try {
      await expect(fetchLatestRecommendationReview()).resolves.toBeNull()
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

describe('fetchOperationalGuardrails', () => {
  it('reads operational guardrail status from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/operations/guardrails')
      return new Response(
        JSON.stringify({
          overall_status: 'warning',
          guardrails: [
            {
              name: 'worker_freshness',
              severity: 'warning',
              state: 'stale',
              observed_value: 120,
              threshold: 90,
              remediation: 'Check worker cadence.',
            },
          ],
          worker_status: {
            status: 'stale',
            healthy: false,
            freshness_minutes: 120,
            fresh_after_minutes: 90,
            latest_worker_run: null,
          },
        }),
        { status: 200 },
      )
    }) as typeof fetch

    try {
      const status = await fetchOperationalGuardrails()

      expect(status.overall_status).toBe('warning')
      expect(status.guardrails[0].name).toBe('worker_freshness')
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

describe('fetchRecommendationQuality', () => {
  it('reads recommendation quality status from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/live/recommendation-quality')
      return new Response(
        JSON.stringify({
          overall_state: 'actionable_present',
          summary: {
            total_recommendations: 3,
            actionable_count: 1,
            watchlist_count: 1,
            rejected_count: 1,
            created_since_latest_worker: 1,
            fresh_snapshot_count: 3,
            latest_snapshot_time: '2026-06-03T13:00:00Z',
          },
          ai_review: { approval_state: 'caution' },
        }),
        { status: 200 },
      )
    }) as typeof fetch

    try {
      const quality = await fetchRecommendationQuality()

      expect(quality.overall_state).toBe('actionable_present')
      expect(quality.summary.actionable_count).toBe(1)
      expect(quality.ai_review.approval_state).toBe('caution')
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

describe('fetchBetLedger', () => {
  it('fetches bet ledger with status and date filters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        summary: {
          fresh_count: 1,
          valid_open_count: 1,
          unsafe_open_count: 0,
          candidate_count: 1,
          tracked_count: 0,
          needs_result_count: 0,
          resulted_count: 0,
          voided_count: 0,
          paper_profit_loss: 0,
          win_rate: null,
        },
        rows: [],
      }),
    } as Response)

    try {
      await fetchBetLedger({ status: 'fresh', dateRange: 'next_7_days' })

      expect(fetchMock).toHaveBeenCalledWith(
        buildApiUrl('/api/live/bet-ledger?status=fresh&date_range=next_7_days'),
      )
    } finally {
      fetchMock.mockRestore()
    }
  })

  it('fetches bet ledger with custom kickoff dates', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        summary: {
          fresh_count: 0,
          valid_open_count: 0,
          unsafe_open_count: 0,
          candidate_count: 0,
          tracked_count: 0,
          needs_result_count: 0,
          resulted_count: 0,
          voided_count: 0,
          paper_profit_loss: 0,
          win_rate: null,
        },
        rows: [],
      }),
    } as Response)

    try {
      await fetchBetLedger({
        status: 'resulted',
        dateRange: 'custom',
        from: '2026-05-01',
        to: '2026-05-31',
      })

      expect(fetchMock).toHaveBeenCalledWith(
        buildApiUrl(
          '/api/live/bet-ledger?status=resulted&date_range=custom&from_date=2026-05-01&to_date=2026-05-31',
        ),
      )
    } finally {
      fetchMock.mockRestore()
    }
  })
})
