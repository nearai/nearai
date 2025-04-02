import unittest

from nearai.shared.naming import get_canonical_name


class TestGetCanonicalName(unittest.TestCase):
    """Unit tests for get_canonical_name."""

    def test_lowercase_conversion(self):  # noqa: D102
        self.assertEqual(get_canonical_name("LLaMA"), "llama")

    def test_dot_to_p_conversion(self):  # noqa: D102
        self.assertEqual(get_canonical_name("model1.5"), "model1p5")

    def test_space_between_digits(self):  # noqa: D102
        self.assertEqual(get_canonical_name("3.1-70b"), "3p1_70b")
        self.assertEqual(get_canonical_name("3.1_70b"), "3p1_70b")
        self.assertEqual(get_canonical_name("3.1- -70b"), "3p1_70b")

    def test_remove_non_alphanumeric(self):  # noqa: D102
        self.assertEqual(get_canonical_name("llama-3.1-70b-instruct"), "llama3p1_70binstruct")

    def test_underscores(self):  # noqa: D102
        self.assertEqual(get_canonical_name("_"), "")
        self.assertEqual(get_canonical_name("a_"), "a")
        self.assertEqual(get_canonical_name("1_"), "1")
        self.assertEqual(get_canonical_name("_a"), "a")
        self.assertEqual(get_canonical_name("_1"), "1")
        self.assertEqual(get_canonical_name("a_a"), "aa")
        self.assertEqual(get_canonical_name("a_1"), "a1")
        self.assertEqual(get_canonical_name("1_a"), "1a")
        self.assertEqual(get_canonical_name("1_1"), "1_1")

        self.assertEqual(get_canonical_name("__"), "")
        self.assertEqual(get_canonical_name("a__"), "a")
        self.assertEqual(get_canonical_name("1__"), "1")
        self.assertEqual(get_canonical_name("__a"), "a")
        self.assertEqual(get_canonical_name("__1"), "1")
        self.assertEqual(get_canonical_name("a__a"), "aa")
        self.assertEqual(get_canonical_name("a__1"), "a1")
        self.assertEqual(get_canonical_name("1__a"), "1a")
        self.assertEqual(get_canonical_name("1__1"), "1_1")

    def test_metallama_conversion(self):  # noqa: D102
        self.assertEqual(get_canonical_name("metallama-3b"), "llama3b")

    def test_qwenq_conversion(self):  # noqa: D102
        self.assertEqual(get_canonical_name("qwen-qwq"), "qwq")

    def test_v_digit_conversion(self):  # noqa: D102
        self.assertEqual(get_canonical_name("llama-v2-7b"), "llama2_7b")
        self.assertEqual(get_canonical_name("gpt-v4"), "gpt4")
        self.assertEqual(get_canonical_name("v4"), "4")
        self.assertEqual(get_canonical_name("3v4"), "3_4")
        self.assertEqual(get_canonical_name("3 v4"), "3_4")
        self.assertEqual(get_canonical_name("mev4"), "mev4")

    def test_meta_llama_3p1_405b_instruct_match(self):  # noqa: D102
        self.assertEqual(
            get_canonical_name("Meta-Llama-3.1-405B-Instruct"), get_canonical_name("llama-v3p1-405b-instruct")
        )
        self.assertEqual(get_canonical_name("llama-3.1-405b-instruct"), get_canonical_name("llama-v3p1-405b-instruct"))

    def test_extensions(self):  # noqa: D102
        self.assertEqual(get_canonical_name("john_smith.near"), get_canonical_name("john_smith"))
        self.assertNotEqual(get_canonical_name("john_smith.ai"), get_canonical_name("john_smith"))
        self.assertNotEqual(get_canonical_name("john_smith.alpha"), get_canonical_name("john_smith"))
        self.assertNotEqual(get_canonical_name("john_smith.a"), get_canonical_name("john_smith"))
        self.assertNotEqual(get_canonical_name("john_smith.a"), get_canonical_name("john_smith.ai"))


if __name__ == "__main__":
    unittest.main()
