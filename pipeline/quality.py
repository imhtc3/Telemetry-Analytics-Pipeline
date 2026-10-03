"""Data-quality checks: each check returns a boolean mask of rows that FAIL it."""
from dataclasses import dataclass, field

import pandas as pd

from .generate import EVENT_TYPES

REQUIRED_COLUMNS = ["event_id", "user_id", "event_type", "platform",
                    "region", "app_version", "latency_ms", "timestamp"]


@dataclass
class QualityReport:
    total_rows: int = 0
    failures: dict = field(default_factory=dict)
    duplicates_removed: int = 0
    rows_loaded: int = 0

    @property
    def rejected(self) -> int:
        return self.total_rows - self.duplicates_removed - self.rows_loaded

    def summary(self) -> str:
        lines = [f"Rows received:       {self.total_rows:,}",
                 f"Duplicates removed:  {self.duplicates_removed:,}"]
        for name, count in self.failures.items():
            lines.append(f"Failed {name + ':':<13} {count:,}")
        lines.append(f"Rows rejected:       {self.rejected:,}")
        lines.append(f"Rows loaded:         {self.rows_loaded:,}")
        return "\n".join(lines)


def check_schema(df: pd.DataFrame) -> None:
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Schema check failed, missing columns: {sorted(missing)}")


def null_keys(df):
    return df["event_id"].isna() | df["user_id"].isna()


def bad_timestamp(df):
    return pd.to_datetime(df["timestamp"], errors="coerce", format="ISO8601").isna()


def unknown_event(df):
    return ~df["event_type"].isin(EVENT_TYPES)


def bad_latency(df):
    return df["latency_ms"].notna() & ((df["latency_ms"] < 0) | (df["latency_ms"] > 60_000))


CHECKS = {"null_keys": null_keys, "timestamp": bad_timestamp,
          "event_type": unknown_event, "latency": bad_latency}


def validate(df: pd.DataFrame, report: QualityReport) -> pd.DataFrame:
    """Drop duplicates, run every check, return only clean rows."""
    check_schema(df)
    report.total_rows = len(df)
    deduped = df.drop_duplicates(subset="event_id")
    report.duplicates_removed = len(df) - len(deduped)

    bad = pd.Series(False, index=deduped.index)
    for name, check in CHECKS.items():
        mask = check(deduped)
        report.failures[name] = int(mask.sum())
        bad |= mask
    clean = deduped[~bad].copy()
    report.rows_loaded = len(clean)
    return clean
