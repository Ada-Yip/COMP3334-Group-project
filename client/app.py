"""
UI for client
"""
import time
from config import SERVER_URL, SHARED_SECRET
from client.api_client import ClientAPI, ClientState

def print_message_from_response(response:   dict):
    """print message from response"""
    try:
        if response.get('status_code') == 200:
            print(f"\n[SUCCESS] {response.get('message', 'OK')}")
        else:
            print(f"\n[ERROR {response.get('status_code', 'Unknown error')}] {response.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"\n[ERROR {response.get('status_code', 'Unknown error')}] {e}")

def main():
    print("========= Secure IM CLI =========\n")
    print("Your input will be stripped of whitespace and case sensitivity")
    register_username = input("Enter your username (e.g., Alice or Bob): ")
    register_password = input("Enter your password (at least 8 characters): ")
    
    state = ClientState()
    client_obj = ClientAPI(state=state)
    res = client_obj.register_user(register_username, register_password)
    print_message_from_response(res)
    print(f"Your username is {client_obj.get_user_name()}")
    print(f"Your user id is {client_obj.get_user_id()}")
    
    print("===========Do you want to send a message?===========\n")
    send_message_flag = False
    send_message = input("Enter 'y' to send a message, 'n' to exit: ")
    if send_message == 'y':
        send_message_flag = True

    while send_message_flag:
        print("===========Send Message===========\n")
        recipient_username = input("Enter the username of the recipient: ")
        if recipient_username == client_obj.get_user_name():
            print("You cannot send message to yourself, please try again")
            return
        else:
            message = input("Enter the message to send: ")
            res = client_obj.send_message(recipient_username, message)
            print_message_from_response(res)
            send_message_flag = False
    
    print("===========Do you want to fetch messages?===========\n")
    fetch_messages = input("Enter 'y' to fetch messages, 'n' to exit: ")
    if fetch_messages == 'y':
        print("===========Fetch Messages===========\n")
        print("Do you want to fetch all message?")
        fetch_all_message = input("Enter 'y' to fetch all message, 'n' to fetch unseen message: ")
        if fetch_all_message == 'y':
            res = client_obj.fetch_messages_all()
            print_message_from_response(res)
        else:
            res = client_obj.fetch_messages_unseen()
            print_message_from_response(res)


if __name__ == "__main__":
    main()