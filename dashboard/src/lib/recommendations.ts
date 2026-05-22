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
  const gradeOptions = uniqueSorted(recommendations.map((item) => item.grade))
  const marketOptions = uniqueSorted(recommendations.map((item) => item.market))
  const approvalMatches =
    filters.approvalState === 'all' || filters.approvalState === approvalState

  const rows = approvalMatches
    ? recommendations
        .map((recommendation) => {
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
        .filter((row) => rowMatchesFilters(row, filters))
        .toSorted((a, b) => {
          const bValue = b.expected_value ?? Number.NEGATIVE_INFINITY
          const aValue = a.expected_value ?? Number.NEGATIVE_INFINITY
          return bValue - aValue
        })
    : []

  return {
    rows,
    combinations: approvalMatches ? combinations.toSorted((a, b) => a.rank - b.rank) : [],
    gradeOptions,
    marketOptions,
    reviewLabel: review?.output.short_summary ?? 'No AI recommendation review yet',
    approvalState,
    topRiskFlags: review?.output.risk_flags ?? ['recommendation_review_missing'],
  }
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
  if (filters.grade !== 'all' && row.grade !== filters.grade) {
    return false
  }
  if (filters.market !== 'all' && row.market !== filters.market) {
    return false
  }
  return confidenceMatches(row.confidence_score, filters.confidence)
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
