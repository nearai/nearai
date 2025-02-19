# Using RAG to Build a Docs Agent

Current AI models are trained on a wide variety of data sources, which makes them outstanding at generating broad text. However, if you need your agent to talk about a topic on which it was not trained (e.g. your own internal documentation), the model will start to [hallucinate](https://thebullshitmachines.com/lesson-2-the-nature-of-bullshit/index.html).

In these very common scenarios, hallucinating is the result of the model trying to generate plausible text, without having the necessary data to do so. 

Thankfully, there is a solution to this problem: Retrieval-Augmented Generation (RAG). This technique consists on **combining two AI models**:

1. The first to **retrieve relevant information** from a structured dataset
2. The second to **generate a response** based on the retrieved information

In this tutorial, we will show you how to build a simple agent that uses RAG to answer questions about NEAR!

---

## What You Will Need

To follow this tutorial you will need two things:

1. A `Hello AI` agent, which you can create by following the [Agents Quickstart Tutorial](../../agents/quickstart.md) 
2. The `NEAR Docs` dataset, which you can download from the [official docs repo](https://github.com/near/docs/tree/master/docs)

---

## Index

This tutorial is divided in the following sections:

- [The problem](./problem.md): A brief example on how common AI models hallucinate when they don't have the necessary data
- [Vector Stores](./vector_store.md): An introduction to vector stores and how to create them
- [RAG Agent](./agent.md): We create an agent that uses the vector store to answer questions about NEAR Protocol tools
- [Chunking](./chunking.md): Where we dive deeper into how vector stores store documents
- [Embeddings](./embeddings.md): We show how one can manually create embeddings for a document