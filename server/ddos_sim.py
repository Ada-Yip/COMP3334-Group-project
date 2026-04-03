"""DDoS simulation: many clients (distinct IPs) hitting the server."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable
import os
import sys

# Ensure repo root is on sys.path for script execution.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SERVER_URL
from scripts.security_test_utils import Stats, is_local_url, post_json, random_ipv4


def _ip_pool(size: int) -> list[str]:
    return [random_ipv4() for _ in range(size)]


def run_ddos_sim(
    base_url: str,
    endpoint: str,
    total_requests: int,
    concurrency: int,
    payload: Dict[str, object],
    timeout_seconds: float,
    dry_run: bool,
    ip_pool: Iterable[str],
) -> Stats:
    stats = Stats()
    ip_list = list(ip_pool)
    if not ip_list:
        ip_list = [random_ipv4()]

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for idx in range(total_requests):
            headers = {
                "Content-Type": "application/json",
                "X-Forwarded-For": ip_list[idx % len(ip_list)],
            }
            futures.append(
                executor.submit(
                    post_json,
                    base_url,
                    endpoint,
                    payload,
                    headers,
                    timeout_seconds,
                    dry_run,
                )
            )

        for future in as_completed(futures):
            status_code, latency, error = future.result()
            stats.record(status_code, latency, error)

    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate a distributed DDoS-like burst.")
    parser.add_argument("--base-url", default=SERVER_URL, help="Base server URL")
    parser.add_argument("--endpoint", default="/login", help="Target endpoint")
    parser.add_argument("--rate", type=int, default=200, help="Approx requests per second")
    parser.add_argument("--duration", type=int, default=5, help="Duration in seconds")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=3.0, help="Per-request timeout (seconds)")
    parser.add_argument("--ip-pool", type=int, default=200, help="Distinct IPs to rotate")
    parser.add_argument("--username", default="ddos_user", help="Login username")
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

    total_requests = max(0, args.rate) * max(0, args.duration)
    payload = {"username": args.username, "password": args.password}

    if args.dry_run:
        print("[DRY RUN] Would send DDoS simulation requests with:")
        print(f"  base_url={args.base_url}")
        print(f"  endpoint={args.endpoint}")
        print(f"  total={total_requests}, concurrency={args.concurrency}")
        print(f"  ip_pool={args.ip_pool}")
        return

    stats = run_ddos_sim(
        base_url=args.base_url,
        endpoint=args.endpoint,
        total_requests=total_requests,
        concurrency=args.concurrency,
        payload=payload,
        timeout_seconds=args.timeout,
        dry_run=args.dry_run,
        ip_pool=_ip_pool(args.ip_pool),
    )

    summary = stats.summary()
    print("\n=== DDoS Simulation Summary ===")
    print(f"Total requests: {summary['total']}")
    print(f"Errors: {summary['errors']}")
    print(f"Status counts: {stats.counts}")
    print(f"Latency avg (ms): {summary['latency_avg_ms']}")
    print(f"Latency p95 (ms): {summary['latency_p95_ms']}")
    print(f"Latency max (ms): {summary['latency_max_ms']}")


if __name__ == "__main__":
    main()
