from typing import Optional
import nacl.signing
import hashlib
import base64
import base58
import requests
from .serializer import BinarySerializer


def verify_signed_message(account_id, public_key, signature, message, nonce, recipient, callback_url):
    is_valid = validate_signature(
        public_key, signature, Payload(message, nonce, recipient, callback_url))

    if not is_valid and callback_url is not None:
        is_valid = validate_signature(
            public_key, signature, Payload(message, nonce, recipient, None))

    if is_valid:
        # verify that key belongs to `account_id`
        return verify_access_key_owner(public_key, account_id)

    return False


def verify_access_key_owner(public_key, account_id):
    try:
        url = f"https://api.fastnear.com/v0/public_key/{public_key}"
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        account_ids = content.get("account_ids", [])
        return account_id in account_ids
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')

    return False


class Payload:
    def __init__(self, message: str, nonce: bytes, recipient: str, callback_url: Optional[str] = None):
        self.tag = 2147484061 # constant from https://github.com/near/NEPs/blob/master/neps/nep-0413.md#example
        self.message = message
        self.nonce = nonce
        self.recipient = recipient
        self.callbackUrl = callback_url


def validate_signature(public_key: str, signature: str, payload: Payload):
    payload_schema = [[
        Payload, {
            'kind': 'struct',
            'fields': [
                ['tag', 'u32'],
                ['message', 'string'],
                ['nonce', [32]],
                ['recipient', 'string'],
                ["callbackUrl",
                 {
                     "kind": "option",
                     "type": "string",
                 },
                 ],
            ],
        }]
    ]
    ED_PREFIX = "ed25519:"

    borsh_payload = BinarySerializer(dict(payload_schema)).serialize(payload)
    to_sign = hashlib.sha256(borsh_payload).digest()
    real_signature = base64.b64decode(signature)

    public_key = nacl.signing.VerifyKey(
        base58.b58decode(public_key[len(ED_PREFIX):]))

    try:
        public_key.verify(to_sign, real_signature)
        # print("Signature is valid.")
        return True
    except nacl.exceptions.BadSignatureError:
        # print("Signature was forged or corrupt.")
        return False
