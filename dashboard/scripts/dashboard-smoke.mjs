import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { chromium } from 'playwright'

const dashboardUrl = process.env.DASHBOARD_URL ?? 'http://127.0.0.1:5173'
const apiUrl = process.env.API_URL ?? 'http://127.0.0.1:8000'
const channel = process.env.PLAYWRIGHT_CHANNEL ?? 'msedge'

const comparisons = await getJson(`${apiUrl}/api/reports/comparisons`)
if (!Array.isArray(comparisons) || comparisons.length === 0) {
  throw new Error('No comparison reports returned by API')
}
if (comparisons.some((comparison) => comparison.name.startsWith('pytest_'))) {
  throw new Error('Default comparison list should not include pytest reports')
}

const firstComparison = comparisons[0]
const detail = await getJson(`${apiUrl}/api/reports/comparisons/${firstComparison.name}`)
const liveStatus = await getJson(`${apiUrl}/api/live/status`)
const recentComparisons = comparisons
  .toSorted((a, b) => Date.parse(b.modified_at) - Date.parse(a.modified_at))
  .slice(0, 6)
const recentDetails = await Promise.all(
  recentComparisons.map((comparison) =>
    getJson(`${apiUrl}/api/reports/comparisons/${comparison.name}`),
  ),
)
const expected = buildExpectedValues(comparisons, detail, recentComparisons, recentDetails)
const expectedLive = buildExpectedLiveValues(liveStatus)

const browser = await launchBrowser()
const screenshotDir = await mkdtemp(join(tmpdir(), 'paper-odds-dashboard-'))

try {
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1100 } })
  const consoleMessages = []
  desktop.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) {
      consoleMessages.push(`${message.type()}: ${message.text()}`)
    }
  })
  desktop.on('pageerror', (error) => {
    consoleMessages.push(`pageerror: ${error.message}`)
  })

  await desktop.goto(dashboardUrl, { waitUntil: 'networkidle' })
  await expectVisibleText(desktop, 'Comparison workspace')
  await expectVisibleText(desktop, 'Report catalog')
  await expectMetric(desktop, `catalog-report-${firstComparison.name}`, expected.bestRoi)
  await expectMetric(desktop, `catalog-report-${firstComparison.name}`, String(expected.totalSettled))
  const catalogSearch = desktop.getByTestId('catalog-search')
  await catalogSearch.fill(firstComparison.name)
  await expectMetric(desktop, `catalog-report-${firstComparison.name}`, expected.bestRoi)
  await catalogSearch.fill('no-matching-report-for-smoke')
  await expectVisibleText(desktop, 'No comparison reports found.')
  await catalogSearch.fill('')
  const visibleCatalogComparisons = comparisons
    .toSorted((a, b) => Date.parse(b.modified_at) - Date.parse(a.modified_at))
    .slice(0, 6)
  const alternateComparison = visibleCatalogComparisons.find(
    (comparison) => comparison.name !== firstComparison.name,
  )
  if (alternateComparison) {
    await desktop.getByTestId(`catalog-report-${alternateComparison.name}`).click()
    await desktop.waitForFunction(
      (name) => document.querySelector('[data-testid="report-select"]')?.value === name,
      alternateComparison.name,
    )
    await desktop.getByTestId(`catalog-report-${firstComparison.name}`).click()
    await desktop.waitForFunction(
      (name) => document.querySelector('[data-testid="report-select"]')?.value === name,
      firstComparison.name,
    )
  }
  await expectVisibleText(desktop, 'Metadata summary')
  await expectVisibleText(desktop, 'Live process monitor')
  await expectVisibleText(desktop, 'AI analyst')
  await expectMetric(desktop, 'ai-analyst-panel', 'AI-assisted advisory analysis')
  await expectMetric(desktop, 'live-process-monitor', expectedLive.statusLabel)
  await expectMetric(desktop, 'live-latest-run', expectedLive.latestRunLabel)
  await expectMetric(desktop, 'live-provider', expectedLive.providerLabel)
  await expectMetric(desktop, 'live-paper-bets', expectedLive.openBetsLabel)
  await expectMetric(desktop, 'live-errors', expectedLive.errorsCount)
  await expectMetric(desktop, 'metric-reports-indexed', String(expected.reportCount))
  await expectMetric(desktop, 'metric-selected-runs', String(expected.runCount))
  await expectMetric(desktop, 'metric-best-roi', expected.bestRoi)
  await expectMetric(desktop, 'metric-best-brier', expected.bestBrier)
  await expectMetric(desktop, 'metric-best-log-loss', expected.bestLogLoss)
  await expectMetric(desktop, 'metric-total-settled', String(expected.totalSettled))
  await expectMetric(desktop, 'metric-analysis-status', 'Ready')
  await expectMetric(desktop, 'sample-size-warning', expected.sampleSize)
  await expectVisibleText(desktop, 'ROI by model and bookmaker')
  await expectVisibleText(desktop, 'Brier score by model and bookmaker')
  await expectVisibleText(desktop, 'Log loss by model and bookmaker')
  await expectVisibleText(desktop, 'Settled bets by model and bookmaker')
  await expectVisibleText(desktop, 'Cross-report comparison')

  const selectedRunBefore = await desktop.getByTestId('selected-run-label').textContent()
  await desktop.getByTestId('run-row-elo::Avg').click()
  await expectMetric(desktop, 'selected-run-label', 'elo / Avg')
  await expectMetric(desktop, 'cross-report-panel', 'elo / Avg')
  await expectMetric(desktop, 'selected-run-insight', 'Selected-run insight')
  await expectMetric(desktop, 'selected-run-insight', expected.selectedRunInsight.label)
  await expectMetric(desktop, 'cross-report-panel', 'ROI and calibration trend')
  await expectVisibleTestId(desktop, 'cross-report-trend-chart')
  await expectPressed(desktop, 'trend-toggle-brierScore', 'true')
  await desktop.getByTestId('trend-toggle-brierScore').click()
  await expectPressed(desktop, 'trend-toggle-brierScore', 'false')
  await desktop.getByTestId('trend-toggle-brierScore').click()
  await expectPressed(desktop, 'trend-toggle-brierScore', 'true')
  if (expected.crossReportRows.length > 0) {
    const firstCrossReportRow = expected.crossReportRows[0]
    await expectMetric(
      desktop,
      `cross-report-row-${firstCrossReportRow.reportName}`,
      percent(firstCrossReportRow.roi),
    )
  }
  await expectMetric(desktop, 'run-comparison', 'Against report average')
  await expectMetric(desktop, 'run-comparison', expected.selectedRunComparison.roiDelta)
  await expectMetric(desktop, 'run-comparison', expected.selectedRunComparison.brierDelta)
  await expectMetric(desktop, 'run-comparison', expected.selectedRunComparison.logLossDelta)
  await expectMetric(desktop, 'run-comparison', expected.selectedRunComparison.settledDelta)
  const selectedRunAfter = await desktop.getByTestId('selected-run-label').textContent()
  if (selectedRunBefore === selectedRunAfter) {
    throw new Error('Run-detail selection did not change after clicking elo / Avg')
  }

  if (consoleMessages.length > 0) {
    throw new Error(`Console issues found:\n${consoleMessages.join('\n')}`)
  }

  const desktopScreenshot = join(screenshotDir, 'desktop.png')
  await desktop.screenshot({ path: desktopScreenshot, fullPage: true })

  const mobile = await browser.newPage({ viewport: { width: 390, height: 1000 } })
  await mobile.goto(dashboardUrl, { waitUntil: 'networkidle' })
  await expectVisibleText(mobile, 'Comparison workspace')
  await expectVisibleText(mobile, 'Live process monitor')
  await expectVisibleText(mobile, 'AI analyst')
  await expectVisibleText(mobile, 'Run detail')
  await expectMetric(mobile, 'metric-best-roi', expected.bestRoi)
  await expectMetric(mobile, 'sample-size-warning', expected.sampleSize)
  const mobileScreenshot = join(screenshotDir, 'mobile.png')
  await mobile.screenshot({ path: mobileScreenshot, fullPage: true })

  console.log(
    JSON.stringify(
      {
        ok: true,
        checkedReport: firstComparison.name,
        screenshots: {
          desktop: desktopScreenshot,
          mobile: mobileScreenshot,
        },
      },
      null,
      2,
    ),
  )
} finally {
  await browser.close()
}

async function launchBrowser() {
  try {
    return await chromium.launch({ channel })
  } catch (error) {
    if (process.env.PLAYWRIGHT_CHANNEL) {
      throw error
    }
    return chromium.launch()
  }
}

async function getJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText} for ${url}`)
  }
  return response.json()
}

async function expectVisibleText(page, text) {
  await page.getByText(text, { exact: false }).first().waitFor({ state: 'visible' })
}

async function expectMetric(page, testId, expectedText) {
  const locator = page.getByTestId(testId)
  await locator.waitFor({ state: 'visible' })
  const text = await locator.textContent()
  if (!text?.includes(expectedText)) {
    throw new Error(`Expected ${testId} to include "${expectedText}", got "${text}"`)
  }
}

async function expectVisibleTestId(page, testId) {
  await page.getByTestId(testId).waitFor({ state: 'visible' })
}

async function expectPressed(page, testId, expectedValue) {
  const locator = page.getByTestId(testId)
  await locator.waitFor({ state: 'visible' })
  const pressed = await locator.getAttribute('aria-pressed')
  if (pressed !== expectedValue) {
    throw new Error(`Expected ${testId} aria-pressed="${expectedValue}", got "${pressed}"`)
  }
}

function buildExpectedValues(comparisons, detail, recentComparisons, recentDetails) {
  const runs = detail.runs ?? []
  const bestRoi = getMetricLeader(runs, 'roi', 'higher')
  const bestBrier = getMetricLeader(runs, 'brier_score', 'lower')
  const bestLogLoss = getMetricLeader(runs, 'log_loss', 'lower')
  const selectedRun = runs.find((run) => run.model === 'elo' && run.bookmaker === 'Avg') ?? runs[0]
  const recentReports = recentComparisons.map((comparison, index) => ({
    name: comparison.name,
    modifiedAt: comparison.modified_at,
    runs: recentDetails[index]?.runs ?? [],
  }))
  const sampleSize = detail.analysis?.sample_size
  return {
    reportCount: comparisons.length,
    runCount: runs.length,
    bestRoi: percent(bestRoi?.roi ?? 0),
    bestBrier: decimal(bestBrier?.brier_score ?? 0),
    bestLogLoss: decimal(bestLogLoss?.log_loss ?? 0),
    totalSettled: runs.reduce((total, run) => total + run.settled_bets, 0),
    crossReportRows: buildCrossReportRows(selectedRun, recentReports),
    selectedRunInsight: buildSelectedRunInsight(buildCrossReportRows(selectedRun, recentReports)),
    selectedRunComparison: buildRunComparison(selectedRun, runs),
    sampleSize: sampleSize ? `${sampleSize.smallest}-${sampleSize.largest}` : '',
  }
}

function buildExpectedLiveValues(status) {
  const latestRun = status.latest_run

  if (!latestRun) {
    return {
      statusLabel: 'No live runs yet',
      latestRunLabel: 'Waiting for first collection',
      providerLabel: 'Provider unavailable',
      openBetsLabel: '0 open',
      errorsCount: '0',
    }
  }

  return {
    statusLabel: statusLabel(latestRun.status),
    latestRunLabel: `${latestRun.run_type} / ${latestRun.run_id}`,
    providerLabel: [latestRun.provider, latestRun.league, latestRun.season]
      .filter(Boolean)
      .join(' / '),
    openBetsLabel: `${status.open_paper_bets} open`,
    errorsCount: String(status.errors_count),
  }
}

function statusLabel(status) {
  if (status === 'completed') {
    return 'Latest run completed'
  }
  if (status === 'failed') {
    return 'Latest run failed'
  }
  if (status === 'running') {
    return 'Latest run running'
  }
  return `Latest run ${status}`
}

function getMetricLeader(runs, metric, direction) {
  return runs.reduce((leader, run) => {
    if (!leader) {
      return run
    }
    return direction === 'higher'
      ? run[metric] > leader[metric]
        ? run
        : leader
      : run[metric] < leader[metric]
        ? run
        : leader
  }, undefined)
}

function percent(value) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 1,
    style: 'percent',
  }).format(value)
}

function decimal(value) {
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 3,
  }).format(value)
}

function signedDecimal(value) {
  return `${value >= 0 ? '+' : ''}${decimal(value)}`
}

function signedPercent(value) {
  return `${value >= 0 ? '+' : ''}${percent(value)}`
}

function buildRunComparison(run, runs) {
  const averageRoi = average(runs, 'roi')
  const averageBrierScore = average(runs, 'brier_score')
  const averageLogLoss = average(runs, 'log_loss')
  const averageSettledBets = average(runs, 'settled_bets')

  return {
    roiDelta: signedPercent(rounded(run.roi - averageRoi)),
    brierDelta: signedDecimal(rounded(run.brier_score - averageBrierScore)),
    logLossDelta: signedDecimal(rounded(run.log_loss - averageLogLoss)),
    settledDelta: signedDecimal(rounded(run.settled_bets - averageSettledBets)),
  }
}

function buildCrossReportRows(selectedRun, reports) {
  return reports
    .flatMap((report) => {
      const run = report.runs.find(
        (item) => item.model === selectedRun.model && item.bookmaker === selectedRun.bookmaker,
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

function buildSelectedRunInsight(rows) {
  const latest = rows[0]
  const averageSettledBets = averageCrossReportMetric(rows, 'settledBets')

  if (!latest || averageSettledBets < 300) {
    return { label: 'Noisy sample' }
  }

  const averageRoi = averageCrossReportMetric(rows, 'roi')
  const averageBrierScore = averageCrossReportMetric(rows, 'brierScore')
  const averageLogLoss = averageCrossReportMetric(rows, 'logLoss')

  if (averageRoi > 0 && latest.brierScore <= averageBrierScore && latest.logLoss <= averageLogLoss) {
    return { label: 'Strong signal' }
  }

  return { label: 'Weak signal' }
}

function averageCrossReportMetric(rows, metric) {
  if (rows.length === 0) {
    return 0
  }
  return rows.reduce((total, row) => total + row[metric], 0) / rows.length
}

function average(runs, metric) {
  if (runs.length === 0) {
    return 0
  }
  return rounded(runs.reduce((total, run) => total + run[metric], 0) / runs.length)
}

function rounded(value) {
  return Number(value.toFixed(4))
}
