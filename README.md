# boditrax-sync

Unofficial CLI to download [Boditrax](https://www.boditrax.com/) 2.0 body-composition scans and
export them as JSON or CSV, or sync them into PostgreSQL or SQLite.

> **This is a reverse-engineering project.** boditrax-sync was built by reverse-engineering the
> private mobile API used by the official Boditrax 2.0 app (see
> [How it works](#how-it-works-reverse-engineering)). It is not affiliated with, endorsed by, or
> supported by Boditrax, and the API may change or stop working at any time. Use it on your own
> account, at your own risk.

Boditrax offers no public API and no practical export of your scan history. This tool signs in to
your own Boditrax account through the same mobile API the official app uses, pulls every reading,
and hands you the data: weight, fat/muscle mass per body segment, phase angles, visceral fat,
blood pressure, cholesterol, metabolic age, and more (34+ metrics per scan).

[![CI](https://github.com/iniTwakkie/boditrax-sync/actions/workflows/ci.yml/badge.svg)](https://github.com/iniTwakkie/boditrax-sync/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

## Features

- Full scan history in one command, no browser or scraping: talks directly to the mobile API
  (`mobile.api.boditrax.cloud`) over gRPC-web with the app's own OAuth flow
- Export to JSON, wide-format CSV (one row per scan, one column per metric), or a compact
  terminal table
- Idempotent sync into PostgreSQL or SQLite: repeat runs are safe and pick up edits made in the
  app
- Zero configuration beyond your Boditrax login; credentials stored with owner-only permissions

## Install

Not on PyPI yet; install straight from GitHub with [pipx](https://pipx.pypa.io/) or
[uv](https://docs.astral.sh/uv/):

```bash
pipx install "git+https://github.com/iniTwakkie/boditrax-sync"                 # exports only
pipx install "git+https://github.com/iniTwakkie/boditrax-sync[postgres]"       # + PostgreSQL
```

or:

```bash
uv tool install "git+https://github.com/iniTwakkie/boditrax-sync"
```

Python 3.10+ is required.

## Usage

```bash
boditrax-sync login                  # prompts for your Boditrax email and password
boditrax-sync fetch                  # terminal table of every scan
boditrax-sync fetch --format json -o scans.json
boditrax-sync fetch --format csv -o scans.csv
boditrax-sync fetch -o scans.csv     # format inferred from the file suffix
```

`login` verifies the credentials against the API before saving them, so you find out immediately
if they are wrong.

### Terminal output

```
Date        Weight kg  Muscle kg  Fat kg  Visceral  BMI   Meta age  Score
2024-04-06  101.5      78.3       19.2    6         27    27        801
2024-06-23  104.6      78.6       22      7         27.8  33        738
...
```

### CSV

Wide format, one row per reading, one column per metric in `BodyMetricTypeId` order (the same
metric names the app's own CSV export uses). Metrics not present on a given scan are left blank.

### JSON

```json
[
  {
    "reading_id": "a1b2c3...",
    "recorded_at": "2026-01-10T09:15:00+00:00",
    "kiosk_id": "0143d4...",
    "device_type_id": 7,
    "reading_type_id": 1,
    "metrics": {
      "BodyWeight": 101.0,
      "MuscleMass": 74.9,
      "FatMass": 22.2,
      "VisceralFatRating": 8.0
    }
  }
]
```

## Sync to a database

```bash
# SQLite (no server needed)
boditrax-sync sync --db-url sqlite:///home/me/boditrax.db

# PostgreSQL (needs the postgres extra)
boditrax-sync sync --db-url postgresql://user:pass@localhost:5432/health

# Preview without writing
boditrax-sync sync --db-url sqlite:///boditrax.db --dry-run
```

Both backends create a self-contained two-table schema: a `boditrax` schema in PostgreSQL
(`boditrax.readings`, `boditrax.metrics`), or plain `readings`/`metrics` tables in SQLite.
Every run re-fetches all readings and upserts them, so scheduling it daily (or hourly) is safe:

```cron
0 7 * * *  /home/me/.local/bin/boditrax-sync sync --db-url sqlite:///home/me/boditrax.db
```

Query example:

```sql
SELECT r.recorded_at, m.value
FROM boditrax.readings r
JOIN boditrax.metrics m USING (reading_id)
WHERE m.metric = 'BodyWeight'
ORDER BY r.recorded_at;
```

## Configuration

Credentials are resolved from the environment first, then from
`~/.config/boditrax-sync/credentials.json` (written by `login`, mode 600).

| Variable | Purpose |
| --- | --- |
| `BODITRAX_USERNAME`, `BODITRAX_PASSWORD` | account credentials (override the file) |
| `BODITRAX_CREDENTIALS` | alternative credentials file path |
| `BODITRAX_DB_URL` | default `--db-url` for `sync` |
| `BODITRAX_CLIENT_SECRET` | override the embedded app client secret |
| `BODITRAX_CONFIG_DIR` | alternative config directory |

Timestamps are gym-local. The default timezone is `Europe/London`; override with
`--timezone`, e.g. `--timezone Europe/Berlin`.

## Metrics

<details>
<summary>All metrics captured per scan</summary>

| Metric | Unit |
| --- | --- |
| BodyWeight | kg |
| FatPercentage | % |
| FatMass | kg |
| FatFreeMass | kg |
| MuscleMass | kg |
| MuscleScore | score |
| BoneMass | kg |
| WaterMass | kg |
| BodyMassIndex | bmi |
| VisceralFatRating | rating |
| BasalMetabolicRatekJ | kJ |
| BmrScore | score |
| MetabolicAge | years |
| Age | years |
| Height | cm |
| LegMuscleScore | score |
| ExtraCellularWaterMass | kg |
| IntraCellularWaterMass | kg |
| TrunkFatMass | kg |
| TrunkMuscleMass | kg |
| LeftArmFatMass / RightArmFatMass | kg |
| LeftArmMuscleMass / RightArmMuscleMass | kg |
| LeftLegFatMass / RightLegFatMass | kg |
| LeftLegMuscleMass / RightLegMuscleMass | kg |
| RightLegMuscleMassScore | score |
| PhaseAngleLeftArm / PhaseAngleRightArm | degrees |
| PhaseAngleLeftLeg / PhaseAngleRightLeg | degrees |
| PhaseAngleRightLegLeftLeg | degrees |
| PhaseAngleLeftLegLeftArm | degrees |
| PhaseAngleRightLegRightArm | degrees |
| RestingHeartRate | bpm |
| SystolicPressure / DiastolicPressure | mmHg |
| SarcopeniaSMI / SarcopeniaASMBW | score |
| Protein | kg |
| Gender | code |
| HDLLevel / LDLLevel / TotalCholesterol / NonHDLLevel | mmol/L |
| Triglycerides | mmol/L |
| TotalCholesterolHDL | ratio |
| BoditraxScore | score |

</details>

## How it works (reverse engineering)

The Boditrax 2.0 app speaks gRPC-web to `mobile.api.boditrax.cloud`. The protocol here was
reverse-engineered from app version 3.1.1 for interoperability (exporting your own data from your
own account) and verified against the app's own CSV export (340/340 values identical,
2026-10-14). No Boditrax software or binaries are included in or redistributed by this
repository; everything here is original code written against the observed protocol.
Authentication is the app's OAuth password grant (client id `boditrax.mobile.app`; the client
secret embedded in this tool is the one shipped in the public mobile app, not a user secret).
The tool fetches all readings via `SyncLoginService/Get` and maps each `BodyMetricTypeId` to the
metric names above.

## Disclaimer

This project is an unaffiliated, unofficial reverse-engineering effort and is not endorsed by or
supported by Boditrax. The API it targets is private and undocumented; Boditrax may change,
rotate, or block it at any time and this tool may stop working. It exists purely for
interoperability: retrieving and storing your own scan data from your own account. Use it at
your own risk, and review Boditrax's terms of service before using it. Never share your
credentials or a database containing your health data.

## Development

```bash
uv sync --all-extras
uv run ruff check .
uv run pytest                       # unit tests, SQLite integration
BODITRAX_TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/boditrax_test \
    uv run pytest                    # also runs the PostgreSQL integration test
```

## License

[MIT](LICENSE)
