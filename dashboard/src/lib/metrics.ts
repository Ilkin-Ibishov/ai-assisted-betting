import type { ComparisonRun } from '@/lib/api'

export type RankedComparisonRun = ComparisonRun & {
  roi_rank: number
  brier_score_rank: number
  log_loss_rank: number
}

export type ChartRow = {
  label: string
  fullLabel: string
  roi: number
  brier: number
  logLoss: number
  settledBets: number
}

export type RunComparison = {
  averageRoi: number
  roiDelta: number
  averageBrierScore: number
  brierScoreDelta: number
  averageLogLoss: number
  logLossDelta: number
  averageSettledBets: number
  settledBetsDelta: number
}

export type CrossReportInput = {
  name: string
  modifiedAt: string
  runs: ComparisonRun[]
}

export type CrossReportRow = {
  reportName: string
  modifiedAt: string
  roi: number
  brierScore: number
  logLoss: number
  settledBets: number
}

export type CrossReportTrendRow = {
  label: string
  fullLabel: string
  roi: number
  brierScore: number
  logLoss: number
}

export type TrendMetricKey = 'roi' | 'brierScore' | 'logLoss'

export type SelectedRunInsight = {
  label: string
  tone: 'caution' | 'negative' | 'positive'
  summary: string
}

type NumericRunKey = 'roi' | 'brier_score' | 'log_loss' | 'settled_bets'

export function rankRuns(runs: ComparisonRun[]): RankedComparisonRun[] {
  const roiRanks = buildRankMap(runs, 'roi', 'higher')
  const brierRanks = buildRankMap(runs, 'brier_score', 'lower')
  const logLossRanks = buildRankMap(runs, 'log_loss', 'lower')

  return runs.map((run, index) => ({
    ...run,
    roi_rank: roiRanks.get(index) ?? index + 1,
    brier_score_rank: brierRanks.get(index) ?? index + 1,
    log_loss_rank: logLossRanks.get(index) ?? index + 1,
  }))
}

export function getMetricLeader(
  runs: ComparisonRun[],
  metric: NumericRunKey,
  direction: 'higher' | 'lower',
) {
  return runs.reduce<ComparisonRun | undefined>((leader, run) => {
    if (!leader) {
      return run
    }

    return isBetter(run[metric], leader[metric], direction) ? run : leader
  }, undefined)
}

export function buildChartRows(runs: ComparisonRun[]): ChartRow[] {
  return runs.map((run) => ({
    label: `${formatModelLabel(run.model)} / ${run.bookmaker}`,
    fullLabel: `${run.model} / ${run.bookmaker}`,
    roi: Number((run.roi * 100).toFixed(2)),
    brier: run.brier_score,
    logLoss: run.log_loss,
    settledBets: run.settled_bets,
  }))
}

export function summarizeMetadata(metadata?: Record<string, unknown>): Array<[string, string]> {
  if (!metadata) {
    return []
  }

  const rows: Array<[string, string]> = [
    ['League', formatMetadataValue(metadata.league)],
    ['Season', formatMetadataValue(metadata.season)],
    ['Models', formatMetadataValue(metadata.models)],
    ['Bookmakers', formatMetadataValue(metadata.bookmakers)],
    ['Workers', formatMetadataValue(metadata.parallel_workers)],
  ]

  return rows.filter(([, value]) => value !== 'Unknown')
}

export function buildRunComparison(run: ComparisonRun, runs: ComparisonRun[]): RunComparison {
  const averageRoi = average(runs, 'roi')
  const averageBrierScore = average(runs, 'brier_score')
  const averageLogLoss = average(runs, 'log_loss')
  const averageSettledBets = average(runs, 'settled_bets')

  return {
    averageRoi,
    roiDelta: rounded(run.roi - averageRoi),
    averageBrierScore,
    brierScoreDelta: rounded(run.brier_score - averageBrierScore),
    averageLogLoss,
    logLossDelta: rounded(run.log_loss - averageLogLoss),
    averageSettledBets,
    settledBetsDelta: rounded(run.settled_bets - averageSettledBets),
  }
}

export function buildCrossReportRows(
  selected: Pick<ComparisonRun, 'model' | 'bookmaker'>,
  reports: CrossReportInput[],
): CrossReportRow[] {
  return reports
    .flatMap((report) => {
      const run = report.runs.find(
        (item) => item.model === selected.model && item.bookmaker === selected.bookmaker,
      )

      return run
        ? [
            {
              reportName: report.name,
              modifiedAt: report.modifiedAt,
              roi: run.roi,
              brierScore: run.brier_score,
              logLoss: run.log_loss,
              settledBets: run.settled_bets,
            },
          ]
        : []
    })
    .toSorted((a, b) => Date.parse(b.modifiedAt) - Date.parse(a.modifiedAt))
}

export function buildCrossReportTrendRows(rows: CrossReportRow[]): CrossReportTrendRow[] {
  return rows
    .toSorted((a, b) => Date.parse(a.modifiedAt) - Date.parse(b.modifiedAt))
    .map((row) => ({
      label: formatTrendDate(row.modifiedAt),
      fullLabel: row.reportName,
      roi: Number((row.roi * 100).toFixed(2)),
      brierScore: row.brierScore,
      logLoss: row.logLoss,
    }))
}

export function toggleTrendMetric(
  visibleMetrics: TrendMetricKey[],
  metric: TrendMetricKey,
): TrendMetricKey[] {
  if (!visibleMetrics.includes(metric)) {
    return [...visibleMetrics, metric]
  }

  if (visibleMetrics.length === 1) {
    return visibleMetrics
  }

  return visibleMetrics.filter((item) => item !== metric)
}

export function buildSelectedRunInsight(rows: CrossReportRow[]): SelectedRunInsight {
  const latest = rows[0]
  const averageSettledBets = averageCrossReportMetric(rows, 'settledBets')

  if (!latest || averageSettledBets < 300) {
    return {
      label: 'Noisy sample',
      tone: 'caution',
      summary: 'Cross-report history is still too small for a confident read.',
    }
  }

  const averageRoi = averageCrossReportMetric(rows, 'roi')
  const averageBrierScore = averageCrossReportMetric(rows, 'brierScore')
  const averageLogLoss = averageCrossReportMetric(rows, 'logLoss')
  const positiveRoi = averageRoi > 0
  const calibrationStable =
    latest.brierScore <= averageBrierScore && latest.logLoss <= averageLogLoss

  if (positiveRoi && calibrationStable) {
    return {
      label: 'Strong signal',
      tone: 'positive',
      summary: 'ROI is positive while latest calibration is at or better than history.',
    }
  }

  return {
    label: 'Weak signal',
    tone: 'negative',
    summary: 'ROI or latest calibration is moving against this selected run.',
  }
}

export function formatModelLabel(model: string) {
  return model.replace('_heuristic', '').replace('baseline', 'base')
}

function averageCrossReportMetric(rows: CrossReportRow[], metric: keyof CrossReportRow) {
  if (rows.length === 0) {
    return 0
  }

  return (
    rows.reduce((total, row) => {
      const value = row[metric]
      return total + (typeof value === 'number' ? value : 0)
    }, 0) / rows.length
  )
}

function formatTrendDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Unknown'
  }

  return new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    month: 'short',
  }).format(date)
}

function average(runs: ComparisonRun[], metric: NumericRunKey) {
  if (runs.length === 0) {
    return 0
  }

  return rounded(runs.reduce((total, run) => total + run[metric], 0) / runs.length)
}

function rounded(value: number) {
  return Number(value.toFixed(4))
}

function buildRankMap(
  runs: ComparisonRun[],
  metric: NumericRunKey,
  direction: 'higher' | 'lower',
) {
  const rankedIndexes = runs
    .map((run, index) => ({ index, value: run[metric] }))
    .toSorted((a, b) =>
      direction === 'higher' ? b.value - a.value : a.value - b.value,
    )

  return new Map(rankedIndexes.map((item, index) => [item.index, index + 1]))
}

function isBetter(current: number, leader: number, direction: 'higher' | 'lower') {
  return direction === 'higher' ? current > leader : current < leader
}

function formatMetadataValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'Unknown'
  }

  if (typeof value === 'number') {
    return String(value)
  }

  if (typeof value === 'string' && value.length > 0) {
    return value
  }

  return 'Unknown'
}
