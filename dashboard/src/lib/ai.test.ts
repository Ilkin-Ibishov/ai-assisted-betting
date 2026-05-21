import { describe, expect, it } from 'vitest'
import type { AIAnalysisRun } from '@/lib/api'
import { buildAIAdvisorySummary } from '@/lib/ai'

describe('buildAIAdvisorySummary', () => {
  it('returns a clear empty advisory state', () => {
    expect(buildAIAdvisorySummary(null)).toEqual({
      label: 'AI-assisted advisory analysis',
      headline: 'No AI advisory yet',
      rootCause: 'Run analyze-live-status to create the first auditable advisory note.',
      nextAction: 'Keep deterministic risk gates active while enabling AI assistance.',
    })
  })

  it('summarizes an existing advisory analysis', () => {
    expect(buildAIAdvisorySummary(analysis())).toEqual({
      label: 'AI-assisted advisory analysis',
      headline: 'Latest live run is completed with 1 open and 1 settled paper bets.',
      rootCause: 'The latest provider failure is caused by missing full kickoff dates.',
      nextAction: 'Resolve Misli kickoff date extraction before treating real Misli import as ready.',
    })
  })
})

function analysis(): AIAnalysisRun {
  return {
    id: 1,
    analysis_type: 'live_status_summary',
    source_type: 'live_status',
    source_id: 'run-001',
    input: {},
    output: {
      label: 'AI-assisted advisory analysis',
      short_summary: 'Latest live run is completed with 1 open and 1 settled paper bets.',
      root_cause: 'The latest provider failure is caused by missing full kickoff dates.',
      risk_flags: ['provider_datetime_missing'],
      recommended_next_actions: [
        'Resolve Misli kickoff date extraction before treating real Misli import as ready.',
      ],
      confidence: 'medium',
      source_record_ids: ['run-001'],
    },
    model_name: 'deterministic_ai_fallback',
    prompt_version: 'ai-live-status-v1',
    status: 'completed',
    error_summary: null,
    created_at: '2026-05-20T00:00:00+00:00',
  }
}
