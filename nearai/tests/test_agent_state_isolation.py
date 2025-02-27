import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nearai.agents.agent import Agent, clear_module_cache


class TestAgentStateIsolation(unittest.TestCase):
    """Test suite for agent state isolation and singleton management.

    These tests validate that our module cache clearing approach
    effectively prevents state leakage between invocations.
    """

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory to mimic agent files
        self.temp_dir = tempfile.mkdtemp()

        # Create a simple agent file with a singleton pattern
        self.agent_file_path = os.path.join(self.temp_dir, "agent.py")
        with open(self.agent_file_path, "w") as f:
            f.write("""
# Simple agent with a singleton pattern
class Context:
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

# Create a function that uses the singleton
def process_task(env, task=None):
    ctx = Context.get_instance()

    # Check if we've seen data from before
    previous_task = ctx.get_data('previous_task')

    # Store current task
    ctx.set_data('previous_task', task)

    # Return both current and previous task to check for leakage
    return {
        'current_task': task,
        'previous_task': previous_task,
        'result': f"Processed: {task}"
    }
""")

        # Create agent metadata
        self.agent_metadata = {
            "name": "test_agent",
            "version": "1.0.0",
            "details": {
                "agent": {"welcome": {"title": "Test Agent", "description": "A test agent for isolation tests"}}
            },
        }

    def tearDown(self):
        """Clean up after tests."""
        # Remove temp files and directory
        import shutil

        shutil.rmtree(self.temp_dir)

        # Make sure we remove any test modules from sys.modules
        for mod_name in list(sys.modules.keys()):
            if mod_name == "agent" or mod_name.startswith("test_agent"):
                del sys.modules[mod_name]

    def test_singleton_reset_method(self):
        """Test that the clear_module_cache method properly resets singletons."""
        # Create an agent with required parameters (using valid identifier format)
        agent = Agent("test/test-agent/1.0.0", self.temp_dir, self.agent_metadata)
        agent.agent_filename = self.agent_file_path

        # Import the test module with singleton
        sys.path.insert(0, self.temp_dir)
        import agent as test_agent

        # Create and populate the singleton
        ctx = test_agent.Context.get_instance()
        ctx.set_data("test_key", "test_value")

        # Verify data is stored
        self.assertEqual(ctx.get_data("test_key"), "test_value")

        # Now clear module cache
        agent.clear_module_cache()

        # The singleton should be reset
        new_ctx = test_agent.Context.get_instance()
        self.assertIsNone(new_ctx.get_data("test_key"))

        # Clean up
        sys.path.remove(self.temp_dir)
        if "agent" in sys.modules:
            del sys.modules["agent"]

    def test_module_level_function(self):
        """Test that clearing module cache with the standalone function works."""
        # Import the test module with singleton
        sys.path.insert(0, self.temp_dir)
        import agent as test_agent

        # Create and populate the singleton
        ctx = test_agent.Context.get_instance()
        ctx.set_data("user", "User1")

        # We need to mock or replace sys.modules with something we can control
        # for the standalone function test since we're not importing agent module directly

        # Option 1: Add the actual agent module to our test modules list
        modules_to_clear = ["agent"]

        # This simulates the global namespace that the module would be imported into
        namespace = {}

        # Call the standalone function to clear the module
        clear_module_cache(modules_to_clear, namespace)

        # After clearing the module, get a new singleton instance
        new_ctx = test_agent.Context.get_instance()
        self.assertIsNone(new_ctx.get_data("user"), "Singleton instance was not reset properly")

        # Clean up
        sys.path.remove(self.temp_dir)

    def test_singleton_persistence_without_clearing(self):
        """Test that demonstrates state persistence without proper clearing."""
        # This test simulates what happens in Lambda without our solution

        # Import the test module with singleton
        sys.path.insert(0, self.temp_dir)
        import agent as test_agent

        # First invocation
        ctx1 = test_agent.Context.get_instance()
        ctx1.set_data("user", "User1")

        # Simulate Lambda container reuse (not cleaning up state)
        # Second invocation (same process, would be different Lambda invocation)
        ctx2 = test_agent.Context.get_instance()

        # State leakage would expose User1's data to User2
        self.assertEqual(ctx2.get_data("user"), "User1")

        # Clean up
        sys.path.remove(self.temp_dir)
        if "agent" in sys.modules:
            del sys.modules["agent"]


if __name__ == "__main__":
    unittest.main()
