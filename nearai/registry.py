import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from packaging.version import InvalidVersion, Version
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from tqdm import tqdm

# Note: We should import nearai.config on this file to make sure the method setup_api_client is called at least once
#       before creating RegistryApi object. This is because setup_api_client sets the default configuration for the
#       API client that is used by Registry API.
from nearai.agents.agent import get_local_agent_files
from nearai.config import CONFIG, DATA_FOLDER
from nearai.lib import check_metadata_present, parse_location
from nearai.openapi_client import EntryInformation, EntryLocation, EntryMetadata, EntryMetadataInput
from nearai.openapi_client.api.registry_api import (
    BodyDownloadFileV1RegistryDownloadFilePost,
    BodyDownloadMetadataV1RegistryDownloadMetadataPost,
    BodyListFilesV1RegistryListFilesPost,
    BodyUploadMetadataV1RegistryUploadMetadataPost,
    RegistryApi,
)
from nearai.openapi_client.exceptions import BadRequestException, NotFoundException
from nearai.shared.file_encryption import OBFUSCATED_SECRET, FileEncryption
from nearai.shared.naming import NamespacedName, get_canonical_name

REGISTRY_FOLDER = "registry"


def get_registry_folder() -> Path:
    """Path to local registry."""
    return DATA_FOLDER / REGISTRY_FOLDER


def resolve_local_path(local_path: Path) -> Path:
    """Determines if the `local_path` is `local_path` or `registry_folder/local_path`.

    Raises FileNotFoundError if folder or parent folder is not present.
    """
    if local_path.exists() or local_path.parent.exists():
        return local_path

    registry_path = get_registry_folder() / local_path
    if registry_path.exists() or registry_path.parent.exists():
        return registry_path

    # If neither exists, raise an error
    raise FileNotFoundError(f"Path not found: {local_path} or {registry_path}")


def get_namespace(local_path: Path) -> str:
    """Returns namespace of an item or user namespace."""
    registry_folder = get_registry_folder()

    try:
        # Check if the path matches the expected structure
        relative_path = local_path.relative_to(registry_folder)

    except ValueError:
        # If local_path is not relative to registry_folder, try resolving it to an absolute path
        local_path = local_path.resolve()
        try:
            # Retry checking if the now absolute path is within registry_folder
            relative_path = local_path.relative_to(registry_folder)
        except ValueError:
            relative_path = None
            pass

    if relative_path:
        parts = relative_path.parts

        # If the path has 3 parts (namespace, item_name, version),
        # return the first part as the namespace
        if len(parts) == 3:
            return str(parts[0])

    # If we couldn't extract a namespace from the path, return the default
    if CONFIG.auth is None:
        raise ValueError("AuthData is None")
    return CONFIG.auth.namespace


def get_agent_id(path: Path, local: bool) -> str:
    metadata = get_metadata(path, local)
    namespace = get_namespace(path)
    name = metadata["name"]
    assert " " not in name
    version = metadata["version"]
    return f"{namespace}/{name}/{version}"


def get_metadata(path: Path, local: bool) -> dict:
    if local:
        metadata_path = path / "metadata.json"
        with open(metadata_path) as f:
            return json.load(f)
    entry_location = parse_location(str(path))
    entry = registry.info(entry_location)
    assert entry
    return entry.to_dict()


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

    def upload_file(
        self, entry_location: EntryLocation, local_path: Path, path: Path, encryption_key: Optional[str] = None
    ) -> bool:
        """Upload a file to the registry."""
        with open(local_path, "rb") as file:
            data = file.read()

            # Encrypt data if encryption is enabled
            if encryption_key:
                data = FileEncryption.encrypt_data(data, encryption_key)

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

    def download_file(
        self, entry_location: EntryLocation, path: Path, local_path: Path, encryption_key: Optional[str] = None
    ):
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

        # Read all data first
        data = result.read()

        # Decrypt if necessary
        if encryption_key:
            try:
                data = FileEncryption.decrypt_data(data, encryption_key)
            except Exception as e:
                print(f"Error: Failed to decrypt file {path}: {str(e)}")
                # Continue with encrypted data - user might want to decrypt manually

        with open(local_path, "wb") as f:
            f.write(data)

    def download(
        self,
        entry_location: Union[str, EntryLocation],
        force: bool = False,
        show_progress: bool = False,
        verbose: bool = True,
        encryption_key: Optional[str] = None,
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
            if not encryption_key:
                metadata_on_disk = get_metadata(download_path, local=True)
                if metadata_on_disk:
                    encryption_key_from_metadata_on_disk = metadata_on_disk.get("details", {}).get(
                        "encryption_key", None
                    )
                    if encryption_key_from_metadata_on_disk != OBFUSCATED_SECRET:
                        encryption_key = encryption_key_from_metadata_on_disk

        files = registry.list_files(entry_location)

        metadata = registry.info(entry_location)

        if metadata is None:
            raise ValueError(f"Entry {entry_location} not found.")

        encryption_key_from_registry = metadata.details.get("encryption_key", None)
        if encryption_key_from_registry is None and encryption_key:
            print("This registry entry is not encrypted, but encryption_key has been provided. Aborting.")
            exit(1)
        if not encryption_key:
            encryption_key = encryption_key_from_registry
        if encryption_key == OBFUSCATED_SECRET:
            print(
                "This registry entry is encrypted. You must provide encryption_key (nearai registry download --encryption_key <secret>). Aborting."  # noqa: E501
            )
            exit(1)
        if encryption_key:
            metadata.details["encryption_key"] = encryption_key

        download_path.mkdir(parents=True, exist_ok=True)

        metadata_path = download_path / "metadata.json"
        with open(metadata_path, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        if encryption_key:
            print(f"Downloading encrypted registry entry and decrypting with encryption_key={encryption_key}")

        for file in (pbar := tqdm(files, disable=not show_progress)):
            pbar.set_description(file)
            registry.download_file(entry_location, file, download_path / file, encryption_key)

        return download_path

    def upload(
        self,
        local_path: Path,
        show_progress: bool = False,
        encrypt: bool = False,
    ) -> EntryLocation:
        """Upload entry to the registry.

        `local_path` should have metadata.json present.
        Files matching patterns in .gitignore (if present) will be excluded from upload.
        If encryption_key is present in metadata.json, uploaded files will be encrypted.
        If encrypt == True, will generate an encryption_key, if encryption_key is not present.
        """
        path = Path(local_path).absolute()

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"

        check_metadata_present(metadata_path)

        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        # Handle encryption key generation if --encrypt flag is used
        if encrypt:
            # Initialize details if not present
            if "details" not in metadata:
                metadata["details"] = {}

            if "encryption_key" in metadata["details"]:
                encryption_key = metadata["details"]["encryption_key"]
            else:
                # Generate encryption key if not present
                encryption_key = FileEncryption.generate_encryption_key()
                metadata["details"]["encryption_key"] = encryption_key

                # Update metadata.json file with the new encryption key
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

        namespace = get_namespace(local_path)
        name = metadata.pop("name")
        assert " " not in name

        entry_location = EntryLocation.model_validate(
            dict(
                namespace=namespace,
                name=name,
                version=metadata.pop("version"),
            )
        )

        entry_metadata = EntryMetadataInput.model_validate(metadata)
        source = entry_metadata.details.get("_source", None)

        if source is not None:
            print(f"Only default source is allowed, found: {source}. Remove details._source from metadata.")
            exit(1)

        encryption_key = entry_metadata.details.get("encryption_key", None)
        if encryption_key == OBFUSCATED_SECRET:
            print(
                f"metadata/details/encryption_key is obfuscated: {encryption_key}. Can't upload without knowing encryption key."  # noqa: E501
            )
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

        entry_files = get_local_agent_files(path)
        files_to_upload = []
        total_size = 0

        for file in entry_files:
            relative = file.relative_to(path)

            # Don't upload metadata file.
            if file == metadata_path:
                continue

            size = file.stat().st_size
            total_size += size

            files_to_upload.append((file, relative, size))

        print("")
        print("UPLOAD CONFIRMATION")
        print("")
        print(f"📍 Entry Location: {entry_location.namespace}/{entry_location.name}/{entry_location.version}")
        print(f"📁 Local Path: {path}")
        if encryption_key:
            encryption_status = "🔐 Private (encrypted)"
        else:
            encryption_status = "🌐 Open source (public)"
        print(f"🔒 Visibility: {encryption_status}")
        print("")
        response = input("Do you want to proceed with the upload? (y/N): ").strip().lower()
        if response not in ["y", "yes", "Y"]:
            exit(0)

        registry.update(entry_location, entry_metadata)
        pbar = tqdm(total=total_size, unit="B", unit_scale=True, disable=not show_progress)
        for file, relative, size in files_to_upload:
            registry.upload_file(entry_location, file, relative, encryption_key=encryption_key)
            pbar.update(size)

        if encrypt:
            console = Console()
            console.print(
                Panel(
                    Text.assemble(
                        ("🔐 Encryption enabled\n\n", "bold green"),
                        (f"Encryption key {encryption_key} generated and stored in metadata.json\n", "dim"),
                    ),
                    title="Encryption",
                    border_style="green",
                    padding=(1, 2),
                )
            )

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
        total = 1000000
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


def check_version_exists(namespace: str, name: str, version: str) -> Tuple[bool, Optional[str]]:
    """Check if a version already exists in the registry.

    Args:
    ----
        namespace: The namespace
        name: The agent name
        version: The version to check

    Returns:
    -------
        Tuple of (exists, error)
        If exists is True, the version exists
        If error is not None, an error occurred during checking

    """
    entry_location = f"{namespace}/{name}/{version}"
    try:
        existing_entry = registry.info(parse_location(entry_location))

        if existing_entry:
            return True, None
        return False, None
    except Exception as e:
        # Only proceed if the error indicates the entry doesn't exist
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            return False, None
        return False, f"Error checking registry: {str(e)}"


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """Validate version string according to PEP 440.

    Args:
    ----
        version: Version string to validate

    Returns:
    -------
        Tuple of (is_valid, error_message)

    """
    try:
        Version(version)
        return True, None
    except InvalidVersion as e:
        return False, f"Invalid version format: {str(e)}. Version must follow PEP 440:https://peps.python.org/pep-0440."


def increment_version_by_type(version: str, increment_type: str) -> str:
    """Increment version according to PEP 440.

    Args:
    ----
        version: Current version string
        increment_type: Type of increment ('major', 'minor', or 'patch')

    Returns:
    -------
        New version string

    Raises:
    ------
        ValueError: If increment_type is invalid or version is invalid

    """
    try:
        v = Version(version)
        major, minor, micro = v.release[:3]

        if increment_type == "major":
            return f"{major + 1}.0.0"
        elif increment_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif increment_type == "patch":
            return f"{major}.{minor}.{micro + 1}"
        else:
            raise ValueError(f"Invalid increment type: {increment_type}")
    except InvalidVersion as e:
        raise ValueError(f"Invalid version format: {str(e)}") from e


registry = Registry()
