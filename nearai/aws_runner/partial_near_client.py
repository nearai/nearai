import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

from nearai.openapi_client import (
    BodyDownloadFileV1RegistryDownloadFilePost,
    BodyDownloadMetadataV1RegistryDownloadMetadataPost,
    BodyListFilesV1RegistryListFilesPost,
)
from nearai.openapi_client.api.registry_api import RegistryApi
from nearai.openapi_client.api_client import ApiClient
from nearai.openapi_client.configuration import Configuration
from nearai.openapi_client.models.body_upload_metadata_v1_registry_upload_metadata_post import (
    BodyUploadMetadataV1RegistryUploadMetadataPost,
)
from nearai.openapi_client.models.entry_location import EntryLocation
from nearai.openapi_client.models.entry_metadata_input import EntryMetadataInput
from nearai.shared.auth_data import AuthData

ENVIRONMENT_FILENAME = "environment.tar.gz"


class PartialNearClient:
    """Wrap NEAR AI api registry methods, uses generated NEAR AI client."""

    def __init__(self, base_url: str, auth: AuthData):  # noqa: D107
        configuration = Configuration(access_token=f"Bearer {auth.model_dump_json()}", host=base_url)
        client = ApiClient(configuration)

        self._client = client
        self.entry_location_pattern = re.compile("^(?P<namespace>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)$")
        self.auth = auth

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
        """Fetches a file from NEAR AI registry."""
        api_instance = RegistryApi(self._client)
        body = BodyDownloadFileV1RegistryDownloadFilePost.from_dict(
            dict(
                entry_location=entry_location,
                path=path,
            )
        )
        assert body is not None, (
            f"Unable to create request body for file download. Entry location: {entry_location}, Path: {path}"
        )
        result = api_instance.download_file_v1_registry_download_file_post(body)
        return result

    def list_files(self, entry_location: dict) -> List[str]:
        """List files in an entry in the registry.

        Return the relative paths to all files with respect to the root of the entry.
        """
        api_instance = RegistryApi(self._client)
        body = BodyListFilesV1RegistryListFilesPost.from_dict(dict(entry_location=entry_location))
        assert body is not None, f"Unable to create request body for file listing. Entry location: {entry_location}"
        result = api_instance.list_files_v1_registry_list_files_post(body)
        return [file.filename for file in result]

    def get_files_from_registry(self, entry_location: dict):
        """Fetches all files from NEAR AI registry."""
        api_instance = RegistryApi(self._client)

        files = self.list_files(entry_location)
        results = []

        with ThreadPoolExecutor() as executor:
            tasks = {}
            for path in files:
                if path is None:
                    continue
                body = BodyDownloadFileV1RegistryDownloadFilePost.from_dict(
                    dict(entry_location=entry_location, path=path)
                )
                if body is None:
                    continue
                future = executor.submit(
                    api_instance.download_file_v1_registry_download_file_post,
                    body,
                )
                tasks[future] = path

            for future in as_completed(tasks):
                path = tasks[future]
                result = future.result()
                results.append({"filename": path, "content": result})
            return results

    def get_agent_metadata(self, identifier: str) -> dict:
        """Fetches metadata for an agent from NEAR AI registry."""
        api_instance = RegistryApi(self._client)
        entry_location = self.parse_location(identifier)
        body = BodyDownloadMetadataV1RegistryDownloadMetadataPost.from_dict(dict(entry_location=entry_location))
        assert body is not None, f"Unable to create request body for agent metadata. Entry location: {entry_location}"
        result = api_instance.download_metadata_v1_registry_download_metadata_post(body)
        return result.to_dict()

    def get_agent(self, identifier):
        """Fetches an agent from NEAR AI registry."""
        entry_location = self.parse_location(identifier)
        # download all agent files
        files = self.get_files_from_registry(entry_location)
        # Add metadata as a file
        files.append({"filename": "metadata.json", "content": self.get_agent_metadata(identifier)})
        return files

    def upload_new_entry(self, local_path: Path):
        """Uploads new entry (e.g. analytics entry) to NEAR AI registry."""
        path = Path(local_path).absolute()
        metadata_path = path / "metadata.json"
        with open(metadata_path) as f:
            plain_metadata: Dict[str, Any] = json.load(f)

        namespace = self.auth.namespace
        name = plain_metadata.pop("name")
        assert " " not in name

        entry_location = EntryLocation.model_validate(
            dict(
                namespace=namespace,
                name=name,
                version=plain_metadata.pop("version"),
            )
        )

        entry_metadata = EntryMetadataInput.model_validate(plain_metadata)
        api_instance = RegistryApi(self._client)

        # Upload metadata first
        api_instance.upload_metadata_v1_registry_upload_metadata_post(
            BodyUploadMetadataV1RegistryUploadMetadataPost(metadata=entry_metadata, entry_location=entry_location)
        )

        # Get all files in path
        entry_files = []
        for file_path in path.rglob("*"):
            if file_path.is_file():
                entry_files.append(file_path)

        for entry_file in entry_files:
            try:
                with open(entry_file, "rb") as file:
                    data = file.read()

                    # Get relative path from the base directory
                    relative_path = entry_file.relative_to(path)

                    api_instance.upload_file_v1_registry_upload_file_post(
                        path=str(relative_path),  # Use relative path
                        file=data,
                        namespace=entry_location.namespace,
                        name=entry_location.name,
                        version=entry_location.version,
                    )
            except Exception as e:
                print(f"Error uploading file {entry_file}: {e}")
                # Continue with other files instead of failing the entire upload
                continue
