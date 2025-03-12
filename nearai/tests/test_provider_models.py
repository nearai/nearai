import unittest

from nearai.config import CONFIG
from nearai.shared.provider_models import ProviderModels


class TestMatchProviderModel(unittest.TestCase):
    """Unit tests for get_provider_namespaced_model."""

    def __init__(self, method_name="runTest"):  # noqa: D107
        super().__init__(method_name)
        self.provider_models = ProviderModels(CONFIG.get_client_config())

    def test_fireworks(self):  # noqa: D102
        self.assertEqual(
            self.provider_models.match_provider_model("fireworks::accounts/yi-01-ai/models/yi-large"),
            ("fireworks", "fireworks::accounts/yi-01-ai/models/yi-large"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("accounts/yi-01-ai/models/yi-large"),
            ("fireworks", "fireworks::accounts/yi-01-ai/models/yi-large"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("llama-v3-70b-instruct"),
            ("fireworks", "fireworks::accounts/fireworks/models/llama-v3-70b-instruct"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("yi-01-ai/yi-large"),
            ("fireworks", "fireworks::accounts/yi-01-ai/models/yi-large"),
        )

    def test_hyperbolic(self):  # noqa: D102
        self.assertEqual(
            self.provider_models.match_provider_model("hyperbolic::StableDiffusion"),
            ("hyperbolic", "hyperbolic::StableDiffusion"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("hyperbolic::Meta-Llama-3.1-70B-Instruct"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )

    def test_registry_with_multiple_providers(self):  # noqa: D102
        self.assertEqual(
            self.provider_models.match_provider_model("llama-3.1-70b-instruct"),
            ("fireworks", "fireworks::accounts/fireworks/models/llama-v3p1-70b-instruct"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("llama-3.1-70b-instruct", provider="hyperbolic"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )
        self.assertEqual(
            self.provider_models.match_provider_model("near.ai/llama-3.1-70b-instruct", provider="hyperbolic"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )


if __name__ == "__main__":
    unittest.main()
