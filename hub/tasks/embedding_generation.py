import asyncio
import logging
import os
import uuid
from typing import List

import openai

from hub.api.v1.models import FILE_URI_PREFIX, S3_URI_PREFIX
from hub.api.v1.sql import SqlClient, VectorStoreFile

logger = logging.getLogger(__name__)

# Constants for chunking strategy
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 400


async def generate_embeddings_for_vector_store(vector_store_id: str):
    logger.info(f"Starting embedding generation for vector store: {vector_store_id}")
    sql_client = SqlClient()
    vector_store = sql_client.get_vector_store(vector_store_id=vector_store_id)

    if not vector_store:
        logger.error(f"Vector store with id {vector_store_id} not found")
        raise ValueError(f"Vector store with id {vector_store_id} not found")

    logger.debug(f"Queueing embedding generation tasks for {len(vector_store.file_ids)} files")
    tasks = [generate_embeddings_for_file(file_id, vector_store_id) for file_id in vector_store.file_ids]

    await asyncio.gather(*tasks)

    logger.info(f"Finished embedding generation tasks for vector store: {vector_store_id}")


async def generate_embeddings_for_file(file_id: str, vector_store_id: str):
    logger.info(f"Starting embedding generation for file: {file_id}")
    sql_client = SqlClient()
    file_details = sql_client.get_file_details(file_id)
    if not file_details:
        logger.error(f"File with id {file_id} not found")
        raise ValueError(f"File with id {file_id} not found")

    content = await get_file_content(file_details)

    chunks = create_chunks(content)
    logger.debug(f"Created {len(chunks)} chunks for file: {file_id}")

    embedding_tasks = [generate_embedding(chunk) for chunk in chunks]

    embeddings = await asyncio.gather(*embedding_tasks)
    logger.debug(f"Generated {len(embeddings)} embeddings for file: {file_id}")

    # Store embeddings in the database
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        embedding_id = f"vfe_{uuid.uuid4().hex[:24]}"
        logger.debug(f"Storing embedding: {embedding_id} for file: {file_id}")
        try:
            sql_client.store_embedding(
                id=embedding_id,
                vector_store_id=vector_store_id,
                file_id=file_id,
                chunk_index=i,
                chunk_text=chunk,
                embedding=embedding,
            )
        except Exception as e:
            logger.error(f"Failed to store embedding: {embedding_id} for file: {file_id}, error: {e}")

    # Update file status
    sql_client.update_file_embedding_status(file_id, "completed")

    # Update vector store embedding info
    if embeddings:
        embedding_model = "nomic-ai/nomic-embed-text-v1.5"  # This should be dynamically set based on the model used
        embedding_dimensions = len(embeddings[0])
        sql_client.update_vector_store_embedding_info(vector_store_id, embedding_model, embedding_dimensions)

    logger.info(f"Finished embedding generation for file: {file_id}")


def create_chunks(text: str) -> List[str]:
    return recursive_split(text, CHUNK_SIZE, CHUNK_OVERLAP)


def recursive_split(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Recursively split text into chunks of specified size with overlap.

    Args:
    ----
        text (str): Input text to split.
        chunk_size (int): Maximum size of each chunk.
        chunk_overlap (int): Overlap size between chunks.

    Returns:
    -------
        List[str]: List of text chunks.

    """
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]
    for separator in separators:
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        chunks: List[str] = []
        current_chunk = ""
        current_length = 0

        for split in splits:
            split_with_sep = split + separator
            split_length = len(split_with_sep)

            if current_length + split_length > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + split_with_sep
                current_length = len(current_chunk)
            else:
                current_chunk += split_with_sep
                current_length += split_length

        if current_chunk:
            chunks.append(current_chunk.strip())

        # Ensure last chunk has proper overlap with second-to-last chunk
        if len(chunks) > 1:
            last_chunk = chunks[-1]
            second_last_chunk = chunks[-2]
            overlap = second_last_chunk[-chunk_overlap:]
            if not last_chunk.startswith(overlap):
                chunks[-1] = overlap + last_chunk

        return chunks

    # If we reach here, it means we couldn't split the text
    return [text]


async def generate_embedding(text: str, query: bool = False):
    """Generate an embedding for the given text.

    For Nomic AI's embedding models, we prefix the input with either 'search_query: '
    or 'search_document: ' depending on whether the text is a query or a document.
    This helps the model understand the context and generate more appropriate embeddings.

    Args:
    ----
        text (str): The text to generate an embedding for.
        query (bool, optional): If True, the text is treated as a search query.
            If False, it's treated as a document. Defaults to False.

    Returns:
    -------
        list: The embedding vector for the input text.

    """
    client = openai.AsyncOpenAI(
        base_url="https://api.fireworks.ai/inference/v1", api_key=os.getenv("FIREWORKS_API_KEY")
    )
    logger.debug(f"Generating embedding for text: {text[:32]}...")
    prefix = "search_query: " if query else "search_document: "
    response = await client.embeddings.create(input=prefix + text, model="nomic-ai/nomic-embed-text-v1.5")
    return response.data[0].embedding  # Return only the embedding vector


async def get_file_content(file_details: VectorStoreFile) -> str:
    """Get the content of the file from the file URI.

    Supports:
    - Local files (file::)
    - S3 files (s3::)
    """
    encoding = file_details.encoding or "utf-8"

    if file_details.file_uri.startswith(FILE_URI_PREFIX):
        with open(file_details.file_uri[len(FILE_URI_PREFIX) :], "r", encoding=encoding) as file:
            return file.read()
    elif file_details.file_uri.startswith(S3_URI_PREFIX):
        import boto3

        s3_client = boto3.client("s3")
        parts = file_details.file_uri[len(S3_URI_PREFIX):].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {file_details.file_uri}")
        bucket_name, key = parts
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response["Body"].read().decode(encoding)
    else:
        raise ValueError(f"Unsupported file URI: {file_details.file_uri}")
