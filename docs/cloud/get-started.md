# Get Started with NEAR AI Cloud

[NEAR AI Cloud](https://cloud.near.ai) offers developers access to private, verifiable AI models through a unified API. This guide will walk you through setting up your account, creating API keys, and making your first requests.

---

## Overview

NEAR AI Cloud provides:

- **Unified API for AI Models**: Access leading AI models like DeepSeek, Llama, OpenAI, Qwen and more through a single API
- **Private Inference**: All AI computations run in Trusted Execution Environments (TEEs) ensuring end-to-end privacy and verifiability
- **Flexible Payments**: Top up or pay as you go

---

## Quick Setup

1. Visit [NEAR AI Cloud](https://cloud.near.ai/), and connect your GitHub or Google account
2. Navigate to the **Credits** section in your dashboard, and purchase the amount of credits you need
3. Go to the **API Keys** section in your dashboard, and create a new API key.

!!! note "API Key Security"
    Keep your API key secure and never share it publicly. You can regenerate keys at any time from your dashboard.

---

## Making Your First Request

Let's chat with one open source model, with privacy protected. Please replace the API key with the one you have created.

=== "python"

    ```python
    import openai

    client = openai.OpenAI(
        base_url="https://cloud-api.near.ai/v1",
        api_key="your-api-key-here"
    )

    response = client.chat.completions.create(
        model="deepseek-chat-v3-0324",
        messages=[{
            "role": "user", "content": "Hello, how are you?"
        }]
    )

    print(response.choices[0].message.content)
    ```

=== "javascript"

    ```javascript
    import OpenAI from 'openai';

    const openai = new OpenAI({
        baseURL: 'https://cloud-api.near.ai/v1',
        apiKey: 'your-api-key-here',
    });

    const completion = await openai.chat.completions.create({
        model: 'deepseek-chat-v3-0324',
        messages: [{
            role: 'user', content: 'Hello, how are you?'
        }]
    });

    console.log(completion.choices[0].message.content);
    ```

=== "curl"

    ```bash
    curl https://cloud-api.near.ai/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-api-key-here" \
    -d '{
        "model": "deepseek-chat-v3-0324",
        "messages": [{
            "role": "user",
            "content": "Hello, how are you?"
        }]
    }'
    ```

---

## Available Models

NEAR AI Cloud now supports a few open source, private and verifiable models. We'll add more models soon.

You can find the model list from [https://cloud.near.ai/models](https://cloud.near.ai/models)

---

## Next Steps

Now that you're set up with NEAR AI Cloud, explore these resources:

- [:material-cog: Private Inference Deep Dive](./private-inference.md) - Learn about private inference
- [:material-check-decagram: Verification Guide](./verification.md) - Understand how to verify private AI responses
