import { describe, expect, it } from 'vitest'
import { buildApiUrl, fetchOddsMovement } from '@/lib/api'

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
