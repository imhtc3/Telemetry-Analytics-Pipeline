import sqlite3
import unittest

import pandas as pd

from pipeline import warehouse
from pipeline.generate import generate_events
from pipeline.quality import QualityReport, check_schema, validate


def make_df(**overrides):
    row = {"event_id": "e1", "user_id": "u1", "event_type": "api_call", "platform": "web",
           "region": "us-west", "app_version": "1.0.0", "latency_ms": 120.0,
           "timestamp": "2026-09-01T10:00:00"}
    row.update(overrides)
    return pd.DataFrame([row])


class QualityTests(unittest.TestCase):
    def test_clean_row_passes(self):
        self.assertEqual(len(validate(make_df(), QualityReport())), 1)

    def test_rejects_null_user(self):
        self.assertEqual(len(validate(make_df(user_id=None), QualityReport())), 0)

    def test_rejects_bad_timestamp(self):
        self.assertEqual(len(validate(make_df(timestamp="garbage"), QualityReport())), 0)

    def test_rejects_negative_latency(self):
        self.assertEqual(len(validate(make_df(latency_ms=-5.0), QualityReport())), 0)

    def test_rejects_unknown_event(self):
        self.assertEqual(len(validate(make_df(event_type="???"), QualityReport())), 0)

    def test_removes_duplicates(self):
        report = QualityReport()
        validate(pd.concat([make_df(), make_df()]), report)
        self.assertEqual(report.duplicates_removed, 1)

    def test_schema_check(self):
        with self.assertRaises(ValueError):
            check_schema(make_df().drop(columns="user_id"))


class EndToEndTests(unittest.TestCase):
    def test_pipeline_loads_only_clean_rows(self):
        raw = generate_events(n_events=5_000, n_users=200)
        report = QualityReport()
        clean = validate(raw, report)
        conn = sqlite3.connect(":memory:")
        warehouse.load(warehouse.transform(clean), conn)
        loaded = conn.execute("SELECT COUNT(*) FROM fact_events").fetchone()[0]
        self.assertEqual(loaded, report.rows_loaded)
        self.assertGreater(report.rejected, 0)
        orphans = conn.execute("""SELECT COUNT(*) FROM fact_events f
            LEFT JOIN dim_user u ON u.user_key = f.user_key WHERE u.user_key IS NULL""").fetchone()[0]
        self.assertEqual(orphans, 0)


if __name__ == "__main__":
    unittest.main()
