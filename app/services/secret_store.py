"""Encrypted secret storage using Fernet symmetric encryption."""

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Fernet = None


class SecretStoreError(Exception):
    """Raised when a secret store operation fails."""
    pass


class FernetSecretStore:
    """Encrypted secret store using Fernet symmetric encryption."""

    def __init__(self, key: str):
        """Initialize with a base64-encoded Fernet key.

        Args:
            key: A valid Fernet encryption key (base64-encoded 32 bytes).
        """
        if not CRYPTO_AVAILABLE:
            raise SecretStoreError("cryptography library is not installed")
        try:
            self._fernet = Fernet(key.encode())
        except Exception as exc:
            raise SecretStoreError(f"Invalid Fernet key: {exc}")

    def encrypt(self, value: str) -> str:
        """Encrypt a string value.

        Args:
            value: The plaintext string to encrypt.

        Returns:
            The encrypted value as a base64-encoded string.
        """
        if not CRYPTO_AVAILABLE:
            raise SecretStoreError("cryptography library is not installed")
        try:
            return self._fernet.encrypt(value.encode()).decode()
        except Exception as exc:
            raise SecretStoreError(f"Encryption failed: {exc}")

    def decrypt(self, value: str) -> str:
        """Decrypt an encrypted value.

        Args:
            value: The encrypted string to decrypt.

        Returns:
            The decrypted plaintext string.
        """
        if not CRYPTO_AVAILABLE:
            raise SecretStoreError("cryptography library is not installed")
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except Exception as exc:
            raise SecretStoreError(f"Decryption failed: {exc}")


def get_secret_store() -> FernetSecretStore:
    """Get a configured FernetSecretStore instance.

    Returns:
        A FernetSecretStore configured with the APP_SECRET_KEY from settings.
    """
    from app.config import get_settings
    settings = get_settings()
    if not settings.APP_SECRET_KEY:
        raise SecretStoreError("APP_SECRET_KEY is not configured")
    return FernetSecretStore(settings.APP_SECRET_KEY)
