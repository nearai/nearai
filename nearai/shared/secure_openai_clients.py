from typing import Any

from openai import AsyncOpenAI, OpenAI


class SecureOpenAI:
    """Secure OpenAI client where api key is only accessible in constructor."""

    def __init__(self, api_key, base_url, **kwargs: Any) -> None:
        """Initialize with auth token that's only accessible in constructor."""
        client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)

        # Define secure method using closure
        def create(self, **params: Any) -> Any:
            """Create a chat completion with secure auth."""
            return client.chat.completions.create(**params)

        # Create completions class
        CompletionsClass = type("Completions", (), {"create": create})  # noqa: N806

        # Create chat class
        ChatClass = type("Chat", (), {"completions": CompletionsClass()})  # noqa: N806

        # Attach chat instance
        self.chat = ChatClass()


class SecureAsyncOpenAI:
    """Secure Async OpenAI client where api key is only accessible in constructor."""

    def __init__(self, api_key, base_url, **kwargs: Any) -> None:
        """Initialize with auth token that's only accessible in constructor."""
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, **kwargs)

        # Define secure method using closure
        async def create(self, **params: Any) -> Any:
            """Create a chat completion with secure auth."""
            return await client.chat.completions.create(**params)

        # Create completions class
        CompletionsClass = type("AsyncCompletions", (), {"create": create})  # noqa: N806

        # Create chat class
        ChatClass = type("AsyncChat", (), {"completions": CompletionsClass()})  # noqa: N806

        # Attach chat instance
        self.chat = ChatClass()
