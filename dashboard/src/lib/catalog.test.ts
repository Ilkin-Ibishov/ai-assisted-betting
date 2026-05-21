import { describe, expect, it } from 'vitest'
import { getVisibleCatalogReports } from '@/lib/catalog'
import type { ComparisonSummary } from '@/lib/api'

describe('getVisibleCatalogReports', () => {
  it('sorts reports by most recent modified time and applies the visible limit', () => {
    const reports = [
      summary({ name: 'older', modified_at: '2026-05-17T10:00:00Z' }),
      summary({ name: 'newest', modified_at: '2026-05-19T10:00:00Z' }),
      summary({ name: 'middle', modified_at: '2026-05-18T10:00:00Z' }),
    ]

    expect(getVisibleCatalogReports(reports, '', 2).map((report) => report.name)).toEqual([
      'newest',
      'middle',
    ])
  })

  it('matches report text across name, filename, league, season, models, and bookmakers', () => {
    const reports = [
      summary({
        name: 'e0_compare_workers2',
        filename: 'e0_compare_workers2_comparison.json',
        league: 'E0',
        season: '2024-2025',
        models: ['elo', 'poisson'],
        bookmakers: ['Avg', 'Pinnacle'],
      }),
      summary({
        name: 'sp1_compare',
        filename: 'sp1_compare_comparison.json',
        league: 'SP1',
        season: '2025-2026',
        models: ['market'],
        bookmakers: ['Bet365'],
      }),
    ]

    expect(getVisibleCatalogReports(reports, 'workers2').map((report) => report.name)).toEqual([
      'e0_compare_workers2',
    ])
    expect(getVisibleCatalogReports(reports, 'pinnacle').map((report) => report.name)).toEqual([
      'e0_compare_workers2',
    ])
    expect(getVisibleCatalogReports(reports, '2025-2026').map((report) => report.name)).toEqual([
      'sp1_compare',
    ])
  })

  it('ignores leading and trailing query whitespace', () => {
    const reports = [
      summary({ name: 'e0_compare', models: ['elo'] }),
      summary({ name: 'sp1_compare', models: ['market'] }),
    ]

    expect(getVisibleCatalogReports(reports, '  elo  ').map((report) => report.name)).toEqual([
      'e0_compare',
    ])
  })
})

function summary(overrides: Partial<ComparisonSummary>): ComparisonSummary {
  return {
    name: 'report',
    filename: 'report_comparison.json',
    league: null,
    season: null,
    models: [],
    bookmakers: [],
    runs: 1,
    modified_at: '2026-05-19T00:00:00Z',
    total_settled_bets: 10,
    best_roi: 0.12,
    best_brier_score: 0.2,
    best_log_loss: 0.5,
    sample_size_smallest: 10,
    sample_size_largest: 10,
    ...overrides,
  }
}
