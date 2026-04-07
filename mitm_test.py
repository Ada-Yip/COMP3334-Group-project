
from __future__ import annotations

import argparse
import os
import secrets
import sys
from dataclasses import dataclass
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLIENT_DIR = os.path.join(REPO_ROOT, "client")
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from config import SERVER_URL
from client.api_client import ClientAPI
from scripts.security_test_utils import is_local_url


@dataclass
class MitmResult:
    baseline_send_ok: bool
    mitm_detected: bool
    mitm_send_status: int | None
    notes: list[str]


def _status_ok(response: dict) -> bool:
    return response.get("status_code") == 200


def _login_or_register(api: ClientAPI, username: str, password: str) -> None:
    login = api.login(username, password)
    if _status_ok(login):
        return

    register = api.register_user(username, password)
    if not _status_ok(register) and register.get("detail") != "User already exists":
        raise RuntimeError(f"Unable to register {username}: {register}")

    login = api.login(username, password)
    if not _status_ok(login):
        raise RuntimeError(f"Unable to login {username}: {login}")


def _ensure_friendship(sender: ClientAPI, receiver: ClientAPI) -> None:
    response = sender.send_friend_request(receiver.get_user_name())
    if response.get("status_code") not in {200, 400}:
        raise RuntimeError(f"Friend request failed: {response}")

    pending = receiver.get_received_requests()
    if pending.get("status_code") != 200:
        raise RuntimeError(f"Cannot read incoming friend requests: {pending}")

    sender_name = sender.get_user_name()
    for request_row in pending.get("requests", []):
        if request_row.get("from_username") == sender_name:
            accept = receiver.respond_friend_request(request_row["id"], "accept")
            if accept.get("status_code") != 200:
                raise RuntimeError(f"Failed to accept friend request: {accept}")
            break


def run_mitm_sim(
    base_url: str,
    alice_username: str,
    bob_username: str,
    attacker_username: str,
    password: str,
    ttl_seconds: int,
    accept_changed_key: bool,
) -> MitmResult:
    notes: list[str] = []

    alice = ClientAPI(base_url=base_url)
    bob = ClientAPI(base_url=base_url)
    attacker = ClientAPI(base_url=base_url)

    _login_or_register(alice, alice_username, password)
    _login_or_register(bob, bob_username, password)
    _login_or_register(attacker, attacker_username, password)

    _ensure_friendship(alice, bob)

    baseline = alice.send_message(bob_username, "baseline-safe-message", age=ttl_seconds)
    baseline_ok = _status_ok(baseline)
    if not baseline_ok:
        notes.append(f"Baseline send failed: {baseline}")
        return MitmResult(False, False, baseline.get("status_code"), notes)

    bob_key_response = alice.get_public_key_by_username(bob_username)
    attacker_key_response = alice.get_public_key_by_username(attacker_username)
    if not _status_ok(bob_key_response) or not _status_ok(attacker_key_response):
        notes.append("Could not fetch target/attacker public keys.")
        return MitmResult(True, False, None, notes)

    original_get_public_key = alice.get_public_key_by_username
    attacker_public_key = attacker_key_response["public_key"]

    def tampered_get_public_key(username: str) -> dict:
        if username == bob_username:
            return {
                "status_code": 200,
                "public_key": attacker_public_key,
                "verification_code": "tampered-by-mitm",
            }
        return original_get_public_key(username)

    alice.get_public_key_by_username = tampered_get_public_key  # type: ignore[method-assign]

    mitm_detected = False
    mitm_send_status: int | None = None

    confirmation = "y" if accept_changed_key else "n"
    with patch("builtins.input", return_value=confirmation):
        try:
            result = alice.send_message(bob_username, "message-under-mitm", age=ttl_seconds)
            mitm_send_status = result.get("status_code")
            if accept_changed_key:
                notes.append(
                    "Changed key was manually accepted; this simulates a user overriding the warning."
                )
            else:
                notes.append("MITM send unexpectedly succeeded even though key change was rejected.")
        except ValueError as exc:
            mitm_detected = "Key change detected" in str(exc)
            notes.append(f"Client blocked MITM send: {exc}")

    return MitmResult(baseline_ok, mitm_detected, mitm_send_status, notes)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate MITM key-substitution attack with two clients.")
    parser.add_argument("--base-url", default=SERVER_URL, help="Base server URL")
    parser.add_argument("--alice", default="", help="Alice username (generated when omitted)")
    parser.add_argument("--bob", default="", help="Bob username (generated when omitted)")
    parser.add_argument("--attacker", default="", help="Attacker username (generated when omitted)")
    parser.add_argument("--password", default="Passw0rd!", help="Password for generated accounts")
    parser.add_argument("--ttl", type=int, default=60, help="Message TTL seconds")
    parser.add_argument(
        "--accept-changed-key",
        action="store_true",
        help="Auto-accept changed key prompt (simulates risky user behavior)",
    )
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

    suffix = secrets.token_hex(3)
    alice = args.alice or f"mitm_alice_{suffix}"
    bob = args.bob or f"mitm_bob_{suffix}"
    attacker = args.attacker or f"mitm_eve_{suffix}"

    if args.dry_run:
        print("[DRY RUN] MITM simulation plan:")
        print(f"  base_url={args.base_url}")
        print(f"  alice={alice}, bob={bob}, attacker={attacker}")
        print("  steps: register/login users -> friend Alice/Bob -> baseline send -> tamper Bob key lookup")
        print(f"  key-change prompt auto-response={'accept' if args.accept_changed_key else 'reject'}")
        return

    result = run_mitm_sim(
        base_url=args.base_url,
        alice_username=alice,
        bob_username=bob,
        attacker_username=attacker,
        password=args.password,
        ttl_seconds=args.ttl,
        accept_changed_key=args.accept_changed_key,
    )

    print("\n=== MITM Simulation Result ===")
    print(f"Baseline send successful: {result.baseline_send_ok}")
    print(f"MITM detected and blocked: {result.mitm_detected}")
    print(f"MITM send status code: {result.mitm_send_status}")
    if result.notes:
        print("Notes:")
        for note in result.notes:
            print(f"- {note}")

    if not result.baseline_send_ok:
        raise SystemExit(2)
    if not args.accept_changed_key and not result.mitm_detected:
        raise SystemExit(3)


if __name__ == "__main__":
    main()

