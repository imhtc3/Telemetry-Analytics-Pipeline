"""Run the full pipeline end to end and print a quality + performance report."""
import argparse
import sqlite3
import time

from pipeline import benchmark, warehouse
from pipeline.generate import generate_events
from pipeline.quality import QualityReport, validate


def main():
    parser = argparse.ArgumentParser(description="Telemetry analytics pipeline")
    parser.add_argument("--events", type=int, default=200_000)
    parser.add_argument("--db", default="telemetry.db")
    args = parser.parse_args()

    t0 = time.perf_counter()
    print(f"[1/5] Generating {args.events:,} raw events ...")
    raw = generate_events(n_events=args.events)

    print("[2/5] Validating data quality ...")
    report = QualityReport()
    clean = validate(raw, report)

    print("[3/5] Transforming into star schema ...")
    tables = warehouse.transform(clean)

    print("[4/5] Loading warehouse (no indexes) and benchmarking ...")
    conn = sqlite3.connect(args.db)
    warehouse.load(tables, conn, with_indexes=False)
    before = benchmark.run(conn)

    print("[5/5] Adding indexes and re-benchmarking ...")
    warehouse.create_indexes(conn)
    after = benchmark.run(conn)
    conn.close()

    print("\n=== Data quality report ===")
    print(report.summary())
    print("\n=== Query performance (ms per query) ===")
    for name in before:
        speedup = before[name] / after[name] if after[name] else float("inf")
        print(f"{name:<24} {before[name]:8.2f} -> {after[name]:7.2f}   ({speedup:.0f}x faster)")
    print(f"\nPipeline finished in {time.perf_counter() - t0:.1f}s -> {args.db}")


if __name__ == "__main__":
    main()
