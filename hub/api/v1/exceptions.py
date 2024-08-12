class TokenValidationError(Exception):
    """Custom exception for token validation errors."""

    def __init__(self, detail: str):  # noqa: D107
        self.detail = detail
