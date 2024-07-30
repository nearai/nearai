import os
from pathlib import Path
from typing import List, Optional, Union

import boto3
from mypy_boto3_s3.client import S3Client
from tqdm import tqdm

import nearai
from nearai.config import CONFIG, DATA_FOLDER
from nearai.db import DisplayRegistry, db


def upload_file(s3_client: S3Client, s3_path: str, local_path: Path) -> None:
    assert local_path.is_file()
    assert local_path.exists()

    statinfo = os.stat(local_path)
    total_length = statinfo.st_size

    with tqdm(
        total=total_length,
        desc=f"upload: {local_path}",
        bar_format="{percentage:.1f}%|{bar:25} | {rate_fmt} | {desc}",
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        s3_client.upload_file(
            str(local_path),
            CONFIG.s3_bucket,
            s3_path,
            Callback=pbar.update,
        )


def download_file(s3_client: S3Client, s3_path: str, local_path: Path) -> None:
    local_path.parent.absolute().mkdir(parents=True, exist_ok=True)

    meta_data = s3_client.head_object(Bucket=CONFIG.s3_bucket, Key=s3_path)
    total_length = int(meta_data.get("ContentLength", 0))
    with tqdm(
        total=total_length,
        desc=f"source: s3://{CONFIG.s3_bucket}/{s3_path}",
        bar_format="{percentage:.1f}%|{bar:25} | {rate_fmt} | {desc}",
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        with open(local_path, "wb") as f:
            s3_client.download_fileobj(CONFIG.s3_bucket, s3_path, f, Callback=pbar.update)


def download_directory(s3_prefix: str, local_directory: Path) -> None:
    if not s3_prefix.endswith("/"):
        s3_prefix += "/"

    s3_client: S3Client = boto3.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")

    found_file = False

    for page in paginator.paginate(Bucket=CONFIG.s3_bucket, Prefix=s3_prefix):
        if "Contents" not in page:
            continue

        for s3_object in page["Contents"]:
            s3_key = s3_object["Key"]
            relative_path = os.path.relpath(s3_key, s3_prefix)
            local_path = local_directory / relative_path

            # Skip directories, S3 keys ending with '/' are folders
            if not s3_key.endswith("/"):
                download_file(s3_client, s3_key, local_path)
                found_file = True

    assert found_file, f"No files found in {s3_prefix}"


def exists_directory_in_s3(s3_path: str) -> bool:
    s3_client = boto3.client("s3")
    response = s3_client.list_objects(Bucket=CONFIG.s3_bucket, Prefix=s3_path, Delimiter="/", MaxKeys=1)
    return "Contents" in response or "CommonPrefixes" in response


class Registry:
    def __init__(self, tags: List[str]):  # noqa: D107
        self.tags = tags
        self.download_folder = DATA_FOLDER / "registry"

        if not self.download_folder.exists():
            self.download_folder.mkdir(parents=True, exist_ok=True)

    def _all_tags(self, tags: List[str]) -> List[str]:
        return list(set(self.tags + tags))

    def update(  # noqa: D102
        self,
        identifier: Union[str, int],
        *,
        author: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: Optional[bool] = None,
    ) -> None:
        entry = db.get_registry_entry_by_identifier(identifier)
        assert entry is not None

        db.update_registry_entry(
            id=entry.id, author=author, description=description, name=name, details=details, show_entry=show_entry
        )

        update = dict(
            author=author,
            description=description,
            name=name,
            details=details,
            show_entry=show_entry,
        )
        update = {k: v for k, v in update.items() if v is not None}
        nearai.log(target="Update in registry", id=id, **update)

    def exists_in_s3(self, name: str) -> bool:  # noqa: D102
        prefix = os.path.join(CONFIG.s3_prefix, name)
        return exists_directory_in_s3(prefix)

    def add(  # noqa: D102
        self,
        *,
        s3_path: str,
        name: Optional[str],
        author: str,
        description: Optional[str],
        details: Optional[dict],
        show_entry: bool,
        tags: List[str],
    ) -> int:
        if db.exists_in_registry(s3_path):
            raise ValueError(f"{s3_path} already exists in the registry")

        registry_id = db.add_to_registry(
            s3_path=s3_path,
            name=name or "",
            author=author,
            description=description,
            details=details,
            show_entry=show_entry,
            tags=self._all_tags(tags),
        )

        nearai.log(target="Add to registry", name=name, author=author)
        return int(registry_id)

    def add_tags(self, *, identifier: Union[str, int], tags: List[str]) -> None:  # noqa: D102
        entry = db.get_registry_entry_by_identifier(identifier)
        assert entry is not None

        current_tags = db.get_tags(entry.id)

        all_tags = list(set(current_tags + tags))
        if len(all_tags) != len(current_tags) + len(tags):
            raise ValueError(f"Some tags are already present. New tags: {tags} Current tags: {current_tags}")

        for tag in tags:
            db.add_tag(registry_id=entry.id, tag=tag)

    def remove_tag(self, *, identifier: Union[str, int], tag: str) -> None:  # noqa: D102
        entry = db.get_registry_entry_by_identifier(identifier)
        assert entry is not None

        current_tags = db.get_tags(entry.id)

        if tag not in current_tags:
            raise ValueError(f"Tag {tag} is not present in {identifier}")

        db.remove_tag(registry_id=entry.id, tag=tag)

    def upload(  # noqa: D102
        self,
        *,
        path: Path,
        s3_path: str,
        author: str,
        description: Optional[str],
        name: Optional[str],
        details: Optional[dict],
        show_entry: bool,
        tags: List[str],
    ) -> int:
        assert path.exists(), "Path does not exist"

        prefix = os.path.join(CONFIG.s3_prefix, s3_path)

        if self.exists_in_s3(s3_path):
            raise ValueError(f"{prefix} already exists in S3")

        registry_id = self.add(
            s3_path=s3_path,
            name=name,
            author=author,
            description=description,
            details=details,
            show_entry=show_entry,
            tags=tags,
        )

        nearai.log(target="Upload to S3", path=s3_path, author=author)

        s3_client = boto3.client("s3")

        if path.is_file():
            upload_file(s3_client, os.path.join(prefix, path.name), path)

        elif path.is_dir():
            for root, _, files in os.walk(path):
                for filename in files:
                    # Construct full local path
                    local_path = os.path.join(root, filename)

                    # Construct relative path for S3
                    relative_path = os.path.relpath(local_path, path)
                    s3_path = os.path.join(prefix, relative_path)

                    upload_file(s3_client, s3_path, Path(local_path))
        return registry_id

    def download(self, identifier: Union[str, int], version: Optional[str] = None) -> Path:  # noqa: D102
        # Try to work in offline mode by checking if identifier is a path first before fetching from database.
        if isinstance(identifier, str) and not identifier.isdigit():
            target = self.download_folder / identifier
            if target.exists():
                return target

        entry = db.get_registry_entry_by_identifier(identifier, version=version)
        assert entry is not None

        path = entry.path
        target = self.download_folder / entry.path

        if not target.exists():
            prefix = os.path.join(CONFIG.s3_prefix, path)
            source = f"s3://{CONFIG.s3_bucket}/{prefix}"
            print(f"Downloading {path} from {source} to {target}")
            nearai.log(target="Download from S3", name=identifier)
            download_directory(prefix, target)

        return target

    def list(self, *, tags: List[str], total: int, show_all: bool) -> List[DisplayRegistry]:  # noqa: D102
        tags = self._all_tags(tags)
        result: List[DisplayRegistry] = db.list_registry_entries(total=total, show_all=show_all, tags=tags)
        return result


dataset = Registry(["dataset"])
model = Registry(["model"])
agent = Registry(["agent"])
registry = Registry([])
