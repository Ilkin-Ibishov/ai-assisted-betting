# 20 — Next Steps for Codex Agent

## Immediate Execution Order

Implement in this exact order:

```text
1. Bootstrap project
2. Database layer
3. Sample provider
4. Feature builder
5. Prediction engine
6. Value detector
7. Paper bet logger
8. Result settler
9. Evaluator
10. Full integration test
```

## Do Not Skip

Do not skip sample provider.

The project must work offline before any live provider is added.

## First Milestone

A complete offline demo must work:

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
python -m app.cli settle-results
python -m app.cli evaluate
```

## Definition of Done

The first milestone is done when:

```text
- all commands run
- DB has all expected tables
- sample data is imported
- predictions are generated
- paper bets are written
- paper bets are settled
- evaluation report is printed
- pytest passes
```

## After First Milestone

Only after the offline demo is stable:

```text
1. Add ManualCSVProvider
2. Add HistoricalCSVProvider
3. Add ReplayProvider
4. Add safe LiveAPIProvider
```

## Important

Do not build the live scraping layer before the offline pipeline is complete.
