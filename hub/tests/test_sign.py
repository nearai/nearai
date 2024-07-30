import unittest

from hub.api.near.sign import Payload, validate_signature, verify_signed_message


class TestSignatureVerification(unittest.TestCase):
    def setUp(self):
        self.account_id = "dev.near"
        self.callback_url = "https://dev.near.social/dev.near/widget/Hub"
        self.message = "Welcome to NEAR.AI"
        self.recipient = "ai.near"
        self.nonce = bytes("1", "utf-8") * 32

        self.public_key = "ed25519:2aPrik9S1qCnnfNo2doETrNa61ZaBwZYC8baschK5din"
        self.signature = "pyiixiWS3zHNhPFhd6EJy2oenB2WfxT5MTcOtNnreA/hqTgRCDKIMxu+6MjmDif7jbC+U1/V7VOT2oSv6kfXBQ=="

    def test_verify_signed_message(self):
        self.assertTrue(
            verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                self.message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )

        illegal_message = ""
        self.assertFalse(
            verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                illegal_message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )

    def test_validate_signature(self):
        payload = Payload(self.message, self.nonce, self.recipient, self.callback_url)
        self.assertTrue(validate_signature(self.public_key, self.signature, payload))


if __name__ == "__main__":
    unittest.main()
