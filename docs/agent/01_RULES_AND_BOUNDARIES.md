# Rules And Boundaries

## Product Scope

- Football only for the MVP.
- Pre-match only.
- Paper betting only.
- SQLite local database.
- CLI-first workflow.
- Deterministic sample provider before any live provider.

## Safety Boundary

Never implement:

- Real-money betting.
- Deposit, withdrawal, payment, or balance flows.
- Bookmaker account automation.
- CAPTCHA bypass.
- Cloudflare or anti-bot bypass.
- Browser fingerprint evasion.
- Stealth browser automation.
- Proxy rotation for evasion.
- Protected/private endpoint scraping without permission.
- Martingale, loss recovery, or aggressive staking systems.

Safe alternatives:

- Official APIs.
- Public CSV files.
- Manually imported files.
- Historical datasets.
- Paper simulation.
- Local reports.

## Engineering Rules

- Core logic must not depend on provider implementations.
- Providers return raw data; normalizers convert it; repositories write it.
- Commands must be idempotent where practical.
- Decision logging is mandatory for each major step.
- Tests must run offline.
- The baseline model must stay explainable and deterministic.

