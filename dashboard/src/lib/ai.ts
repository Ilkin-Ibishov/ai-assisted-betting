import type { AIAnalysisRun } from '@/lib/api'

export type AIAdvisorySummary = {
  label: string
  headline: string
  rootCause: string
  nextAction: string
}

export function buildAIAdvisorySummary(analysis?: AIAnalysisRun | null): AIAdvisorySummary {
  if (!analysis) {
    return {
      label: 'AI-assisted advisory analysis',
      headline: 'No AI advisory yet',
      rootCause: 'Run analyze-live-status to create the first auditable advisory note.',
      nextAction: 'Keep deterministic risk gates active while enabling AI assistance.',
    }
  }

  return {
    label: analysis.output.label,
    headline: analysis.output.short_summary,
    rootCause: analysis.output.root_cause,
    nextAction:
      analysis.output.recommended_next_actions[0] ??
      'Review live status and comparison reports before changing the next experiment.',
  }
}
