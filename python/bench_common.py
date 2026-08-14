"""Shared loading and statistics for the timing CSVs written by the simulator."""

import csv
import math
from collections import defaultdict

LOG_THRESHOLD = 100.0


def load(path):
    """Reads the timing CSV into a list of dicts with numeric fields."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "tag": row["tag"],
                "method": row["method"],
                "N": int(row["N"]),
                "L": float(row["L"]),
                "M": int(row["M"]),
                "rc": float(row["rc"]),
                "periodic": row["periodic"] == "1",
                "run": int(row["run"]),
                "seconds": float(row["seconds"]),
                "build_seconds": float(row.get("build_seconds") or 0.0),
                "sweep_seconds": float(row.get("sweep_seconds") or 0.0),
                "grid_bytes": int(row.get("grid_bytes") or 0),
                "grid_live_blocks": int(row.get("grid_live_blocks") or 0),
                "pair_tests": int(row.get("pair_tests") or 0),
            })
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def aggregate(rows, key):
    """Groups seconds by key(row) and returns {key: (mean, sample stddev, n)}."""
    buckets = defaultdict(list)
    for row in rows:
        buckets[key(row)].append(row["seconds"])

    out = {}
    for k, values in buckets.items():
        n = len(values)
        mean = sum(values) / n
        if n > 1:
            var = sum((v - mean) ** 2 for v in values) / (n - 1)
            std = math.sqrt(var)
        else:
            std = 0.0
        out[k] = (mean, std, n)
    return out


def spans_orders(values):
    """True when the positive values span at least LOG_THRESHOLD."""
    positive = [v for v in values if v > 0]
    if len(positive) < 2:
        return False
    return max(positive) / min(positive) >= LOG_THRESHOLD


def fit_slope(xs, ys):
    """Least-squares slope of log(y) against log(x): the exponent of y ~ x^k."""
    pairs = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(pairs) < 2:
        return float("nan")
    n = len(pairs)
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    den = sum((p[0] - mx) ** 2 for p in pairs)
    return num / den if den else float("nan")
