import { describe, expect, it } from 'vitest'
import type { ComparisonRun } from '@/lib/api'
import {
  buildChartRows,
  buildCrossReportRows,
  buildCrossReportTrendRows,
  buildSelectedRunInsight,
  buildRunComparison,
  getMetricLeader,
  rankRuns,
  summarizeMetadata,
  toggleTrendMetric,
} from '@/lib/metrics'

const runs: ComparisonRun[] = [
  {
    model: 'baseline_heuristic',
    bookmaker: 'B365',
    total_bets: 10,
    settled_bets: 9,
    wins: 5,
    losses: 4,
    roi: 0.12,
    profit_loss_units: 1.2,
    average_odds: 2.1,
    average_edge: 0.03,
    brier_score: 0.25,
    log_loss: 0.69,
  },
  {
    model: 'elo',
    bookmaker: 'Avg',
    total_bets: 12,
    settled_bets: 12,
    wins: 6,
    losses: 6,
    roi: 0.05,
    profit_loss_units: 0.6,
    average_odds: 2.2,
    average_edge: 0.02,
    brier_score: 0.21,
    log_loss: 0.61,
  },
  {
    model: 'elo',
    bookmaker: 'B365',
    total_bets: 11,
    settled_bets: 10,
    wins: 4,
    losses: 6,
    roi: -0.02,
    profit_loss_units: -0.2,
    average_odds: 2.3,
    average_edge: 0.01,
    brier_score: 0.23,
    log_loss: 0.65,
  },
]

describe('dashboard metrics', () => {
  it('ranks runs by ROI descending and calibration ascending', () => {
    const ranked = rankRuns(runs)

    expect(ranked.map((run) => [run.model, run.bookmaker, run.roi_rank])).toEqual([
      ['baseline_heuristic', 'B365', 1],
      ['elo', 'Avg', 2],
      ['elo', 'B365', 3],
    ])
    expect(ranked.find((run) => run.bookmaker === 'Avg')?.brier_score_rank).toBe(1)
    expect(ranked.find((run) => run.bookmaker === 'Avg')?.log_loss_rank).toBe(1)
  })

  it('selects the correct leader for each metric direction', () => {
    expect(getMetricLeader(runs, 'roi', 'higher')?.bookmaker).toBe('B365')
    expect(getMetricLeader(runs, 'brier_score', 'lower')?.bookmaker).toBe('Avg')
    expect(getMetricLeader(runs, 'log_loss', 'lower')?.bookmaker).toBe('Avg')
  })

  it('builds chart rows with percentage ROI and compact labels', () => {
    expect(buildChartRows(runs)[0]).toEqual({
      label: 'base / B365',
      fullLabel: 'baseline_heuristic / B365',
      roi: 12,
      brier: 0.25,
      logLoss: 0.69,
      settledBets: 9,
    })
  })

  it('summarizes comparison metadata for display', () => {
    expect(
      summarizeMetadata({
        league: 'E0',
        season: '2526',
        models: ['baseline_heuristic', 'elo'],
        bookmakers: ['B365', 'Avg'],
        parallel_workers: 2,
      }),
    ).toEqual([
      ['League', 'E0'],
      ['Season', '2526'],
      ['Models', 'baseline_heuristic, elo'],
      ['Bookmakers', 'B365, Avg'],
      ['Workers', '2'],
    ])
  })

  it('compares a selected run against report averages', () => {
    const comparison = buildRunComparison(runs[1], runs)

    expect(comparison).toEqual({
      averageRoi: 0.05,
      roiDelta: 0,
      averageBrierScore: 0.23,
      brierScoreDelta: -0.02,
      averageLogLoss: 0.65,
      logLossDelta: -0.04,
      averageSettledBets: 10.3333,
      settledBetsDelta: 1.6667,
    })
  })

  it('builds cross-report rows for the selected model and bookmaker', () => {
    const rows = buildCrossReportRows(
      { model: 'elo', bookmaker: 'Avg' },
      [
        {
          name: 'older_report',
          modifiedAt: '2026-05-17T10:00:00Z',
          runs: [
            { ...runs[1], roi: 0.02, brier_score: 0.24, log_loss: 0.7, settled_bets: 8 },
          ],
        },
        {
          name: 'newer_report',
          modifiedAt: '2026-05-19T10:00:00Z',
          runs: [
            { ...runs[0] },
            { ...runs[1], roi: 0.08, brier_score: 0.2, log_loss: 0.6, settled_bets: 14 },
          ],
        },
        {
          name: 'missing_pair',
          modifiedAt: '2026-05-18T10:00:00Z',
          runs: [{ ...runs[0] }],
        },
      ],
    )

    expect(rows).toEqual([
      {
        reportName: 'newer_report',
        modifiedAt: '2026-05-19T10:00:00Z',
        roi: 0.08,
        brierScore: 0.2,
        logLoss: 0.6,
        settledBets: 14,
      },
      {
        reportName: 'older_report',
        modifiedAt: '2026-05-17T10:00:00Z',
        roi: 0.02,
        brierScore: 0.24,
        logLoss: 0.7,
        settledBets: 8,
      },
    ])
  })

  it('builds chronological cross-report trend rows with percentage ROI', () => {
    const rows = buildCrossReportTrendRows([
      {
        reportName: 'newer_report',
        modifiedAt: '2026-05-19T10:00:00Z',
        roi: 0.08,
        brierScore: 0.2,
        logLoss: 0.6,
        settledBets: 14,
      },
      {
        reportName: 'older_report',
        modifiedAt: '2026-05-17T10:00:00Z',
        roi: 0.02,
        brierScore: 0.24,
        logLoss: 0.7,
        settledBets: 8,
      },
    ])

    expect(rows).toEqual([
      {
        label: 'May 17',
        fullLabel: 'older_report',
        roi: 2,
        brierScore: 0.24,
        logLoss: 0.7,
      },
      {
        label: 'May 19',
        fullLabel: 'newer_report',
        roi: 8,
        brierScore: 0.2,
        logLoss: 0.6,
      },
    ])
  })

  it('toggles trend metrics while keeping at least one metric visible', () => {
    expect(toggleTrendMetric(['roi', 'brierScore'], 'brierScore')).toEqual(['roi'])
    expect(toggleTrendMetric(['roi'], 'brierScore')).toEqual(['roi', 'brierScore'])
    expect(toggleTrendMetric(['roi'], 'roi')).toEqual(['roi'])
  })

  it('summarizes low-sample cross-report history as noisy', () => {
    expect(
      buildSelectedRunInsight([
        {
          reportName: 'older_report',
          modifiedAt: '2026-05-17T10:00:00Z',
          roi: 0.04,
          brierScore: 0.22,
          logLoss: 0.64,
          settledBets: 80,
        },
      ]),
    ).toEqual({
      label: 'Noisy sample',
      tone: 'caution',
      summary: 'Cross-report history is still too small for a confident read.',
    })
  })

  it('summarizes positive ROI with improving calibration as strong', () => {
    expect(
      buildSelectedRunInsight([
        {
          reportName: 'newer_report',
          modifiedAt: '2026-05-19T10:00:00Z',
          roi: 0.08,
          brierScore: 0.2,
          logLoss: 0.6,
          settledBets: 340,
        },
        {
          reportName: 'older_report',
          modifiedAt: '2026-05-17T10:00:00Z',
          roi: 0.03,
          brierScore: 0.23,
          logLoss: 0.68,
          settledBets: 320,
        },
      ]),
    ).toEqual({
      label: 'Strong signal',
      tone: 'positive',
      summary: 'ROI is positive while latest calibration is at or better than history.',
    })
  })

  it('summarizes negative ROI or worsening calibration as weak', () => {
    expect(
      buildSelectedRunInsight([
        {
          reportName: 'newer_report',
          modifiedAt: '2026-05-19T10:00:00Z',
          roi: -0.04,
          brierScore: 0.26,
          logLoss: 0.72,
          settledBets: 360,
        },
        {
          reportName: 'older_report',
          modifiedAt: '2026-05-17T10:00:00Z',
          roi: 0.01,
          brierScore: 0.22,
          logLoss: 0.64,
          settledBets: 330,
        },
      ]),
    ).toEqual({
      label: 'Weak signal',
      tone: 'negative',
      summary: 'ROI or latest calibration is moving against this selected run.',
    })
  })
})
