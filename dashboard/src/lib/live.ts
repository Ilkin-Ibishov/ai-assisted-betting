import type { LiveStatus } from '@/lib/api'

export type LiveProcessSummary = {
  statusLabel: string
  statusTone: 'neutral' | 'positive' | 'negative' | 'running'
  latestRunLabel: string
  providerLabel: string
  countersLabel: string
  errorLabel: string
  openBetsLabel: string
  settledBetsLabel: string
}

export function buildLiveProcessSummary(status?: LiveStatus): LiveProcessSummary {
  if (!status?.latest_run) {
    return {
      statusLabel: 'No live runs yet',
      statusTone: 'neutral',
      latestRunLabel: 'Waiting for first collection',
      providerLabel: 'Provider unavailable',
      countersLabel: '0 read / 0 created / 0 skipped',
      errorLabel: 'No recorded live errors',
      openBetsLabel: '0 open',
      settledBetsLabel: '0 settled',
    }
  }

  const latestRun = status.latest_run
  return {
    statusLabel: statusLabel(latestRun.status),
    statusTone: statusTone(latestRun.status),
    latestRunLabel: `${latestRun.run_type} / ${latestRun.run_id}`,
    providerLabel: [latestRun.provider, latestRun.league, latestRun.season]
      .filter(Boolean)
      .join(' / '),
    countersLabel: `${latestRun.items_read} read / ${latestRun.items_created} created / ${latestRun.items_skipped} skipped`,
    errorLabel:
      latestRun.errors_count > 0
        ? `${latestRun.errors_count} errors: ${latestRun.error_summary ?? 'No summary'}`
        : 'No errors in latest run',
    openBetsLabel: `${status.open_paper_bets} open`,
    settledBetsLabel: `${status.settled_paper_bets} settled`,
  }
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
