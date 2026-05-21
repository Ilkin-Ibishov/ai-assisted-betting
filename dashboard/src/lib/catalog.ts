import type { ComparisonSummary } from '@/lib/api'

export function getVisibleCatalogReports(
  comparisons: ComparisonSummary[],
  query: string,
  limit = 6,
): ComparisonSummary[] {
  const normalizedQuery = query.trim().toLowerCase()

  return comparisons
    .filter((comparison) =>
      normalizedQuery ? catalogSearchText(comparison).includes(normalizedQuery) : true,
    )
    .toSorted((a, b) => Date.parse(b.modified_at) - Date.parse(a.modified_at))
    .slice(0, limit)
}

function catalogSearchText(comparison: ComparisonSummary): string {
  return [
    comparison.name,
    comparison.filename,
    comparison.league,
    comparison.season,
    ...comparison.models,
    ...comparison.bookmakers,
  ]
    .filter((value): value is string => Boolean(value))
    .join(' ')
    .toLowerCase()
}
