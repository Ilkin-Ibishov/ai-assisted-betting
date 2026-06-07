# Task 88 - Dashboard Threshold Policy Operations

Status: planned

## Goal

Add operator-facing threshold policy controls to the dashboard without weakening the paper-only safety model.

## Requirements

- Show latest policy state, active policy values, evidence, and rollback availability.
- Add guarded approve/apply/rollback controls only after Task 87 governance is implemented.
- Require explicit reason text for mutating operations.
- Make disabled or low-sample states visually clear.
- Keep all actions paper-only; do not add real-money betting controls.

## Acceptance Criteria

- Operators can understand why a policy is advisory, proposed, approved, applied, or rolled back.
- Mutating controls call authenticated or deliberately protected backend endpoints.
- Dashboard tests cover the main states and disabled controls.
- Production smoke still proves read-only dashboard health.

## Verification

```powershell
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Use dashboard controls only after deployment proof and governance logging are in place.

