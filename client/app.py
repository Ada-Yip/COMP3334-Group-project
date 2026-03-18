"""
UI for client
"""
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import SERVER_URL, SHARED_SECRET
from api_client import ClientAPI, ClientState

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
    client_api = ClientAPI(state=state)
    res = client_api.register_user(register_username, register_password)
    print_message_from_response(res)
    print(f"Your username is {client_api.get_user_name()}")
    print(f"Your user id is {client_api.get_user_id()}")
    
if __name__ == "__main__":
    main()