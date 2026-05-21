import { describe, expect, it } from 'vitest'
import { buildApiUrl } from '@/lib/api'

describe('buildApiUrl', () => {
  it('keeps relative API paths when no deployed API base is configured', () => {
    expect(buildApiUrl('/api/health', '')).toBe('/api/health')
  })

  it('prefixes API paths with the deployed API base URL', () => {
    expect(buildApiUrl('/api/health', 'https://paper-odds-api.up.railway.app/')).toBe(
      'https://paper-odds-api.up.railway.app/api/health',
    )
  })
})
