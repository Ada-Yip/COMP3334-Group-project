"""
UI for client
"""
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import SERVER_URL, SHARED_SECRET
from api_client import ClientAPI, ClientState


def print_message_from_response(response: dict):
    """print message from response"""
    try:
        if response.get('status_code') == 200:
            print(f"\n[SUCCESS] {response.get('message', 'OK')}")
        else:
            print(f"\n[ERROR {response.get('status_code', 'Unknown error')}] {response.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"\n[ERROR {response.get('status_code', 'Unknown error')}] {e}")


def normalize_choice(user_input: str) -> str:
    """Normalize command-style input."""
    return user_input.strip().lower()


def main():
    print("========= Secure IM CLI =========\n")
    print("Your input will be stripped of whitespace and case sensitivity")
    print("============Do you want to login?============\n")
    login = normalize_choice(input("Enter 'y' to login, 'n' to register: "))
    if login == 'y':
        while True:
            print("============Login============\n")
            input_username = input("Enter your username: ")
            input_password = input("Enter your password: ")
            state = ClientState()
            client_obj = ClientAPI(state=state)
            res = client_obj.login(input_username, input_password)
            print_message_from_response(res)
            if res.get("status_code") == 200:
                break
            else:
                print("Login failed, please try again")
                continue
    else:
        while True:
            print("============Register============\n")
            input_username = input("Enter your username: ")
            input_password = input("Enter your password: ")
            state = ClientState()
            client_obj = ClientAPI(state=state)
            res = client_obj.register_user(input_username, input_password)
            print_message_from_response(res)
            if res.get("status_code") == 200:
                print("account registered and logged in successfully")
                client_obj.login(input_username, input_password)
                break
            else:
                print("Login failed, please try again")
                continue

    while True:
        print("\n===========What would you like to do?===========")
        print("1) Send a message")
        print("2) Fetch messages")
        print("3) Logout and exit")
        print("4) Exit without logout")

        action = normalize_choice(input("Choose 1/2/3/4: "))

        if action == '1':
            print("===========Send Message===========\n")
            recipient_username = input("Enter the username of the recipient: ")
            if recipient_username == client_obj.get_user_name():
                print("You cannot send message to yourself, please try again")
                continue

            message = input("Enter the message to send: ")
            res = client_obj.send_message(recipient_username, message)
            print_message_from_response(res)

        elif action == '2':
            print("===========Fetch Messages===========\n")
            fetch_all_message = normalize_choice(
                input("Enter 'y' to fetch all messages, 'n' to fetch unseen messages: ")
            )
            if fetch_all_message == 'y':
                res = client_obj.fetch_messages_all()
            else:
                res = client_obj.fetch_messages_unseen()
            print_message_from_response(res)

        elif action == '3':
            res = client_obj.logout()
            print_message_from_response(res)
            return

        elif action == '4':
            print("Exit without logout selected.")
            return

        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
