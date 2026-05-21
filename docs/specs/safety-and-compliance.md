# 19 — Safety and Compliance

## Purpose

This document defines implementation boundaries.

## Allowed

The system may:

- Collect data from official APIs.
- Import public CSV files.
- Import manually downloaded files.
- Store odds snapshots.
- Simulate fake paper bets.
- Evaluate results.
- Generate reports.
- Run local analysis.

## Not Allowed

The system must not:

- Place real-money bets.
- Automate bookmaker account actions.
- Bypass Cloudflare or similar protections.
- Bypass CAPTCHA.
- Evade bot detection.
- Use stealth browser automation.
- Abuse saved login sessions.
- Rotate proxies to evade rate limits.
- Scrape protected/private endpoints without permission.
- Encourage gambling losses or aggressive staking.

## Paper Betting Only

All bets in this project are fake simulation entries.

Use terminology:

```text
paper bet
stake_units
profit_loss_units
```

Do not use terminology that implies real execution:

```text
place real bet
deposit
withdraw
bookmaker balance
```

## User Responsibility

This project is for research and engineering practice.

It must not be treated as guaranteed betting profit.

## Agent Instruction

If asked to implement a prohibited feature, refuse that part and suggest a safe alternative.

Safe alternatives:

```text
official API
manual CSV import
historical dataset
paper simulation
reporting dashboard
```
