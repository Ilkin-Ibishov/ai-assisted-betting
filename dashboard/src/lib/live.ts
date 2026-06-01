import type { LiveStatus, ResultFetchJobsResponse } from '@/lib/api'

export type LiveProcessSummary = {
  statusLabel: string
  statusTone: 'neutral' | 'positive' | 'negative' | 'running'
  latestRunLabel: string
  providerLabel: string
  countersLabel: string
  totalErrorsLabel: string
  errorLabel: string
  openBetsLabel: string
  settledBetsLabel: string
}

export type ResultPipelineSummary = {
  statusLabel: string
  statusTone: 'neutral' | 'positive' | 'negative' | 'running'
  dueLabel: string
  completedLabel: string
  pendingLabel: string
  failureLabel: string
  latestJobLabel: string
  latestJobHelper: string
}

export function buildLiveProcessSummary(status?: LiveStatus): LiveProcessSummary {
  if (!status?.latest_run) {
    return {
      statusLabel: 'No live runs yet',
      statusTone: 'neutral',
      latestRunLabel: 'Waiting for first collection',
      providerLabel: 'Provider unavailable',
      countersLabel: '0 read / 0 created / 0 skipped',
      totalErrorsLabel: '0 historical',
      errorLabel: 'No recorded live errors',
      openBetsLabel: '0 open',
      settledBetsLabel: '0 settled',
    }
  }

  const latestRun = status.latest_run
  return {
    statusLabel: statusLabel(latestRun.status),
    statusTone: statusTone(latestRun.status),
    latestRunLabel: runTypeLabel(latestRun.run_type),
    providerLabel: [latestRun.provider, latestRun.model_name ?? latestRun.league, latestRun.season]
      .filter(Boolean)
      .join(' / '),
    countersLabel: `${latestRun.items_read} read / ${latestRun.items_created} created / ${latestRun.items_skipped} skipped`,
    totalErrorsLabel: `${status.errors_count} historical`,
    errorLabel:
      latestRun.errors_count > 0
        ? `${latestRun.errors_count} errors: ${latestRun.error_summary ?? 'No summary'}`
        : status.errors_count > 0
          ? 'Latest run clean'
          : 'No recorded live errors',
    openBetsLabel: `${status.open_paper_bets} open`,
    settledBetsLabel: `${status.settled_paper_bets} settled`,
  }
}

export function buildResultPipelineSummary(
  response?: ResultFetchJobsResponse,
): ResultPipelineSummary {
  if (!response || response.summary.total === 0) {
    return {
      statusLabel: 'No result jobs',
      statusTone: 'neutral',
      dueLabel: '0 due',
      completedLabel: '0 completed',
      pendingLabel: '0 pending',
      failureLabel: '0 failed',
      latestJobLabel: 'Waiting for tracked matches',
      latestJobHelper: 'No Misli result follow-up queue yet',
    }
  }

  const latestJob = response.jobs[0]
  const hasFailures = response.summary.failed > 0
  const hasDue = response.summary.due > 0
  return {
    statusLabel: hasFailures
      ? 'Result fetch needs review'
      : hasDue
        ? 'Result jobs due'
        : 'Result queue healthy',
    statusTone: hasFailures ? 'negative' : hasDue ? 'running' : 'positive',
    dueLabel: `${response.summary.due} due`,
    completedLabel: `${response.summary.completed} completed`,
    pendingLabel: `${response.summary.pending + response.summary.postponed} waiting`,
    failureLabel: `${response.summary.failed} failed`,
    latestJobLabel: latestJob?.match_label ?? 'No queued match',
    latestJobHelper: latestJob
      ? `${latestJob.status} / next ${formatShortDate(latestJob.next_attempt_at)}`
      : 'No Misli result follow-up queue yet',
  }
}

function runTypeLabel(runType: string) {
  return runType.replaceAll('_', ' ')
}

function statusLabel(status: string) {
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

function statusTone(status: string): LiveProcessSummary['statusTone'] {
  if (status === 'completed') {
    return 'positive'
  }
  if (status === 'failed') {
    return 'negative'
  }
  if (status === 'running') {
    return 'running'
  }
  return 'neutral'
}

function formatShortDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'unknown'
  }
  return new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
  }).format(date)
}
