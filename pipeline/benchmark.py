"""Time the analytical queries before and after indexing."""
import sqlite3
import time

QUERIES = {
    "errors_on_one_day": """
        SELECT COUNT(*) FROM fact_events
        WHERE date_key = 20260915 AND event_type = 'error'""",
    "one_user_activity": """
        SELECT COUNT(*), AVG(latency_ms) FROM fact_events
        WHERE user_key = 123""",
    "latency_by_platform": """
        SELECT p.platform, AVG(f.latency_ms) FROM fact_events f
        JOIN dim_platform p ON p.platform_key = f.platform_key
        WHERE f.event_type = 'api_call' GROUP BY p.platform""",
}


def time_query(conn: sqlite3.Connection, sql: str, repeats: int = 10) -> float:
    conn.execute(sql).fetchall()  # warm-up
    start = time.perf_counter()
    for _ in range(repeats):
        conn.execute(sql).fetchall()
    return (time.perf_counter() - start) / repeats * 1000  # ms per run


def run(conn: sqlite3.Connection) -> dict:
    return {name: time_query(conn, sql) for name, sql in QUERIES.items()}
