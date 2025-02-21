# Building a Documentation Agent with RAG

Current AI models are trained on vast datasets, making them powerful at generating general-purpose text. However, when asked about specific topics outside their training data (like your company's internal documentation), these models often [hallucinate](https://thebullshitmachines.com/lesson-2-the-nature-of-bullshit/index.html) - generating plausible-sounding but incorrect information.

Thankfully, there is a solution to this problem: Retrieval-Augmented Generation (RAG). This technique consists on **combining two key components**:

1. A **retrieval system** that finds relevant information from your custom dataset
2. A **language model** that generates accurate responses using the retrieved information

In this tutorial, you'll learn how to build a RAG-powered agent that accurately answers questions about NEAR Protocol!

---

## What You Will Need

To follow this tutorial you will need:

1. A `Hello AI` agent - You can create one by following the [Agents Quickstart Tutorial](../../agents/quickstart.md) (estimated time: 5 minutes)
2. The `NEAR Docs` dataset - Download it from the [official docs repo](https://github.com/near/docs/tree/master/docs). You'll only need the markdown (`.md`) files

!!!info
    Make sure you have completed the [Agents Quickstart Tutorial](../../agents/quickstart.md) first, as this tutorial builds upon those concepts.

---

## Index

This tutorial is divided in the following sections:

- [The problem](./problem.md): A brief example on how common AI models hallucinate when they don't have the relevant data
- [Vector Stores](./vector_store.md): An introduction to vector stores and how to create them
- [RAG Agent](./agent.md): We create an agent that uses the vector store to answer questions about NEAR Protocol tools
- [Chunking](./chunking.md): Dive deeper into how vector stores store documents
- [Embeddings](./embeddings.md): We show how one can manually create embeddings for a document