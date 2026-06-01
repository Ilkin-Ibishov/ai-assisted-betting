import { describe, expect, it } from 'vitest'
import type {
  AIAnalysisRun,
  OddsMovementSummary,
  PaperCombination,
  PaperRecommendation,
} from '@/lib/api'
import {
  buildRecommendationDashboardSummary,
  riskBadgeTone,
} from '@/lib/recommendations'

describe('recommendation dashboard helpers', () => {
  it('joins recommendations to odds movement and sorts by expected value', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [
        recommendation({ id: 1, expected_value: 0.1, source_match_id: 'match-1' }),
        recommendation({ id: 2, expected_value: 0.22, source_match_id: 'match-2' }),
      ],
      combinations: [combination({ rank: 2 }), combination({ rank: 1 })],
      movements: [
        movement({
          source_match_id: 'match-2',
          home_team: 'North',
          away_team: 'South',
          movement_direction: 'up',
        }),
      ],
      review: review({ approval_state: 'caution' }),
      filters: { grade: 'all', market: 'all', confidence: 'all', approvalState: 'all' },
    })

    expect(summary.rows.map((row) => row.id)).toEqual([2, 1])
    expect(summary.rows[0].match_label).toBe('North vs South')
    expect(summary.rows[0].movement_direction).toBe('up')
    expect(summary.combinations.map((item) => item.rank)).toEqual([1, 2])
    expect(summary.approvalState).toBe('caution')
  })

  it('filters by grade, market, confidence, and approval state', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [
        recommendation({
          id: 1,
          confidence_score: 0.72,
          grade: 'recommended',
          market: '1X2',
        }),
        recommendation({
          id: 2,
          confidence_score: 0.55,
          grade: 'watch',
          market: 'TOTALS',
        }),
      ],
      combinations: [],
      movements: [],
      review: review({ approval_state: 'approve' }),
      filters: {
        approvalState: 'approve',
        confidence: 'high',
        grade: 'recommended',
        market: '1X2',
      },
    })

    expect(summary.rows.map((row) => row.id)).toEqual([1])
    expect(summary.gradeOptions).toEqual(['recommended', 'watch'])
    expect(summary.marketOptions).toEqual(['1X2', 'TOTALS'])
  })

  it('defaults actionable rows to active positive-EV candidates only', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [
        recommendation({ id: 1, expected_value: 0.12, grade: 'lean', status: 'active' }),
        recommendation({
          id: 2,
          expected_value: -0.04,
          grade: 'watch',
          status: 'active',
          risk_flags: ['negative_expected_value'],
        }),
        recommendation({ id: 3, expected_value: 0.18, grade: 'reject', status: 'rejected' }),
      ],
      combinations: [
        combination({ id: 1, leg_recommendation_ids: [1], rank: 2 }),
        combination({ id: 2, leg_recommendation_ids: [1, 2], rank: 1 }),
      ],
      movements: [],
      review: review({ approval_state: 'caution' }),
      filters: {
        approvalState: 'all',
        confidence: 'all',
        grade: 'actionable',
        market: 'all',
      },
    })

    expect(summary.rows.map((row) => row.id)).toEqual([1])
    expect(summary.combinations.map((item) => item.id)).toEqual([1])
    expect(summary.actionableCount).toBe(1)
    expect(summary.blockedCount).toBe(2)
    expect(summary.decisionState).toBe('candidate_ready')
  })

  it('does not mark watch or low-confidence rows as actionable candidates', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [
        recommendation({
          id: 1,
          confidence_score: 0.35,
          expected_value: 0.18,
          grade: 'watch',
          risk_flags: ['low_confidence'],
          status: 'active',
        }),
      ],
      combinations: [],
      movements: [],
      review: review({ approval_state: 'caution' }),
      filters: {
        approvalState: 'all',
        confidence: 'all',
        grade: 'actionable',
        market: 'all',
      },
    })

    expect(summary.rows).toEqual([])
    expect(summary.actionableCount).toBe(0)
    expect(summary.blockedCount).toBe(1)
    expect(summary.decisionState).toBe('blocked_by_risk')
  })

  it('does not mark candidates ready when the AI review rejects them', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [
        recommendation({
          id: 1,
          expected_value: 0.18,
          grade: 'recommended',
          risk_flags: ['no_current_risk_flags'],
          status: 'active',
        }),
      ],
      combinations: [],
      movements: [],
      review: review({ approval_state: 'reject' }),
      filters: {
        approvalState: 'all',
        confidence: 'all',
        grade: 'actionable',
        market: 'all',
      },
    })

    expect(summary.rows.map((row) => row.id)).toEqual([1])
    expect(summary.actionableCount).toBe(1)
    expect(summary.blockedCount).toBe(0)
    expect(summary.decisionState).toBe('blocked_by_risk')
  })

  it('marks the daily card blocked when all recommendations are unsafe', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [
        recommendation({
          id: 1,
          expected_value: -0.08,
          grade: 'watch',
          status: 'active',
          risk_flags: ['negative_expected_value'],
        }),
      ],
      combinations: [],
      movements: [],
      review: review({ approval_state: 'reject' }),
      filters: {
        approvalState: 'all',
        confidence: 'all',
        grade: 'actionable',
        market: 'all',
      },
    })

    expect(summary.rows).toEqual([])
    expect(summary.actionableCount).toBe(0)
    expect(summary.blockedCount).toBe(1)
    expect(summary.decisionState).toBe('blocked_by_risk')
  })

  it('returns empty rows when the AI approval filter does not match', () => {
    const summary = buildRecommendationDashboardSummary({
      recommendations: [recommendation({ id: 1 })],
      combinations: [combination({ rank: 1 })],
      movements: [],
      review: review({ approval_state: 'reject' }),
      filters: {
        approvalState: 'approve',
        confidence: 'all',
        grade: 'all',
        market: 'all',
      },
    })

    expect(summary.rows).toEqual([])
    expect(summary.combinations).toEqual([])
  })

  it('maps risk flags to stable badge tones', () => {
    expect(riskBadgeTone('no_current_risk_flags')).toBe('positive')
    expect(riskBadgeTone('provider_health_warning')).toBe('danger')
    expect(riskBadgeTone('combination_correlation_heuristic')).toBe('warning')
    expect(riskBadgeTone('manual_review')).toBe('neutral')
  })
})

function recommendation(overrides: Partial<PaperRecommendation>): PaperRecommendation {
  return {
    id: 1,
    match_id: 1,
    prediction_id: null,
    source_run_id: null,
    source_match_id: 'match-1',
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
    confidence_score: 0.7,
    current_odds: 2,
    expected_value: 0.2,
    risk_flags: ['no_current_risk_flags'],
    rationale: 'Seed recommendation',
    created_at: '2026-05-19T12:00:00+00:00',
    ...overrides,
  }
}

function combination(overrides: Partial<PaperCombination>): PaperCombination {
  return {
    id: 1,
    leg_recommendation_ids: [1, 2],
    leg_count: 2,
    model_name: 'baseline_heuristic',
    model_version: 'v0',
    grade: 'recommended',
    status: 'active',
    rank: 1,
    combined_odds: 3.8,
    estimated_probability: 0.36,
    combined_expected_value: 0.36,
    confidence_score: 0.69,
    risk_flags: ['no_current_risk_flags'],
    rationale: 'Seed combination',
    created_at: '2026-05-19T12:00:00+00:00',
    ...overrides,
  }
}

function movement(overrides: Partial<OddsMovementSummary>): OddsMovementSummary {
  return {
    match_id: 1,
    source: 'misli_public',
    source_match_id: 'match-1',
    league: 'Sample Premier',
    home_team: 'Home',
    away_team: 'Away',
    kickoff_time: '2026-05-19T20:30:00+04:00',
    bookmaker: 'Misli.az',
    market: '1X2',
    selection: 'HOME',
    opening_odds: 2,
    previous_odds: 1.9,
    current_odds: 2,
    latest_snapshot_time: '2026-05-19T12:00:00+00:00',
    market_latest_snapshot_time: '2026-05-19T12:00:00+00:00',
    movement_direction: 'stable',
    status: 'active',
    is_stale: false,
    snapshots_count: 2,
    ...overrides,
  }
}

function review(
  overrides: Partial<AIAnalysisRun['output']>,
): AIAnalysisRun {
  return {
    id: 1,
    analysis_type: 'recommendation_review',
    source_type: 'paper_recommendations',
    source_id: 'latest',
    input: {},
    output: {
      label: 'AI-assisted advisory analysis',
      short_summary: 'Reviewed recommendations.',
      root_cause: 'Deterministic review.',
      risk_flags: ['no_current_risk_flags'],
      recommended_next_actions: ['Keep paper-only.'],
      confidence: 'medium',
      source_record_ids: ['paper_recommendation:1'],
      approval_state: 'approve',
      concerns: [],
      confidence_explanation: 'Seed confidence.',
      rejected_assumptions: ['No real-money readiness is implied.'],
      next_checks: ['Backtest thresholds.'],
      ...overrides,
    },
    model_name: 'deterministic_ai_fallback',
    prompt_version: 'ai-recommendation-review-v1',
    status: 'completed',
    error_summary: null,
    created_at: '2026-05-19T12:00:00+00:00',
  }
}
