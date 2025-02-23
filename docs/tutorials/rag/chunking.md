# Chunking

Before converting documentation into vector embeddings, the NEAR AI platform segments the text into smaller, manageable chunks. This process, known as text chunking, serves several crucial purposes:

Chunking a document not only makes it less computationally expensive to process, but also allows the model to better understand and represent the information within.

!!! tip
    Embedding models transform documents into fixed-size vectors, regardless of the original document size. By dividing documents into smaller chunks, we achieve more granular and accurate representation.
    
    It's more effective to have multiple vectors representing specific sections than a single vector trying to capture an entire document's meaning.

!!! warning
    Most users won't need to modify the default chunking settings. Only consider adjusting them if you notice the agent consistently struggles to answer questions due to how the documents are segmented.

---

## Chunking Strategy

When creating the vector store we left a parameter commented in the code, the `chunking_strategy`. This parameter allows you to specify how the documents are "split" into chunks before being processed by the model.

```python
vs = client.beta.vector_stores.create(
    name="docs-vector-store-chunks",
    file_ids=file_ids,
    # chunking_strategy={
    #     "chunk_overlap_tokens": 400,
    #     "max_chunk_size_tokens": 800
    # }
)
```

The `chunking_strategy` parameter is a dictionary that can have the following keys:
    - `chunk_overlap_tokens`: The number of tokens that the chunks will overlap. Default is 400.
    - `max_chunk_size_tokens`: The maximum number of tokens that a chunk can have. Default is 800.

By default, the platform will divide the document into chunks of 800 tokens, with an overlap of 400 tokens.

![Chunking Strategy](chunks.png)

It is important to notice that chunks are not created based on the document's structure, but merely on counting tokens, which can lead to a loss of context.

Make sure you change the `chunking_strategy` to better fit your documents' structure. For example, if your documents have a lot of code snippets, you can increase the `size` and `overlap` to make sure that the code can be correctly retrieved by the vector store.