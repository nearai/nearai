import os
import unittest

from jasnah.agent import Agent
from jasnah.environment import Environment
from jasnah.config import CONFIG
from jasnah.registry import Registry

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_REGISTRY_ID = 81  # this is a valid registry id of a previous test run containing an empty chat.txt


class TestEnvironment(unittest.TestCase):
    """Integration tests for saving and loading Environments"""

    def test_save_without_base_id(self):
        test_dir= TEST_DIR
        path = f'{test_dir}/test-agents/test'
        agent = Agent('test', path, 'test')
        _agents = [agent]
        registry = Registry([])
        env = Environment(path, _agents, CONFIG.llm_config, registry, 'unittest_user')
        run_id = env._generate_run_id()

        assert env.save_to_registry("test", run_id, "unittest-save") is not None

    def test_load_by_registry_id(self):
        test_dir= TEST_DIR
        path = f'{test_dir}/test-agents/test'
        if os.path.exists(path):
            for file in os.listdir(path):
                print(f"Removing {file}")
                os.remove(os.path.join(path, file))

        agent = Agent('test', path, 'test')
        _agents = [agent]
        registry = Registry([])
        env = Environment(path, _agents, CONFIG.llm_config, registry, 'unittest_user')
        env.load_from_registry(str(SAVED_REGISTRY_ID))

        assert os.path.exists(f'{path}/chat.txt')


if __name__ == '__main__':
    unittest.main()