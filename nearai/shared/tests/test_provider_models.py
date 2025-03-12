import unittest

from nearai.shared.naming import NamespacedName
from nearai.shared.provider_models import get_provider_namespaced_model


class TestGetProviderNamespacedModel(unittest.TestCase):
    """Unit tests for get_provider_namespaced_model."""

    def test_hyperbolic(self):  # noqa: D102
        self.assertEqual(
            get_provider_namespaced_model("hyperbolic::StableDiffusion"),
            ("hyperbolic", NamespacedName(name="StableDiffusion")),
        )
        self.assertEqual(
            get_provider_namespaced_model("hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
            ("hyperbolic", NamespacedName(name="Meta-Llama-3.1-70B-Instruct")),
        )

    def test_fireworks(self):  # noqa: D102
        self.assertEqual(
            get_provider_namespaced_model("fireworks::accounts/fireworks/models/mixtral-8x7b-instruct"),
            ("fireworks", NamespacedName(name="mixtral-8x7b-instruct")),
        )
        self.assertEqual(
            get_provider_namespaced_model("fireworks::accounts/yi-01-ai/models/yi-large"),
            ("fireworks", NamespacedName(name="yi-large", namespace="yi-01-ai")),
        )

    def test_url_provider(self):  # noqa: D102
        self.assertEqual(
            get_provider_namespaced_model("https://api.openai.com/v1::gpt-4o"),
            ("https://api.openai.com/v1", NamespacedName(name="gpt-4o")),
        )
        self.assertEqual(
            get_provider_namespaced_model("gpt-4o", provider="https://api.openai.com/v1"),
            ("https://api.openai.com/v1", NamespacedName(name="gpt-4o")),
        )

    def test_local_provider(self):  # noqa: D102
        self.assertEqual(
            get_provider_namespaced_model("local::llama3-70b"),
            ("local", NamespacedName(name="llama3-70b")),
        )
        self.assertEqual(
            get_provider_namespaced_model("mixtral-8x7b", provider="local"),
            ("local", NamespacedName(name="mixtral-8x7b")),
        )


if __name__ == "__main__":
    unittest.main()
