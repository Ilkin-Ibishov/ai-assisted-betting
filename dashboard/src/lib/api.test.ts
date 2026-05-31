import { describe, expect, it, vi } from 'vitest'
import {
  buildApiUrl,
  fetchBetLedger,
  fetchOperationalGuardrails,
  fetchLatestRecommendationReview,
  fetchOddsMovement,
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
  it('reads paper recommendations from the API', async () => {
    const originalFetch = globalThis.fetch
    globalThis.fetch = (async (url: string) => {
      expect(url).toBe('/api/live/recommendations')
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

describe('fetchBetLedger', () => {
  it('fetches bet ledger with status and date filters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        summary: {
          fresh_count: 1,
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

    await fetchBetLedger({ status: 'fresh', dateRange: 'next_7_days' })

    expect(fetchMock).toHaveBeenCalledWith(
      buildApiUrl('/api/live/bet-ledger?status=fresh&date_range=next_7_days'),
    )
  })
})
