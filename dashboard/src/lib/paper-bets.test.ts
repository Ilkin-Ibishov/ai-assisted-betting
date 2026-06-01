import { describe, expect, it } from 'vitest'
import type { PaperBet } from '@/lib/api'
import { groupPaperBets, paperBetRiskSummary } from '@/lib/paper-bets'

describe('paper bet helpers', () => {
  it('separates valid open bets from unsafe legacy open rows', () => {
    const groups = groupPaperBets([
      paperBet({ id: 1, is_valid_open: true, status: 'open' }),
      paperBet({
        id: 2,
        is_valid_open: false,
        risk_flags: ['negative_expected_value', 'low_confidence'],
        status: 'open',
      }),
      paperBet({ id: 3, is_valid_open: false, status: 'won' }),
    ])

    expect(groups.validOpenBets.map((bet) => bet.id)).toEqual([1])
    expect(groups.unsafeOpenBets.map((bet) => bet.id)).toEqual([2])
    expect(groups.settledBets.map((bet) => bet.id)).toEqual([3])
  })

  it('formats risk flags for compact UI warnings', () => {
    expect(paperBetRiskSummary(['negative_expected_value', 'past_kickoff_open'])).toBe(
      'Negative Expected Value, Past Kickoff Open',
    )
    expect(paperBetRiskSummary(['no_current_risk_flags'])).toBe('No current risk flags')
  })
})

function paperBet(overrides: Partial<PaperBet>): PaperBet {
  return {
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
    ...overrides,
  }
}
