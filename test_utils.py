from __future__ import annotations

import math
import random
import time
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import urlparse


class Stats:
    def __init__(self) -> None:
        self.total = 0
        self.errors = 0
        self.counts: Dict[str, int] = {}
        self.latencies: list[float] = []

    def record(self, status_code: Optional[int], latency: float, error: Optional[str] = None) -> None:
        self.total += 1
        if error is not None or status_code is None:
            self.errors += 1
            key = "error"
        else:
            key = str(status_code)
            self.latencies.append(latency)

        self.counts[key] = self.counts.get(key, 0) + 1

    def summary(self) -> Dict[str, Optional[float]]:
        return {
            "total": self.total,
            "errors": self.errors,
            "latency_avg_ms": _safe_avg(self.latencies) * 1000 if self.latencies else None,
            "latency_p95_ms": _percentile(self.latencies, 0.95) * 1000 if self.latencies else None,
            "latency_max_ms": max(self.latencies) * 1000 if self.latencies else None,
        }


def _safe_avg(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[rank]


def is_local_url(base_url: str) -> bool:
    host = urlparse(base_url).hostname
    return host in {"127.0.0.1", "localhost"}


def build_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    endpoint = path if path.startswith("/") else f"/{path}"
    return f"{base}{endpoint}"


def random_ipv4() -> str:
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def post_json(
    base_url: str,
    path: str,
    payload: Dict[str, object],
    headers: Optional[Dict[str, str]] = None,
    timeout_seconds: float = 3.0,
    dry_run: bool = False,
) -> Tuple[Optional[int], float, Optional[str]]:
    if dry_run:
        return 0, 0.0, None

    try:
        import requests
    except ImportError as exc:
        raise SystemExit("Missing dependency 'requests'. Run: pip install -r requirements.txt") from exc

    url = build_url(base_url, path)
    start = time.monotonic()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        return response.status_code, time.monotonic() - start, None
    except requests.RequestException as exc:
        return None, time.monotonic() - start, str(exc)
