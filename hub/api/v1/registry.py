import json
import re
from collections import defaultdict
from os import getenv
from typing import Any, Dict, List

import boto3
import botocore
import botocore.exceptions
from dotenv import load_dotenv
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from nearai.config import DEFAULT_NAMESPACE
from pydantic import BaseModel
from sqlmodel import delete, select, text

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.entry_location import EntryLocation, valid_identifier
from hub.api.v1.models import RegistryEntry, Tags, get_session

DEFAULT_NAMESPACE_WRITE_ACCESS_LIST = [
    "spensa2.near",
    "marcelo.near",
    "vadim.near",
    "root.near",
    "cmrfrd.near",
    "pierre-dev.near",
    "alomonos.near",
    "flatirons.near",
    "calebjacob.near",
]

load_dotenv()
S3_BUCKET = getenv("S3_BUCKET")

s3 = boto3.client("s3")

v1_router = APIRouter(
    prefix="/registry",
    tags=["registry"],
)


tag_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")


def valid_tag(tag: str) -> str:
    result = tag_pattern.match(tag)
    if result is None:
        raise HTTPException(status_code=400, detail=f"Invalid tag: {repr(tag)}. Should match {tag_pattern.pattern}")
    return result[0]


def with_write_access(use_forms=False):
    default = Depends(EntryLocation.as_form) if use_forms else Body()

    def fn_with_write_access(
        entry_location: EntryLocation = default,
        auth: AuthToken = Depends(revokable_auth),
    ) -> EntryLocation:
        """Check the user has write access to the entry."""
        if auth.account_id == entry_location.namespace:
            return entry_location
        if entry_location.namespace == DEFAULT_NAMESPACE:
            if auth.account_id in DEFAULT_NAMESPACE_WRITE_ACCESS_LIST:
                return entry_location
        raise HTTPException(
            status_code=403,
            detail=f"Unauthorized. Namespace: {entry_location.namespace} != Account: {auth.account_id}",
        )

    return fn_with_write_access


def get_or_create(entry_location: EntryLocation = Depends(with_write_access())) -> int:
    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.namespace == entry_location.namespace,
                RegistryEntry.name == entry_location.name,
                RegistryEntry.version == entry_location.version,
            )
        ).first()

        if entry is None:
            entry = RegistryEntry(
                namespace=entry_location.namespace,
                name=entry_location.name,
                version=entry_location.version,
            )
            session.add(entry)
            session.commit()

        return entry.id


def get(entry_location: EntryLocation = Body()) -> RegistryEntry:
    with get_session() as session:
        entry = session.exec(
            select(RegistryEntry).where(
                RegistryEntry.namespace == entry_location.namespace,
                RegistryEntry.name == entry_location.name,
                RegistryEntry.version == entry_location.version,
            )
        ).first()

        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")

        return entry


class EntryMetadataInput(BaseModel):
    category: str
    description: str
    tags: List[str]
    details: Dict
    show_entry: bool


class EntryMetadata(EntryMetadataInput):
    name: str
    version: str


def check_file_exists(key):
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


@v1_router.post("/upload_file")
async def upload_file(
    entry_location: EntryLocation = Depends(with_write_access(use_forms=True)),
    path: str = Form(...),
    file: UploadFile = File(...),
):
    entry = get(entry_location)
    key = entry.get_key(path)

    if check_file_exists(key):
        raise HTTPException(status_code=400, detail=f"File {key} already exists.")

    assert isinstance(S3_BUCKET, str)
    s3.upload_fileobj(file.file, S3_BUCKET, key)

    return {"status": "File uploaded", "path": key}


@v1_router.post("/download_file")
async def download_file(
    entry: RegistryEntry = Depends(get),
    path: str = Body(),
):
    source = entry.details.get("_source")

    if source is None:
        # Default source, which is S3
        assert isinstance(S3_BUCKET, str)
        bucket = S3_BUCKET
        key = entry.get_key(path)
    elif source["origin"] == "s3":
        bucket = source["bucket"]
        key = source["key"]
        key = key.strip("/") + "/" + path.strip("/")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

    # https://stackoverflow.com/a/71126498/4950797
    object = s3.get_object(Bucket=bucket, Key=key)
    return StreamingResponse(object["Body"].iter_chunks())


@v1_router.post("/upload_metadata")
async def upload_metadata(registry_entry_id: int = Depends(get_or_create), metadata: EntryMetadataInput = Body()):
    with get_session() as session:
        entry = session.get(RegistryEntry, registry_entry_id)
        assert entry is not None

        full_metadata = EntryMetadata(name=entry.name, version=entry.version, **metadata.model_dump())

        entry.category = full_metadata.category
        entry.description = full_metadata.description
        entry.details = full_metadata.details
        entry.show_entry = full_metadata.show_entry

        session.add(entry)

        # Delete all previous tags
        # Ignore type check since delete is not supported as a valid statement.
        # https://github.com/tiangolo/sqlmodel/issues/909
        session.exec(delete(Tags).where(Tags.registry_id == entry.id))  # type: ignore

        # Add the new tags
        if len(full_metadata.tags) > 0:
            tags = [Tags(registry_id=entry.id, tag=tag) for tag in full_metadata.tags]
            session.add_all(tags)

        session.commit()

        return {"status": "Updated metadata", "namespace": entry.namespace, "metadata": full_metadata.model_dump()}


@v1_router.post("/download_metadata")
async def download_metadata(entry: RegistryEntry = Depends(get)) -> EntryMetadata:
    with get_session() as session:
        q_tags = select(Tags).where(Tags.registry_id == entry.id)
        tags = [tag.tag for tag in session.exec(q_tags).all()]

    return EntryMetadata(
        name=entry.name,
        version=entry.version,
        category=entry.category,
        description=entry.description,
        tags=tags,
        details=entry.details,
        show_entry=entry.show_entry,
    )


class Filename(BaseModel):
    filename: str


@v1_router.post("/list_files")
async def list_files(entry: RegistryEntry = Depends(get)) -> List[Filename]:
    """List all files that belong to a entry."""
    source = entry.details.get("_source")

    if source is None:
        # Default source, which is S3
        assert isinstance(S3_BUCKET, str)
        bucket = S3_BUCKET
        key = entry.get_key()
    elif source["origin"] == "s3":
        bucket = source["bucket"]
        key = source["key"]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

    key = key.strip("/") + "/"

    objects = s3.list_objects(Bucket=bucket, Prefix=key)
    files = [Filename(filename=obj["Key"][len(key) :]) for obj in objects.get("Contents", [])]
    return files


class EntryInformation(BaseModel):
    id: int
    namespace: str
    name: str
    version: str
    category: str
    description: str
    details: Dict[str, Any]
    tags: List[str]
    num_stars: int
    starred_by_point_of_view: bool


@v1_router.post("/list_entries")
async def list_entries(
    namespace: str = "",
    category: str = "",
    tags: str = "",
    total: int = 32,
    offset: int = 0,
    show_hidden: bool = False,
    show_latest_version: bool = True,
    starred_by: str = "",
    star_point_of_view: str = "",
) -> List[EntryInformation]:
    tags_list = list({tag for tag in tags.split(",") if tag})

    bind_params: Dict[str, Any] = {
        "show_entry": 1 - int(show_hidden),
    }

    if category:
        category = valid_tag(category)
        category_condition = "AND category = :category"
        bind_params["category"] = category
    else:
        category_condition = ""

    if namespace:
        namespace = valid_identifier(namespace)
        namespace_condition = "AND registry.namespace = :namespace"
        bind_params["namespace"] = namespace
    else:
        namespace_condition = ""

    latest_version_condition = (
        """JOIN (SELECT MAX(id) as id FROM registry_entry GROUP BY namespace, name) last_entry
             ON last_entry.id = registry.id"""
        if show_latest_version
        else ""
    )

    bind_params["star_point_of_view"] = star_point_of_view
    bind_params["starred_by"] = starred_by

    if starred_by:
        starred_by_condition = "AND CountedStars.starred_by_target = 1"
    else:
        starred_by_condition = ""

    with get_session() as session:
        entries_info: List[EntryInformation] = []

        if len(tags_list) == 0:
            query_text = f"""WITH
            CountedStars AS (
                SELECT namespace, name, COUNT(account_id) as num_stars,
                CASE WHEN MAX(account_id = :star_point_of_view) THEN 1 ELSE 0 END as starred_by_pov,
                CASE WHEN MAX(account_id = :starred_by) THEN 1 ELSE 0 END as starred_by_target
                FROM stars
                GROUP BY namespace, name
            )
            SELECT registry.id, registry.namespace, registry.name, registry.version,
            registry.category, registry.description, registry.details,
            CountedStars.num_stars, CountedStars.starred_by_pov
            FROM registry_entry registry
            LEFT JOIN CountedStars
            ON registry.namespace = CountedStars.namespace AND registry.name = CountedStars.name
            {latest_version_condition}
            WHERE show_entry >= :show_entry
                {category_condition}
                {namespace_condition}
                {starred_by_condition}
            ORDER BY registry.id DESC
            LIMIT :total
            OFFSET :offset
            """

            bind_params["total"] = total
            bind_params["offset"] = offset

        else:
            tags_list = [valid_tag(tag) for tag in tags_list]

            query_text = f"""WITH
                    CountedStars AS (
                        SELECT namespace, name, COUNT(account_id) as num_stars,
                        CASE WHEN MAX(account_id = :star_point_of_view) THEN 1 ELSE 0 END as starred_by_pov,
                        CASE WHEN MAX(account_id = :starred_by) THEN 1 ELSE 0 END as starred_by_target
                        FROM stars
                        GROUP BY namespace, name
                    ),
                    FilteredRegistry AS (
                        SELECT registry.id, CountedStars.num_stars, CountedStars.starred_by_pov
                        FROM registry_entry registry
                        {latest_version_condition}
                        JOIN entry_tags ON registry.id = entry_tags.registry_id
                        LEFT JOIN CountedStars
                        ON registry.namespace = CountedStars.namespace AND registry.name = CountedStars.name
                        WHERE show_entry >= :show_entry
                            AND entry_tags.tag IN :tags
                            {category_condition}
                            {namespace_condition}
                            {starred_by_condition}
                        GROUP BY registry.id
                        HAVING COUNT(DISTINCT entry_tags.tag) = :ntags
                    ),
                    RankedRegistry AS (
                        SELECT id, num_stars, starred_by_pov, ROW_NUMBER() OVER (ORDER BY id DESC) AS col_rank
                        FROM FilteredRegistry
                    )

                    SELECT registry.id, registry.namespace, registry.name, registry.version,
                           registry.category, registry.description, registry.details,
                           ranked.num_stars, ranked.starred_by_pov
                    FROM RankedRegistry ranked
                    JOIN registry_entry registry ON ranked.id = registry.id
                    WHERE   ranked.col_rank >= :lower_bound AND
                            ranked.col_rank < :upper_bound
                    ORDER BY registry.id DESC
                """

            bind_params["lower_bound"] = offset + 1
            bind_params["upper_bound"] = offset + total + 1
            bind_params["tags"] = tags_list
            bind_params["ntags"] = len(tags_list)

        for id, namespace_, name, version, category_, description, details, num_stars, pov in session.exec(
            text(query_text).bindparams(**bind_params)
        ).all():  # type: ignore
            print(namespace_, name, version, num_stars)
            entries_info.append(
                EntryInformation(
                    id=id,
                    namespace=namespace_,
                    name=name,
                    version=version,
                    category=category_,
                    description=description,
                    details=json.loads(details),
                    tags=[],
                    num_stars=num_stars or 0,
                    starred_by_point_of_view=bool(pov),
                )
            )

        # Get the tags of all entries
        ids = [entry.id for entry in entries_info]

        q_tags = select(Tags).where(Tags.registry_id.in_(ids))  # type: ignore
        q_tags_r = session.exec(q_tags).all()

        q_tags_dict: Dict[int, List[str]] = defaultdict(list)
        for tag in q_tags_r:
            q_tags_dict[tag.registry_id].append(tag.tag)

        for entry in entries_info:
            entry.tags = q_tags_dict[entry.id]

        entries_info.sort(key=lambda x: x.id, reverse=True)

        return entries_info
