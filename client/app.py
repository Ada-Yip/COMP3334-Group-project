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

    login_register = True
    while login_register:
        print("========= Secure IM CLI =========\n")
        print("Your input will be stripped of whitespace and case sensitivity")
        print("============Do you want to login?============\n")
        login = normalize_choice(input("Enter 'y' to login, 'n' to register: "))
        if login == 'y':
            while True:
                print("============Login============\n")
                input_username = input("Enter your username: ")
                if input_username == "exit":
                    print("Returning to login/registration choice.")
                    break
                input_password = input("Enter your password: ")
                if input_password == "exit":
                    print("Returning to login/registration choice.")
                    break
                state = ClientState()
                client_obj = ClientAPI(state=state)
                res = client_obj.login(input_username, input_password)
                print_message_from_response(res)
                if res.get("status_code") == 200:
                    login_register = False
                    break
                else:
                    print("Login failed, please try again")
                    continue
        elif login == 'n':
            while True:
                print("============Register============\n")
                input_username = input("Enter your username: ")
                if input_username == "exit":
                    print("Returning to login/registration choice.")
                    break
                input_password = input("Enter your password: ")
                if input_password == "exit":
                    print("Returning to login/registration choice.")
                    break
                state = ClientState()
                client_obj = ClientAPI(state=state)
                res = client_obj.register_user(input_username, input_password)
                print_message_from_response(res)
                if res.get("status_code") == 200:
                    print("account registered and logged in successfully")
                    client_obj.login(input_username, input_password)
                    login_register = False
                    break
                else:
                    print("Login failed, please try again")
                    continue
        elif login == 'exit':
            print("Exiting application.")
            return
        else:
            print("Invalid choice. Please enter 'y' or 'n'.")

    def view_messages(client_obj):
        """
        View messages with conversation list, unread counters, and pagination
        """
        while True:
            print("\n===========Conversation List===========\n")
            conversations = client_obj.get_conversations_list()
            if not conversations:
                print("No conversations yet.\n")
                return
            for idx, conv in enumerate(conversations, 1):
                time_ago = client_obj._calc_time_ago(conv.last_timestamp)
                if conv.unread_count > 0:
                    print(f"[{idx}] {conv.sender_username} -  Last: {time_ago} ({conv.unread_count} unread)")
                else:
                    print(f"[{idx}] {conv.sender_username} -  Last: {time_ago}")
            print(f"\n[0] Back to main menu")
            print("--------------------------------")
            try:
                choice = input("Select conversation (number): ").strip()
                if choice == '0':
                    return
                choice_idx = int(choice) - 1
                if choice_idx < 0 or choice_idx >= len(conversations):
                    print("Invalid choice. Please try again.")
                    continue
                selected_conv = conversations[choice_idx]
                sender = selected_conv.sender_username
                offset = 0
                limit = 10
                all_messages = selected_conv.message_list
                all_messages.sort(key=lambda m: m.get('timestamp', 0), reverse=True)
                while True:
                    print(f"\n===========Messages from {sender}===========\n")
                    paginated = all_messages[offset:offset + limit]
                    if not paginated:
                        print("No more messages.\n")
                        break
                    print(f"Showing messages {offset + 1} to {offset + len(paginated)} of {len(all_messages)}")
                    print("--------------------------------\n")
                    for message in paginated:
                        sender_name = message.get('sender_username')
                        receiver_name = message.get('receiver_username')
                        ciphertext = message.get('ciphertext')
                        nonce = message.get('nonce')
                        timestamp = message.get('timestamp')
                        age = message.get('age')
                        print(f"From: {sender_name}")
                        print(f"To: {receiver_name}")
                        try:
                            if age < 0:
                                print(f"Message: [Expired Message]")
                                print(f"Sent at {timestamp}, expired {abs(age)} seconds ago")
                            elif ciphertext and nonce and ciphertext != "0":
                                plaintext = client_obj.crypto_manager.decrypt(ciphertext, nonce)
                                print(f"Message: {plaintext}")
                                print(f"Sent at {timestamp}")
                                if age > 0:
                                    print(f"Expires in {age} seconds")
                                else:
                                    print(f"Message never expires")
                            else:
                                print(f"Message: [Error] Missing ciphertext or nonce")
                        except Exception as e:
                            print(f"Message: [Decryption Failed - Data corrupted or wrong key]")
                        print("--------------------------------\n")
                    if offset + limit < len(all_messages):
                        user_input = input("Press [Enter] to continue loading messages, or [0] to go back: ").strip()
                        if user_input == '0':
                            break
                        offset += limit
                    else:
                        print("No more messages.\n")
                        input("Press [Enter] to go back to conversations: ")
                        break
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue

    while True:
        print("\n===========What would you like to do?===========")
        print("1) Send a message")
        print("2) Fetch messages")
        print("3) View messages")
        print("4) Logout and exit")
        print("5) Exit without logout")

        action = normalize_choice(input("Choose 1/2/3/4/5: "))

        if action == '1':
            print("===========Send Message===========\n")
            recipient_username = input("Enter the username of the recipient: ")
            if recipient_username == client_obj.get_user_name():
                print("You cannot send message to yourself, please try again")
                continue

            message = input("Enter the message to send: ")
            while True:
                try:
                    duration = abs(int(input("Enter expiry time (in seconds) for the message (0 = always valid): ")))
                    break
                except Exception:
                    print("Invalid input! Please enter a valid integer.")
            res = client_obj.send_message(recipient_username, message, duration)
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
            view_messages(client_obj)

        elif action == '4':
            res = client_obj.logout()
            print_message_from_response(res)
            return

        elif action == '5':
            print("Exit without logout selected.")
            return

        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()
