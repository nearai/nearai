import os
import unittest

from nearai.agents.agent import Agent
from nearai.config import CONFIG
from nearai.db import db
from nearai.agents.environment import Environment

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_REGISTRY_ID = 81  # this is a valid registry id of a previous test run containing an empty chat.txt


class TestEnvironment(unittest.TestCase):
    """Integration tests for saving and loading Environments"""

    def test_save_without_base_id(self):
        test_dir = TEST_DIR
        path = f"{test_dir}/test-agents/test"
        agent = Agent("test", path, "test")
        _agents = [agent]
        env = Environment(path, _agents, CONFIG)
        run_id = env._generate_run_id()

        assert env.save_to_registry("test", run_id) is not None

    def test_save_with_base_id(self):
        test_dir = TEST_DIR
        path = f"{test_dir}/test-agents/test"
        agent = Agent("test", path, "test")
        _agents = [agent]
        env = Environment(path, _agents, CONFIG)
        run_id = env._generate_run_id()

        assert env.save_to_registry("test", run_id, "unittest-save") is not None
        generated_name = f"environment_run_test_{run_id}"
        registry_entry = db.get_registry_entry_by_identifier(generated_name)
        assert registry_entry is not None
        assert registry_entry.details[0]["base_id"] == "unittest-save"

    def test_save_as_name(self):
        test_dir = TEST_DIR
        path = f"{test_dir}/test-agents/test"
        agent = Agent("test", path, "test")
        _agents = [agent]
        env = Environment(path, _agents, CONFIG)
        run_id = env._generate_run_id()

        assert env.save_to_registry("test", run_id, None, "unittest-base") is not None

    def test_load_by_registry_id(self):
        test_dir = TEST_DIR
        path = f"{test_dir}/test-agents/test"
        if os.path.exists(path):
            for file in os.listdir(path):
                print(f"Removing {file}")
                os.remove(os.path.join(path, file))

        agent = Agent("test", path, "test")
        _agents = [agent]
        env = Environment(path, _agents, CONFIG)
        env.load_from_registry(str(SAVED_REGISTRY_ID))

        assert os.path.exists(f"{path}/chat.txt")


if __name__ == "__main__":
    unittest.main()
