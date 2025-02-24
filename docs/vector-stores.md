Vector Stores are a special kind of database that stores documents and allows retrieving them through natural language. 

---

!!! tip
    Read our tutorial on [**Vector Stores**](../tutorials/rag/introduction.md) to discover how you can build an agent that answers questions based on your custom data

---

- [**NEAR AI**](../docs/cli.md) Python dependencies (e.g., `nearai`, `openai`) installed.
- A local directory containing your text files (e.g., `.md`, `.txt`) for upload.

---

## 1. Import and Configure

The code imports standard libraries and NEAR AI modules to load configuration settings, including the API URL and credentials. It then constructs the API base URL and initializes an OpenAI-compatible client, ensuring that you have a valid connection to the NEAR AI endpoint.

```python
import json
from glob import glob

import openai
import nearai

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))
```

---

## 2. Create a Vector Store

Using the initialized client, a vector store is created with a specified name. The returned store’s unique ID is essential for attaching files and performing future operations like querying and deleting.

```python
vector_store = client.beta.vector_stores.create(name="My_Vector_Store")
print(f"Vector store created: {vector_store.id}")
```

??? note "Example Output"
    ```python
    Vector store created: vs_60e3f8e647074623a1715f0f
    ```

---

## 3. Upload and Attach Files

A file (e.g., example_file.md) is opened in binary mode and uploaded via the API. Once uploaded, it is attached to the vector store using the store’s ID and the file’s unique ID, making its contents available for embedding and semantic search.

```python
uploaded_file = client.files.create(
    file=open("dataset/data_mining.md", "rb"),
    purpose="assistants",
)

client.beta.vector_stores.files.create(
    vector_store_id=vector_store.id,
    file_id=uploaded_file.id,
)

print(f"File uploaded and attached: {uploaded_file.filename}")
```

??? note "Example Output"
    ```python
    File uploaded and attached: data_mining.md
    ```

---

## 4. Wait for Processing

The script continuously polls the vector store’s status until the file embeddings are complete. This ensures that the vector store is fully updated and ready for queries.

```python
while True:
    status = client.beta.vector_stores.retrieve(vector_store.id)
    if status.file_counts.completed == 1:
        break
    time.sleep(1)

print("File processed! The vector store is ready.")
```

??? note "Example Output"
    ```python
    File processed! The vector store is ready.
    ```

---

## 5. Retrieve a File’s Raw Content

Using the file’s unique ID, the file is retrieved as a binary stream. The binary data is then decoded into a UTF-8 string, allowing you to view and verify the file’s content.

```python
file_id = uploaded_file.id  # e.g., "file_abc123"

retrieved_content = client.files.content(file_id=file_id)
raw_bytes = retrieved_content.read()
file_text = raw_bytes.decode("utf-8")
print("Retrieved file content:", file_text)
```

??? note "Example Output"
    ```python
    Retrieved file content: Data mining
    Machine learning and data mining often employ the same methods and overlap significantly, but while machine learning focuses on prediction, based on known properties learned from the training data, data mining focuses on the discovery of (previously) unknown properties in the data (this is the analysis step of knowledge discovery in databases). Data mining uses many machine learning methods, but with different goals; on the other hand, machine learning also employs data mining methods as "unsupervised learning" or as a preprocessing step to improve learner accuracy. Much of the confusion between these two research communities (which do often have separate conferences and separate journals, ECML PKDD being a major exception) comes from the basic assumptions they work with: in machine learning, performance is usually evaluated with respect to the ability to reproduce known knowledge, while in knowledge discovery and data mining (KDD) the key task is the discovery of previously unknown knowledge. Evaluated with respect to known knowledge, an uninformed (unsupervised) method will easily be outperformed by other supervised methods, while in a typical KDD task, supervised methods cannot be used due to the unavailability of training data.

    Machine learning also has intimate ties to optimization: Many learning problems are formulated as minimization of some loss function on a training set of examples. Loss functions express the discrepancy between the predictions of the model being trained and the actual problem instances (for example, in classification, one wants to assign a label to instances, and models are trained to correctly predict the preassigned labels of a set of examples).[35]
    ```

---

## 6. Delete a File

The code demonstrates how to delete a specific file from the vector store by providing both the store’s and file’s IDs. This operation removes the file and its embeddings, helping to manage and update your stored data.

```python
client.beta.vector_stores.files.delete(
    vector_store_id=vector_store.id,
    file_id=file_id
)
print(f"File {file_id} deleted from the vector store.")
```

??? note "Example Output"
    ```python
    File file_b43b19f7dbb04b649c196080 deleted from the vector store.
    ```

---

## 7. Query the Vector Store

An inference client is set up to perform semantic searches. A natural language query is issued to the vector store, which returns relevant text chunks along with metadata, allowing you to extract contextually pertinent information.

```python
client_config = ClientConfig(base_url=base_url, auth=CONFIG.auth)
inference_client = InferenceClient(client_config)

search_query = "Explain the difference between supervised and unsupervised learning."
vs_results = inference_client.query_vector_store(vector_store.id, search_query)
```

??? note "Example Output"
    ```python
    Your search query response from vector store: [{'file_id': 'file_278138cf53a245558766c31d', 'chunk_text': 'Data mining\nMachine learning and data mining often employ the same methods and overlap significantly, but while machine learning focuses on prediction, based on known properties learned from the training data, data mining focuses on the discovery of (previously) unknown properties in the data (this is the analysis step of knowledge discovery in databases). Data mining uses many machine learning methods, but with different goals; on the other hand, machine learning also employs data mining methods as "unsupervised learning" or as a preprocessing step to improve learner accuracy. Much of the confusion between these two research communities (which do often have separate conferences and separate journals, ECML PKDD being a major exception) comes from the basic assumptions they work with: in machine learning, performance is usually evaluated with respect to the ability to reproduce known knowledge, while in knowledge discovery and data mining (KDD) the key task is the discovery of previously unknown knowledge. Evaluated with respect to known knowledge, an uninformed (unsupervised) method will easily be outperformed by other supervised methods, while in a typical KDD task, supervised methods cannot be used due to the unavailability of training data.\n\nMachine learning also has intimate ties to optimization: Many learning problems are formulated as minimization of some loss function on a training set of examples. Loss functions express the discrepancy between the predictions of the model being trained and the actual problem instances (for example, in classification, one wants to assign a label to instances, and models are trained to correctly predict the preassigned labels of a set of examples).[35]', 'distance': 0.6951444615680473}]
    ```

---

## 8. Generate an LLM Response with Context

The retrieved text chunks are concatenated into a context string that is embedded into a system prompt. Combined with the user’s query, these messages are sent to the LLM API to generate a detailed, context-aware response.

```python
    context_text = vs_results

    system_prompt = (
        "You are an AI assistant specialized in Machine Learning. "
        "Use the following context to answer the user's question in detail. "
        "Do not mention the vector store directly."
        f'{context_text}'
    )

    user_message = {
        "role": "user",
        "content": search_query
    }

    messages = [
        {"role": "system", "content": system_prompt},
        user_message
    ]

    response = client.chat.completions.create(
        model="llama-v3p1-70b-instruct",
        messages=messages,
        max_tokens=1024
    )

    print("LLM Response:", response.choices[0].message.content)
```

??? note "Example Output"
    ```python
    LLM Response: Supervised and unsupervised learning are two fundamental concepts in machine learning that differ in their approach to training models on data.

    **Supervised Learning:**

    In supervised learning, the model is trained on labeled data, where the correct output is already known. The goal is to learn a mapping between the input data and the corresponding output labels, so the model can make accurate predictions on new, unseen data. The model is "supervised" in the sense that it is guided by the labeled data, which provides a clear target for the model to learn from.

    Here's an example:

    * You have a dataset of images of cats and dogs, and each image is labeled as either "cat" or "dog".
    * You train a supervised learning model on this dataset, and the model learns to recognize patterns in the images that distinguish cats from dogs.
    * Once trained, the model can be used to classify new, unseen images as either cats or dogs.

    **Unsupervised Learning:**

    In unsupervised learning, the model is trained on unlabeled data, and there is no clear target output. The goal is to discover patterns, relationships, or groupings within the data, without any prior knowledge of the expected output. The model is "unsupervised" in the sense that it is left to discover hidden structures or features in the data on its own.

    Here's an example:

    * You have a dataset of customer purchase history, and you want to identify clusters of customers with similar buying behavior.
    * You train an unsupervised learning model on this dataset, and the model identifies patterns in the data that correspond to different customer segments (e.g., frequent buyers, one-time buyers, etc.).

    **Key differences:**

    1. **Labeled vs. unlabeled data**: Supervised learning requires labeled data, while unsupervised learning uses unlabeled data.
    2. **Training objective**: Supervised learning aims to predict a target output, while unsupervised learning aims to discover hidden patterns or relationships in the data.
    3. **Model evaluation**: Supervised learning models are typically evaluated using metrics such as accuracy, precision, and recall, which measure the model's ability to predict the correct output. Unsupervised learning models are often evaluated using metrics such as cluster coherence, silhouette score, or Calinski-Harabasz index, which measure the quality of the discovered patterns or groupings.

    In summary, supervised learning is used when there is a clear target output, and the goal is to predict that output accurately. Unsupervised learning is used when there is no clear target output, and the goal is to discover hidden patterns or relationships in the data.
    ```

---

## Full Code Example for Creating and Querying a Vector Store

Copy and paste the complete code below to quickly set up your vector store and perform inference. By integrating vector store capabilities with LLM queries, you can build context-aware applications that leverage your custom data for precise and relevant AI responses.

<details>
<summary>Click to Expand – Full Code for Quick Setup</summary>
```python
    import json
    import openai
    import os
    import time
    from glob import glob

    from nearai.config import Config, load_config_file
    from nearai.shared.client_config import ClientConfig
    from nearai.shared.inference_client import InferenceClient

    # Import and Configure
    CONFIG = Config()
    config_data = load_config_file(local=False)
    CONFIG = CONFIG.update_with(config_data)
    if CONFIG.api_url is None:
        raise ValueError("CONFIG.api_url is None")
    base_url = CONFIG.api_url + "/v1"
    client = openai.OpenAI(base_url=base_url, api_key=json.dumps(config_data["auth"]))

    # Create a Vector Store
    vector_store = client.beta.vector_stores.create(name="My_Vector_Store")
    print(f"Vector store created: {vector_store.id}")


    # Upload and Attach a File
    # Replace "example_file.md" with your file path
    uploaded_file = client.files.create(
        file=open("dataset/data_mining.md", "rb"),
        purpose="assistants",
    )
    client.beta.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=uploaded_file.id,
    )
    print(f"File uploaded and attached: {uploaded_file.filename}")

    # Wait for Processing
    while True:
        status = client.beta.vector_stores.retrieve(vector_store.id)
        if status.file_counts.completed == 1:
            break
        time.sleep(1)
    print("File processed! The vector store is ready.")

    # Retrieve a File's Raw Content
    file_id = uploaded_file.id
    retrieved_content = client.files.content(file_id=file_id)
    raw_bytes = retrieved_content.read()
    file_text = raw_bytes.decode("utf-8")
    print("Retrieved file content:")
    print(file_text)

    # # Delete the File from the Vector Store
    # client.beta.vector_stores.files.delete(
    #     vector_store_id=vector_store.id,
    #     file_id=file_id
    # )
    # print(f"File {file_id} deleted from the vector store.")

    # Query the Vector Store
    client_config = ClientConfig(base_url=base_url, auth=CONFIG.auth)
    inference_client = InferenceClient(client_config)
    search_query = "what is data mining?"
    vs_results = inference_client.query_vector_store(vector_store.id, search_query)

    # Flatten the results if nested
    flattened_chunks = []
    for sublist in [vs_results]:
        flattened_chunks.extend(sublist)
    for idx, chunk in enumerate(flattened_chunks, start=1):
        print(f"\nChunk {idx}:")
        print(chunk.get("chunk_text", "No text available"))

    # Generate an LLM Response with Context
    context_text = "\n---\n".join(chunk["chunk_text"] for chunk in flattened_chunks)
    system_prompt = (
        "You are an AI assistant specialized in Machine Learning. "
        "Use the following context to answer the user's question in detail. "
        "Do not mention the vector store directly.\n\n"
        f"Context:\n{context_text}"
    )
    user_message = {"role": "user", "content": search_query}
    messages = [
        {"role": "system", "content": system_prompt},
        user_message
    ]
    response = client.chat.completions.create(
        model="llama-v3p1-70b-instruct",  # Replace with a your model of choice
        messages=messages,
        max_tokens=1024
    )
    print("LLM Response:")
    print(response.choices[0].message.content)
```

</details>



??? example "Output"
    Vector store created: vs_ee172363a14f4b41a9c5a254
    File uploaded and attached: data_mining.md
    File processed! The vector store is ready.
    Retrieved file content:
    Data mining
    Machine learning and data mining often employ the same methods and overlap significantly, but while machine learning focuses on prediction, based on known properties learned from the training data, data mining focuses on the discovery of (previously) unknown properties in the data (this is the analysis step of knowledge discovery in databases). Data mining uses many machine learning methods, but with different goals; on the other hand, machine learning also employs data mining methods as "unsupervised learning" or as a preprocessing step to improve learner accuracy. Much of the confusion between these two research communities (which do often have separate conferences and separate journals, ECML PKDD being a major exception) comes from the basic assumptions they work with: in machine learning, performance is usually evaluated with respect to the ability to reproduce known knowledge, while in knowledge discovery and data mining (KDD) the key task is the discovery of previously unknown knowledge. Evaluated with respect to known knowledge, an uninformed (unsupervised) method will easily be outperformed by other supervised methods, while in a typical KDD task, supervised methods cannot be used due to the unavailability of training data.

    Machine learning also has intimate ties to optimization: Many learning problems are formulated as minimization of some loss function on a training set of examples. Loss functions express the discrepancy between the predictions of the model being trained and the actual problem instances (for example, in classification, one wants to assign a label to instances, and models are trained to correctly predict the preassigned labels of a set of examples).[35]

    Chunk 1:
    Data mining
    Machine learning and data mining often employ the same methods and overlap significantly, but while machine learning focuses on prediction, based on known properties learned from the training data, data mining focuses on the discovery of (previously) unknown properties in the data (this is the analysis step of knowledge discovery in databases). Data mining uses many machine learning methods, but with different goals; on the other hand, machine learning also employs data mining methods as "unsupervised learning" or as a preprocessing step to improve learner accuracy. Much of the confusion between these two research communities (which do often have separate conferences and separate journals, ECML PKDD being a major exception) comes from the basic assumptions they work with: in machine learning, performance is usually evaluated with respect to the ability to reproduce known knowledge, while in knowledge discovery and data mining (KDD) the key task is the discovery of previously unknown knowledge. Evaluated with respect to known knowledge, an uninformed (unsupervised) method will easily be outperformed by other supervised methods, while in a typical KDD task, supervised methods cannot be used due to the unavailability of training data.

    Machine learning also has intimate ties to optimization: Many learning problems are formulated as minimization of some loss function on a training set of examples. Loss functions express the discrepancy between the predictions of the model being trained and the actual problem instances (for example, in classification, one wants to assign a label to instances, and models are trained to correctly predict the preassigned labels of a set of examples).[35]
    LLM Response:
    Data mining is a discipline that involves the automatic discovery of patterns, relationships, and insights from large datasets. It is a step in the knowledge discovery in databases (KDD) process, which aims to extract valuable knowledge or patterns from data.

    Data mining uses various techniques, including machine learning, statistics, and database systems, to analyze and extract insights from data. The goal of data mining is to identify previously unknown patterns, relationships, or trends in the data, which can help organizations make informed decisions, improve operations, or create new opportunities.

    Data mining involves several key steps:

    1. **Data collection**: Gathering data from various sources, such as databases, text files, or online sources.
    2. **Data cleaning and preprocessing**: Ensuring the quality and accuracy of the data by handling missing values, removing duplicates, and transforming data into a suitable format for analysis.
    3. **Data analysis**: Applying various techniques, such as clustering, decision trees, and regression analysis, to identify patterns and relationships in the data.
    4. **Pattern evaluation**: Assessing the discovered patterns and relationships to determine their validity, usefulness, and potential applications.
    5. **Knowledge representation**: Presenting the extracted insights in a meaningful and interpretable way, such as through visualizations, reports, or data visualizations.

    Data mining has numerous applications in business, healthcare, finance, marketing, and other fields, including:

    1. **Customer behavior analysis**: Identifying purchasing patterns, preferences, and demographics to improve customer segmentation and targeted marketing.
    2. **Fraud detection**: Discovering anomalies and unusual patterns in financial transactions to prevent fraudulent activities.
    3. **Predictive maintenance**: Analyzing sensor data and equipment logs to predict equipment failures and schedule maintenance.
    4. **Disease diagnosis**: Identifying patterns in patient data to improve diagnosis accuracy and personalized treatment.
    5. **Market analysis**: Analyzing market trends, customer preferences, and competitor data to inform business strategy.

    In summary, data mining is a powerful discipline that helps organizations uncover hidden insights and patterns in their data, enabling them to make data-driven decisions and drive business success.


### Next Steps

* Create chat completion for your AI agent using [inference (OpenAI)](../docs/inference.md)

<!-- ## Helpful links:

*  Load local files into the vector store: [vector store.py](https://github.com/nearai/nearai/tree/main/hub/examples/vector_store.py)
*  Load a GitHub repository into the vector store: [vector store from source.py](https://github.com/nearai/nearai/tree/main/hub/examples/vector_store_from_source.py)
*  Create this help document: [vector store build doc.py](https://github.com/nearai/nearai/tree/main/hub/examples/examples%2Fvector_store_build doc.py) -->
