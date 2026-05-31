import type { BetLedgerQuery, BetLedgerResponse, BetLedgerRowState } from '@/lib/api'

export type BetLedgerDefaultQuery = Required<Pick<BetLedgerQuery, 'status' | 'dateRange'>>

export const betLedgerDefaultQuery: BetLedgerDefaultQuery = {
  status: 'fresh',
  dateRange: 'next_7_days',
}

export type BetLedgerTone = 'success' | 'warning' | 'info' | 'muted'

export function buildBetLedgerDisplaySummary(response: BetLedgerResponse) {
  const summary = response.summary

  return {
    cards: [
      { label: 'Fresh', value: String(summary.fresh_count), tone: 'success' as const },
      { label: 'Tracked', value: String(summary.tracked_count), tone: 'info' as const },
      { label: 'Needs result', value: String(summary.needs_result_count), tone: 'warning' as const },
      { label: 'Resulted', value: String(summary.resulted_count), tone: 'info' as const },
      {
        label: 'Paper P/L',
        value: formatUnits(summary.paper_profit_loss),
        tone: summary.paper_profit_loss >= 0 ? ('success' as const) : ('warning' as const),
      },
      { label: 'Win rate', value: formatPercent(summary.win_rate), tone: 'info' as const },
    ],
  }
}

export function betLedgerStateLabel(state: BetLedgerRowState): string {
  if (state === 'needs_result') return 'Needs result'
  if (state === 'resulted') return 'Resulted'
  if (state === 'voided') return 'Voided'
  return 'Fresh'
}

export function betLedgerStateTone(state: BetLedgerRowState): BetLedgerTone {
  if (state === 'fresh') return 'success'
  if (state === 'needs_result') return 'warning'
  if (state === 'voided') return 'muted'
  return 'info'
}

function formatUnits(value: number): string {
  const formatted = Math.abs(value).toFixed(1)
  return `${value >= 0 ? '+' : '-'}${formatted}u`
}

function formatPercent(value: number | null): string {
  if (value === null) return '--'
  return `${(value * 100).toFixed(1)}%`
}
