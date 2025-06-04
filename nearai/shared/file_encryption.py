import base64

from cryptography.fernet import Fernet

OBFUSCATED_SECRET = "<secret>"


class FileEncryption:
    """Handles file encryption and decryption for registry uploads."""

    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new encryption key.

        Returns:
            Base64-encoded encryption key string

        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode("utf-8")

    @staticmethod
    def encrypt_data(data: bytes, encryption_key: str) -> bytes:
        """Encrypt data using the provided encryption key.

        Args:
            data: Raw bytes to encrypt
            encryption_key: Base64-encoded encryption key

        Returns:
            Encrypted bytes

        """
        # Decode the base64 key
        key_bytes = base64.urlsafe_b64decode(encryption_key.encode("utf-8"))
        fernet = Fernet(key_bytes)
        return fernet.encrypt(data)

    @staticmethod
    def decrypt_data(encrypted_data: bytes, encryption_key: str) -> bytes:
        """Decrypt data using the provided encryption key.

        Args:
            encrypted_data: Encrypted bytes to decrypt
            encryption_key: Base64-encoded encryption key

        Returns:
            Decrypted bytes

        """
        # Decode the base64 key
        key_bytes = base64.urlsafe_b64decode(encryption_key.encode("utf-8"))
        fernet = Fernet(key_bytes)
        return fernet.decrypt(encrypted_data)
