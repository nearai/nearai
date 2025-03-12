import unittest

# how to run:
# python -m unittest discover -s hub/tests
import nearai.shared.near.sign as near


class TestSignatureVerification(unittest.TestCase):
    def setUp(self):  # noqa: D102
        self.account_id = "dev.near"
        self.callback_url = "https://near.ai"
        self.message = "Test"
        self.recipient = "test.near"
        self.nonce = "1722875604184"

        self.public_key = "ed25519:2aPrik9S1qCnnfNo2doETrNa61ZaBwZYC8baschK5din"
        self.signature = "RzzQgi83NFzStiVnQjqBh1riQSK1u/W5KrPBqkAIsFLSornxSrLaJBZCP99c7Y+3Cvve4zmP39zs/eNHg2nSCw=="

    def test_validate_signature(self):  # noqa: D102
        payload = near.Payload(self.message, self.nonce, self.recipient, self.callback_url)
        self.assertTrue(near.validate_signature(self.public_key, self.signature, payload))

    def test_validate_signature_no_callback_url(self):  # noqa: D102
        payload = near.Payload(self.message, self.nonce, self.recipient, None)
        self.assertFalse(near.validate_signature(self.public_key, self.signature, payload))

    def test_create_signature(self):  # noqa: D102
        payload = near.Payload(self.message, self.nonce, self.recipient, self.callback_url)
        private_key = "ed25519:5j4jxNMwYim8phkmCJtPu8792ocAPHV6F3d9V4soJUoUXj5nUxAWmgg71VqW3rYU7aFYvrhsaEGvy6Pnrtrw9rkQ"
        signature, public_key = near.create_signature(private_key, payload)

        self.assertEqual(
            public_key,
            'ed25519:D7okgamWraWASEVYUUfAXhLtU5ehbuVVC4GSqntE7bjE'
        )
        self.assertEqual(
            signature,
            'TGRZUlGLWUhTbI23XeS9cPik8UX1PAtXblmya0hW2Piz5yjsDEB9yr1OqClKKiPjpKrtSfPiQjZL6Bp2WB3YBg=='
        )

    def test_verify_signed_message(self):  # noqa: D102
        self.assertTrue(
            near.verify_signed_message(
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
            near.verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                illegal_message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )

    def test_verify_signed_message_with_expired_nonce(self):  # noqa: D102
        self.account_id = "dev.near"
        self.callback_url = None
        self.message = "Hello from past"
        self.recipient = "future.near"
        self.nonce = "1000000000000"
        self.public_key = "ed25519:2aPrik9S1qCnnfNo2doETrNa61ZaBwZYC8baschK5din"
        self.signature = ".mdwjNstfX6o2rD1aXNTpAtdhame/t+3AE2gqPAWhmc4tbn9i7UjLeQJDlnF9wHNhhEiaa90lxgavBZBXcXgdBg=="

        with self.assertRaises(ValueError) as context:
            near.verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                self.message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )

        self.assertEqual(str(context.exception), "Nonce is too old")

    def test_verify_signed_message_with_timestamp_nonce(self):  # noqa: D102
        self.account_id = "zavodil.near"
        self.callback_url = "http://localhost:5173?message=Welcome+to+NEAR+AI+Hub%21&recipient=ai.near&nonce=00000000000000000001722333704261&type=remote"
        self.message = "Welcome to NEAR AI Hub!"
        self.recipient = "ai.near"
        self.nonce = "1722333704261"
        self.public_key = "ed25519:HFd5upW3ppKKqwmNNbm56JW7VHXzEoDpwFKuetXLuNSq"
        self.signature = "f527uJAg0o60I1BozX+zo0NrAmOdw9UdXvmLGQoA2i/gkOGTeR9AMH1sJQQdCSA4RGrOnyyKfaLTbjGWW6uTAQ=="

        self.assertTrue(
            near.verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                self.message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )


if __name__ == "__main__":
    unittest.main()
