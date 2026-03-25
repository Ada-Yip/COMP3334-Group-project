import sys
import os
import time
from datetime import datetime
import pyotp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import SERVER_URL
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
    """Main function."""
    login_register = True
    while login_register:
        print("========= Authenticator APP =========\n")
        print("Your input will be stripped of whitespace and case sensitivity")
        print("You will need to Login to use this app\n")
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
    print(f"Logged in as {client_obj.get_user_name()}")

    try:
        print(f"Fetching OTP from {client_obj.get_user_name()}")
        secret = client_obj.get_otp_key()
        if secret.get("status_code") != 200:
            print_message_from_response(secret)
            return
        else:
            secret = secret.get('data')['secret_key']
    except Exception as e:
        print(f"Error: {e}")
        return

    totp = pyotp.TOTP(secret)

    last_code = ""

    print("=========OTP Code Generator=========")

    while True:
        current_code = totp.now()

        if current_code != last_code:
            print(f"New Code: {current_code}")
            last_code = current_code

        time.sleep(1)


if __name__ == "__main__":
    main()