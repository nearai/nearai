"""Unit tests for the cache manager.

These tests verify that the cache manager properly isolates state
between invocations and prevents state leakage.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from nearai.aws_runner.cache_manager import CacheManager


class TestCacheManager(unittest.TestCase):
    """Test the cache manager functionality."""

    def setUp(self):
        """Initialize a cache manager for testing."""
        self.cache_manager = CacheManager()
        # Initialize base modules with current sys.modules state
        self.cache_manager._base_modules = set(sys.modules.keys())
        self.cache_manager._initialize()

    def test_agent_cache_isolation(self):
        """Test that agent cache properly isolates state."""
        # Create a mock agent with a valid identifier format
        mock_agent = MagicMock()
        mock_agent.identifier = "test/test_agent/1.0.0"
        mock_agent.agent_files = [{"filename": "test.py", "content": "print('hello')"}]
        mock_agent.metadata = {"name": "TestAgent", "version": "1.0.0"}

        # Cache the agent
        self.cache_manager.cache_agent(mock_agent)

        # Modify the original agent (simulating state changes during execution)
        mock_agent.agent_files[0]["content"] = "print('modified')"
        mock_agent.metadata["status"] = "modified"

        # Create a mock Agent class that will be returned by patch
        mock_agent_instance = MagicMock()
        mock_agent_class = MagicMock(return_value=mock_agent_instance)

        # Retrieve from cache with mocked Agent class
        with patch("nearai.aws_runner.cache_manager.Agent", mock_agent_class):
            # Get the agent from cache
            self.cache_manager.get_agent("test/test_agent/1.0.0")

            # Verify Agent constructor was called
            self.assertTrue(mock_agent_class.called, "Agent constructor was not called")

            # Check that Agent constructor was called with the original data
            # (Deep copy should have preserved the original values)
            constructor_args = mock_agent_class.call_args[0]
            self.assertEqual(constructor_args[0], "test/test_agent/1.0.0")

            # Check the content of the files (should be the original, not modified)
            files_arg = mock_agent_class.call_args[0][1]
            self.assertEqual(files_arg[0]["content"], "print('hello')")

            # Check the metadata (should not contain the modifications)
            metadata_arg = mock_agent_class.call_args[0][2]
            self.assertEqual(metadata_arg["name"], "TestAgent")
            self.assertNotIn("status", metadata_arg)

    def test_provider_models_cache(self):
        """Test the provider models cache functionality."""
        # Create mock provider models
        mock_models = {"model1": {"type": "text"}, "model2": {"type": "image"}}

        # Cache the models
        self.cache_manager.cache_provider_models(mock_models)

        # Modify the original data
        mock_models["model3"] = {"type": "audio"}
        mock_models["model1"]["modified"] = True

        # Retrieve from cache and verify isolation
        retrieved_models, age = self.cache_manager.get_provider_models()

        # Models should be isolated from modifications
        self.assertIn("model1", retrieved_models)
        self.assertIn("model2", retrieved_models)
        self.assertNotIn("model3", retrieved_models)
        self.assertNotIn("modified", retrieved_models["model1"])

        # Age should be small (just created)
        self.assertLess(age, 1.0)

    def test_module_singleton_reset(self):
        """Test that our singleton reset functionality works correctly."""

        # Create a simple singleton class
        class Singleton:
            _instance = None

            @classmethod
            def get_instance(cls):
                if cls._instance is None:
                    cls._instance = cls()
                return cls._instance

            def __init__(self):
                self.data = {}

            def set_data(self, key, value):
                self.data[key] = value

            def get_data(self, key):
                return self.data.get(key)

        # Create an instance and set some data
        instance = Singleton.get_instance()
        instance.set_data("test", "value")

        # Verify the singleton is working as expected
        self.assertIs(Singleton.get_instance(), instance)
        self.assertEqual(Singleton.get_instance().get_data("test"), "value")

        # Create a simple module-like object with our singleton class
        test_module = types.ModuleType("test_singleton_module")
        test_module.Singleton = Singleton

        # Import and use reset_module_singletons directly from agent.py
        from nearai.agents.agent import reset_module_singletons

        # Apply the singleton reset function
        reset_module_singletons(test_module)

        # Verify the singleton instance was reset
        self.assertIsNone(Singleton._instance)

        # Get a new instance and verify it's fresh
        new_instance = Singleton.get_instance()
        self.assertIsNotNone(new_instance)
        self.assertIsNot(new_instance, instance)
        self.assertIsNone(new_instance.get_data("test"))


if __name__ == "__main__":
    unittest.main()
