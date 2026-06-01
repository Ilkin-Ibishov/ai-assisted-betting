import type { PaperBet } from '@/lib/api'

export type PaperBetGroups = {
  validOpenBets: PaperBet[]
  unsafeOpenBets: PaperBet[]
  settledBets: PaperBet[]
}

export function groupPaperBets(paperBets: PaperBet[]): PaperBetGroups {
  return paperBets.reduce<PaperBetGroups>(
    (groups, bet) => {
      if (bet.status !== 'open') {
        groups.settledBets.push(bet)
      } else if (bet.is_valid_open) {
        groups.validOpenBets.push(bet)
      } else {
        groups.unsafeOpenBets.push(bet)
      }

      return groups
    },
    { validOpenBets: [], unsafeOpenBets: [], settledBets: [] },
  )
}

export function paperBetRiskSummary(flags: string[]): string {
  const visibleFlags = flags.filter((flag) => flag !== 'no_current_risk_flags')

  if (!visibleFlags.length) {
    return 'No current risk flags'
  }

  return visibleFlags.map(formatRiskFlag).join(', ')
}

function formatRiskFlag(flag: string): string {
  return flag
    .split('_')
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(' ')
}
