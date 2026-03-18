"""
UI for client
"""
import sys
import os
import requests
import time
#from crypto_manager import CryptoManager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import SERVER_URL, SHARED_SECRET


def print_message_from_response(response: requests.Response):
    """print message from response"""
    try:
        res = response.json()
        if response.status_code == 200:
            print(f"\n[SUCESS]{res.get('message', 'OK')}")
        else:
            print(f"\n[ERROR {response.status_code}] {res.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"\n[ERROR {response.status_code}] {e}")

def main():
    print("========= Secure IM CLI =========\n")
    print("Your input will be stripped of whitespace and case sensitivity")
    register_username = input("Enter your username (e.g., Alice or Bob): ")
    register_password = input("Enter your password (at least 8 characters): ")
    
    #crypto = CryptoManager(SHARED_SECRET)
    res=requests.post(f"{SERVER_URL}/register", json={
        "username": register_username, "password": register_password
    })
    print_message_from_response(res)
    
if __name__ == "__main__":
    main()