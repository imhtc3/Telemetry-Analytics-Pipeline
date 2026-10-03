# Telemetry Analytics Pipeline

An end-to-end ETL pipeline that turns raw, messy app telemetry into a clean star-schema warehouse, with automated data-quality checks and measured query optimization.

## What it does

```
raw events  ->  validate  ->  transform  ->  load (SQLite)  ->  index + benchmark  ->  SQL reports
(1M rows)      (dedupe +      (star          fact_events +      before/after
               4 checks)      schema)        3 dimensions)      timings
```

1. **Generate**: creates realistic app events (opens, clicks, API calls, errors) with injected problems: missing user IDs, malformed timestamps, unknown event types, negative latencies, and duplicate deliveries.
2. **Validate** (`pipeline/quality.py`): schema check, deduplication on `event_id`, and four row-level checks. Bad rows are rejected and counted in a quality report.
3. **Transform** (`pipeline/warehouse.py`): splits clean events into `fact_events` plus `dim_user`, `dim_platform` and `dim_date`, with surrogate keys.
4. **Load + optimize**: loads the warehouse, benchmarks three analytical queries, adds composite indexes, and benchmarks again.
5. **Report** (`sql/reports.sql`): daily active users, error rate by app version, API latency by region.

## Results (1,000,000 events)

| Metric | Result |
| --- | --- |
| Rows received | 1,015,000 |
| Duplicates removed | 15,000 |
| Bad rows rejected | 30,000 (null keys, bad timestamps, unknown events, invalid latency) |
| Rows loaded | 970,000 |
| Errors-on-one-day query | 55 ms -> 0.04 ms after indexing |
| Single-user activity query | 47 ms -> 0.06 ms |
| Latency-by-platform aggregate | 141 ms -> 18 ms (covering index) |
| End-to-end runtime | ~26 s |

Timings vary by machine; run it yourself to get your numbers.

## Run it

```bash
pip install -r requirements.txt
python run_pipeline.py --events 1000000      # full run
python -m unittest discover -s tests -v       # 8 tests
python -c "import sqlite3; c=sqlite3.connect('telemetry.db'); print(c.execute(open('sql/reports.sql').read().split(';')[0]).fetchall()[:5])"
```

Or with Docker: `docker build -t telemetry . && docker run telemetry`

## Design decisions

- **Star schema**: dimensions keep the fact table narrow and make GROUP BY reports simple.
- **Validate before load**: bad data never reaches the warehouse, and every rejection is counted, so data loss is visible rather than silent.
- **Composite indexes chosen from the queries**: `(date_key, event_type)` serves dashboard filters; `(event_type, platform_key, latency_ms)` is a covering index for the latency aggregate.
- **SQLite** keeps it runnable anywhere; the same DDL ports to PostgreSQL or Azure SQL.


