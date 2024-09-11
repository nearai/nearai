import re
from typing import List

from openapi_client import (
    BodyDownloadEnvironmentV1DownloadEnvironmentPost,
    BodyDownloadFileV1RegistryDownloadFilePost,
    BodyListFilesV1RegistryListFilesPost,
    BodyUploadMetadataV1RegistryUploadMetadataPost,
)
from openapi_client.api.agents_assistants_api import AgentsAssistantsApi
from openapi_client.api.default_api import DefaultApi
from openapi_client.api.registry_api import RegistryApi
from openapi_client.models.chat_completions_request import ChatCompletionsRequest
from openapi_client.models.request import Request
from runner.environment import ENVIRONMENT_FILENAME


class PartialNearClient:
    """Wrap NearAI api registry methods, uses generated NearAI client."""

    def __init__(self, client, auth: dict):  # noqa: D107
        self._client = client
        self.entry_location_pattern = re.compile("^(?P<namespace>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)$")
        self.auth = auth

    def completions(self, model, messages, stream=False, temperature=None, **kwargs):
        """Calls NearAI Api to return all completions for given messages using the given model."""
        api_instance = DefaultApi(self._client)
        chat_completions_request = ChatCompletionsRequest(
            # todo move model mappings into hub
            model="fireworks::accounts/fireworks/models/llama-v3p1-405b-instruct-long",
            messages=messages,
            stream=stream,
            temperature=temperature,
            **kwargs,
        )
        request = Request(actual_instance=chat_completions_request, anyof_schema_1_validator=chat_completions_request)
        api_response = api_instance.chat_completions_v1_chat_completions_post(request)

        return api_response

    def parse_location(self, entry_location: str) -> dict:
        """Create a EntryLocation from a string in the format namespace/name/version."""
        match = self.entry_location_pattern.match(entry_location)

        if match is None:
            raise ValueError(
                f"Invalid entry format: {entry_location}. Should have the format <namespace>/<name>/<version>"
            )

        return {
            "namespace": match.group("namespace"),
            "name": match.group("name"),
            "version": match.group("version"),
        }

    def get_file_from_registry(self, entry_location: dict, path: str):
        """Fetches a file from NearAI registry."""
        api_instance = RegistryApi(self._client)
        result = api_instance.download_file_v1_registry_download_file_post(
            BodyDownloadFileV1RegistryDownloadFilePost.from_dict(
                dict(
                    entry_location=entry_location,
                    path=path,
                )
            )
        )
        return result

    def list_files(self, entry_location: dict) -> List[str]:
        """List files in from an entry in the registry.

        Return the relative paths to all files with respect to the root of the entry.
        """
        api_instance = RegistryApi(self._client)
        result = api_instance.list_files_v1_registry_list_files_post(
            BodyListFilesV1RegistryListFilesPost.from_dict(dict(entry_location=entry_location))
        )
        return [file.filename for file in result]

    def get_files_from_registry(self, entry_location: dict):
        """Fetches all files from NearAI registry."""
        api_instance = RegistryApi(self._client)

        files = self.list_files(entry_location)
        results = []

        for path in files:
            result = api_instance.download_file_v1_registry_download_file_post(
                BodyDownloadFileV1RegistryDownloadFilePost.from_dict(
                    dict(
                        entry_location=entry_location,
                        path=path,
                    )
                )
            )
            results.append({"filename": path, "content": result})
        return results

    def get_agent(self, identifier):
        """Fetches an agent from NearAI registry."""
        entry_location = self.parse_location(identifier)
        # download all agent files
        return self.get_files_from_registry(entry_location)

    def get_environment(self, env_id):
        """Fetches an environment from NearAI registry."""
        entry_location = self.parse_location(env_id)
        api_instance = AgentsAssistantsApi(self._client)
        result = api_instance.download_environment_v1_download_environment_post(
            BodyDownloadEnvironmentV1DownloadEnvironmentPost.from_dict(
                dict(
                    entry_location=entry_location,
                    path=ENVIRONMENT_FILENAME,
                )
            ),
            _headers={"Accept": "application/gzip"},
        )
        return result

    def save_environment(self, file: bytes, name: str, description: str, details: dict, tags: List[str]) -> str:
        """Saves an environment to NearAI registry."""
        api_instance = RegistryApi(self._client)

        author = self.auth.get("account_id")
        metadata = {
            "category": "environment",
            "description": description,
            "details": details,
            "tags": tags,
            "show_entry": True,
        }
        entry_location = {"namespace": author, "name": name, "version": "0"}
        api_instance.upload_metadata_v1_registry_upload_metadata_post(
            BodyUploadMetadataV1RegistryUploadMetadataPost(metadata=metadata, entry_location=entry_location)
        )

        api_instance.upload_file_v1_registry_upload_file_post(
            path=ENVIRONMENT_FILENAME,
            file=file,
            namespace=entry_location["namespace"],
            name=entry_location["name"],
            version=entry_location["version"],
        )
        return f"{author}/{name}/0"
