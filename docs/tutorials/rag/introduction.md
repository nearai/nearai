# Building a Documentation Agent with RAG

Current AI models are trained on vast datasets, making them powerful at generating general-purpose text. However, when asked about specific topics outside their training data (like your company's internal documentation), these models often [hallucinate](https://thebullshitmachines.com/lesson-2-the-nature-of-bullshit/index.html) - generating plausible-sounding but incorrect information.

Thankfully, there is a solution to this problem: Retrieval-Augmented Generation (RAG). This technique consists on **combining two key components**:

1. A **retrieval system** that finds relevant information from your custom dataset
2. A **language model** that generates accurate responses using the retrieved information

In this tutorial, you'll learn how to build a RAG-powered agent that accurately answers questions about NEAR Protocol.

---

## What You Will Need

To follow this tutorial you will need:

1. NEAR AI CLI installed on your local machine → [Installation Guide](../../cli.md)
2. Basic understanding of creating a NEAR AI agent → [Agents Quickstart Tutorial](../../agents/quickstart.md)

---

## Overview

This tutorial is divided in the following sections:

- [The problem](./problem.md) → Understanding AI hallucination from incorrect data
- [Vector Stores](./vector_store.md) → Getting started with vector stores
- [RAG Agent](./agent.md) → Building a NEAR Documentation Q&A agent
- [Chunking](./chunking.md) → Dive deeper into how vector stores store documents
- [Embeddings](./embeddings.md) → Creating document embeddings manually