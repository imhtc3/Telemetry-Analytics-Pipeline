-- Business reports on the warehouse. Run with: sqlite3 telemetry.db < sql/reports.sql

-- 1. Daily active users
SELECT d.date, COUNT(DISTINCT f.user_key) AS daily_active_users
FROM fact_events f JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.date ORDER BY d.date;

-- 2. Error rate by app version (spot bad releases)
SELECT p.app_version,
       ROUND(100.0 * SUM(f.event_type = 'error') / COUNT(*), 2) AS error_rate_pct
FROM fact_events f JOIN dim_platform p ON p.platform_key = f.platform_key
GROUP BY p.app_version ORDER BY error_rate_pct DESC;

-- 3. API latency by region
SELECT p.region, ROUND(AVG(f.latency_ms), 1) AS avg_latency_ms, MAX(f.latency_ms) AS max_latency_ms
FROM fact_events f JOIN dim_platform p ON p.platform_key = f.platform_key
WHERE f.event_type = 'api_call'
GROUP BY p.region ORDER BY avg_latency_ms DESC;
