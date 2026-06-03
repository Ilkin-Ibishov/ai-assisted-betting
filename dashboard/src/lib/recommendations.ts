import type {
  AIAnalysisRun,
  OddsMovementSummary,
  PaperCombination,
  PaperRecommendation,
} from '@/lib/api'

export type RecommendationFilters = {
  grade: string
  market: string
  confidence: 'all' | 'high' | 'medium' | 'low'
  approvalState: 'all' | 'approve' | 'caution' | 'reject'
}

export type RecommendationRow = PaperRecommendation & {
  movement_direction?: OddsMovementSummary['movement_direction']
  league?: string
  match_label?: string
}

export type RecommendationDashboardSummary = {
  rows: RecommendationRow[]
  combinations: PaperCombination[]
  gradeOptions: string[]
  marketOptions: string[]
  reviewLabel: string
  approvalState: 'approve' | 'caution' | 'reject' | 'missing'
  topRiskFlags: string[]
  actionableCount: number
  watchlistCount: number
  blockedCount: number
  decisionState: 'candidate_ready' | 'blocked_by_risk' | 'empty'
  latestRecommendationAt?: string
}

export function buildRecommendationDashboardSummary({
  combinations,
  filters,
  movements,
  recommendations,
  review,
}: {
  combinations: PaperCombination[]
  filters: RecommendationFilters
  movements: OddsMovementSummary[]
  recommendations: PaperRecommendation[]
  review?: AIAnalysisRun | null
}): RecommendationDashboardSummary {
  const approvalState = review?.output.approval_state ?? 'missing'
  const movementByKey = new Map(movements.map((movement) => [movementKey(movement), movement]))
  const currentRecommendations = latestRecommendationsByMarketLeg(recommendations)
  const gradeOptions = uniqueSorted(currentRecommendations.map((item) => item.grade))
  const marketOptions = uniqueSorted(currentRecommendations.map((item) => item.market))
  const approvalMatches =
    filters.approvalState === 'all' || filters.approvalState === approvalState
  const enrichedRows = currentRecommendations.map((recommendation) => {
    const movement = movementByKey.get(recommendationKey(recommendation))
    return {
      ...recommendation,
      league: movement?.league,
      match_label: movement
        ? `${movement.home_team} vs ${movement.away_team}`
        : recommendation.source_match_id,
      movement_direction: movement?.movement_direction,
    }
  })
  const actionableRows = enrichedRows.filter(isActionableRecommendation)
  const watchlistRows = enrichedRows.filter(isWatchlistRecommendation)
  const actionableIds = new Set(actionableRows.map((row) => row.id))
  const effectiveFilters = {
    ...filters,
    grade:
      filters.grade === 'auto'
        ? actionableRows.length
          ? 'actionable'
          : 'watchlist'
        : filters.grade,
  }
  const approvalAllowsCandidate = approvalState === 'approve' || approvalState === 'caution'
  const latestRecommendationAt = currentRecommendations
    .map((recommendation) => recommendation.created_at)
    .toSorted((a, b) => b.localeCompare(a))[0]

  const rows = approvalMatches
    ? enrichedRows
        .filter((row) => rowMatchesFilters(row, effectiveFilters))
        .toSorted((a, b) => {
          const bValue = b.expected_value ?? Number.NEGATIVE_INFINITY
          const aValue = a.expected_value ?? Number.NEGATIVE_INFINITY
          return bValue - aValue
        })
    : []

  return {
    rows,
    combinations: approvalMatches
      ? combinations
          .filter((combination) =>
            combinationMatchesFilters(combination, effectiveFilters, actionableIds),
          )
          .toSorted((a, b) => a.rank - b.rank)
      : [],
    gradeOptions,
    marketOptions,
    reviewLabel: review?.output.short_summary ?? 'No AI recommendation review yet',
    approvalState,
    topRiskFlags: review?.output.risk_flags ?? ['recommendation_review_missing'],
    actionableCount: actionableRows.length,
    watchlistCount: watchlistRows.length,
    blockedCount: currentRecommendations.length - actionableRows.length,
    decisionState: approvalAllowsCandidate && actionableRows.length
      ? 'candidate_ready'
      : currentRecommendations.length
        ? 'blocked_by_risk'
        : 'empty',
    latestRecommendationAt,
  }
}

function combinationMatchesFilters(
  combination: PaperCombination,
  filters: RecommendationFilters,
  actionableIds: Set<number>,
) {
  if (filters.grade === 'actionable') {
    return (
      combination.status === 'active' &&
      combination.leg_recommendation_ids.length > 0 &&
      combination.leg_recommendation_ids.every((id) => actionableIds.has(id)) &&
      combination.combined_expected_value > 0 &&
      !combination.risk_flags.some(isBlockingRiskFlag)
    )
  }
  if (filters.grade !== 'all' && combination.grade !== filters.grade) {
    return false
  }
  return true
}

export function riskBadgeTone(flag: string): 'neutral' | 'positive' | 'warning' | 'danger' {
  if (flag === 'no_current_risk_flags') {
    return 'positive'
  }
  if (
    flag.includes('reject') ||
    flag.includes('missing') ||
    flag.includes('failed') ||
    flag.includes('provider')
  ) {
    return 'danger'
  }
  if (flag.includes('low') || flag.includes('heuristic') || flag.includes('stale')) {
    return 'warning'
  }
  return 'neutral'
}

function rowMatchesFilters(row: RecommendationRow, filters: RecommendationFilters) {
  if (filters.grade === 'watchlist') {
    return isWatchlistRecommendation(row)
  }
  if (filters.grade === 'actionable') {
    if (!isActionableRecommendation(row)) {
      return false
    }
  } else if (filters.grade !== 'all' && row.grade !== filters.grade) {
    return false
  }
  if (filters.market !== 'all' && row.market !== filters.market) {
    return false
  }
  return confidenceMatches(row.confidence_score, filters.confidence)
}

function latestRecommendationsByMarketLeg(recommendations: PaperRecommendation[]) {
  const latestByKey = new Map<string, PaperRecommendation>()
  for (const recommendation of recommendations) {
    const key = recommendationKey(recommendation)
    const current = latestByKey.get(key)
    if (!current || compareRecommendationFreshness(recommendation, current) > 0) {
      latestByKey.set(key, recommendation)
    }
  }
  return Array.from(latestByKey.values())
}

function compareRecommendationFreshness(
  left: PaperRecommendation,
  right: PaperRecommendation,
) {
  const snapshotComparison = left.latest_snapshot_time.localeCompare(right.latest_snapshot_time)
  if (snapshotComparison !== 0) {
    return snapshotComparison
  }
  return left.created_at.localeCompare(right.created_at)
}

function isActionableRecommendation(row: RecommendationRow) {
  return (
    row.status === 'active' &&
    (row.grade === 'recommended' || row.grade === 'lean') &&
    (row.expected_value ?? Number.NEGATIVE_INFINITY) > 0 &&
    !row.risk_flags.some(isBlockingRiskFlag)
  )
}

function isWatchlistRecommendation(row: RecommendationRow) {
  return (
    row.status === 'active' &&
    (row.expected_value ?? Number.NEGATIVE_INFINITY) > 0 &&
    !isActionableRecommendation(row) &&
    !row.risk_flags.some(isHardBlockingRiskFlag)
  )
}

function isBlockingRiskFlag(flag: string) {
  return [
    'negative_expected_value',
    'missing_prediction',
    'stale_odds',
    'missing_outcome',
    'provider_health_warning',
    'edge_below_threshold',
    'low_confidence',
  ].includes(flag)
}

function isHardBlockingRiskFlag(flag: string) {
  return [
    'negative_expected_value',
    'missing_prediction',
    'stale_odds',
    'missing_outcome',
    'provider_health_warning',
    'edge_below_threshold',
  ].includes(flag)
}

function confidenceMatches(value: number | null, filter: RecommendationFilters['confidence']) {
  if (filter === 'all') {
    return true
  }
  if (value === null) {
    return filter === 'low'
  }
  if (filter === 'high') {
    return value >= 0.7
  }
  if (filter === 'medium') {
    return value >= 0.6 && value < 0.7
  }
  return value < 0.6
}

function recommendationKey(recommendation: PaperRecommendation) {
  return [
    recommendation.source_match_id,
    recommendation.bookmaker,
    recommendation.market,
    recommendation.selection,
  ].join('::')
}

function movementKey(movement: OddsMovementSummary) {
  return [
    movement.source_match_id,
    movement.bookmaker,
    movement.market,
    movement.selection,
  ].join('::')
}

function uniqueSorted(values: string[]) {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b))
}
