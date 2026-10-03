"""Generate synthetic app telemetry events, including realistic 'dirty' rows."""
import random
from datetime import datetime, timedelta

import pandas as pd

EVENT_TYPES = ["app_open", "page_view", "click", "api_call", "error", "app_close"]
PLATFORMS = ["windows", "android", "ios", "web"]
REGIONS = ["us-west", "us-east", "eu-north", "asia-south"]
VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]


def generate_events(n_events: int = 200_000, n_users: int = 5_000,
                    bad_row_rate: float = 0.03, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    start = datetime(2026, 9, 1)
    rows = []
    for i in range(n_events):
        event_type = rng.choices(EVENT_TYPES, weights=[10, 35, 30, 18, 3, 4])[0]
        latency = round(rng.lognormvariate(4.5, 0.6), 1) if event_type == "api_call" else None
        rows.append({
            "event_id": f"evt_{i:08d}",
            "user_id": f"user_{rng.randint(1, n_users):05d}",
            "event_type": event_type,
            "platform": rng.choice(PLATFORMS),
            "region": rng.choice(REGIONS),
            "app_version": rng.choice(VERSIONS),
            "latency_ms": latency,
            "timestamp": (start + timedelta(seconds=rng.randint(0, 30 * 24 * 3600))).isoformat(),
        })
    df = pd.DataFrame(rows)

    # Inject data-quality problems seen in real telemetry.
    n_bad = int(n_events * bad_row_rate)
    idx = rng.sample(range(n_events), n_bad)
    for k, j in enumerate(idx):
        problem = k % 4
        if problem == 0:
            df.at[j, "user_id"] = None                      # missing key
        elif problem == 1:
            df.at[j, "timestamp"] = "not-a-date"            # malformed timestamp
        elif problem == 2:
            df.at[j, "event_type"] = "unknwn_evt"           # unknown category
        else:
            df.at[j, "event_type"] = "api_call"
            df.at[j, "latency_ms"] = -50.0                  # impossible value
    dupes = df.sample(n=n_bad // 2, random_state=seed)      # duplicate deliveries
    return pd.concat([df, dupes], ignore_index=True)
