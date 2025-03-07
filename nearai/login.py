import http.server
import json
import os.path
import socket
import socketserver
import threading
import time
import urllib.parse as urlparse
from pathlib import Path

import nearai.shared.near.sign as near
from nearai.config import load_config_file, save_config_file
from nearai.shared.auth_data import AuthData

RECIPIENT = "ai.near"
MESSAGE = "Welcome to NEAR AI"
NONCE = None
PORT = None

httpd = None


def update_auth_config(account_id, signature, public_key, callback_url, nonce):
    """Update authentication configuration if the provided signature is valid."""
    if near.verify_signed_message(
        account_id,
        public_key,
        signature,
        MESSAGE,
        nonce,
        RECIPIENT,
        callback_url,
    ):
        config = load_config_file()

        auth = AuthData.model_validate(
            {
                "account_id": account_id,
                "signature": signature,
                "public_key": public_key,
                "callback_url": callback_url,
                "nonce": nonce,
                "recipient": RECIPIENT,
                "message": MESSAGE,
            }
        )

        config["auth"] = auth.model_dump()
        save_config_file(config)

        print(f"Auth data has been successfully saved! You are now logged in with account ID: {account_id}")
        return True
    else:
        print("Signature verification failed. Abort")
        return False


def print_login_status():
    """Prints the current authentication status if available in the config file."""
    config = load_config_file()
    if config.get("auth") and config["auth"].get("account_id"):
        print(f"Auth data for: {config['auth']['account_id']}")
        print(f"signature: {config['auth']['signature']}")
        print(f"public_key: {config['auth']['public_key']}")
        print(f"nonce: {config['auth']['nonce']}")
        print(f"message: {config['auth']['message']}")
        print(f"recipient: {config['auth']['recipient']}")
    else:
        print("Near auth details not found")


class AuthHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Webserver logging method."""
        pass  # Override to suppress logging

    def do_GET(self):  # noqa: N802
        """Webserver GET method."""
        global NONCE, PORT

        script_path = Path(__file__).resolve()
        assets_folder = script_path.parent / "assets"

        if self.path.startswith("/capture"):
            with open(os.path.join(assets_folder, "auth_capture.html"), "r", encoding="utf-8") as file:
                content = file.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        if self.path.startswith("/auth"):
            parsed_url = urlparse.urlparse(self.path)
            fragment = parsed_url.query
            params = urlparse.parse_qs(fragment)

            required_params = ["accountId", "signature", "publicKey"]

            if all(param in params for param in required_params):
                update_auth_config(
                    params["accountId"][0],
                    params["signature"][0],
                    params["publicKey"][0],
                    callback_url=generate_callback_url(PORT),
                    nonce=NONCE,
                )
            else:
                print("Required parameters not found")

            with open(os.path.join(assets_folder, "auth_complete.html"), "r", encoding="utf-8") as file:
                content = file.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

            # Give the server some time to read the response before shutting it down
            def shutdown_server():
                global httpd
                time.sleep(2)  # Wait 2 seconds before shutting down
                if httpd:
                    httpd.shutdown()

            threading.Thread(target=shutdown_server).start()


def find_open_port() -> int:
    """Finds and returns an open port number by binding to a free port on the local machine."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def generate_callback_url(port):
    """Generates a callback URL using the specified port number."""
    return f"http://localhost:{port}/capture"


def print_url_message(url):
    """Prints a message instructing the user to visit the given URL to complete the login process."""
    print(f"Please visit the following URL to complete the login process: {url}")


def generate_nonce():
    """Generates a nonce based on the current time in milliseconds."""
    return str(int(time.time() * 1000))


def generate_and_save_signature(account_id, private_key):
    """Generates a signature for the given account ID and private key, then updates the auth configuration."""
    nonce = generate_nonce()
    payload = near.Payload(MESSAGE, nonce, RECIPIENT, "")

    signature, public_key = near.create_signature(private_key, payload)

    if update_auth_config(account_id, signature, public_key, "", nonce):
        print_login_status()


def login_with_file_credentials(account_id):
    """Logs in using credentials from a file for the specified account ID, generating and saving a signature."""
    file_path = os.path.expanduser(os.path.join("~/.near-credentials/", "mainnet", f"{account_id}.json"))

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            content = file.read()
            account_data = json.loads(content)
            private_key = account_data.get("private_key", None)
            if not private_key:
                return print(f"Private key is missing for {account_id} on mainnet")
            generate_and_save_signature(account_id, account_data["private_key"])

    else:
        return print(f"Account data is missing for {account_id}")


def login_with_near_auth(remote, auth_url):
    """Initiates the login process using NEAR authentication, either starting a local server to handle the callback or providing a URL for remote authentication."""  # noqa: E501
    global NONCE, PORT
    NONCE = generate_nonce()

    params = {
        "message": MESSAGE,
        "nonce": NONCE,
        "recipient": RECIPIENT,
    }

    if not remote:
        PORT = find_open_port()

        global httpd
        with socketserver.TCPServer(("", PORT), AuthHandler) as httpd:
            params["callbackUrl"] = f"http://localhost:{PORT}/capture"

            encoded_params = urlparse.urlencode(params)

            print_url_message(f"{auth_url}?{encoded_params}")

            httpd.serve_forever()

    else:
        encoded_params = urlparse.urlencode(params)

        print_url_message(f"{auth_url}?{encoded_params}")
        print("After visiting the URL, follow the instructions to save your auth signature")
