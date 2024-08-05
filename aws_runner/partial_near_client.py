from openapi_client.api.default_api import DefaultApi
from openapi_client.api.registry_api import RegistryApi
from openapi_client.models.chat_completions_request import ChatCompletionsRequest
from openapi_client.models.request import Request


class MockRegistry:
    def __init__(self):  # noqa: D107
        self.entries = {}

    def upload(self, **kwargs):
        """Mocked: Uploads an entry to the registry."""
        return "mock_registry_id"


class PartialNearClient:
    """Mocks NearAI api registry methods, uses generated NearAI client for completion calls."""

    def __init__(self, client):  # noqa: D107
        self._client = client

    def completions(self, model, messages, stream=False, temperature=None, **kwargs):
        """Calls NearAI Api to return all completions for given messages using the given model."""
        api_instance = DefaultApi(self._client)
        chat_completions_request = ChatCompletionsRequest(
            model="fireworks::accounts/fireworks/models/llama-v3-70b-instruct",  # todo move model mappings into hub
            messages=messages,
            stream=stream,
            temperature=temperature,
            **kwargs,
        )
        request = Request(actual_instance=chat_completions_request, anyof_schema_1_validator=chat_completions_request)
        api_response = api_instance.chat_completions_v1_chat_completions_post(request)

        return api_response

    def get_agent(self, identifier, fail_if_not_found=True):
        """Fetches an agent from NearAI registry."""
        api_instance = RegistryApi(self._client)
        return api_instance.get_agent_v1_registry_agents_name_get(identifier)

    def get_environment(self, env_id):
        """Fetches an environment from NearAI registry."""
        api_instance = RegistryApi(self._client)
        return api_instance.get_environment_v1_registry_environments_id_get(env_id)

    def save_environment(self):
        """Mocked: Saves an environment to NearAI registry."""
        print("save_environment is mocked")
        return None
