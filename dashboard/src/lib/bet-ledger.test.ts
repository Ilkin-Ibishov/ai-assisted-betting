import { describe, expect, it } from 'vitest'
import type { BetLedgerRow } from '@/lib/api'
import {
  betLedgerDefaultQuery,
  betLedgerStateLabel,
  betLedgerStateTone,
  buildBetLedgerDisplaySummary,
} from '@/lib/bet-ledger'

describe('bet ledger helpers', () => {
  it('uses Fresh plus next 7 days by default', () => {
    expect(betLedgerDefaultQuery).toEqual({ status: 'fresh', dateRange: 'next_7_days' })
  })

  it('builds display summary from backend summary', () => {
    const summary = buildBetLedgerDisplaySummary({
      summary: {
        fresh_count: 2,
        tracked_count: 1,
        needs_result_count: 1,
        resulted_count: 3,
        voided_count: 1,
        paper_profit_loss: 2.4,
        win_rate: 0.667,
      },
      rows: [row({ state: 'fresh' }), row({ state: 'needs_result' })],
    })

    expect(summary.cards.map((card) => card.label)).toEqual([
      'Fresh',
      'Tracked',
      'Needs result',
      'Resulted',
      'Paper P/L',
      'Win rate',
    ])
    expect(summary.cards[4].value).toBe('+2.4u')
    expect(summary.cards[5].value).toBe('66.7%')
  })

  it('labels row states for compact UI display', () => {
    expect(betLedgerStateLabel('needs_result')).toBe('Needs result')
    expect(betLedgerStateTone('needs_result')).toBe('warning')
    expect(betLedgerStateLabel('voided')).toBe('Voided')
    expect(betLedgerStateTone('voided')).toBe('muted')
  })
})

function row(overrides: Partial<BetLedgerRow>): BetLedgerRow {
  return {
    id: 'recommendation-1',
    row_type: 'candidate',
    paper_bet_id: null,
    recommendation_id: 1,
    prediction_id: null,
    provider: 'misli_public',
    run_id: null,
    source_match_id: 'match-1',
    league: 'Sample Premier',
    home_team: 'Home',
    away_team: 'Away',
    match_label: 'Home vs Away',
    kickoff_at: '2026-05-30T20:30:00+04:00',
    market: '1X2',
    selection: 'HOME',
    odds: 2.2,
    implied_probability: 0.45,
    model_probability: 0.61,
    edge: 0.16,
    expected_value: 0.35,
    confidence_score: 0.7,
    model_name: 'baseline_heuristic',
    model_version: 'v0',
    state: 'fresh',
    status: 'active',
    is_valid_open: true,
    risk_flags: ['no_current_risk_flags'],
    outcome: null,
    settled_at: null,
    paper_profit_loss: null,
    closing_odds: null,
    clv: null,
    created_at: '2026-05-29T08:00:00+00:00',
    updated_at: null,
    source_snapshot_at: '2026-05-29T08:00:00+00:00',
    rationale: 'Positive edge.',
    ...overrides,
  }
}
