import { describe, expect, it } from 'vitest'
import {
  buildApiUrl,
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
