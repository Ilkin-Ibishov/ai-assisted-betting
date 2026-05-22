import { lazy, Suspense, useMemo, useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertCircle,
  ArrowUpDown,
  BarChart3,
  Bot,
  CalendarClock,
  Database,
  Filter,
  RefreshCcw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Trophy,
} from 'lucide-react'
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import type { ColumnDef, SortingState } from '@tanstack/react-table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  fetchComparisonDetail,
  fetchComparisons,
  fetchLatestAIAnalysis,
  fetchLatestRecommendationReview,
  fetchLiveStatus,
  fetchOddsMovement,
  fetchOperationalGuardrails,
  fetchPaperCombinations,
  fetchPaperRecommendations,
} from '@/lib/api'
import type {
  AIAnalysisRun,
  ComparisonReport,
  ComparisonRun,
  ComparisonSummary,
  LiveStatus,
  OddsMovementSummary,
  OperationalGuardrailStatus,
  PaperCombination,
  PaperRecommendation,
} from '@/lib/api'
import { buildAIAdvisorySummary } from '@/lib/ai'
import { getVisibleCatalogReports } from '@/lib/catalog'
import { buildLiveProcessSummary } from '@/lib/live'
import {
  buildRecommendationDashboardSummary,
  riskBadgeTone,
} from '@/lib/recommendations'
import type { RecommendationFilters } from '@/lib/recommendations'
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
import type {
  ChartRow,
  CrossReportRow,
  CrossReportTrendRow,
  RankedComparisonRun,
  SelectedRunInsight,
  TrendMetricKey,
  RunComparison,
} from '@/lib/metrics'

const MetricChart = lazy(() => import('@/components/dashboard/metric-chart'))
const CrossReportTrendChart = lazy(
  () => import('@/components/dashboard/cross-report-trend-chart'),
)

const percent = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
  style: 'percent',
})

const decimal = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 3,
})

const emptyRuns: ComparisonRun[] = []

function App() {
  const [selectedName, setSelectedName] = useState<string>('')

  const comparisons = useQuery({
    queryKey: ['comparisons'],
    queryFn: fetchComparisons,
  })

  const currentName = selectedName || comparisons.data?.[0]?.name || ''

  const detail = useQuery({
    queryKey: ['comparison-detail', currentName],
    queryFn: () => fetchComparisonDetail(currentName),
    enabled: Boolean(currentName),
  })

  const liveStatus = useQuery({
    queryKey: ['live-status'],
    queryFn: fetchLiveStatus,
  })

  const guardrails = useQuery({
    queryKey: ['operational-guardrails'],
    queryFn: fetchOperationalGuardrails,
  })

  const aiAnalysis = useQuery({
    queryKey: ['ai-analysis-latest'],
    queryFn: fetchLatestAIAnalysis,
  })

  const recommendations = useQuery({
    queryKey: ['paper-recommendations'],
    queryFn: fetchPaperRecommendations,
  })

  const combinations = useQuery({
    queryKey: ['paper-combinations'],
    queryFn: fetchPaperCombinations,
  })

  const oddsMovement = useQuery({
    queryKey: ['odds-movement'],
    queryFn: fetchOddsMovement,
  })

  const recommendationReview = useQuery({
    queryKey: ['ai-recommendation-review-latest'],
    queryFn: fetchLatestRecommendationReview,
  })

  const selectedSummary = comparisons.data?.find((item) => item.name === currentName)
  const runs = detail.data?.runs ?? emptyRuns
  const rankedRuns = useMemo(() => rankRuns(runs), [runs])
  const chartData = useMemo(() => buildChartRows(runs), [runs])
  const metadataRows = useMemo(() => summarizeMetadata(detail.data?.metadata), [detail.data])
  const bestRoi = getMetricLeader(runs, 'roi', 'higher')
  const bestBrier = getMetricLeader(runs, 'brier_score', 'lower')
  const bestLogLoss = getMetricLeader(runs, 'log_loss', 'lower')

  return (
    <main className="min-h-screen bg-[#f7f8fa] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col gap-4 px-4 py-4 lg:flex-row lg:px-6">
        <aside className="flex w-full shrink-0 flex-col gap-4 rounded-md border border-slate-200 bg-white p-4 shadow-sm lg:w-72">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
              <BarChart3 className="h-4 w-4" />
              Paper Odds Lab
            </div>
            <h1 className="mt-3 text-2xl font-semibold tracking-normal text-slate-950">
              Analytical Dashboard
            </h1>
          </div>
          <div className="grid gap-2 text-sm">
            <NavItem icon={Database} label="Comparison reports" active />
            <NavItem icon={Activity} label="Process metrics" />
            <NavItem icon={ShieldCheck} label="Read-only mode" />
          </div>
          <div className="mt-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            <div className="font-medium text-slate-900">Local API</div>
            <div className="mt-1">FastAPI proxy: /api to 127.0.0.1:8000</div>
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col gap-4">
          <header className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge>Local reports</Badge>
                <Badge variant="secondary">Read only</Badge>
              </div>
              <h2 className="mt-3 text-2xl font-semibold tracking-normal">
                Comparison workspace
              </h2>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <select
                data-testid="report-select"
                value={currentName}
                onChange={(event) => setSelectedName(event.target.value)}
                className="h-10 min-w-64 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none ring-offset-white focus:ring-2 focus:ring-slate-400"
                aria-label="Comparison report"
              >
                {comparisons.data?.map((comparison) => (
                  <option key={comparison.name} value={comparison.name}>
                    {comparison.name}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void comparisons.refetch()
                  void detail.refetch()
                }}
                title="Refresh reports"
              >
                <RefreshCcw className="h-4 w-4" />
                Refresh
              </Button>
            </div>
          </header>

          {comparisons.isError ? (
            <ApiWarning />
          ) : (
            <DashboardContent
              comparisons={comparisons.data ?? []}
              comparisonLoading={comparisons.isLoading}
              detail={detail.data}
              detailLoading={detail.isLoading}
              selectedSummary={selectedSummary}
              bestRoi={bestRoi}
              bestBrier={bestBrier}
              bestLogLoss={bestLogLoss}
              chartData={chartData}
              metadataRows={metadataRows}
              onSelectReport={setSelectedName}
              liveError={liveStatus.isError}
              liveLoading={liveStatus.isLoading}
              liveStatus={liveStatus.data}
              guardrailError={guardrails.isError}
              guardrailLoading={guardrails.isLoading}
              guardrailStatus={guardrails.data}
              aiAnalysis={aiAnalysis.data}
              aiError={aiAnalysis.isError}
              aiLoading={aiAnalysis.isLoading}
              combinations={combinations.data ?? []}
              oddsMovement={oddsMovement.data ?? []}
              recommendationError={
                recommendations.isError ||
                combinations.isError ||
                oddsMovement.isError ||
                recommendationReview.isError
              }
              recommendationLoading={
                recommendations.isLoading ||
                combinations.isLoading ||
                oddsMovement.isLoading ||
                recommendationReview.isLoading
              }
              recommendationReview={recommendationReview.data}
              recommendations={recommendations.data ?? []}
              runs={rankedRuns}
            />
          )}
        </section>
      </div>
    </main>
  )
}

type DashboardContentProps = {
  comparisons: ComparisonSummary[]
  comparisonLoading: boolean
  detail?: ComparisonReport
  detailLoading: boolean
  selectedSummary?: ComparisonSummary
  bestRoi?: ComparisonRun
  bestBrier?: ComparisonRun
  bestLogLoss?: ComparisonRun
  chartData: ChartRow[]
  metadataRows: Array<[string, string]>
  onSelectReport: (name: string) => void
  liveError: boolean
  liveLoading: boolean
  liveStatus?: LiveStatus
  guardrailError: boolean
  guardrailLoading: boolean
  guardrailStatus?: OperationalGuardrailStatus
  aiAnalysis?: AIAnalysisRun | null
  aiError: boolean
  aiLoading: boolean
  combinations: PaperCombination[]
  oddsMovement: OddsMovementSummary[]
  recommendationError: boolean
  recommendationLoading: boolean
  recommendationReview?: AIAnalysisRun | null
  recommendations: PaperRecommendation[]
  runs: RankedComparisonRun[]
}

function DashboardContent({
  comparisons,
  comparisonLoading,
  detail,
  detailLoading,
  selectedSummary,
  bestRoi,
  bestBrier,
  bestLogLoss,
  chartData,
  metadataRows,
  onSelectReport,
  liveError,
  liveLoading,
  liveStatus,
  guardrailError,
  guardrailLoading,
  guardrailStatus,
  aiAnalysis,
  aiError,
  aiLoading,
  combinations,
  oddsMovement,
  recommendationError,
  recommendationLoading,
  recommendationReview,
  recommendations,
  runs,
}: DashboardContentProps) {
  const [selectedRunKey, setSelectedRunKey] = useState('')
  const selectedRun = runs.find((run) => runKey(run) === selectedRunKey) ?? runs[0]
  const recentComparisons = useMemo(
    () => getVisibleCatalogReports(comparisons, ''),
    [comparisons],
  )
  const crossReportDetails = useQueries({
    queries: recentComparisons.map((comparison) => ({
      enabled: Boolean(selectedRun),
      queryFn: () => fetchComparisonDetail(comparison.name),
      queryKey: ['comparison-detail', comparison.name],
    })),
  })
  const crossReportInputs = recentComparisons.flatMap((comparison, index) => {
    const report = crossReportDetails[index]?.data

    return report
      ? [
          {
            name: comparison.name,
            modifiedAt: comparison.modified_at,
            runs: report.runs ?? [],
          },
        ]
      : []
  })
  const crossReportRows = selectedRun
    ? buildCrossReportRows(selectedRun, crossReportInputs)
    : []
  const crossReportTrendRows = buildCrossReportTrendRows(crossReportRows)
  const selectedRunInsight = buildSelectedRunInsight(crossReportRows)
  const crossReportLoading =
    Boolean(selectedRun) && crossReportDetails.some((query) => query.isLoading)

  return (
    <>
      <ReportCatalog
        comparisons={comparisons}
        loading={comparisonLoading}
        onSelectReport={onSelectReport}
        selectedName={selectedSummary?.name ?? ''}
      />

      <LiveProcessMonitor
        error={liveError}
        loading={liveLoading}
        status={liveStatus}
      />

      <OperationalGuardrailsPanel
        error={guardrailError}
        loading={guardrailLoading}
        status={guardrailStatus}
      />

      <AIAnalystPanel
        analysis={aiAnalysis}
        error={aiError}
        loading={aiLoading}
      />

      <RecommendationDashboardPanel
        combinations={combinations}
        error={recommendationError}
        loading={recommendationLoading}
        movements={oddsMovement}
        recommendations={recommendations}
        review={recommendationReview}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Reports indexed"
          testId="metric-reports-indexed"
          value={comparisonLoading ? undefined : String(comparisons.length)}
          helper="Local comparison JSON files"
        />
        <MetricCard
          label="Selected runs"
          testId="metric-selected-runs"
          value={detailLoading ? undefined : String(runs.length || selectedSummary?.runs || 0)}
          helper={selectedSummary?.filename ?? 'Waiting for report'}
        />
        <MetricCard
          label="Best ROI"
          testId="metric-best-roi"
          value={bestRoi ? percent.format(bestRoi.roi) : undefined}
          helper={bestRoi ? `${bestRoi.model} / ${bestRoi.bookmaker}` : 'No run selected'}
          icon={Trophy}
        />
        <MetricCard
          label="Best Brier"
          testId="metric-best-brier"
          value={bestBrier ? decimal.format(bestBrier.brier_score) : undefined}
          helper={bestBrier ? `${bestBrier.model} / ${bestBrier.bookmaker}` : 'No run selected'}
          icon={Target}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(420px,1.1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Metadata summary</CardTitle>
            <CardDescription>Replay context from the selected comparison report.</CardDescription>
          </CardHeader>
          <CardContent>
            {detailLoading ? (
              <RunTableSkeleton />
            ) : metadataRows.length ? (
              <div className="grid gap-2">
                {metadataRows.map(([label, value]) => (
                  <div
                    key={label}
                    className="grid grid-cols-[100px_minmax(0,1fr)] gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
                  >
                    <span className="text-slate-500">{label}</span>
                    <span className="truncate font-medium text-slate-900" title={value}>
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="No metadata available for this report." />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sample-size warning</CardTitle>
            <CardDescription>Use ROI carefully when settled samples are still small.</CardDescription>
          </CardHeader>
          <CardContent>
            {detailLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : detail?.analysis?.sample_size ? (
              <div
                className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"
                data-testid="sample-size-warning"
              >
                <div className="flex items-center gap-2 font-semibold">
                  <AlertCircle className="h-4 w-4" />
                  {detail.analysis.sample_size.smallest}-{detail.analysis.sample_size.largest}{' '}
                  settled bets
                </div>
                <p className="mt-2 leading-6">{detail.analysis.sample_size.warning}</p>
              </div>
            ) : (
              <EmptyState text="Analysis sample-size payload is not available." />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          label="Best log loss"
          testId="metric-best-log-loss"
          value={bestLogLoss ? decimal.format(bestLogLoss.log_loss) : undefined}
          helper={
            bestLogLoss ? `${bestLogLoss.model} / ${bestLogLoss.bookmaker}` : 'No run selected'
          }
          icon={Target}
        />
        <MetricCard
          label="Total settled bets"
          testId="metric-total-settled"
          value={detailLoading ? undefined : String(totalSettledBets(runs))}
          helper="Across visible model/bookmaker runs"
          icon={Database}
        />
        <MetricCard
          label="Analysis status"
          testId="metric-analysis-status"
          value={detail?.analysis ? 'Ready' : undefined}
          helper={detail?.analysis?.interpretation ?? 'Waiting for analysis'}
          icon={SlidersHorizontal}
        />
      </div>

      <Suspense fallback={<ChartGridSkeleton />}>
        <div className="grid gap-4 xl:grid-cols-2">
          <MetricChart
            data={chartData}
            dataKey="roi"
            description="ROI in percentage points."
            loading={detailLoading}
            title="ROI by model and bookmaker"
          />
          <MetricChart
            data={chartData}
            dataKey="brier"
            description="Lower values indicate better calibration."
            loading={detailLoading}
            title="Brier score by model and bookmaker"
          />
          <MetricChart
            data={chartData}
            dataKey="logLoss"
            description="Lower values indicate better probability quality."
            loading={detailLoading}
            title="Log loss by model and bookmaker"
          />
          <MetricChart
            data={chartData}
            dataKey="settledBets"
            description="Settled sample size for each run."
            loading={detailLoading}
            title="Settled bets by model and bookmaker"
          />
        </div>
      </Suspense>

      <CrossReportPanel
        loading={crossReportLoading}
        rows={crossReportRows}
        selectedRun={selectedRun}
        selectedRunInsight={selectedRunInsight}
        trendRows={crossReportTrendRows}
      />

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Analysis guidance</CardTitle>
            <CardDescription>Current interpretation and next experiment note.</CardDescription>
          </CardHeader>
          <CardContent>
            {detailLoading ? (
              <div className="grid gap-3">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : detail?.analysis ? (
              <div className="grid gap-4 text-sm text-slate-700">
                <InfoBlock label="Interpretation" value={detail.analysis.interpretation} />
                <InfoBlock label="Next experiment" value={detail.analysis.next_experiment} />
              </div>
            ) : (
              <EmptyState text="Select a report to load analysis." />
            )}
          </CardContent>
        </Card>

        <RunDetailCard
          comparison={selectedRun ? buildRunComparison(selectedRun, runs) : undefined}
          loading={detailLoading}
          run={selectedRun}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Run ranking preview</CardTitle>
          <CardDescription>
            Model and bookmaker metrics from the selected report.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {detailLoading ? (
            <RunTableSkeleton />
          ) : (
            <RunTable
              runs={runs}
              selectedRunKey={selectedRun ? runKey(selectedRun) : ''}
              onSelectRun={setSelectedRunKey}
            />
          )}
        </CardContent>
      </Card>
    </>
  )
}

function LiveProcessMonitor({
  error,
  loading,
  status,
}: {
  error: boolean
  loading: boolean
  status?: LiveStatus
}) {
  const summary = buildLiveProcessSummary(status)

  return (
    <Card data-testid="live-process-monitor">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle>Live process monitor</CardTitle>
            <CardDescription>
              Paper-only collection and settlement status from the local run registry.
            </CardDescription>
          </div>
          <Badge className={liveStatusClass(summary.statusTone)} variant="secondary">
            {loading ? 'Loading live status' : summary.statusLabel}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            Live status API is not reachable.
          </div>
        ) : (
          <div className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr_0.8fr_1fr]">
            <LiveStatusTile
              label="Latest run"
              testId="live-latest-run"
              value={summary.latestRunLabel}
              helper={status?.latest_run ? formatDate(status.latest_run.started_at) : 'Not started'}
            />
            <LiveStatusTile
              label="Provider"
              testId="live-provider"
              value={summary.providerLabel}
              helper={summary.countersLabel}
            />
            <LiveStatusTile
              label="Paper bets"
              testId="live-paper-bets"
              value={summary.openBetsLabel}
              helper={summary.settledBetsLabel}
            />
            <LiveStatusTile
              label="Errors"
              testId="live-errors"
              value={status ? String(status.errors_count) : '0'}
              helper={summary.errorLabel}
            />
          </div>
        )}

        {!loading && !error && status?.latest_run ? (
          <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Last success
              </div>
              <div className="mt-1 truncate font-medium text-slate-900">
                {status.latest_success?.run_id ?? 'No successful run recorded'}
              </div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Last failure
              </div>
              <div className="mt-1 truncate font-medium text-slate-900">
                {status.latest_failure?.run_id ?? 'No failed run recorded'}
              </div>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function OperationalGuardrailsPanel({
  error,
  loading,
  status,
}: {
  error: boolean
  loading: boolean
  status?: OperationalGuardrailStatus
}) {
  const visibleGuardrails = status?.guardrails ?? []

  return (
    <Card data-testid="operational-guardrails">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle>
              <span className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4" />
                Operational guardrails
              </span>
            </CardTitle>
            <CardDescription>
              Warning and critical states before paper recommendations become misleading.
            </CardDescription>
          </div>
          <Badge className={guardrailBadgeClass(status?.overall_status)} variant="secondary">
            {loading ? 'Loading guardrails' : (status?.overall_status ?? 'unknown')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            Operational guardrails API is not reachable.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {visibleGuardrails.map((guardrail) => (
              <div
                className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm"
                data-testid={`guardrail-${guardrail.name}`}
                key={guardrail.name}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {guardrail.name.replaceAll('_', ' ')}
                  </div>
                  <Badge className={guardrailBadgeClass(guardrail.severity)} variant="secondary">
                    {guardrail.severity}
                  </Badge>
                </div>
                <div className="mt-2 truncate font-semibold text-slate-950">
                  {guardrail.state.replaceAll('_', ' ')}
                </div>
                <div className="mt-1 line-clamp-2 text-slate-500">
                  {guardrail.remediation}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function AIAnalystPanel({
  analysis,
  error,
  loading,
}: {
  analysis?: AIAnalysisRun | null
  error: boolean
  loading: boolean
}) {
  const summary = buildAIAdvisorySummary(analysis)

  return (
    <Card data-testid="ai-analyst-panel">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Bot className="h-4 w-4" />
                AI analyst
              </span>
            </CardTitle>
            <CardDescription>
              Advisory explanations from structured run, model, and provider data.
            </CardDescription>
          </div>
          <Badge variant="secondary">{summary.label}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <RunTableSkeleton />
        ) : error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            AI advisory API is not reachable.
          </div>
        ) : (
          <div className="grid gap-3 xl:grid-cols-3">
            <InfoBlock label="Summary" value={summary.headline} />
            <InfoBlock label="Root cause" value={summary.rootCause} />
            <InfoBlock label="Next action" value={summary.nextAction} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function RecommendationDashboardPanel({
  combinations,
  error,
  loading,
  movements,
  recommendations,
  review,
}: {
  combinations: PaperCombination[]
  error: boolean
  loading: boolean
  movements: OddsMovementSummary[]
  recommendations: PaperRecommendation[]
  review?: AIAnalysisRun | null
}) {
  const [filters, setFilters] = useState<RecommendationFilters>({
    approvalState: 'all',
    confidence: 'all',
    grade: 'all',
    market: 'all',
  })
  const summary = useMemo(
    () =>
      buildRecommendationDashboardSummary({
        combinations,
        filters,
        movements,
        recommendations,
        review,
      }),
    [combinations, filters, movements, recommendations, review],
  )

  return (
    <Card data-testid="recommendation-dashboard">
      <CardHeader>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Target className="h-4 w-4" />
                Recommendation dashboard
              </span>
            </CardTitle>
            <CardDescription>
              Live paper recommendations, combinations, risk flags, odds movement, and AI review.
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className={approvalBadgeClass(summary.approvalState)} variant="secondary">
              AI {summary.approvalState}
            </Badge>
            {summary.topRiskFlags.slice(0, 3).map((flag) => (
              <RiskBadge flag={flag} key={flag} />
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <RunTableSkeleton />
        ) : error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            Recommendation APIs are not reachable.
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <RecommendationFiltersBar
              filters={filters}
              gradeOptions={summary.gradeOptions}
              marketOptions={summary.marketOptions}
              onChange={setFilters}
            />
            <div
              className="grid gap-3 text-sm md:grid-cols-3"
              data-testid="recommendation-ai-review"
            >
              <InfoBlock label="AI review" value={summary.reviewLabel} />
              <InfoBlock
                label="Approval"
                value={review?.output.approval_state ?? 'No AI approval state yet'}
              />
              <InfoBlock
                label="Next check"
                value={review?.output.next_checks?.[0] ?? 'Run analyze-recommendations.'}
              />
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
              <RecommendationTable rows={summary.rows} />
              <CombinationList combinations={summary.combinations} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function RecommendationFiltersBar({
  filters,
  gradeOptions,
  marketOptions,
  onChange,
}: {
  filters: RecommendationFilters
  gradeOptions: string[]
  marketOptions: string[]
  onChange: (filters: RecommendationFilters) => void
}) {
  return (
    <div className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 md:grid-cols-4">
      <FilterSelect
        label="Grade"
        value={filters.grade}
        options={['all', ...gradeOptions]}
        onChange={(grade) => onChange({ ...filters, grade })}
      />
      <FilterSelect
        label="Market"
        value={filters.market}
        options={['all', ...marketOptions]}
        onChange={(market) => onChange({ ...filters, market })}
      />
      <FilterSelect
        label="Confidence"
        value={filters.confidence}
        options={['all', 'high', 'medium', 'low']}
        onChange={(confidence) =>
          onChange({
            ...filters,
            confidence: confidence as RecommendationFilters['confidence'],
          })
        }
      />
      <FilterSelect
        label="AI approval"
        value={filters.approvalState}
        options={['all', 'approve', 'caution', 'reject']}
        onChange={(approvalState) =>
          onChange({
            ...filters,
            approvalState: approvalState as RecommendationFilters['approvalState'],
          })
        }
      />
    </div>
  )
}

function FilterSelect({
  label,
  onChange,
  options,
  value,
}: {
  label: string
  onChange: (value: string) => void
  options: string[]
  value: string
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
      {label}
      <select
        className="h-9 rounded-md border border-slate-300 bg-white px-2 text-sm font-normal normal-case tracking-normal text-slate-900 outline-none focus:ring-2 focus:ring-slate-400"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

function RecommendationTable({ rows }: { rows: ReturnType<typeof buildRecommendationDashboardSummary>['rows'] }) {
  if (!rows.length) {
    return <EmptyState text="No recommendations match the active filters." />
  }

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Candidate</th>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Market</th>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Odds</th>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Move</th>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Edge</th>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Confidence</th>
            <th className="border-b border-slate-200 px-3 py-2 font-medium">Risk</th>
          </tr>
        </thead>
        <tbody data-testid="recommendation-table">
          {rows.map((row) => (
            <tr className="border-b border-slate-100 last:border-0" key={row.id}>
              <td className="max-w-72 px-3 py-3">
                <div className="font-semibold text-slate-950">{row.selection}</div>
                <div className="truncate text-xs text-slate-500" title={row.match_label}>
                  {row.match_label}
                </div>
                <div className="mt-1">
                  <Badge variant="secondary">{row.grade}</Badge>
                </div>
              </td>
              <td className="px-3 py-3 text-slate-700">{row.market}</td>
              <td className="px-3 py-3 text-slate-900">
                {formatOptionalDecimal(row.current_odds)}
              </td>
              <td className="px-3 py-3 text-slate-700">
                {row.movement_direction ?? 'unknown'}
              </td>
              <td className="px-3 py-3 text-slate-900">
                {formatOptionalPercent(row.edge)}
              </td>
              <td className="px-3 py-3 text-slate-900">
                {formatOptionalPercent(row.confidence_score)}
              </td>
              <td className="px-3 py-3">
                <div className="flex flex-wrap gap-1">
                  {row.risk_flags.map((flag) => (
                    <RiskBadge flag={flag} key={flag} />
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CombinationList({ combinations }: { combinations: PaperCombination[] }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Filter className="h-4 w-4" />
        Ranked combinations
      </div>
      <div className="mt-3 grid gap-2" data-testid="combination-list">
        {combinations.length ? (
          combinations.slice(0, 6).map((combination) => (
            <div
              className="rounded-md border border-slate-200 bg-white p-3 text-sm"
              key={combination.id}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-semibold text-slate-950">
                    #{combination.rank} / {combination.leg_count} legs
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    EV {percent.format(combination.combined_expected_value)} / odds{' '}
                    {decimal.format(combination.combined_odds)}
                  </div>
                </div>
                <Badge variant="secondary">{combination.grade}</Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {combination.risk_flags.map((flag) => (
                  <RiskBadge flag={flag} key={flag} />
                ))}
              </div>
            </div>
          ))
        ) : (
          <EmptyState text="No paper combinations match the active filters." />
        )}
      </div>
    </div>
  )
}

function RiskBadge({ flag }: { flag: string }) {
  return (
    <Badge className={riskBadgeClass(riskBadgeTone(flag))} variant="secondary">
      {flag}
    </Badge>
  )
}

function riskBadgeClass(tone: ReturnType<typeof riskBadgeTone>) {
  if (tone === 'positive') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-950'
  }
  if (tone === 'danger') {
    return 'border-rose-200 bg-rose-50 text-rose-950'
  }
  if (tone === 'warning') {
    return 'border-amber-200 bg-amber-50 text-amber-950'
  }
  return 'border-slate-200 bg-slate-100 text-slate-700'
}

function approvalBadgeClass(state: RecommendationDashboardPanelState) {
  if (state === 'approve') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-950'
  }
  if (state === 'reject') {
    return 'border-rose-200 bg-rose-50 text-rose-950'
  }
  if (state === 'caution') {
    return 'border-amber-200 bg-amber-50 text-amber-950'
  }
  return 'border-slate-200 bg-slate-100 text-slate-700'
}

type RecommendationDashboardPanelState = ReturnType<
  typeof buildRecommendationDashboardSummary
>['approvalState']

function LiveStatusTile({
  helper,
  label,
  testId,
  value,
}: {
  helper: string
  label: string
  testId: string
  value: string
}) {
  return (
    <div
      className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm"
      data-testid={testId}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 truncate text-base font-semibold text-slate-950" title={value}>
        {value}
      </div>
      <div className="mt-1 truncate text-slate-500" title={helper}>
        {helper}
      </div>
    </div>
  )
}

function liveStatusClass(tone: ReturnType<typeof buildLiveProcessSummary>['statusTone']) {
  if (tone === 'positive') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-950'
  }
  if (tone === 'negative') {
    return 'border-rose-200 bg-rose-50 text-rose-950'
  }
  if (tone === 'running') {
    return 'border-sky-200 bg-sky-50 text-sky-950'
  }
  return 'border-slate-200 bg-slate-100 text-slate-700'
}

function guardrailBadgeClass(severity?: OperationalGuardrailStatus['overall_status']) {
  if (severity === 'ok') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-950'
  }
  if (severity === 'critical') {
    return 'border-rose-200 bg-rose-50 text-rose-950'
  }
  if (severity === 'warning') {
    return 'border-amber-200 bg-amber-50 text-amber-950'
  }
  return 'border-slate-200 bg-slate-100 text-slate-700'
}

function CrossReportPanel({
  loading,
  rows,
  selectedRun,
  selectedRunInsight,
  trendRows,
}: {
  loading: boolean
  rows: CrossReportRow[]
  selectedRun?: RankedComparisonRun
  selectedRunInsight: SelectedRunInsight
  trendRows: CrossReportTrendRow[]
}) {
  const [visibleTrendMetrics, setVisibleTrendMetrics] = useState<TrendMetricKey[]>([
    'roi',
    'brierScore',
    'logLoss',
  ])

  return (
    <Card data-testid="cross-report-panel">
      <CardHeader>
        <CardTitle>Cross-report comparison</CardTitle>
        <CardDescription>
          Recent performance for the selected model/bookmaker pair.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <RunTableSkeleton />
        ) : selectedRun && rows.length ? (
          <div className="overflow-x-auto">
            <div className="mb-3 text-sm font-medium text-slate-700">
              {selectedRun.model} / {selectedRun.bookmaker}
            </div>
            <SelectedRunInsightPanel insight={selectedRunInsight} />
            <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                ROI and calibration trend
              </div>
              <div className="mb-3 flex flex-wrap gap-2">
                <TrendMetricToggle
                  active={visibleTrendMetrics.includes('roi')}
                  label="ROI"
                  metric="roi"
                  onToggle={(metric) =>
                    setVisibleTrendMetrics((current) => toggleTrendMetric(current, metric))
                  }
                />
                <TrendMetricToggle
                  active={visibleTrendMetrics.includes('brierScore')}
                  label="Brier"
                  metric="brierScore"
                  onToggle={(metric) =>
                    setVisibleTrendMetrics((current) => toggleTrendMetric(current, metric))
                  }
                />
                <TrendMetricToggle
                  active={visibleTrendMetrics.includes('logLoss')}
                  label="Log loss"
                  metric="logLoss"
                  onToggle={(metric) =>
                    setVisibleTrendMetrics((current) => toggleTrendMetric(current, metric))
                  }
                />
              </div>
              <Suspense fallback={<Skeleton className="h-56 w-full" />}>
                <CrossReportTrendChart
                  data={trendRows}
                  loading={loading}
                  visibleMetrics={visibleTrendMetrics}
                />
              </Suspense>
            </div>
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2 font-medium">Report</th>
                  <th className="px-3 py-2 font-medium">Updated</th>
                  <th className="px-3 py-2 font-medium">ROI</th>
                  <th className="px-3 py-2 font-medium">Brier</th>
                  <th className="px-3 py-2 font-medium">Log loss</th>
                  <th className="px-3 py-2 font-medium">Settled</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    className="border-b border-slate-100 last:border-0"
                    data-testid={`cross-report-row-${row.reportName}`}
                    key={row.reportName}
                  >
                    <td className="max-w-72 truncate px-3 py-2 font-medium text-slate-900">
                      {row.reportName}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{formatDate(row.modifiedAt)}</td>
                    <td className="px-3 py-2 text-slate-800">{percent.format(row.roi)}</td>
                    <td className="px-3 py-2 text-slate-800">
                      {decimal.format(row.brierScore)}
                    </td>
                    <td className="px-3 py-2 text-slate-800">{decimal.format(row.logLoss)}</td>
                    <td className="px-3 py-2 text-slate-800">{row.settledBets}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState text="Select a run to compare it across recent reports." />
        )}
      </CardContent>
    </Card>
  )
}

function SelectedRunInsightPanel({ insight }: { insight: SelectedRunInsight }) {
  const toneClass =
    insight.tone === 'positive'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-950'
      : insight.tone === 'negative'
        ? 'border-rose-200 bg-rose-50 text-rose-950'
        : 'border-amber-200 bg-amber-50 text-amber-950'

  return (
    <div
      className={`mb-4 rounded-md border p-3 text-sm ${toneClass}`}
      data-testid="selected-run-insight"
    >
      <div className="text-xs font-semibold uppercase tracking-wide">Selected-run insight</div>
      <div className="mt-2 font-semibold">{insight.label}</div>
      <p className="mt-1 leading-5">{insight.summary}</p>
    </div>
  )
}

function TrendMetricToggle({
  active,
  label,
  metric,
  onToggle,
}: {
  active: boolean
  label: string
  metric: TrendMetricKey
  onToggle: (metric: TrendMetricKey) => void
}) {
  return (
    <button
      aria-pressed={active}
      className={`h-8 rounded-md border px-3 text-xs font-medium transition-colors ${
        active
          ? 'border-slate-900 bg-slate-900 text-white'
          : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-100'
      }`}
      data-testid={`trend-toggle-${metric}`}
      onClick={() => onToggle(metric)}
      type="button"
    >
      {label}
    </button>
  )
}

function ReportCatalog({
  comparisons,
  loading,
  onSelectReport,
  selectedName,
}: {
  comparisons: ComparisonSummary[]
  loading: boolean
  onSelectReport: (name: string) => void
  selectedName: string
}) {
  const [catalogQuery, setCatalogQuery] = useState('')
  const visibleReports = useMemo(
    () => getVisibleCatalogReports(comparisons, catalogQuery),
    [catalogQuery, comparisons],
  )

  return (
    <Card data-testid="report-catalog">
      <CardHeader>
        <CardTitle>Report catalog</CardTitle>
        <CardDescription>Recent comparison reports with headline metrics.</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="grid gap-2 xl:grid-cols-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <label className="relative block">
              <span className="sr-only">Search reports</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                aria-label="Search reports"
                className="h-10 w-full rounded-md border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-900 outline-none ring-offset-white placeholder:text-slate-400 focus:ring-2 focus:ring-slate-400"
                data-testid="catalog-search"
                onChange={(event) => setCatalogQuery(event.target.value)}
                placeholder="Search reports, models, bookmakers"
                type="search"
                value={catalogQuery}
              />
            </label>

            {visibleReports.length ? (
              <div className="grid gap-3 xl:grid-cols-3">
                {visibleReports.map((comparison) => (
                  <button
                    className={`rounded-md border p-3 text-left text-sm transition-colors ${
                      comparison.name === selectedName
                        ? 'border-slate-900 bg-slate-50'
                        : 'border-slate-200 bg-white hover:bg-slate-50'
                    }`}
                    data-testid={`catalog-report-${comparison.name}`}
                    key={comparison.name}
                    onClick={() => onSelectReport(comparison.name)}
                    type="button"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div
                          className="truncate font-semibold text-slate-950"
                          title={comparison.name}
                        >
                          {comparison.name}
                        </div>
                        <div className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                          <CalendarClock className="h-3.5 w-3.5" />
                          {formatDate(comparison.modified_at)}
                        </div>
                      </div>
                      <Badge variant="secondary">{comparison.runs} runs</Badge>
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                      <CatalogMetric
                        label="ROI"
                        value={formatOptionalPercent(comparison.best_roi)}
                      />
                      <CatalogMetric
                        label="Brier"
                        value={formatOptionalDecimal(comparison.best_brier_score)}
                      />
                      <CatalogMetric
                        label="Settled"
                        value={formatOptionalInteger(comparison.total_settled_bets)}
                      />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState text="No comparison reports found." />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CatalogMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
      <div className="text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-slate-950">{value}</div>
    </div>
  )
}

function RunTable({
  runs,
  selectedRunKey,
  onSelectRun,
}: {
  runs: RankedComparisonRun[]
  selectedRunKey: string
  onSelectRun: (key: string) => void
}) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'roi_rank', desc: false }])
  const columns = useMemo<ColumnDef<RankedComparisonRun>[]>(
    () => [
      { accessorKey: 'roi_rank', header: 'ROI rank' },
      { accessorKey: 'model', header: 'Model' },
      { accessorKey: 'bookmaker', header: 'Bookmaker' },
      { accessorKey: 'settled_bets', header: 'Settled' },
      {
        accessorKey: 'roi',
        header: 'ROI',
        cell: ({ row }) => percent.format(row.original.roi),
      },
      {
        accessorKey: 'profit_loss_units',
        header: 'P/L',
        cell: ({ row }) => decimal.format(row.original.profit_loss_units),
      },
      {
        accessorKey: 'brier_score',
        header: 'Brier',
        cell: ({ row }) => decimal.format(row.original.brier_score),
      },
      {
        accessorKey: 'log_loss',
        header: 'Log loss',
        cell: ({ row }) => decimal.format(row.original.log_loss),
      },
    ],
    [],
  )

  // TanStack Table exposes stable table helpers that React Compiler cannot memoize.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    columns,
    data: runs,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (!runs.length) {
    return <EmptyState text="No run rows available." />
  }

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table
        className="w-full min-w-[860px] border-collapse text-left text-sm"
        data-testid="run-ranking-table"
      >
        <thead className="bg-slate-50 text-slate-600">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="border-b border-slate-200 px-3 py-2 font-medium">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-left"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                  </button>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              data-testid={`run-row-${runKey(row.original)}`}
              className={`cursor-pointer border-b border-slate-100 last:border-0 ${
                runKey(row.original) === selectedRunKey ? 'bg-slate-100' : 'hover:bg-slate-50'
              }`}
              onClick={() => onSelectRun(runKey(row.original))}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2 text-slate-800">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MetricCard({
  label,
  value,
  helper,
  icon: Icon,
  testId,
}: {
  label: string
  value?: string
  helper: string
  icon?: typeof Database
  testId?: string
}) {
  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2">
        <CardDescription>
          <span className="flex items-center gap-2">
            {Icon ? <Icon className="h-4 w-4" /> : null}
            {label}
          </span>
        </CardDescription>
        <CardTitle className="text-2xl">{value ?? <Skeleton className="h-8 w-20" />}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="truncate text-sm text-slate-500" title={helper}>
          {helper}
        </p>
      </CardContent>
    </Card>
  )
}

function RunDetailCard({
  comparison,
  run,
  loading,
}: {
  comparison?: RunComparison
  run?: RankedComparisonRun
  loading: boolean
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Run detail</CardTitle>
        <CardDescription>Selected model/bookmaker configuration and metrics.</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <RunTableSkeleton />
        ) : run ? (
          <div className="grid gap-3 text-sm">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Selected run
              </div>
              <div
                className="mt-2 text-base font-semibold text-slate-950"
                data-testid="selected-run-label"
              >
                {run.model} / {run.bookmaker}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <DetailMetric label="ROI rank" value={`#${run.roi_rank}`} />
              <DetailMetric label="ROI" value={percent.format(run.roi)} />
              <DetailMetric label="Brier rank" value={`#${run.brier_score_rank}`} />
              <DetailMetric label="Brier" value={decimal.format(run.brier_score)} />
              <DetailMetric label="Log rank" value={`#${run.log_loss_rank}`} />
              <DetailMetric label="Log loss" value={decimal.format(run.log_loss)} />
              <DetailMetric label="Settled" value={String(run.settled_bets)} />
              <DetailMetric label="Profit units" value={decimal.format(run.profit_loss_units)} />
            </div>
            {comparison ? (
              <div
                className="grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-3"
                data-testid="run-comparison"
              >
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Against report average
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <DetailMetric
                    label="ROI delta"
                    value={formatSignedPercent(comparison.roiDelta)}
                  />
                  <DetailMetric
                    label="Brier delta"
                    value={formatSignedDecimal(comparison.brierScoreDelta)}
                  />
                  <DetailMetric
                    label="Log loss delta"
                    value={formatSignedDecimal(comparison.logLossDelta)}
                  />
                  <DetailMetric
                    label="Settled delta"
                    value={formatSignedDecimal(comparison.settledBetsDelta)}
                  />
                </div>
              </div>
            ) : null}
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Model config
              </div>
              <pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-700">
                {JSON.stringify(run.model_config ?? {}, null, 2)}
              </pre>
            </div>
          </div>
        ) : (
          <EmptyState text="Select a run to inspect details." />
        )}
      </CardContent>
    </Card>
  )
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-slate-950">{value}</div>
    </div>
  )
}

function runKey(run: ComparisonRun) {
  return `${run.model}::${run.bookmaker}`
}

function totalSettledBets(runs: ComparisonRun[]) {
  return runs.reduce((total, run) => total + run.settled_bets, 0)
}

function formatDate(value: string | undefined) {
  if (!value) {
    return 'Unknown'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Unknown'
  }
  return new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
  }).format(date)
}

function formatOptionalPercent(value: number | null) {
  return typeof value === 'number' ? percent.format(value) : 'N/A'
}

function formatOptionalDecimal(value: number | null) {
  return typeof value === 'number' ? decimal.format(value) : 'N/A'
}

function formatOptionalInteger(value: number | null | undefined) {
  return typeof value === 'number' ? String(value) : 'N/A'
}

function formatSignedPercent(value: number) {
  return `${value >= 0 ? '+' : ''}${percent.format(value)}`
}

function formatSignedDecimal(value: number) {
  return `${value >= 0 ? '+' : ''}${decimal.format(value)}`
}

function NavItem({
  icon: Icon,
  label,
  active = false,
}: {
  icon: typeof Database
  label: string
  active?: boolean
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded-md px-3 py-2 ${
        active ? 'bg-slate-900 text-white' : 'text-slate-600'
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </div>
  )
}

function ApiWarning() {
  return (
    <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
      <div>
        <div className="font-semibold">Dashboard API is not reachable.</div>
        <div className="mt-1">
          Start FastAPI with .\.venv\Scripts\python.exe -m uvicorn app.api:api --reload,
          then refresh this page.
        </div>
      </div>
    </div>
  )
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <p className="mt-2 leading-6">{value}</p>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex h-full min-h-32 items-center justify-center rounded-md border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
      {text}
    </div>
  )
}

function ChartGridSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartSkeletonCard />
      <ChartSkeletonCard />
      <ChartSkeletonCard />
      <ChartSkeletonCard />
    </div>
  )
}

function ChartSkeletonCard() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-56" />
        <Skeleton className="h-4 w-72 max-w-full" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-64 w-full" />
      </CardContent>
    </Card>
  )
}

function RunTableSkeleton() {
  return (
    <div className="grid gap-2">
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-9 w-full" />
      <Skeleton className="h-9 w-full" />
    </div>
  )
}

export default App
