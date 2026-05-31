import { ChevronDown, Trophy } from 'lucide-react'
import { useMemo, useState } from 'react'
import type {
  BetLedgerDateRange,
  BetLedgerResponse,
  BetLedgerRow,
  BetLedgerRowState,
  BetLedgerStatus,
} from '@/lib/api'
import {
  betLedgerStateLabel,
  betLedgerStateTone,
  buildBetLedgerDisplaySummary,
} from '@/lib/bet-ledger'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const statusOptions: Array<{ label: string; value: BetLedgerStatus }> = [
  { label: 'Fresh', value: 'fresh' },
  { label: 'Needs result', value: 'needs_result' },
  { label: 'Resulted', value: 'resulted' },
  { label: 'Voided', value: 'voided' },
  { label: 'All', value: 'all' },
]

const dateOptions: Array<{ label: string; value: BetLedgerDateRange }> = [
  { label: 'Today', value: 'today' },
  { label: 'Tomorrow', value: 'tomorrow' },
  { label: 'Next 7 days', value: 'next_7_days' },
  { label: 'Last 30 days', value: 'last_30_days' },
  { label: 'All', value: 'all' },
]

export function BetLedgerPanel({
  dateRange,
  error,
  ledger,
  loading,
  onDateRangeChange,
  onStatusChange,
  status,
}: {
  dateRange: BetLedgerDateRange
  error: boolean
  ledger?: BetLedgerResponse
  loading: boolean
  onDateRangeChange: (dateRange: BetLedgerDateRange) => void
  onStatusChange: (status: BetLedgerStatus) => void
  status: BetLedgerStatus
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const summary = useMemo(
    () => (ledger ? buildBetLedgerDisplaySummary(ledger) : null),
    [ledger],
  )

  return (
    <Card data-testid="bet-ledger-panel">
      <CardHeader className="gap-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5" />
              Bet ledger
            </CardTitle>
            <CardDescription>
              Fresh opportunities, unresolved matches, results, probabilities, and paper P/L.
            </CardDescription>
          </div>
          <div className="flex flex-col gap-2">
            <SegmentedControl
              label="Status"
              options={statusOptions}
              value={status}
              onChange={onStatusChange}
            />
            <SegmentedControl
              label="Kickoff"
              options={dateOptions}
              value={dateRange}
              onChange={onDateRangeChange}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-950">
            Bet ledger API is not reachable.
          </div>
        ) : null}
        {loading ? <LedgerSkeleton /> : null}
        {!loading && summary ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
            {summary.cards.map((card) => (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3" key={card.label}>
                <div className="text-xs font-medium uppercase text-slate-500">{card.label}</div>
                <div className="mt-1 text-lg font-semibold text-slate-950">{card.value}</div>
              </div>
            ))}
          </div>
        ) : null}
        {!loading && ledger && ledger.rows.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
            No ledger rows match the active kickoff and status filters.
          </div>
        ) : null}
        {!loading && ledger && ledger.rows.length > 0 ? (
          <LedgerTable
            expandedId={expandedId}
            onToggleExpanded={(id) => setExpandedId(expandedId === id ? null : id)}
            rows={ledger.rows}
          />
        ) : null}
      </CardContent>
    </Card>
  )
}

function SegmentedControl<T extends string>({
  label,
  onChange,
  options,
  value,
}: {
  label: string
  onChange: (value: T) => void
  options: Array<{ label: string; value: T }>
  value: T
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium uppercase text-slate-500">{label}</span>
      <div className="flex flex-wrap gap-1 rounded-md border border-slate-200 bg-slate-50 p-1">
        {options.map((option) => (
          <Button
            aria-pressed={value === option.value}
            className="h-8 px-2 text-xs"
            key={option.value}
            onClick={() => onChange(option.value)}
            type="button"
            variant={value === option.value ? 'default' : 'outline'}
          >
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

function LedgerTable({
  expandedId,
  onToggleExpanded,
  rows,
}: {
  expandedId: string | null
  onToggleExpanded: (id: string) => void
  rows: BetLedgerRow[]
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            {[
              'Kickoff',
              'Type',
              'Match',
              'Pick',
              'Model %',
              'Implied %',
              'Edge',
              'Odds',
              'State',
              'Outcome',
              'Paper P/L',
              '',
            ].map((heading) => (
              <th className="border-b border-slate-200 px-3 py-2 font-medium" key={heading}>
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <LedgerRow
              expanded={expandedId === row.id}
              key={row.id}
              onToggle={() => onToggleExpanded(row.id)}
              row={row}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function LedgerRow({
  expanded,
  onToggle,
  row,
}: {
  expanded: boolean
  onToggle: () => void
  row: BetLedgerRow
}) {
  return (
    <>
      <tr className="border-b border-slate-100 last:border-0">
        <td className="px-3 py-3 text-slate-700">{formatDate(row.kickoff_at)}</td>
        <td className="px-3 py-3">
          <Badge className="border border-slate-200 bg-white text-slate-700" variant="secondary">
            {rowTypeLabel(row.row_type)}
          </Badge>
        </td>
        <td className="max-w-72 px-3 py-3">
          <div className="truncate font-semibold text-slate-950" title={row.match_label}>
            {row.match_label}
          </div>
          <div className="truncate text-xs text-slate-500" title={row.league}>
            {row.league}
          </div>
        </td>
        <td className="px-3 py-3 text-slate-900">
          {row.selection} / {row.market}
        </td>
        <td className="px-3 py-3 text-slate-900">{formatPercent(row.model_probability)}</td>
        <td className="px-3 py-3 text-slate-900">{formatPercent(row.implied_probability)}</td>
        <td className="px-3 py-3 text-slate-900">{formatSignedPercent(row.edge)}</td>
        <td className="px-3 py-3 text-slate-900">{formatDecimal(row.odds)}</td>
        <td className="px-3 py-3">
          <Badge className={stateClass(row.state)} variant="secondary">
            {betLedgerStateLabel(row.state)}
          </Badge>
        </td>
        <td className="px-3 py-3 text-slate-900">{row.outcome ?? '--'}</td>
        <td className="px-3 py-3 text-slate-900">{formatUnits(row.paper_profit_loss)}</td>
        <td className="px-3 py-3 text-right">
          <Button
            aria-expanded={expanded}
            className="h-8 w-8 p-0"
            onClick={onToggle}
            title="Show row details"
            type="button"
            variant="outline"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
        </td>
      </tr>
      {expanded ? (
        <tr className="border-b border-slate-100 bg-slate-50">
          <td className="px-3 py-3 text-sm text-slate-700" colSpan={12}>
            <div className="grid gap-2 md:grid-cols-3">
              <Detail label="Row type" value={rowTypeLabel(row.row_type)} />
              <Detail label="Raw status" value={row.status} />
              <Detail label="Paper bet ID" value={formatId(row.paper_bet_id)} />
              <Detail label="Recommendation ID" value={formatId(row.recommendation_id)} />
              <Detail label="Source match ID" value={row.source_match_id} />
              <Detail label="Settled" value={row.settled_at ? formatDate(row.settled_at) : '--'} />
              <Detail label="Closing odds" value={formatDecimal(row.closing_odds)} />
              <Detail label="CLV" value={formatSignedDecimal(row.clv)} />
              <Detail label="Rationale" value={row.rationale ?? '--'} />
              <Detail label="Risk flags" value={row.risk_flags.join(', ') || '--'} />
              <Detail
                label="Snapshot"
                value={row.source_snapshot_at ? formatDate(row.source_snapshot_at) : '--'}
              />
              <Detail
                label="Model"
                value={`${row.model_name ?? '--'} / ${row.model_version ?? '--'}`}
              />
              <Detail label="Created" value={formatDate(row.created_at)} />
            </div>
          </td>
        </tr>
      ) : null}
    </>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  )
}

function LedgerSkeleton() {
  return (
    <div className="grid gap-3">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton className="h-16" key={index} />
        ))}
      </div>
      <Skeleton className="h-56" />
    </div>
  )
}

function stateClass(state: BetLedgerRowState) {
  const tone = betLedgerStateTone(state)
  if (tone === 'success') return 'border border-emerald-200 bg-emerald-50 text-emerald-900'
  if (tone === 'warning') return 'border border-amber-200 bg-amber-50 text-amber-900'
  if (tone === 'muted') return 'border border-slate-200 bg-slate-100 text-slate-600'
  return 'border border-blue-200 bg-blue-50 text-blue-900'
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatPercent(value: number | null) {
  return value === null ? '--' : `${(value * 100).toFixed(1)}%`
}

function formatSignedPercent(value: number | null) {
  return value === null ? '--' : `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}pp`
}

function formatDecimal(value: number | null) {
  return value === null ? '--' : value.toFixed(2)
}

function formatSignedDecimal(value: number | null) {
  return value === null ? '--' : `${value >= 0 ? '+' : ''}${value.toFixed(3)}`
}

function formatUnits(value: number | null) {
  return value === null ? '--' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}u`
}

function formatId(value: number | null) {
  return value === null ? '--' : String(value)
}

function rowTypeLabel(rowType: BetLedgerRow['row_type']) {
  if (rowType === 'candidate') return 'Candidate'
  if (rowType === 'tracked') return 'Paper bet'
  if (rowType === 'resulted') return 'Resulted'
  return 'Voided'
}
