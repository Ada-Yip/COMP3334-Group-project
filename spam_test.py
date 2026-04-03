from __future__ import annotations

import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SERVER_URL
from scripts.security_ddos_sim import run_ddos_sim
from scripts.security_load_test import run_load_test
from scripts.security_test_utils import is_local_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Run basic security load/DDOS tests.")
    parser.add_argument("--base-url", default=SERVER_URL, help="Base server URL")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without sending requests")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow non-local base URLs (use with caution)",
    )
    args = parser.parse_args()

    if not is_local_url(args.base_url) and not args.allow_remote:
        raise SystemExit("Refusing to run against non-local target. Use --allow-remote to override.")

    if args.dry_run:
        print("[DRY RUN] Would run:")
        print("  1) Load test: 100 requests, concurrency 10")
        print("  2) DDoS sim:  200 requests, concurrency 25, ip_pool 100")
        return

    print("Running load test...")
    load_stats = run_load_test(
        base_url=args.base_url,
        endpoint="/login",
        total_requests=100,
        concurrency=10,
        payload={"username": "runner_user", "password": "invalid_password"},
        timeout_seconds=3.0,
        dry_run=False,
    )
    print(f"Load status counts: {load_stats.counts}")

    print("Running DDoS simulation...")
    ddos_stats = run_ddos_sim(
        base_url=args.base_url,
        endpoint="/login",
        total_requests=200,
        concurrency=25,
        payload={"username": "runner_user", "password": "invalid_password"},
        timeout_seconds=3.0,
        dry_run=False,
        ip_pool=[f"10.0.0.{i}" for i in range(1, 101)],
    )
    print(f"DDoS status counts: {ddos_stats.counts}")


if __name__ == "__main__":
    main()
