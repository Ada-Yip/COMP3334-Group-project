"""
UI for client
"""
import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import SERVER_URL
from api_client import ClientAPI, ClientState

import pyotp


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

def friend_management_menu(client_obj: ClientAPI):
    """Submenu for friend-related operations."""
    while True:
        print("\n=========== Friend Management ===========")
        print("1) Send friend request")
        print("2) View received friend requests")
        print("3) View sent friend requests")
        print("4) List friends")
        print("5) Remove friend")
        print("6) Block a user")
        print("7) Unblock a user")
        print("8) Back to main menu")
        
        choice = normalize_choice(input("Choose 1-8: "))
        
        if choice == '1':
            # Send friend request
            to_username = input("Enter username to send friend request: ").strip()
            if to_username == client_obj.get_user_name():
                print("You cannot send a friend request to yourself!")
                continue
            res = client_obj.send_friend_request(to_username)
            print_message_from_response(res)
        
        elif choice == '2':
            # View received requests
            res = client_obj.get_received_requests()
            if res.get("status_code") == 200:
                requests = res.get("requests", [])
                if not requests:
                    print("No pending friend requests received.")
                else:
                    print("\n--- Received Friend Requests ---")
                    for req in requests:      ###
                        local_time = datetime.fromtimestamp(req['created_at'])
                        print(f"ID: {req['id']} | From: {req['from_username']} | Sent: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    action = input("\nEnter request ID to accept/decline (or 'q' to go back): ").strip()
                    if action != 'q':
                        try:
                            req_id = int(action)
                            accept_decline = normalize_choice(input("Accept (a) or decline (d)? "))
                            if accept_decline == 'a':
                                res2 = client_obj.respond_friend_request(req_id, "accept")
                                print_message_from_response(res2)
                            elif accept_decline == 'd':
                                res2 = client_obj.respond_friend_request(req_id, "decline")
                                print_message_from_response(res2)
                            else:
                                print("Invalid choice")
                        except ValueError:
                            print("Invalid request ID")
            else:
                print_message_from_response(res)
        
        elif choice == '3':
            # View sent requests
            res = client_obj.get_sent_requests()
            if res.get("status_code") == 200:
                requests = res.get("requests", [])
                if not requests:
                    print("No pending friend requests sent.")
                else:
                    print("\n--- Sent Friend Requests ---")
                    for req in requests:       ###
                        local_time = datetime.fromtimestamp(req['created_at'])
                        print(f"ID: {req['id']} | To: {req['to_username']} | Sent: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print_message_from_response(res)
        
        elif choice == '4':
            # List friends
            res = client_obj.get_friends()
            if res.get("status_code") == 200:
                friends = res.get("friends", [])
                if not friends:
                    print("You don't have any friends yet.")
                else:
                    print(f"\n--- Friends List (Total: {len(friends)}) ---")
                    for friend in friends:
                        print(f"- {friend['username']}")
            else:
                print_message_from_response(res)
        
        elif choice == '5':
            # Remove friend
            friend_to_remove = input("Enter username to remove from friends: ").strip()
            res = client_obj.remove_friend(friend_to_remove)
            print_message_from_response(res)
        
        elif choice == '6':
            # Block a user
            to_block = input("Enter username to block: ").strip()
            if to_block == client_obj.get_user_name():
                print("You cannot block yourself!")
            else:
                res = client_obj.block_user(to_block)
                print_message_from_response(res)
        
        elif choice == '7':
            # Unblock a user
            to_unblock = input("Enter username to unblock: ").strip()
            res = client_obj.unblock_user(to_unblock)
            print_message_from_response(res)
        
        elif choice == '8':
            break
        
        else:
            print("Invalid choice. Please enter 1-8.")


def open_chat_room(client_obj: ClientAPI, partner_username: str):
    """independent chat room, refresh status whenever user input 'r'"""
    offset = 0
    limit = 10
    
    while True:
        conversations = client_obj.get_conversations_list()
        
        selected_conv = next((c for c in conversations if c.sender_username == partner_username), None)
        if not selected_conv:
            print(f"\nNo messages found with {partner_username}.")
            return

        all_messages = sorted(selected_conv.message_list, key=lambda m: m.get("timestamp", 0), reverse=True)
        
        print(f"\n=========== Conversation with {partner_username} ===========")
        paginated = all_messages[offset:offset + limit]
        
        if not paginated:
            print("No more messages.\n")
            break
            
        print(f"Showing messages {offset + 1} to {offset + len(paginated)} of {len(all_messages)}")
        print("--------------------------------\n")
        
        for message in paginated:
            sender_name = message.get("sender_username")
            receiver_name = message.get("receiver_username")
            ciphertext = message.get("ciphertext")
            nonce = message.get("nonce")
            timestamp = message.get("timestamp")
            age = message.get("age")
            counter = message.get("counter", 0)
            is_delivered = message.get("is_delivered", False)

            current_username = client_obj.get_user_name()
            peer_name = sender_name if sender_name != current_username else receiver_name

            print(f"From: {sender_name}")
            print(f"To: {receiver_name}")
            try:
                sent_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                if age < 0:
                    print("Message: [Expired Message]")
                    print(f"Sent at {sent_time}, expired {abs(age)} seconds ago")
                elif ciphertext and nonce and ciphertext != "0":    
                    if peer_name not in client_obj.crypto_manager.session_keys: 
                        peer_res = client_obj.get_public_key_by_username(peer_name)
                        if peer_res.get("status_code") == 200:
                            client_obj.crypto_manager.derive_shared_key(peer_res['public_key'], peer_name)
                    
                    plaintext, is_replay = client_obj.crypto_manager.decrypt(
                        b64_ciphertext=ciphertext, 
                        b64_nonce=nonce, 
                        sender_username=sender_name, 
                        recipient_username=receiver_name, 
                        counter=counter,
                    )

                    if sender_name == current_username:
                        sent_status = "[Delivered/Read]" if is_delivered else "[Sent]"
                        print(f"Message: {sent_status} {plaintext}")
                    else:
                        received_status = "[History]" if is_replay else "[New]"
                        print(f"Message: {received_status} {plaintext}")
                        
                    print(f"Sent at {sent_time}")
                    print(f"Expires in {age} seconds" if age > 0 else "Message never expires")
                else:
                    print("Message: [Error] Missing ciphertext or nonce")
            except Exception as e:
                print("Message: [Decryption Failed - Data corrupted or wrong key]")
            print("--------------------------------\n")
        
        if offset + limit < len(all_messages):
            user_input = input("Press [Enter] for next page, [r] to Refresh status, or [0] to go back: ").strip().lower()
            if user_input == "0":
                break
            elif user_input == "r":
                continue
            else:
                offset += limit
        else:
            user_input = input("No more messages. Press [r] to Refresh status, or [0] to go back: ").strip().lower()
            if user_input == "0" or user_input == "":
                break
            elif user_input == "r":
                offset = 0
                continue

def view_messages(client_obj: ClientAPI):
        """View conversation list and refresh status"""
        while True:
            print("\n=========== Conversation List ===========")
            conversations = client_obj.get_conversations_list()
            if not conversations:
                print("No conversations yet.\n")
                return
                
            for idx, conv in enumerate(conversations, 1):
                time_ago = client_obj.calc_time_ago(conv.last_timestamp)
                if conv.unread_count > 0:
                    print(f"[{idx}] {conv.sender_username} - Last: {time_ago} ({conv.unread_count} unread)")
                else:
                    print(f"[{idx}] {conv.sender_username} - Last: {time_ago}")
            
            print("\n[r] Refresh list")        
            print("[0] Back to main menu")
            print("--------------------------------")
            
            choice = input("Select conversation (number) or action: ").strip().lower()
            if choice == "0":
                return
            elif choice == "r":
                continue
                
            try:
                choice_idx = int(choice) - 1
                if choice_idx < 0 or choice_idx >= len(conversations):
                    print("Invalid choice. Please try again.")
                    continue
                
                # open chat room
                selected_conv = conversations[choice_idx]
                open_chat_room(client_obj, selected_conv.sender_username)
                
            except ValueError:
                print("Invalid input. Please enter a number or 'r'.")


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
                if input_username == "exit":  # Add Magic Word to exit the application at any point during login/registration
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

    while True:
        print("\n===========What would you like to do?===========")
        print("1) Send a message")
        print("2) View messages")
        print("3) Friend management")
        print("4) Setup OTP/Check OTP")
        print("5) Logout and exit")
        print("6) Exit without logout")

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
            continue

        elif action == '2':
            view_messages(client_obj)

        elif action == '3':
            friend_management_menu(client_obj)

        elif action == '4':
            print("===============OTP Status================\n")
            status = client_obj.get_otp_key()
            if status.get("status_code") == 200:
                print(f"You already setup OTP, current OTP is {pyotp.TOTP(status.get('data').get('secret_key')).now()}") #See Code for test, Can be deleted later
                continue
            res = client_obj.set_otp()
            print_message_from_response(res)
            if res.get("status_code") == 200:
                print(f"You have setup the OTP for this account. You will need to use it in addition to password for login.")
            else:
                print("OTP setup failed, please try again.")
            continue
        
        elif action == '5':
            res = client_obj.logout()
            print_message_from_response(res)
            return

        elif action == '6':
            print("Exit without logout selected.")
            return
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, 5, 6.")


if __name__ == "__main__":
    main()
