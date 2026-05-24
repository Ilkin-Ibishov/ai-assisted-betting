# Misli.az Public Discovery

Discovery date: 2026-05-19  
Timezone: Asia/Baku  
Status: feasible for a guarded public snapshot prototype

## Scope

Inspected only public, unauthenticated pages:

```text
https://www.misli.az/
https://www.misli.az/idman-novleri/futbol
```

The project boundary still blocks:

```text
login/account automation
CAPTCHA or bot bypass
proxy or stealth evasion
real bet placement
disallowed account or protected bookmaker paths
```

## Findings

The football page renders public pre-match event rows in the DOM.

Observed stable row anchors:

```text
.bulletinItemRow
data-event-id
.bulletinDate
.bulletinHomeTeam
.bulletinAwayTeam
.odssRate
.oddValue
```

Observed public fields:

```text
event id
sport route
home team
away team
kickoff time label
league tooltip
public event detail link
1X2 odds by rendered column order
raw row text
```

Current prototype:

```powershell
node tools\misli-public-snapshot.mjs --out data\misli-public-snapshot.sample.json
```

The script writes a JSON snapshot like:

```json
{
  "source": "misli_public",
  "page_url": "https://www.misli.az/idman-novleri/futbol",
  "event_count": 28,
  "events": [
    {
      "source_match_id": "misli:football:2816300",
      "home_team": "Rid",
      "away_team": "Volfsberq",
      "kickoff_time": "20:30",
      "odds": [
        {"market": "1X2", "selection": "HOME", "odds_decimal": 2.16},
        {"market": "1X2", "selection": "DRAW", "odds_decimal": 3.18},
        {"market": "1X2", "selection": "AWAY", "odds_decimal": 2.94}
      ]
    }
  ]
}
```

## Task 47 Date Evidence

Task 47 reran the public football snapshot on 2026-05-20:

```powershell
node tools\misli-public-snapshot.mjs --out data\misli-public-snapshot.task47.json
```

The rendered page still leaves `kickoff_date` blank in raw rows, but many rows include relative date labels inside `kickoff_time`, such as:

```text
Bu Gün 23:00
Sabah 02:00
```

The provider now resolves only high-confidence relative labels against `scraped_at` in the `Asia/Baku` timezone:

```text
Bu Gün HH:MM -> scraped_at local date
Sabah HH:MM -> scraped_at local date + 1 day
bare HH:MM -> resolve to snapshot scraped_at local date
```

Task 47 scratch import evidence:

```text
events read: 21
matches created: 20
matches skipped: 1
match errors: 1
odds created: 60
```

Task 69 changed this after production proof showed current upcoming-event pages can include bare time rows. The provider now resolves bare `HH:MM` to the snapshot `scraped_at` local date.

## Limitations

- The snapshot uses rendered DOM selectors, so frontend class churn can break collection.
- In headless Playwright, 1X2 labels may be hidden while values remain visible; the prototype maps the first three odds columns to HOME, DRAW, AWAY.
- Public rows can now resolve `Bu Gün`, `Sabah`, and bare `HH:MM` labels against trusted snapshot `scraped_at`; rendered date-group extraction remains a stronger future improvement.
- The current tool collects a snapshot only; it does not import into SQLite or join against results.
- Event detail pages were not scraped during discovery.

## Next

Task 38 formalized provider capability metadata and raw DTOs for this snapshot shape in:

```text
app/providers/base.py
app/providers/misli_public.py
tests/unit/test_live_provider_contract.py
```

Task 40 should add a manual collection command that runs the public snapshot tool, validates the JSON, and imports matches plus 1X2 odds through normalizers and repositories.
