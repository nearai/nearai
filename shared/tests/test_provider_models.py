import unittest

from shared.naming import NamespacedName
from shared.provider_models import get_provider_namespaced_model


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


if __name__ == "__main__":
    unittest.main()
