export type ComparisonSummary = {
  name: string
  filename: string
  league?: string | null
  season?: string | null
  models: string[]
  bookmakers: string[]
  runs: number
  modified_at: string
  total_settled_bets: number
  best_roi: number | null
  best_brier_score: number | null
  best_log_loss: number | null
  sample_size_smallest: number | null
  sample_size_largest: number | null
}

export type ComparisonAnalysis = {
  text: string
  sample_size: {
    smallest: number
    largest: number
    warning: string
  }
  interpretation: string
  next_experiment: string
}

export type ComparisonRun = {
  model: string
  bookmaker: string
  total_bets: number
  settled_bets: number
  wins: number
  losses: number
  roi: number
  profit_loss_units: number
  average_odds: number
  average_edge: number
  brier_score: number
  log_loss: number
  roi_rank?: number
  brier_score_rank?: number
  log_loss_rank?: number
  model_config?: Record<string, unknown>
}

export type ComparisonReport = {
  metadata?: Record<string, unknown>
  rankings?: Record<string, unknown>
  runs: ComparisonRun[]
  analysis?: ComparisonAnalysis
}

export type LiveRun = {
  id: number
  run_id: string
  run_type: string
  provider: string
  league?: string | null
  season?: string | null
  status: string
  started_at: string
  finished_at?: string | null
  items_read: number
  items_created: number
  items_updated: number
  items_skipped: number
  errors_count: number
  error_summary?: string | null
  model_name?: string | null
  created_at: string
}

export type LiveStatus = {
  latest_run: LiveRun | null
  latest_success: LiveRun | null
  latest_failure: LiveRun | null
  open_paper_bets: number
  settled_paper_bets: number
  runs_count: number
  errors_count: number
}

export type OddsMovementSummary = {
  match_id: number
  source: string
  source_match_id: string
  league: string
  home_team: string
  away_team: string
  kickoff_time: string
  bookmaker: string
  market: string
  selection: string
  opening_odds: number
  previous_odds: number | null
  current_odds: number | null
  latest_snapshot_time: string
  market_latest_snapshot_time: string
  movement_direction: 'new' | 'up' | 'down' | 'stable' | 'missing' | 'stale'
  status: 'active' | 'missing' | 'stale'
  is_stale: boolean
  snapshots_count: number
}

export type AIAnalysisOutput = {
  label: string
  short_summary: string
  root_cause: string
  risk_flags: string[]
  recommended_next_actions: string[]
  confidence: string
  source_record_ids: string[]
}

export type AIAnalysisRun = {
  id: number
  analysis_type: string
  source_type: string
  source_id?: string | null
  input: Record<string, unknown>
  output: AIAnalysisOutput
  model_name: string
  prompt_version: string
  status: string
  error_summary?: string | null
  created_at: string
}

export async function fetchComparisons(): Promise<ComparisonSummary[]> {
  return getJson('/api/reports/comparisons')
}

export async function fetchComparisonDetail(name: string): Promise<ComparisonReport> {
  return getJson(`/api/reports/comparisons/${encodeURIComponent(name)}`)
}

export async function fetchLiveStatus(): Promise<LiveStatus> {
  return getJson('/api/live/status')
}

export async function fetchOddsMovement(): Promise<OddsMovementSummary[]> {
  return getJson('/api/live/odds-movement')
}

export async function fetchLatestAIAnalysis(): Promise<AIAnalysisRun | null> {
  const response = await fetch(buildApiUrl('/api/ai/analysis/latest'))

  if (response.status === 404) {
    return null
  }

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<AIAnalysisRun>
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(buildApiUrl(url))

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

export function buildApiUrl(
  path: string,
  apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '',
): string {
  if (!apiBaseUrl) {
    return path
  }

  return `${apiBaseUrl.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}`
}
