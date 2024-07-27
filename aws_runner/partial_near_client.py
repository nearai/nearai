from openapi_client.models.request import Request
from openapi_client.api.default_api import DefaultApi
from openapi_client.models.chat_completions_request import ChatCompletionsRequest


class MockRegistry:
    def __init__(self):
        self.entries = {}

    def upload(self, **kwargs):
        return "mock_registry_id"


class PartialNearClient:
    """Mocks NearAI api registry methods, uses generated NearAI client for completion calls"""
    def __init__(self, client):
        self._client = client

    def completions(self, model, messages, stream=False, temperature=None, **kwargs):
        api_instance = DefaultApi(self._client)
        chat_completions_request = ChatCompletionsRequest(
            provider="fireworks",  # todo remove this hardcoding
            model="accounts/fireworks/models/llama-v3-70b-instruct",  #model,
            messages=messages,
            stream=stream,
            temperature=temperature,
            **kwargs
        )
        request = Request(actual_instance=chat_completions_request, anyof_schema_1_validator=chat_completions_request)
        api_response = api_instance.chat_completions_v1_chat_completions_post(request)

        return api_response

    def get_registry_entry_by_identifier(self, identifier, fail_if_not_found=True):
        print("Mock get_registry_entry_by_identifier call")
        return None

    def registry(self):
        return MockRegistry()