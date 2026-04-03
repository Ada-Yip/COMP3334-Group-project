from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SERVER_URL
from scripts.security_test_utils import Stats, is_local_url, post_json


def run_load_test(
    base_url: str,
    endpoint: str,
    total_requests: int,
    concurrency: int,
    payload: Dict[str, object],
    timeout_seconds: float,
    dry_run: bool,
) -> Stats:
    stats = Stats()
    headers = {"Content-Type": "application/json"}

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                post_json,
                base_url,
                endpoint,
                payload,
                headers,
                timeout_seconds,
                dry_run,
            )
            for _ in range(total_requests)
        ]
        for future in as_completed(futures):
            status_code, latency, error = future.result()
            stats.record(status_code, latency, error)

    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Large-volume request test against the server.")
    parser.add_argument("--base-url", default=SERVER_URL, help="Base server URL")
    parser.add_argument("--endpoint", default="/login", help="Target endpoint")
    parser.add_argument("--total", type=int, default=200, help="Total requests to send")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=3.0, help="Per-request timeout (seconds)")
    parser.add_argument("--username", default="load_test_user", help="Login username")
    parser.add_argument("--password", default="invalid_password", help="Login password")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without sending requests")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow non-local base URLs (use with caution)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not is_local_url(args.base_url) and not args.allow_remote:
        raise SystemExit("Refusing to run against non-local target. Use --allow-remote to override.")

    payload = {"username": args.username, "password": args.password}

    if args.dry_run:
        print("[DRY RUN] Would send load test requests with:")
        print(f"  base_url={args.base_url}")
        print(f"  endpoint={args.endpoint}")
        print(f"  total={args.total}, concurrency={args.concurrency}")
        return

    stats = run_load_test(
        base_url=args.base_url,
        endpoint=args.endpoint,
        total_requests=args.total,
        concurrency=args.concurrency,
        payload=payload,
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
    )

    summary = stats.summary()
    print("\n=== Load Test Summary ===")
    print(f"Total requests: {summary['total']}")
    print(f"Errors: {summary['errors']}")
    print(f"Status counts: {stats.counts}")
    print(f"Latency avg (ms): {summary['latency_avg_ms']}")
    print(f"Latency p95 (ms): {summary['latency_p95_ms']}")
    print(f"Latency max (ms): {summary['latency_max_ms']}")


if __name__ == "__main__":
    main()
