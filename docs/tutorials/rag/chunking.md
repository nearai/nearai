# Chunking

Before transforming the docs into embeddings, the platform divides them into smaller chunks of text. 

Chunking a document does not only make it less computationally expensive to process, but also allows the model to better understand the document as a whole.

Embedding models tend to transform documents (whatever its size) into a fixed-size vector.

By dividing the document into smaller chunks, we can better represent the document as a whole.


!!! tip
    Think about it, it is not the same to represent a 8000 words document as a single vector, than to represent it as 10 vectors of 800 words each.

---

## Chunking Strategy

When creating the vector store we left a parameter commented in the code, the `chunking_strategy`. This parameter allows you to specify how the documents are "split" into chunks before being processed by the model.

The `chunking_strategy` parameter is a dictionary that can have the following keys:
    - `chunk_overlap_tokens`: The number of tokens that the chunks will overlap. Default is 400.
    - `max_chunk_size_tokens`: The maximum number of tokens that a chunk can have. Default is 800.

**TODO ADD IMAGE HERE**

By default, the platform will divide the document into chunks of 800 tokens, with an overlap of 400 tokens.

However, the way that these chunks are created is not smart at all. The platform simply takes the first `max_chunk_size_tokens` tokens (e.g. 800) and then moves `chunk_overlap_tokens` tokens to the right to create the next chunk.

This means that the chunks are not created based on the document's structure, which can lead to a loss of context.

You can change the `chunking_strategy` to better fit your documents' structure. For example, if your documents have a lot of code snippets, you can increase the `chunk_overlap_tokens` to make sure that the code snippets are not split into different chunks.