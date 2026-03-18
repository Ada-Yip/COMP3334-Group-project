"""Simple CLI UI for interacting with api_server.py endpoints."""

#  Powered by GPT5.3, at least we dont need to touch here yet.

from __future__ import annotations

import json

try:
	# Supports package execution: `python -m client.UI` from project root.
	from client.api_client import (
		ClientState,
		fetch_messages,
		generate_nonce,
		get_new_messages,
		get_public_key,
		register_user,
		reserve_local_message_id,
		send_message,
	)
except ModuleNotFoundError:
	# Supports direct script execution: `python UI.py` inside `client`.
	from api_client import (
		ClientState,
		fetch_messages,
		generate_nonce,
		get_new_messages,
		get_public_key,
		register_user,
		reserve_local_message_id,
		send_message,
	)


def _print_menu() -> None:
	print("\n=== E2EE Demo Client ===")
	print("1) Register user")
	print("2) Set current user")
	print("3) Get public key")
	print("4) Send message")
	print("5) Fetch messages")
	print("6) Show client state")
	print("0) Exit")


def _read_int(prompt: str) -> int:
	while True:
		raw = input(prompt).strip()
		try:
			return int(raw)
		except ValueError:
			print("Please enter a valid integer.")


def _register_flow(state: ClientState) -> None:
	user_name = input("user_name: ").strip()
	password = input("password: ").strip()
	public_key = input("public_key: ").strip() or "demo_public_key"

	result = register_user(state.base_url, user_name, password, public_key)
	print(json.dumps(result, indent=2))


def _set_current_user_flow(state: ClientState) -> None:
	state.current_user_id = _read_int("current user_id: ")
	state.current_username = input("current username: ").strip()
	print(f"Current user set to {state.current_username} (id={state.current_user_id}).")


def _get_public_key_flow(state: ClientState) -> None:
	user_id = _read_int("target user_id: ")
	result = get_public_key(state.base_url, user_id)
	print(json.dumps(result, indent=2))


def _send_flow(state: ClientState) -> None:
	if state.current_user_id is None or not state.current_username:
		print("Set current user first (option 2).")
		return

	receiver_id = _read_int("receiver_id: ")
	receiver_username = input("receiver_username: ").strip()
	plaintext = input("message text (used as ciphertext for now): ").strip()

	nonce = input("nonce (leave blank to auto-generate): ").strip() or generate_nonce()
	local_message_id = reserve_local_message_id(state)

	result = send_message(
		base_url=state.base_url,
		sender_id=state.current_user_id,
		sender_username=state.current_username,
		receiver_id=receiver_id,
		receiver_username=receiver_username,
		ciphertext=plaintext,
		nonce=nonce,
	)
	print(f"Local message id: {local_message_id}")
	print(json.dumps(result, indent=2))


def _fetch_flow(state: ClientState) -> None:
	if state.current_user_id is None:
		print("Set current user first (option 2).")
		return

	result = fetch_messages(state.base_url, state.current_user_id)
	print(json.dumps(result, indent=2))

	new_messages = get_new_messages(state, result)
	if not new_messages:
		print("No new unseen messages in this client session.")
		return

	print("\nNew messages:")
	for msg in new_messages:
		print(
			f"- message_id={msg.get('message_id')} "
			f"from {msg.get('sender_username')} -> {msg.get('receiver_username')} "
			f"ciphertext={msg.get('ciphertext')} nonce={msg.get('nonce')}"
		)


def _show_state(state: ClientState) -> None:
	print("\nClient state")
	print(f"- base_url: {state.base_url}")
	print(f"- current_user_id: {state.current_user_id}")
	print(f"- current_username: {state.current_username}")
	print(f"- next_local_message_id: {state.next_local_message_id}")
	print(f"- seen_message_ids_count: {len(state.seen_message_ids)}")


def run_cli_loop(base_url: str = "http://127.0.0.1:8000") -> None:
	state = ClientState(base_url=base_url)

	while True:
		_print_menu()
		choice = input("Choose an option: ").strip()

		if choice == "1":
			_register_flow(state)
		elif choice == "2":
			_set_current_user_flow(state)
		elif choice == "3":
			_get_public_key_flow(state)
		elif choice == "4":
			_send_flow(state)
		elif choice == "5":
			_fetch_flow(state)
		elif choice == "6":
			_show_state(state)
		elif choice == "0":
			print("Bye.")
			return
		else:
			print("Unknown option. Please choose 0-6.")


def main() -> None:
	run_cli_loop()


if __name__ == "__main__":
	main()
