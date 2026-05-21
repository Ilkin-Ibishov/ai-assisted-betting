# Codex Task 01 — Bootstrap Project

## Goal

Create the initial Python project structure for Paper Odds Lab.

## Requirements

Create:

```text
app/
  __init__.py
  cli.py
  config.py

app/db/
app/providers/
app/normalizers/
app/core/
app/schemas/
app/services/
app/utils/

data/
  sample/
  imports/
  exports/

reports/
tests/
  unit/
  integration/
```

Create:

```text
pyproject.toml
.env.example
.gitignore
README.md
```

## Dependencies

Use:

```text
typer
pydantic
sqlalchemy
python-dotenv
pytest
pandas
```

## CLI

Implement basic Typer CLI:

```bash
python -m app.cli --help
```

Commands can be placeholders initially:

```text
init-db
import-sample-data
generate-features
generate-predictions
write-paper-bets
settle-results
evaluate
```

Each placeholder should print a clear "not implemented yet" message.

## Acceptance

The following must work:

```bash
python -m app.cli --help
pytest
```

## Do Not Do

- Do not implement web dashboard during bootstrap. Dashboard work is now explicitly planned for Tasks 22-25 after the offline/replay core.
- Do not implement live scraping.
- Do not implement real betting.
