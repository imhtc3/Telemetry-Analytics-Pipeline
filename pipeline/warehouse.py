"""Star-schema warehouse in SQLite: one fact table + dimension tables."""
import sqlite3

import pandas as pd

DDL = """
DROP TABLE IF EXISTS fact_events;
DROP TABLE IF EXISTS dim_user;
DROP TABLE IF EXISTS dim_platform;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_user     (user_key INTEGER PRIMARY KEY, user_id TEXT UNIQUE NOT NULL);
CREATE TABLE dim_platform (platform_key INTEGER PRIMARY KEY, platform TEXT, region TEXT,
                           app_version TEXT, UNIQUE(platform, region, app_version));
CREATE TABLE dim_date     (date_key INTEGER PRIMARY KEY, date TEXT, day_of_week TEXT, week INTEGER);

CREATE TABLE fact_events (
    event_id     TEXT PRIMARY KEY,
    user_key     INTEGER REFERENCES dim_user(user_key),
    platform_key INTEGER REFERENCES dim_platform(platform_key),
    date_key     INTEGER REFERENCES dim_date(date_key),
    event_type   TEXT NOT NULL,
    latency_ms   REAL,
    event_ts     TEXT NOT NULL
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_fact_date_type ON fact_events(date_key, event_type)",
    "CREATE INDEX IF NOT EXISTS ix_fact_user ON fact_events(user_key)",
    "CREATE INDEX IF NOT EXISTS ix_fact_type_platform ON fact_events(event_type, platform_key, latency_ms)",
]


def transform(clean: pd.DataFrame) -> dict:
    """Split clean events into dimension tables and a fact table with surrogate keys."""
    df = clean.copy()
    df["event_ts"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df["date"] = df["event_ts"].dt.strftime("%Y-%m-%d")
    df["date_key"] = df["event_ts"].dt.strftime("%Y%m%d").astype(int)

    dim_user = df[["user_id"]].drop_duplicates().reset_index(drop=True)
    dim_user["user_key"] = dim_user.index + 1

    dim_platform = df[["platform", "region", "app_version"]].drop_duplicates().reset_index(drop=True)
    dim_platform["platform_key"] = dim_platform.index + 1

    dim_date = df[["date_key", "date", "event_ts"]].drop_duplicates("date_key").copy()
    dim_date["day_of_week"] = dim_date["event_ts"].dt.day_name()
    dim_date["week"] = dim_date["event_ts"].dt.isocalendar().week.astype(int)
    dim_date = dim_date.drop(columns="event_ts")

    fact = (df.merge(dim_user, on="user_id")
              .merge(dim_platform, on=["platform", "region", "app_version"]))
    fact["event_ts"] = fact["event_ts"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    fact = fact[["event_id", "user_key", "platform_key", "date_key",
                 "event_type", "latency_ms", "event_ts"]]
    return {"dim_user": dim_user, "dim_platform": dim_platform,
            "dim_date": dim_date, "fact_events": fact}


def load(tables: dict, conn: sqlite3.Connection, with_indexes: bool = True) -> None:
    conn.executescript(DDL)
    for name in ["dim_user", "dim_platform", "dim_date", "fact_events"]:
        tables[name].to_sql(name, conn, if_exists="append", index=False)
    if with_indexes:
        create_indexes(conn)
    conn.commit()


def create_indexes(conn: sqlite3.Connection) -> None:
    for stmt in INDEXES:
        conn.execute(stmt)
    conn.execute("ANALYZE")
    conn.commit()
