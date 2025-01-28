import json
from pathlib import Path
from shutil import copyfileobj
from typing import Any, Dict, List, Optional, Union

from tqdm import tqdm

# Note: We should import nearai.config on this file to make sure the method setup_api_client is called at least once
#       before creating RegistryApi object. This is because setup_api_client sets the default configuration for the
#       API client that is used by Registry API.
from nearai.config import CONFIG, DATA_FOLDER
from nearai.lib import check_metadata, parse_location
from nearai.openapi_client import EntryInformation, EntryLocation, EntryMetadata, EntryMetadataInput
from nearai.openapi_client.api.registry_api import (
    BodyDownloadFileV1RegistryDownloadFilePost,
    BodyDownloadMetadataV1RegistryDownloadMetadataPost,
    BodyListFilesV1RegistryListFilesPost,
    BodyUploadMetadataV1RegistryUploadMetadataPost,
    RegistryApi,
)
from nearai.openapi_client.exceptions import BadRequestException, NotFoundException
from nearai.shared.naming import NamespacedName, get_canonical_name

REGISTRY_FOLDER = "registry"


def get_registry_folder() -> Path:
    """Path to local registry."""
    return DATA_FOLDER / REGISTRY_FOLDER


def get_namespace(local_path: Path) -> str:
    """Returns namespace of an item or user namespace."""
    registry_folder = get_registry_folder()

    try:
        # Check if the path matches the expected structure
        relative_path = local_path.relative_to(registry_folder)
        parts = relative_path.parts

        # If the path has 3 parts (namespace, item_name, version),
        # return the first part as the namespace
        if len(parts) == 3:
            return str(parts[0])
    except ValueError:
        # relative_to() raises ValueError if local_path is not relative to registry_folder
        pass

    # If we couldn't extract a namespace from the path, return the default
    if CONFIG.auth is None:
        raise ValueError("AuthData is None")
    return CONFIG.auth.namespace


class Registry:
    def __init__(self):
        """Create Registry object to interact with the registry programmatically."""
        self.download_folder = DATA_FOLDER / "registry"
        self.api = RegistryApi()

        if not self.download_folder.exists():
            self.download_folder.mkdir(parents=True, exist_ok=True)

    def update(self, entry_location: EntryLocation, metadata: EntryMetadataInput) -> Dict[str, Any]:
        """Update metadata of a entry in the registry."""
        result = self.api.upload_metadata_v1_registry_upload_metadata_post(
            BodyUploadMetadataV1RegistryUploadMetadataPost(metadata=metadata, entry_location=entry_location)
        )
        return result

    def info(self, entry_location: EntryLocation) -> Optional[EntryMetadata]:
        """Get metadata of a entry in the registry."""
        try:
            return self.api.download_metadata_v1_registry_download_metadata_post(
                BodyDownloadMetadataV1RegistryDownloadMetadataPost.from_dict(dict(entry_location=entry_location))
            )
        except NotFoundException:
            return None

    def upload_file(self, entry_location: EntryLocation, local_path: Path, path: Path) -> bool:
        """Upload a file to the registry."""
        with open(local_path, "rb") as file:
            data = file.read()

            try:
                self.api.upload_file_v1_registry_upload_file_post(
                    path=str(path),
                    file=data,
                    namespace=entry_location.namespace,
                    name=entry_location.name,
                    version=entry_location.version,
                )
                return True
            except BadRequestException as e:
                if isinstance(e.body, str) and "already exists" in e.body:
                    return False

                raise e

    def download_file(self, entry_location: EntryLocation, path: Path, local_path: Path):
        """Download a file from the registry."""
        result = self.api.download_file_v1_registry_download_file_post_without_preload_content(
            BodyDownloadFileV1RegistryDownloadFilePost.from_dict(
                dict(
                    entry_location=entry_location,
                    path=str(path),
                )
            )
        )

        local_path.parent.mkdir(parents=True, exist_ok=True)

        with open(local_path, "wb") as f:
            copyfileobj(result, f)

    def download(
        self,
        entry_location: Union[str, EntryLocation],
        force: bool = False,
        show_progress: bool = False,
        verbose: bool = True,
    ) -> Path:
        """Download entry from the registry locally."""
        if isinstance(entry_location, str):
            entry_location = parse_location(entry_location)

        download_path = get_registry_folder() / entry_location.namespace / entry_location.name / entry_location.version

        if download_path.exists():
            if not force:
                if verbose:
                    print(
                        f"Entry {entry_location} already exists at {download_path}. Use --force to overwrite the entry."
                    )
                return download_path

        files = registry.list_files(entry_location)

        download_path.mkdir(parents=True, exist_ok=True)

        metadata = registry.info(entry_location)

        if metadata is None:
            raise ValueError(f"Entry {entry_location} not found.")

        metadata_path = download_path / "metadata.json"
        with open(metadata_path, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        for file in (pbar := tqdm(files, disable=not show_progress)):
            pbar.set_description(file)
            registry.download_file(entry_location, file, download_path / file)

        return download_path

    def upload(
        self,
        local_path: Path,
        metadata: Optional[EntryMetadata] = None,
        show_progress: bool = False,
    ) -> EntryLocation:
        """Upload entry to the registry.

        If metadata is provided it will overwrite the metadata in the directory,
        otherwise it will use the metadata.json found on the root of the directory.
        """
        path = Path(local_path).absolute()

        if not path.exists():
            # try path in local registry if original path not exists
            path = get_registry_folder() / local_path

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"

        if metadata is not None:
            with open(metadata_path, "w") as f:
                f.write(metadata.model_dump_json(indent=2))

        check_metadata(metadata_path)

        with open(metadata_path) as f:
            plain_metadata: Dict[str, Any] = json.load(f)

        namespace = get_namespace(local_path)
        name = plain_metadata.pop("name")

        entry_location = EntryLocation.model_validate(
            dict(
                namespace=namespace,
                name=name,
                version=plain_metadata.pop("version"),
            )
        )

        entry_metadata = EntryMetadataInput.model_validate(plain_metadata)
        source = entry_metadata.details.get("_source", None)

        if source is not None:
            print(f"Only default source is allowed, found: {source}. Remove details._source from metadata.")
            exit(1)

        if self.info(entry_location) is None:
            # New entry location. Check for similar names in registry.
            entries = self.list_all_visible()
            canonical_namespace = get_canonical_name(namespace)
            canonical_name = get_canonical_name(name)

            for entry in entries:
                if entry.name == name and entry.namespace == namespace:
                    break
                if (
                    get_canonical_name(entry.name) == canonical_name
                    and get_canonical_name(entry.namespace) == canonical_namespace
                ):
                    print(f"A registry item with a similar name already exists: {entry.namespace}/{entry.name}")
                    exit(1)

        registry.update(entry_location, entry_metadata)

        all_files = []
        total_size = 0

        # Traverse all files in the directory `path`
        for file in path.rglob("*"):
            if not file.is_file():
                continue

            relative = file.relative_to(path)

            # Don't upload metadata file.
            if file == metadata_path:
                continue

            # Don't upload backup files.
            if file.name.endswith("~"):
                continue

            # Don't upload configuration files.
            if relative.parts[0] == ".nearai":
                continue

            size = file.stat().st_size
            total_size += size

            all_files.append((file, relative, size))

        pbar = tqdm(total=total_size, unit="B", unit_scale=True, disable=not show_progress)
        for file, relative, size in all_files:
            if "__pycache__" in relative.parts:
                continue
            registry.upload_file(entry_location, file, relative)
            pbar.update(size)

        return entry_location

    def list_files(self, entry_location: EntryLocation) -> List[str]:
        """List files in from an entry in the registry.

        Return the relative paths to all files with respect to the root of the entry.
        """
        result = self.api.list_files_v1_registry_list_files_post(
            BodyListFilesV1RegistryListFilesPost.from_dict(dict(entry_location=entry_location))
        )
        return [file.filename for file in result]

    def list(
        self,
        namespace: str,
        category: str,
        tags: str,
        total: int,
        offset: int,
        show_all: bool,
        show_latest_version: bool,
        starred_by: str = "",
    ) -> List[EntryInformation]:
        """List and filter entries in the registry."""
        return self.api.list_entries_v1_registry_list_entries_post(
            namespace=namespace,
            category=category,
            tags=tags,
            total=total,
            offset=offset,
            show_hidden=show_all,
            show_latest_version=show_latest_version,
            starred_by=starred_by,
        )

    def list_all_visible(self, category: str = "") -> List[EntryInformation]:
        """List all visible entries."""
        total = 10000
        entries = self.list(
            namespace="",
            category=category,
            tags="",
            total=total,
            offset=0,
            show_all=False,
            show_latest_version=True,
        )
        assert len(entries) < total
        return entries

    def dict_models(self) -> Dict[NamespacedName, NamespacedName]:
        """Returns a mapping canonical->name."""
        entries = self.list_all_visible(category="model")
        result: Dict[NamespacedName, NamespacedName] = {}
        for entry in entries:
            namespaced_name = NamespacedName(name=entry.name, namespace=entry.namespace)
            canonical_namespaced_name = namespaced_name.canonical()
            if canonical_namespaced_name in result:
                raise ValueError(
                    f"Duplicate registry entry for model {namespaced_name}, canonical {canonical_namespaced_name}"
                )
            result[canonical_namespaced_name] = namespaced_name
        return result


registry = Registry()
