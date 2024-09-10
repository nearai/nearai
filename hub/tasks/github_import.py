import base64
import logging
import mimetypes
import os
import time
from typing import Dict, Optional

import chardet
import requests
from dotenv import load_dotenv

from hub.api.v1.files import upload_file_to_storage
from hub.api.v1.models import GitHubSource
from hub.api.v1.sql import SqlClient
from hub.tasks.embedding_generation import generate_embeddings_for_file

logger = logging.getLogger(__name__)


load_dotenv()

BASE_URL = "https://api.github.com/repos"
RATE_LIMIT_WAIT = 60
MAX_CONTENT_LENGTH = 1024 * 1024  # 1 MB

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def handle_rate_limit(func):
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code == 403:
            print(f"Rate limit exceeded. Waiting for {RATE_LIMIT_WAIT} seconds...")
            time.sleep(RATE_LIMIT_WAIT)
            return wrapper(*args, **kwargs)
        return response

    return wrapper


@handle_rate_limit
def github_get(url: str, source_auth: Optional[str] = None) -> requests.Response:
    headers = HEADERS
    if not source_auth and not GITHUB_TOKEN:
        raise ValueError("Github token is required")
    if source_auth:
        headers["Authorization"] = f"token {source_auth}"
    return requests.get(url, headers=headers)


def get_repo_contents(owner: str, repo: str, branch: str = "main", caller_auth: Optional[str] = None) -> Optional[Dict]:
    url = f"{BASE_URL}/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = github_get(url, caller_auth)
    if response.status_code == 200:
        return response.json()
    print(f"Error fetching contents: {response.status_code}")
    return None


def read_file_content(blob_url: str) -> Optional[str]:
    response = github_get(blob_url)
    if response.status_code == 200:
        content = base64.b64decode(response.json()["content"])
        if len(content) > MAX_CONTENT_LENGTH:
            print("File too large, skipping content.")
            return None

        # Detect encoding
        detected = chardet.detect(content)
        encoding = detected["encoding"] if detected and detected["encoding"] else "utf-8"

        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            print(f"Unable to decode content for {blob_url} with utf-8")
            return None
    print(f"Error fetching file content: {response.status_code}")
    return None


def print_file_content(path: str, content: Optional[str]) -> None:
    if content is None:
        print(f"url: {path}, Binary file detected, skipping content.")
        return
    print(f"File: {path}")
    if content:
        print(f"Content:\n{content[:500]}...")  # Print first 500 characters
        print("=" * 50 + "\n")
    else:
        raise Exception("Could not read file content.")


async def create_file_from_content(account_id: str, filename: str, content: str, purpose: str) -> Optional[str]:
    """Create a file record from content and upload it to storage.

    Args:
    ----
        account_id (str): The account ID of the user.
        filename (str): The name of the file.
        content (str): The content of the file.
        purpose (str): The purpose of the file.

    Returns:
    -------
        Optional[str]: The file ID if successful, None otherwise.

    """
    content_bytes = content.encode("utf-8")
    file_size = len(content_bytes)
    content_type = mimetypes.guess_type(filename)[0] or "text/plain"

    # Use os.path.basename to get just the filename without any directory structure
    safe_filename = os.path.basename(filename)
    object_key = f"hub/vector-store-files/{account_id}/{safe_filename}"
    try:
        file_uri = await upload_file_to_storage(content_bytes, object_key)
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {str(e)}")
        return None

    sql_client = SqlClient()
    try:
        file_id = sql_client.create_file(
            account_id=account_id,
            file_uri=file_uri,
            purpose=purpose,
            filename=safe_filename,
            content_type=content_type,
            file_size=file_size,
            encoding="utf-8",
        )
        return file_id
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        return None


async def process_github_source(
    source: GitHubSource, vector_store_id: str, account_id: str, source_auth: Optional[str] = None
):
    """Process files from a GitHub source and add them to the vector store.

    Args:
    ----
        source (GitHubSource): The GitHub source details.
        vector_store_id (str): The ID of the vector store to add files to.
        account_id (str): The account ID of the user.
        source_auth (Optional[str]): The caller's authentication token for the source.
            If available, a default token from the environment will be used as a fallback.

    """
    logger.info(f"Processing GitHub source for vector store: {vector_store_id}")
    sql_client = SqlClient()

    repo_contents = get_repo_contents(source.owner, source.repo, source.branch, source_auth)
    if repo_contents is None or "tree" not in repo_contents:
        logger.error(f"Failed to fetch repository contents for {source.owner}/{source.repo}")
        return

    for item in repo_contents["tree"]:
        if item["type"] != "blob":
            continue

        content = read_file_content(item["url"])
        if content is None:
            continue

        file_id = await create_file_from_content(account_id, item["path"], content, "assistants")
        if not file_id:
            continue

        vector_store = sql_client.get_vector_store(vector_store_id)
        if not vector_store:
            logger.error(f"Vector store {vector_store_id} not found")
            continue

        sql_client.update_files_in_vector_store(
            vector_store_id=vector_store_id,
            file_ids=vector_store.file_ids + [file_id],
            account_id=account_id,
        )
        await generate_embeddings_for_file(file_id, vector_store_id)

    # Update vector store status to completed
    logger.info(f"Completed processing GitHub source for vector store: {vector_store_id}")
